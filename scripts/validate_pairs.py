"""Validate paired evaluation records for structural consistency (not correctness)."""
import argparse
import json
import re
from pathlib import Path

SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def validate(payload):
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records:
        return ["records must be a nonempty list"]
    errors = []
    cases = {}
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record {i}: expected object")
            continue
        case_id, arm, digest = (record.get(k) for k in ("case_id", "arm", "case_sha256"))
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"record {i}: invalid case_id")
            continue
        if arm not in ("baseline", "council"):
            errors.append(f"record {i}: invalid arm")
            continue
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"record {i}: invalid case_sha256")
            continue
        group = cases.setdefault(case_id, {})
        if arm in group:
            errors.append(f"case {case_id}: duplicate {arm} arm")
        group[arm] = digest
    for case_id, arms in sorted(cases.items()):
        if set(arms) != {"baseline", "council"}:
            errors.append(f"case {case_id}: missing paired arm")
        elif arms["baseline"] != arms["council"]:
            errors.append(f"case {case_id}: mismatched case_sha256")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"input error: {exc}\n")
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")
    print("Paired records valid (structural checks only).")


if __name__ == "__main__":
    main()
