"""Opt-in GitHub Actions PR reviewer (runs trusted base code; never executes PR code)."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from .core import Council
from .gitdiff import diff_snapshot
from .github import upsert_bot_pr_comment
from .metering import MeteredClient
from .providers import DEFAULT_MODELS, KEY_VARS, LLMClient, ModelSpec
from .report import write_report

_SHA = re.compile(r"[0-9a-f]{40}")


def parse_pr_event(event: dict, *, expected_repo: str) -> tuple[str, int, str, str]:
    """Reject forks, mismatched repository identity and ambiguous SHA refs."""
    pr = event.get("pull_request")
    repo = event.get("repository", {}).get("full_name")
    if not isinstance(pr, dict) or not isinstance(repo, str) or repo != expected_repo:
        raise ValueError("Unexpected GitHub repository/event")
    base = pr.get("base", {})
    head = pr.get("head", {})
    if (base.get("repo") or {}).get("full_name") != repo or (head.get("repo") or {}).get("full_name") != repo:
        raise ValueError("Fork pull requests cannot use this credentialed workflow")
    number = pr.get("number")
    if type(number) is not int or not 1 <= number <= 2_147_483_647:
        raise ValueError("Invalid pull request number")
    base_sha, head_sha = base.get("sha"), head.get("sha")
    if not isinstance(base_sha, str) or not _SHA.fullmatch(base_sha):
        raise ValueError("Invalid base SHA")
    if not isinstance(head_sha, str) or not _SHA.fullmatch(head_sha):
        raise ValueError("Invalid head SHA")
    return repo, number, base_sha, head_sha


def run_github_pr_review(*, env: dict | None = None, client=None, post=None) -> dict:
    env = dict(os.environ if env is None else env)
    if env.get("CONSENSUSTREE_AUTO_REVIEW") != "true":
        return {"status": "skipped", "reason": "Explicit repository opt-in missing"}
    if env.get("GITHUB_EVENT_NAME") != "pull_request_target":
        raise ValueError("Credentialed GitHub PR automation requires the trusted pull_request_target event")
    event_file = Path(env.get("GITHUB_EVENT_PATH", ""))
    if not event_file.is_file() or event_file.stat().st_size > 500_000:
        raise ValueError("Missing or oversized event payload")
    event = json.loads(event_file.read_text(encoding="utf-8"))
    repo, number, base, head = parse_pr_event(event, expected_repo=env.get("GITHUB_REPOSITORY", ""))
    root = Path(env.get("GITHUB_WORKSPACE", "")).resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise ValueError("Expected Git checkout workspace")
    provider = env.get("CONSENSUSTREE_PROVIDER", "openai")
    model = env.get("CONSENSUSTREE_MODEL") or DEFAULT_MODELS.get(provider)
    spec = ModelSpec(provider, model)
    if provider in KEY_VARS and not env.get(KEY_VARS[provider], "") and client is None:
        raise ValueError("AI provider credential not configured")
    if not env.get("GITHUB_TOKEN") and post is None:
        raise ValueError("GitHub token not configured")
    # No untrusted project code executed: git diff reads bytes only.
    # The trusted workflow checks out base.sha and fetches head only as Git objects.
    # Refuse to proceed if the working tree is not the expected trusted base.
    import subprocess
    checkout = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=10, check=False)
    if checkout.returncode or checkout.stdout.decode("ascii", "replace").strip() != base:
        raise ValueError("Checkout does not match the trusted PR base SHA")
    snapshot = diff_snapshot(root, base=base, head=head, max_files=30, max_chars=48_000)
    reviewer = Council([spec] * 3, client=MeteredClient(client or LLMClient(timeout=45), max_calls=4))
    report = reviewer.review_snapshot(snapshot)
    if report.errors or report.execution.get("completion", {}).get("status") != "complete":
        return {"status": "partial", "posted": False, "failures": len(report.errors)}
    with tempfile.TemporaryDirectory(prefix="ct-pr-") as temporary:
        report_file = Path(temporary) / "report.md"
        write_report(report, str(report_file), None)
        poster = post or upsert_bot_pr_comment
        outcome = poster(repo, number, report_file, token=env.get("GITHUB_TOKEN", ""))
    return {"status": "reviewed", "files": len(snapshot.files),
            "truncated": snapshot.truncated, "posted": bool(outcome.get("posted")),
            "action": outcome.get("action", "unknown")}


def main() -> int:
    try:
        result = run_github_pr_review()
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in {"reviewed", "skipped"} else 2
    except Exception as exc:
        # Never print arbitrary exception values from provider transport.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
