"""Intentionally simplistic fixture to demonstrate possible review findings.

This script is not intended for production deployment.
"""

import json


def parse_request(body: str):
    """Parse JSON without schema validation (intentionally omitted)."""
    return json.loads(body)


def ratio(numerator: int, denominator: int):
    # Intentionally unhandled zero division, for reviewers to notice.
    return numerator / denominator


def store_config(config: dict):
    # No actual persistence in this example.
    return {"status": "ok", "keys": len(config)}
