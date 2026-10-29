"""Command-line user interface."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from typing import Sequence

from . import __version__
from .core import AgentResult, Council, CouncilReport
from .providers import DEFAULT_MODELS, KEY_VARS, LLMClient, ModelSpec, ProviderError
from .report import write_report
from .scanner import scan
from .gitdiff import diff_snapshot
from .verification import run_unittest, write_evidence, load_evidence
from .hierarchy import HierarchicalCouncil, adaptive_group_count
from .metering import MeteredClient, load_pricing
from .dashboard import write_dashboard
from .plugins import available_plugins, load_client_plugin
from .privacy import secret_warnings, privacy_preflight
from .github import pr_comment
from .benchmark import evaluate_suite
import json
import platform
import shutil
from pathlib import Path


def _add_model_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("models and execution")
    group.add_argument("--plugin", help="Explicitly load an installed third-party client plugin")
    group.add_argument("--provider", choices=list(DEFAULT_MODELS), default="openai",
                       help="Provider for all 3 roles (default: openai)")
    group.add_argument("--model", help="Override the default model for --provider")
    group.add_argument("--models", help="Comma-separated provider:model per role (1-3), e.g. openai:gpt-4.1-mini,gemini:gemini-2.5-flash,anthropic:claude-sonnet-4-5")
    group.add_argument("--no-synthesis", action="store_true", help="Skip the extra chair model call")
    group.add_argument("--pricing-file", help="JSON with your own USD rates per million tokens (estimate only)")
    group.add_argument("--max-requests", type=int, default=4,
                       help="Max requests for a basic council; hierarchy uses --max-calls")
    group.add_argument("--timeout", type=float, default=120, help="HTTP timeout in seconds (default: 120)")
    group.add_argument("--ollama-url", default=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                       help="Ollama server URL (default: http://localhost:11434)")
    group.add_argument("--output", default="consensustree-report.md", help="Write Markdown report here")
    group.add_argument("--json", dest="json_output", help="Also write a JSON report to this path")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="consensustree", description="Multi-agent AI council: code reviews and decisions"
    )
    parser.add_argument("--version", action="version", version=f"ConsensusTree AI {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    review = sub.add_parser("review", help="Review code files with independent AI specialists")
    review.add_argument("path", help="Source file or project directory")
    review.add_argument("--evidence", help="Attach prior verify-command JSON (untrusted metadata)")
    review.add_argument("--allow-sensitive", action="store_true",
                        help="Override best-effort credential warning (may expose secrets)")
    review.add_argument("--dry-run", action="store_true", help="List files without making any API calls")
    review.add_argument("--smart-context", action="store_true", help="Prioritize changed files, nearby dependencies and tests")
    review.add_argument("--focus", default="", help="Keywords to prioritize with --smart-context")
    review.add_argument("--max-files", type=int, default=20)
    review.add_argument("--max-chars", type=int, default=24_000)
    review.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="Exclude files/paths matching glob (repeatable)")
    _add_model_options(review)
    pr = sub.add_parser("pr-review", help="Review an offline Git diff between revisions")
    pr.add_argument("path", help="Local Git repository")
    pr.add_argument("--base", default="HEAD~1")
    pr.add_argument("--head", default="HEAD")
    pr.add_argument("--evidence", help="Attach prior verify-command JSON")
    pr.add_argument("--allow-sensitive", action="store_true")
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--max-files", type=int, default=20)
    pr.add_argument("--max-chars", type=int, default=24000)
    _add_model_options(pr)
    debate = sub.add_parser("debate", help="Hierarchical multi-agent debate over a question or code snapshot")
    debate.add_argument("question", nargs="?", default=None)
    debate.add_argument("--review-path", help="Review code instead of a question")
    debate.add_argument("--groups", type=int, default=2)
    debate.add_argument("--adaptive", action="store_true", help="Use a transparent complexity heuristic for groups")
    debate.add_argument("--max-calls", type=int, default=15)
    debate.add_argument("--evidence", help="Attach prior verify-command JSON")
    debate.add_argument("--allow-sensitive", action="store_true")
    debate.add_argument("--dry-run", action="store_true")
    _add_model_options(debate)
    verify = sub.add_parser("verify", help="Opt-in execution of Python unittest in a trusted repository")
    verify.add_argument("path", help="Local repository")
    verify.add_argument("--unsafe-execute", action="store_true", help="I authorize executing local test code")
    verify.add_argument("--timeout", type=int, default=45)
    verify.add_argument("--output", default="consensustree-test-evidence.json")
    ask = sub.add_parser("ask", help="Ask independent agents to assess a decision")
    ask.add_argument("question", help="Question in quotes")
    ask.add_argument("--allow-sensitive", action="store_true",
                     help="Explicitly override privacy preflight after reviewing the question")
    _add_model_options(ask)
    demo = sub.add_parser("demo", help="Produce a clearly labeled OFFLINE demo report; no model calls")
    demo.add_argument("--output", default="consensustree-demo.md")
    demo.add_argument("--json", dest="json_output")
    dashboard = sub.add_parser("dashboard", help="Convert a JSON report to offline interactive HTML")
    dashboard.add_argument("report", help="JSON report generated with --json")
    dashboard.add_argument("--output", default="consensustree-dashboard.html")
    plugins = sub.add_parser("plugins", help="List installed provider client plugins without loading code")
    plugins.add_argument("action", choices=["list"])
    github = sub.add_parser("github-comment", help="Preview or explicitly post a PR comment")
    github.add_argument("--repo", required=True, help="owner/repo")
    github.add_argument("--pr", type=int, required=True)
    github.add_argument("--report", required=True)
    github.add_argument("--confirm", action="store_true", help="Post review to GitHub (requires GITHUB_TOKEN)")
    bench = sub.add_parser("benchmark", help="Score saved reports using labeled phrase checks")
    bench.add_argument("--suite", required=True)
    bench.add_argument("--reports", required=True)
    bench.add_argument("--output", default="consensustree-benchmark.json")
    doctor = sub.add_parser("doctor", help="Inspect local runtime and whether provider keys are configured")
    doctor.add_argument("--json", action="store_true", dest="json_format")
    quick = sub.add_parser("quickstart", help="Generate offline sample Markdown, JSON and HTML in one command")
    quick.add_argument("--dir", default="consensustree-quickstart", help="Local output directory")
    studio = sub.add_parser("studio", help="Run the LOCAL-ONLY interactive browser workbench")
    studio.add_argument("--root", default=".", help="Directory permitted for local code reviews")
    studio.add_argument("--port", type=int, default=8765, help="Loopback port (default 8765)")
    studio.add_argument("--open", action="store_true", help="Open browser automatically")
    return parser


def _get_models(args: argparse.Namespace) -> list[ModelSpec]:
    if args.models:
        if args.model:
            raise ValueError("Use either --models or --model, not both")
        entries = [s.strip() for s in args.models.split(",")]
        if not (1 <= len(entries) <= 3):
            raise ValueError("--models supports 1 to 3 provider:model entries")
        return [ModelSpec.parse(entry) for entry in entries]
    model = args.model or DEFAULT_MODELS[args.provider]
    return [ModelSpec(args.provider, model)] * 3


def _demo() -> CouncilReport:
    """Fixed, labeled fixture. Not a simulated claim of a live review."""
    created = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return CouncilReport(
        mode="demo", task="Illustrative decision: Should a startup deploy a new AI feature?",
        created_utc=created, demo=True,
        agents=[
            AgentResult("Pragmatist", "illustrative-fixture", "**Recommendation:** Build a small pilot.\n\n**Reasoning:** Control budget and define measurable outcomes.", 0),
            AgentResult("Skeptic", "illustrative-fixture", "**Risks:** Unclear user demand, model costs, unreliable outputs.", 0),
            AgentResult("Strategist", "illustrative-fixture", "**Recommendation:** Evaluate against existing workflows and track retention.", 0),
        ],
        chair_model="illustrative-fixture",
        synthesis="**Final recommendation:** Run a limited pilot first.\n\n**Areas of agreement:** All three favor evidence before scaling.\n\n**Disagreements / uncertainties:** ROI remains unverified.\n\n**Priority next steps:** Define metrics, deploy a pilot, evaluate.\n\n**Verification required:** Real user research and cost data.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "studio":
            from .studio import serve
            serve(args.root, args.port, open_browser=args.open)
            return 0
        if args.command == "doctor":
            from . import __version__
            info = {"version": __version__, "python": platform.python_version(),
                    "git_available": bool(shutil.which("git")),
                    "api_key_configured": {k: bool(os.environ.get(v)) for k,v in KEY_VARS.items()},
                    "local_ollama_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "note": "No API or network requests made; key values are never printed."}
            if args.json_format:
                print(json.dumps(info, indent=2))
            else:
                print(f"ConsensusTree {info['version']} | Python {info['python']} | Git: {info['git_available']}")
                for k, available in info["api_key_configured"].items():
                    print(f"  {k}: {'configured' if available else 'not configured'}")
            return 0
        if args.command == "quickstart":
            from .dashboard import render_dashboard
            from .report import to_markdown
            dest = Path(args.dir).expanduser()
            dest.mkdir(parents=True, exist_ok=True)
            report = _demo()
            (dest / "sample.md").write_text(to_markdown(report), encoding="utf-8")
            (dest / "sample.json").write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
            (dest / "sample.html").write_text(render_dashboard(report.to_dict()), encoding="utf-8")
            print(f"OFFLINE DEMO ONLY: {dest / 'sample.html'}")
            return 0
        if args.command == "plugins":
            print(json.dumps(available_plugins(), indent=2))
            return 0
        if args.command == "github-comment":
            print(json.dumps(pr_comment(args.repo, args.pr, args.report, confirm=args.confirm), indent=2))
            return 0
        if args.command == "benchmark":
            result = evaluate_suite(args.suite, args.reports)
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"Benchmark report saved: {args.output} (phrase coverage, not accuracy)")
            return 0
        if args.command == "dashboard":
            write_dashboard(args.report, args.output)
            print(f"Offline dashboard saved: {args.output}")
            return 0
        if args.command == "verify":
            evidence = run_unittest(args.path, consent=args.unsafe_execute, timeout=args.timeout)
            write_evidence(evidence, args.output)
            print(f"Test evidence saved: {args.output}")
            return 0 if evidence["passed"] else 2
        if args.command == "demo":
            report = _demo()
        else:
            models = _get_models(args)
            if args.timeout <= 0 or args.timeout > 600:
                raise ValueError("--timeout must be between 0 and 600 seconds")
            # Preflight before loading optional third-party plugin code or creating
            # the provider transport; failed privacy checks make zero API calls.
            if args.command == "ask":
                privacy_preflight(args.question, allow_sensitive=args.allow_sensitive)
            elif args.command == "debate" and not args.review_path and not args.dry_run:
                privacy_preflight(args.question or "", allow_sensitive=args.allow_sensitive)
            underlying_client = (load_client_plugin(args.plugin) if args.plugin else
                                 LLMClient(timeout=args.timeout, ollama_url=args.ollama_url))
            prices = load_pricing(args.pricing_file) if args.pricing_file else None
            metered = MeteredClient(underlying_client,
                                    max_calls=args.max_calls if args.command == "debate" else args.max_requests,
                                    pricing=prices)
            if args.command == "debate":
                if args.no_synthesis:
                    raise ValueError("--no-synthesis is not available for hierarchical debate")
                if args.adaptive and args.groups != 2:
                    raise ValueError("Use --adaptive or --groups, not both")
                if args.review_path:
                    snapshot = scan(args.review_path)
                    content = snapshot.text
                    print(f"Debate snapshot: {len(snapshot.files)} files", file=sys.stderr)
                    for filename in snapshot.files:
                        print(f"  {filename}", file=sys.stderr)
                    if snapshot.truncated:
                        print("WARNING: Source snapshot truncated.", file=sys.stderr)
                else:
                    snapshot = None
                    if not args.question:
                        raise ValueError("Pass a question or --review-path")
                    content = args.question
                warnings = secret_warnings(content)
                if warnings:
                    print("WARNING: possible sensitive data categories: " + ", ".join(warnings), file=sys.stderr)
                    if not args.dry_run:
                        privacy_preflight(content, allow_sensitive=args.allow_sensitive)
                count = adaptive_group_count(content) if args.adaptive else args.groups
                planned = 4 * count + 1
                if args.dry_run:
                    print(f"DRY RUN: {count} groups, {planned} planned model calls; no API calls.")
                    return 0
                missing = sorted({KEY_VARS[m.provider] for m in models if m.provider in KEY_VARS and not os.getenv(KEY_VARS[m.provider], "").strip()}) if not args.plugin else []
                if missing:
                    raise ValueError("Missing API keys: " + ", ".join(missing))
                council = HierarchicalCouncil(models, client=metered, groups=count, max_calls=args.max_calls,
                                              allow_sensitive=args.allow_sensitive)
                report = council.review_snapshot(snapshot) if snapshot else council.ask(args.question)
            elif args.command in ("review", "pr-review"):
                if args.command == "pr-review":
                    snapshot = diff_snapshot(args.path, base=args.base, head=args.head,
                                             max_files=args.max_files, max_chars=args.max_chars)
                else:
                    snapshot = scan(args.path, max_files=args.max_files, max_chars=args.max_chars,
                                    exclude=args.exclude, smart=args.smart_context, focus=args.focus)
                print(f"Source snapshot: {len(snapshot.files)} files, {len(snapshot.text):,} characters", file=sys.stderr)
                for f in snapshot.files:
                    print(f"  {f}", file=sys.stderr)
                if snapshot.truncated:
                    print(f"WARNING: Bounded review. {len(snapshot.files)} of {snapshot.eligible_files} eligible files selected, {snapshot.omitted_files} omitted.", file=sys.stderr)
                warnings = secret_warnings(snapshot.text)
                if warnings:
                    print("WARNING: possible sensitive data categories: " + ", ".join(warnings), file=sys.stderr)
                if args.dry_run:
                    print("DRY RUN: no source code sent to any provider.", file=sys.stderr)
                    return 0
                if warnings and not args.allow_sensitive:
                    raise ValueError("Sensitive patterns detected. Review locally before using --allow-sensitive.")
                missing = sorted({KEY_VARS[m.provider] for m in models if m.provider in KEY_VARS and not os.getenv(KEY_VARS[m.provider], "").strip()}) if not args.plugin else []
                if missing:
                    raise ValueError("Missing API key environment variable(s): " + ", ".join(missing))
                print("NOTICE: Listed source content will be passed to the selected provider/client plugin.", file=sys.stderr)
                council = Council(models, client=metered, allow_sensitive=args.allow_sensitive,
                                  synthesize=not args.no_synthesis, on_event=lambda s: print(s, file=sys.stderr))
                report = council.review_snapshot(snapshot)
            else:
                missing = sorted({KEY_VARS[m.provider] for m in models if m.provider in KEY_VARS and not os.getenv(KEY_VARS[m.provider], "").strip()}) if not args.plugin else []
                if missing:
                    raise ValueError("Missing API key environment variable(s): " + ", ".join(missing))
                privacy_preflight(args.question, allow_sensitive=args.allow_sensitive)
                council = Council(models, client=metered, allow_sensitive=args.allow_sensitive,
                                  synthesize=not args.no_synthesis, on_event=lambda s: print(s, file=sys.stderr))
                report = council.ask(args.question)
        if args.command != "demo":
            report.execution["metering"] = metered.usage()
            if args.command in ("review", "pr-review", "debate") and args.evidence:
                report.evidence = load_evidence(args.evidence)
        write_report(report, args.output, args.json_output)
        print(f"Report saved: {args.output}")
        if args.json_output:
            print(f"JSON saved: {args.json_output}")
        if report.errors:
            print(f"WARNING: {len(report.errors)} step(s) failed; report is partial.", file=sys.stderr)
            return 2
        return 0
    except (ValueError, ProviderError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
