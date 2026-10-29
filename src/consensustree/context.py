"""Deterministic, opt-in relevance ranking for bounded repository snapshots.

This is NOT semantic indexing or comprehensive review: it ranks files using
Git changes, filenames, shallow imports and nearby tests, all without executing
repository content or calling external services.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .scanner import _safe_parts, EXTENSIONS, _read_bounded_regular_file


def changed_files(root: Path) -> set[str]:
    """Find changes to tracked files and staged files; fail closed on Git errors."""
    if not (root / ".git").exists():
        return set()
    try:
        check = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                               capture_output=True, timeout=8, check=False)
        if check.returncode:
            # Freshly initialized repositories may not have a first commit yet.
            return set()
        changes: set[str] = set()
        for args in (("diff", "--name-only", "-z", "HEAD"),
                     ("diff", "--name-only", "--cached", "-z")):
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                    timeout=8, check=False)
            if result.returncode or len(result.stdout) > 2_000_000:
                raise ValueError("Cannot safely determine changed files")
            for part in result.stdout.split(b"\0"):
                if part:
                    name = Path(part.decode("utf-8", "surrogateescape"))
                    if not name.is_absolute() and ".." not in name.parts and _safe_parts(name):
                        changes.add(name.as_posix())
        return changes
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Cannot safely determine changed files") from exc


def rank_candidates(root: Path, candidates: list[Path], *, focus: str = "") -> tuple[list[Path], dict]:
    """Prioritize changes and related paths; keep the result explainable."""
    if len(candidates) > 50_000:
        raise ValueError("Too many candidate files for smart context; select a subdirectory")
    if len(focus) > 200 or any(c in focus for c in "\r\n\0"):
        raise ValueError("Invalid context focus")
    changes = changed_files(root)
    focus_words = set(re.findall(r"[a-z0-9]{3,}", focus.casefold()))
    changed_stems = {Path(name).stem.casefold() for name in changes}
    changed_dirs = {str(Path(name).parent) for name in changes}
    ranked = []
    # Only probe import dependencies for the first bounded set. Reading every
    # file in a huge repository would defeat bounded analysis.
    dependency_probe_budget = 1500
    for path in candidates:
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if (path.suffix.casefold() not in EXTENSIONS or not _safe_parts(rel)
                or path.is_symlink() or not path.resolve().is_relative_to(root)):

            continue
        name = rel.as_posix()
        stem = path.stem.casefold()
        score = 0
        if name in changes:
            score += 120
        if str(rel.parent) in changed_dirs and changes:
            score += 35
        if focus_words:
            score += 45 * len(focus_words & set(re.findall(r"[a-z0-9]{3,}", name.casefold())))
        if ("test" in stem or "spec" in stem) and any(s and s in stem for s in changed_stems):
            score += 24
        if changed_stems and score < 120 and dependency_probe_budget > 0:
            dependency_probe_budget -= 1
            raw = _read_bounded_regular_file(path)
            if raw:
                snippet = raw[:20000].decode("utf-8", "replace").casefold()
                # Low-cost dependency signal, NOT a full language parser.
                if any(re.search(r"(?:import|from|require|include)\s*[(\s'\"]*" +
                                 re.escape(stem_name) + r"\b", snippet)
                       for stem_name in changed_stems if stem_name and len(stem_name) > 2):
                    score += 50
        ranked.append((-score, name, path))
    ranked.sort()
    return [p for _, _, p in ranked], {"strategy": "changed-file-and-dependency-heuristic",
                                     "changed_files_detected": len(changes),
                                     "candidates_ranked": len(ranked),
                                     "focus_provided": bool(focus),
                                     "not_semantic_or_exhaustive": True}
