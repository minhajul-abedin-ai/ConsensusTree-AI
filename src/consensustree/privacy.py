"""Small, conservative best-effort secret preflight, NOT a secret scanner."""
from __future__ import annotations
import re

PATTERNS = {
    "Possible OpenAI-style key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "Possible GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{24,}\b"),
    "Possible AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Private key header": re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "Likely hardcoded credential": re.compile(
        r"(?i)\b(?:password|api_key|access_token|secret_key)\b\s*[:=]\s*['\"][^'\"\n]{12,}['\"]"),
}


def secret_warnings(source: str) -> list[str]:
    """Return *category names only*, never raw credentials."""
    return [label for label, pattern in PATTERNS.items() if pattern.search(source)]


def privacy_preflight(source: str, *, allow_sensitive: bool = False) -> list[str]:
    """Uniform preflight for all model-bound user input paths.

    Uses best-effort patterns only: callers must not imply comprehensive
    secret detection. Return category names, never matching secret text.
    """
    warnings = secret_warnings(source)
    if warnings and not allow_sensitive:
        raise ValueError("Possible credentials detected. Remove sensitive content or explicitly use --allow-sensitive.")
    return warnings
