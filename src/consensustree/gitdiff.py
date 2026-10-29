"""Read a bounded Git diff without executing project code.

Diff files can still contain secrets. Always inspect the paths and obtain
permission before uploading a change to a hosted language model.
"""
from __future__ import annotations
import subprocess
import re
from pathlib import Path

from .scanner import Snapshot, EXTENSIONS, _safe_parts, _sensitive


def _git(root: Path, *args: str) -> bytes:
    try:
        p = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Git unavailable or command timed out") from exc
    if p.returncode != 0:
        raise ValueError("Git diff failed. Check that the directory is a Git repository and both revisions exist.")
    if len(p.stdout) > 10_000_000:
        raise ValueError("Git diff too large; choose a narrower base or head")
    return p.stdout


def diff_snapshot(path: str | Path, *, base: str = "HEAD~1", head: str = "HEAD",
                  max_files: int = 20, max_chars: int = 24_000) -> Snapshot:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Git review path must be a directory")
    if not 1 <= max_files <= 100 or not 500 <= max_chars <= 150_000:
        raise ValueError("max-files must be 1..100 and max-chars 500..150000")
    # Git revisions are positional options; never accept option-like rev arguments.
    for rev in (base, head):
        if not isinstance(rev, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./~^{}-]{0,119}", rev):
            raise ValueError("Invalid Git revision (no flags or whitespace allowed)")
    names = _git(root, "diff", "--name-only", "--no-ext-diff", "--no-renames", "-z", base, head).split(b"\x00")
    selected = []
    for raw in names:
        if not raw:
            continue
        try:
            name = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        rel = Path(name)
        if (rel.is_absolute() or ".." in rel.parts or
            not _safe_parts(rel) or
            any(ord(ch) < 32 or ord(ch) == 127 or 0xD800 <= ord(ch) <= 0xDFFF
                for ch in name)):
            continue
        if rel.suffix.lower() not in EXTENSIONS or _sensitive(rel):
            continue
        selected.append(name)
    if not selected:
        raise ValueError("No supported changed source files found")
    limited = selected[:max_files]
    diff = _git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--unified=3", base, head, "--", *limited)
    text = diff.decode("utf-8", "replace")
    truncated = len(selected) > max_files or len(text) > max_chars
    return Snapshot(str(root), limited, text[:max_chars], truncated,
                    eligible_files=len(selected), omitted_files=max(0, len(selected)-len(limited)))
