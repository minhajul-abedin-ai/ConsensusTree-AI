"""Private, local-only browser workbench for running ConsensusTree councils.

This intentionally is NOT a publicly deployable multi-user application. The
server binds to 127.0.0.1, validates Host, Origin and a CSRF/capability token,
restricts code reviews to one explicitly selected local root, and requires
explicit source-sharing consent. No provider credentials are served to browsers.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import threading
import urllib.parse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .core import Council
from .dashboard import render_dashboard
from .hierarchy import HierarchicalCouncil
from .metering import MeteredClient
from .privacy import secret_warnings
from .providers import DEFAULT_MODELS, KEY_VARS, LLMClient, ModelSpec, ProviderError
from .scanner import Snapshot, scan

def _local_ollama_url() -> str:
    """Only allow a local inference endpoint in the browser Studio."""
    url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or
        parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or
        parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Studio requires a loopback OLLAMA_BASE_URL (localhost or 127.0.0.1)")
    try:
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError("Invalid local Ollama port") from None
    return url


MAX_BODY = 36_000
MAX_JOBS = 8
_ALLOWED_MODELS = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,110}$")


@dataclass
class Job:
    status: str = "running"
    events: list[str] = field(default_factory=list)
    report: dict | None = None
    error: str | None = None
    created_utc: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))

    def view(self) -> dict:
        return {"status": self.status, "events": self.events[-20:],
                "report": self.report, "error": self.error,
                "created_utc": self.created_utc}


class StudioState:
    def __init__(self, root: Path, *, client_factory: Callable[[int], Any] | None = None):
        root = root.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Studio root must be a directory")
        self.root = root
        self.token = secrets.token_urlsafe(32)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.RLock()
        self.client_factory = client_factory or (lambda max_calls: MeteredClient(
            LLMClient(timeout=60, ollama_url=_local_ollama_url()), max_calls))

    def resolve_target(self, relative: str) -> Path:
        if not isinstance(relative, str) or len(relative) > 500:
            raise ValueError("Invalid relative review path")
        candidate = (self.root / relative).resolve(strict=True)
        if not candidate.is_relative_to(self.root):
            raise ValueError("Review path must stay inside the selected project root")
        if not (candidate.is_file() or candidate.is_dir()):
            raise ValueError("Review target must be a file or directory")
        return candidate

    def snapshot(self, relative: str) -> Snapshot:
        return scan(self.resolve_target(relative), max_files=20, max_chars=24_000, smart=True)

    @staticmethod
    def fingerprint(snapshot: Snapshot) -> str:
        # Consent covers both the *location* and the excerpt.  Two distinct
        # folders can contain identically named, identical files; hashing the
        # excerpt alone would allow a preview for A to authorize a run on B.
        data = os.fsencode(snapshot.root) + b"\0" + snapshot.text.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def preview(self, relative: str) -> dict:
        snap = self.snapshot(relative)
        return {"files": snap.files, "file_count": len(snap.files), "eligible_files": snap.eligible_files,
                "omitted_files": snap.omitted_files, "characters": len(snap.text),
                "source_excerpt": snap.text, "truncated": snap.truncated, "fingerprint": self.fingerprint(snap),
                "warnings": secret_warnings(snap.text),
                "notice": "Only selected excerpts are sent to the provider after you explicitly consent. Review local code for sensitive data first."}

    def start(self, payload: dict) -> str:
        allowed = {"mode", "consent", "provider", "model", "strategy", "groups", "path", "question", "fingerprint", "reviewers"}
        if set(payload) - allowed:
            raise ValueError("Unsupported session configuration fields")
        mode = payload.get("mode")
        if mode not in {"review", "ask"}:
            raise ValueError("Select review or ask mode")
        if payload.get("consent") is not True:
            raise ValueError("Confirm that you understand selected content will be sent to the model provider")
        provider = payload.get("provider", "ollama")
        if not isinstance(provider, str) or provider not in DEFAULT_MODELS:
            raise ValueError("Unknown model provider")
        model = payload.get("model") or DEFAULT_MODELS[provider]
        if not isinstance(model, str) or not _ALLOWED_MODELS.fullmatch(model) or any(part in {".", ".."} for part in model.split("/")):
            raise ValueError("Invalid model name")
        strategy = payload.get("strategy", "basic")
        if strategy not in {"basic", "hierarchical"}:
            raise ValueError("Unknown council strategy")
        groups = payload.get("groups", 2)
        if not isinstance(groups, int) or isinstance(groups, bool) or groups not in (1, 2):
            raise ValueError("Groups must be 1 or 2")
        relative = payload.get("path", ".")
        question = payload.get("question", "")
        snapshot = None
        if mode == "review":
            snapshot = self.snapshot(relative)
            expected_hash = payload.get("fingerprint")
            if not isinstance(expected_hash, str) or not secrets.compare_digest(expected_hash, self.fingerprint(snapshot)):
                raise ValueError("Source changed since preview. Preview the files again before running.")
            warnings = secret_warnings(snapshot.text)
            if warnings:
                raise ValueError("Possible secrets detected. Review or remove sensitive content before starting an AI review.")
        else:
            if not isinstance(question, str) or not question.strip() or len(question) > 25_000:
                raise ValueError("Question must have 1–25,000 characters")
            if secret_warnings(question):
                raise ValueError("Possible credentials found in question. Remove sensitive data before making a provider request.")
        if provider in KEY_VARS and "reviewers" not in payload:
            if not os.environ.get(KEY_VARS[provider], "").strip():
                raise ValueError(f"Set the {KEY_VARS[provider]} environment variable before running this model")
        reviewer_specs = None
        if "reviewers" in payload:
            raw_reviewers = payload["reviewers"]
            if not isinstance(raw_reviewers, list) or len(raw_reviewers) != 3:
                raise ValueError("Specify exactly three reviewer model configurations")
            reviewer_specs = []
            for item in raw_reviewers:
                if not isinstance(item, dict) or set(item) != {"provider", "model"}:
                    raise ValueError("Each reviewer must have provider and model")
                selected_provider, selected_model = item["provider"], item["model"]
                if not isinstance(selected_provider, str) or selected_provider not in DEFAULT_MODELS or not isinstance(selected_model, str) or not _ALLOWED_MODELS.fullmatch(selected_model) or any(part in {".", ".."} for part in selected_model.split("/")):
                    raise ValueError("Invalid reviewer provider/model")
                if selected_provider in KEY_VARS and not os.environ.get(KEY_VARS[selected_provider], "").strip():
                    raise ValueError(f"Set {KEY_VARS[selected_provider]} before using this reviewer")
                reviewer_specs.append(ModelSpec(selected_provider, selected_model))
        max_calls = 4 if strategy == "basic" else (4 * groups + 1)
        with self.lock:
            if any(j.status == "running" for j in self.jobs.values()):
                raise RuntimeError("A review is already running. Finish it before starting another.")
            while len(self.jobs) >= MAX_JOBS:
                oldest = next(iter(self.jobs))
                del self.jobs[oldest]
            job_id = secrets.token_urlsafe(12)
            self.jobs[job_id] = Job(events=["Council accepted. Preparing independent reviewers…"])
        thread = threading.Thread(
            target=self._execute, args=(job_id, mode, question, snapshot, strategy, groups, provider, model, max_calls, reviewer_specs),
            daemon=True, name="consensustree-review")
        thread.start()
        return job_id

    def _execute(self, job_id: str, mode: str, question: str, snapshot: Snapshot | None,
                 strategy: str, groups: int, provider: str, model: str, max_calls: int,
                 reviewer_specs: list[ModelSpec] | None = None) -> None:
        def notify(message: str) -> None:
            with self.lock:
                self.jobs[job_id].events.append(message[:300])
        try:
            client = self.client_factory(max_calls)
            models = reviewer_specs or [ModelSpec(provider, model)] * 3
            if strategy == "hierarchical":
                council = HierarchicalCouncil(models, client=client, groups=groups, max_calls=max_calls)
            else:
                council = Council(models, client=client, on_event=notify)
            report = council.review_snapshot(snapshot) if snapshot is not None else council.ask(question)
            if hasattr(client, "usage"):
                report.execution["metering"] = client.usage()
            report.execution["source"] = "local-studio"
            # No claims about factual verification or tests performed.
            with self.lock:
                job = self.jobs[job_id]
                job.report = report.to_dict()
                job.status = "completed"
                gate = report.execution.get("completion", {})
                if gate.get("status") == "partial":
                    job.events.append("PARTIAL COUNCIL: One or more planned steps failed. Do not treat this as complete consensus.")
                else:
                    job.events.append("Completed. Treat all AI findings as unverified until independently checked.")
        except Exception as exc:
            # Do not return exception details, environment values, or tokens to a browser.
            with self.lock:
                job = self.jobs[job_id]
                job.status = "failed"
                job.error = (str(exc)[:500] if isinstance(exc, (ProviderError, ValueError)) else
                             "The review could not complete. Check the local terminal for provider configuration and availability.")
                job.events.append("Model execution failed.")
            import logging
            logging.getLogger("consensustree.studio").warning("Review job failed (%s)", type(exc).__name__)


def _studio_template() -> str:
    template = files("consensustree").joinpath("studio_template.html").read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", template, re.DOTALL)
    script = re.search(r"<script>(.*?)</script>", template, re.DOTALL)
    if not css or not script:
        raise RuntimeError("Studio template missing static assets")
    def digest(text: str) -> str:
        return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")
    return template.replace("__STYLE_HASH__", digest(css.group(1))).replace("__SCRIPT_HASH__", digest(script.group(1)))


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_server(root: str | Path, port: int = 8765, *, client_factory=None) -> StudioServer:
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Port must be 0..65535")
    if client_factory is None:
        _local_ollama_url()  # Fail fast on remote/insecure provider endpoints.
    state = StudioState(Path(root), client_factory=client_factory)
    page = _studio_template().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        server_version = f"ConsensusTreeStudio/{__version__}"
        sys_version = ""
        def setup(self):
            super().setup()
            # Avoid unbounded idle/slow-body connections on the local Studio.
            self.connection.settimeout(15)

        def log_message(self, format, *args):
            # Do not log capability-token URLs or sensitive query strings.
            return

        def _same_host(self) -> bool:
            return self.headers.get("Host", "") in {
                f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            return not origin or origin in {f"http://127.0.0.1:{self.server.server_port}",
                                            f"http://localhost:{self.server.server_port}"}

        def _authorized(self, path: str) -> bool:
            params = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
            given = self.headers.get("X-CT-Token", "") or params.get("token", [""])[0]
            return bool(given) and secrets.compare_digest(given, state.token)

        def _send(self, code: int, content: bytes, *, kind="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            if kind.startswith("text/html"):
                self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(content)

        def _json(self, code: int, value: dict):
            self._send(code, json.dumps(value, ensure_ascii=False).encode("utf-8"))

        def _guard(self) -> bool:
            if not self._same_host() or not self._origin_ok() or not self._authorized(self.path):
                self._json(403, {"error": "Access denied"})
                return False
            return True

        def do_GET(self):
            if not self._guard():
                return
            path = urllib.parse.urlsplit(self.path).path
            if path == "/":
                self._send(200, page, kind="text/html; charset=utf-8")
            elif path == "/api/status":
                self._json(200, {"root": str(state.root), "providers": DEFAULT_MODELS,
                                 "configured": _configured_keys(), "version": __version__,
                                 "local_only": True})
            elif path.startswith("/api/jobs/"):
                job_id = path.split("/")[-1]
                with state.lock:
                    job = state.jobs.get(job_id)
                    value = job.view() if job else None
                if value is None:
                    self._json(404, {"error": "Unknown job"})
                else:
                    self._json(200, value)
            elif path.startswith("/api/dashboard/"):
                job_id = path.split("/")[-1]
                with state.lock:
                    job = state.jobs.get(job_id)
                    report = job.report if job else None
                if report is None:
                    self._json(404, {"error": "No completed report"})
                else:
                    html = render_dashboard(report).encode("utf-8")
                    # The offline dashboard enforces a stricter CSP via a meta tag.
                    self._send(200, html, kind="text/html; charset=utf-8")
            else:
                self._json(404, {"error": "Not found"})

        def do_POST(self):
            if not self._guard():
                return
            path = urllib.parse.urlsplit(self.path).path
            if path not in {"/api/preview", "/api/run", "/api/demo"}:
                self._json(404, {"error": "Not found"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self._json(415, {"error": "Use application/json"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    self._json(413, {"error": "Request body exceeds limit or is empty"})
                    return
                raw = self.rfile.read(length)
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError("Expected JSON object")
                if path == "/api/preview":
                    self._json(200, state.preview(body.get("path", ".")))
                elif path == "/api/demo":
                    from .cli import _demo
                    self._json(200, {"report": _demo().to_dict(), "notice": "Fictional offline demo; no AI calls were made."})
                else:
                    job_id = state.start(body)
                    self._json(202, {"job_id": job_id, "status": "running"})
            except (ValueError, OSError, KeyError) as exc:
                self._json(400, {"error": str(exc)[:350]})
            except RuntimeError as exc:
                self._json(409, {"error": str(exc)[:350]})
            except Exception:
                self._json(500, {"error": "Unexpected local server error"})

    def _configured_keys() -> dict[str, bool]:
        import os
        return {p: bool(os.environ.get(env)) for p, env in KEY_VARS.items()}

    server = StudioServer(("127.0.0.1", port), Handler)
    server.studio_token = state.token
    return server


def serve(root: str | Path = ".", port: int = 8765, *, open_browser: bool = False) -> None:
    with create_server(root, port) as server:
        address = f"http://127.0.0.1:{server.server_port}/?token={server.studio_token}"
        print("ConsensusTree AI — LOCAL ONLY browser studio")
        print("Do not share this private URL. It grants access to your local workspace.")
        print(address, flush=True)
        if open_browser:
            import webbrowser
            webbrowser.open(address)
        try:
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:
            print("\nStudio stopped.")
        finally:
            server.shutdown()
