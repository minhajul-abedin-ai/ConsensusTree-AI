"""Convert production benchmark output to paired structural preflight records.

No model execution, provider calls, accuracy scoring or content-hash verification.
"""
import argparse
import json
import re
from pathlib import Path

HEX = re.compile(r"[0-9a-f]{64}\Z")


def convert(result):
    if not isinstance(result, dict) or result.get("benchmark_type") != "production_Council_vs_single_model":
        raise ValueError("Expected production_Council_vs_single_model result")
    cases = result.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Expected nonempty cases list")
    records = []
    seen = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"case {index}: expected object")
        case_id, digest = case.get("id"), case.get("source_sha256")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ValueError(f"case {index}: missing or duplicate id")
        if not isinstance(digest, str) or not HEX.fullmatch(digest):
            raise ValueError(f"case {index}: invalid source_sha256")
        if "baseline" not in case or "council" not in case or case["baseline"] is None or case["council"] is None:
            raise ValueError(f"case {index}: missing baseline or council output")
        seen.add(case_id)
        for arm in ("baseline", "council"):
            records.append({"case_id": case_id, "arm": arm, "case_sha256": digest})
    return {"records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Production benchmark JSON output")
    parser.add_argument("output", type=Path, help="Preflight manifest path")
    args = parser.parse_args()
    try:
        converted = convert(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.write_text(json.dumps(converted, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"conversion failed: {exc}\n")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
