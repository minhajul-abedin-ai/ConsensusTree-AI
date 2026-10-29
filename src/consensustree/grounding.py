"""Deterministic *reference integrity*, never factual verification.

Check whether LLM-cited file:line positions were actually present in the excerpt
provided to the models. It does not establish that a reported defect exists.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .scanner import Snapshot


_SOURCE_START = re.compile(r'^--- FILE: (.+) ---$')
_SOURCE_END = re.compile(r'^--- END FILE: (.+) ---$')
_NUMBERED_LINE = re.compile(r'^\s*(\d+) \| ')
# Simple lexical check for citations to source files that were NOT in the excerpt.
# Path names with spaces and non-standard extensions are not recognized.
_UNKNOWN_REF = re.compile(
    r"(?<![\w/.-])`?(?P<path>(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\."
    r"(?:py|js|jsx|ts|tsx|go|rs|java|rb|php|c|cpp|h|hpp|css|html|json|yaml|yml|toml|sh|sql|md|vue|svelte))"
    r"`?(?::(?P<colon>\d{1,7})|#L(?P<hash>\d{1,7})|\s+line\s+(?P<word>\d{1,7}))", re.I)


def _submitted_lines(snapshot: Snapshot) -> dict[str, set[int]]:
    lines: dict[str, set[int]] = defaultdict(set)
    current: str | None = None
    for line in snapshot.text.splitlines():
        start = _SOURCE_START.fullmatch(line)
        if start:
            current = start.group(1)
            continue
        if _SOURCE_END.fullmatch(line):
            current = None
            continue
        numbered = _NUMBERED_LINE.match(line)
        if current and numbered:
            lines[current].add(int(numbered.group(1)))
    return dict(lines)


def audit_report_references(snapshot: Snapshot, agents: list) -> dict:
    """Return exact reference counts, with strong limitations in every report.

    Accepts `path:12`, `path#L12`, and `path line 12`. Does not
    infer bugs, test execution, credibility, or correctness from citation counts.
    """
    visible = _submitted_lines(snapshot)
    checked = []
    counts = {"checked_references": 0, "in_snapshot": 0, "outside_snapshot": 0,
              "agents_without_line_references": 0, "unrecognized_files": 0, "details": checked,
              "method": "literal source path and visible line number matching only",
              "fact_checked": False}
    for agent in agents:
        found = set()
        # Longest first prevents partial matches (e.g. app.py vs src/app.py).
        for path in sorted(visible, key=len, reverse=True):
            escaped = re.escape(path)
            # Tolerate optional Markdown backticks, with a clear line separator.
            rx = re.compile(r'(?<![\w/.-])`?' + escaped +
                            r'`?(?::(\d{1,7})|#L(\d{1,7})|\s+line\s+(\d{1,7}))', re.I)
            for m in rx.finditer(agent.content):
                line = int(next(g for g in m.groups() if g is not None))
                found.add((path, line))
        for match in _UNKNOWN_REF.finditer(agent.content):
            path = match.group("path")
            if path not in visible:
                line = int(match.group("colon") or match.group("hash") or match.group("word"))
                found.add((path, line))
        if not found:
            counts["agents_without_line_references"] += 1
        for path, line in sorted(found):
            ok = line in visible.get(path, set())
            if path not in visible:
                counts["unrecognized_files"] += 1
            counts["checked_references"] += 1
            counts["in_snapshot" if ok else "outside_snapshot"] += 1
            if len(checked) < 150:
                checked.append({"role": agent.role, "file": path, "line": line,
                                "present_in_excerpt": ok,
                                "recognized_file": path in visible})
    return counts
