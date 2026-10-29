"""Self-contained accessible offline report studio.

No third-party code, telemetry or external network access in exported HTML.
All model text is rendered using text nodes (never as executable HTML).
"""
from __future__ import annotations

import json
import hashlib
import base64
import re
from importlib.resources import files
from pathlib import Path


def render_dashboard(report: dict) -> str:
    if not isinstance(report, dict) or not {"mode", "task", "agents"}.issubset(report):
        raise ValueError("Expected ConsensusTree report object with mode, task, agents")
    if report["mode"] not in {"ask", "review", "demo"} or not isinstance(report["task"], str) or not isinstance(report["agents"], list):
        raise ValueError("Invalid ConsensusTree mode, task or agents")
    # Avoid inserting untrusted model text as HTML or as a closing script tag.
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = files("consensustree").joinpath("dashboard_template.html").read_text(encoding="utf-8")
    # Inline scripts/styles are pinned to immutable hashes. Avoid unsafe-inline
    # while keeping the exported dashboard fully self-contained and offline.
    css = re.search(r"<style>(.*?)</style>", template, re.DOTALL)
    js = re.search(r"<script>(.*?)</script>", template, re.DOTALL)
    if not css or not js:
        raise RuntimeError("Dashboard template missing expected static assets")
    def sha256(data: str) -> str:
        return "sha256-" + base64.b64encode(hashlib.sha256(data.encode("utf-8")).digest()).decode("ascii")
    return (template.replace("__SCRIPT_HASH__", sha256(js.group(1)))
                    .replace("__STYLE_HASH__", sha256(css.group(1)))
                    .replace("__REPORT_DATA__", payload))


def write_dashboard(report_path: str | Path, output: str | Path) -> None:
    source = Path(report_path).expanduser()
    if source.stat().st_size > 12_000_000:
        raise ValueError("Dashboard report exceeds 12 MB")
    report = json.loads(source.read_text(encoding="utf-8"))
    target = Path(output).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(report), encoding="utf-8")
