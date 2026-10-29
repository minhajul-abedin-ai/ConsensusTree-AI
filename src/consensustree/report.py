"""Safe-ish Markdown output (AI output still needs human review)."""
from __future__ import annotations

import json
from pathlib import Path

from .core import CouncilReport


def to_markdown(report: CouncilReport) -> str:
    title = {"ask": "Decision council", "review": "Code review council", "demo": "Demonstration"}[report.mode]
    out = [f"# ConsensusTree AI — {title}", "",
           f"**Generated (UTC):** {report.created_utc}",
           f"**Task:** {report.task.replace(chr(10), ' ')}", ""]
    if report.demo:
        out += ["> **DEMO ONLY:** These are fixed illustrative outputs, not live model analysis.", ""]
    if report.reviewed_files:
        out += [f"**Files provided:** {len(report.reviewed_files)}", "",
                "<details><summary>Source files in this review</summary>", ""]
        out += [f"- `{p}`" for p in report.reviewed_files]
        out += ["", "</details>", ""]
    if report.snapshot_truncated:
        out += ["> **Partial snapshot:** File-count or size limits excluded some content.", ""]
    completion = report.execution.get("completion") if report.execution else None
    if completion:
        label = completion["status"].upper()
        out += [f"**Council execution:** {label} "
                f"({completion['successful_specialists']}/{completion['expected_specialists']} specialists)", ""]
        if completion["status"] != "complete":
            out += ["> **INCOMPLETE COUNCIL:** Some planned steps failed. Do not interpret this report as full consensus.", ""]
    if report.synthesis:
        out += ["## Council synthesis", "", f"*Chair: `{report.chair_model}`*", "",
                report.synthesis, ""]
    else:
        out += ["## Council synthesis", "", "Not available. Read the individual reports below.", ""]
    if report.evidence:
        item = report.evidence
        out += ["## Imported test evidence (not independently authenticated)", "",
                f"**Tool:** {item.get('verified_by', 'unspecified')}",
                f"**Reported passed:** {item.get('passed', 'unknown')}",
                f"**Reported exit code:** {item.get('exit_code', 'unknown')}", "",
                "> Evidence is user-supplied JSON and could be altered. Review logs before relying on it.", "",
                "```text", str(item.get('output', ''))[:16000].replace('```', '[fence]'), "```", ""]
    if report.groups:
        out += ["## Group deliberations (unverified)", ""]
        for group in report.groups:
            out += [f"### Group {group['group']}", "", group['summary'], ""]
    ref_audit = report.execution.get("reference_audit") if report.execution else None
    if ref_audit:
        out += ["## Source-reference integrity (not fact checking)", "",
                f"**Checked file:line references:** {ref_audit['checked_references']}",
                f"**Within submitted lines:** {ref_audit['in_snapshot']}",
                f"**Outside submitted lines:** {ref_audit['outside_snapshot']}",
                f"**Agents with no line references:** {ref_audit['agents_without_line_references']}",
                f"**Unrecognized file references:** {ref_audit.get('unrecognized_files', 0)}", "",
                "> Checking that a file and line appeared in the supplied excerpt does NOT prove the finding is true.", ""]
    if report.execution:
        out += ["## Execution metadata", "", "```json", json.dumps(report.execution, indent=2), "```", ""]
    out += ["## Independent agent reports", ""]
    for i, a in enumerate(report.agents, start=1):
        out += [f"### {i}. {a.role}", "", f"*Model: `{a.model}` | Duration: {a.duration_seconds:.2f}s*", "",
                a.content, ""]
    if report.errors:
        out += ["## Incomplete or failed steps", ""]
        out += [f"- {e}" for e in report.errors]
        out += [""]
    out += ["---", "",
            "*AI-generated suggestions can be wrong. Secret-pattern warnings, optional "
            "user-authorized tests and source-line checks have important limitations; none "
            "proves an AI finding is true. Verify conclusions independently.*", ""]
    return "\n".join(out)


def write_report(report: CouncilReport, destination: str | Path, json_destination: str | Path | None = None) -> None:
    target = Path(destination).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_markdown(report), encoding="utf-8")
    if json_destination is not None:
        target_json = Path(json_destination).expanduser()
        target_json.parent.mkdir(parents=True, exist_ok=True)
        target_json.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
