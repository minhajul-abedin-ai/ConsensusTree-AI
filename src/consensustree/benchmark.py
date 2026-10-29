"""Reproducible report-text checks against a user-supplied labeled suite.

This checks expected phrase coverage, NOT correctness, calibration, or quality.
For real model quality, use held-out data and independent human adjudication.
"""
from __future__ import annotations
import json
from pathlib import Path


def evaluate_suite(suite_file: str | Path, reports_dir: str | Path) -> dict:
    suite = json.loads(Path(suite_file).read_text(encoding="utf-8"))
    if not isinstance(suite, dict) or not isinstance(suite.get("cases"), list):
        raise ValueError("Suite must contain a 'cases' list")
    base = Path(reports_dir).expanduser().resolve()
    rows = []
    for case in suite["cases"]:
        name = case["id"]
        filename = case["report"]
        dest = (base / filename).resolve()
        if not dest.is_relative_to(base) or dest.suffix != ".json":
            raise ValueError("Report path must be a relative .json inside reports directory")
        try:
            data = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            rows.append({"case": name, "status": "missing or invalid report", "coverage": None})
            continue
        texts = [str(data.get("synthesis") or "")]
        texts += [str(a.get("content", "")) for a in data.get("agents", [])]
        full = "\n".join(texts).casefold()
        expected = case.get("required_terms", [])
        prohibited = case.get("prohibited_terms", [])
        if not isinstance(expected, list) or not isinstance(prohibited, list):
            raise ValueError("Terms must be lists")
        hits = [s for s in expected if isinstance(s, str) and s.casefold() in full]
        violations = [s for s in prohibited if isinstance(s, str) and s.casefold() in full]
        rows.append({"case": name, "status": "checked", "matched": len(hits),
                     "expected": len(expected), "coverage": round(len(hits)/len(expected), 3) if expected else None,
                     "prohibited_term_hits": violations})
    measured = [x for x in rows if x.get("coverage") is not None]
    return {"suite": suite.get("name", "unnamed"), "metric": "expected phrase coverage only",
            "not_a_quality_or_accuracy_score": True, "cases": rows,
            "average_coverage": round(sum(x["coverage"] for x in measured)/len(measured), 3) if measured else None,
            "measured_cases": len(measured), "total_cases": len(rows)}
