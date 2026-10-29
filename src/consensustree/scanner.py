"""Bounded source-file sampler for user-approved code reviews.

When a valid Git working tree is selected, uses Git's own exclude rules
(including .gitignore) to avoid accidentally including ignored files.
NOT an exhaustive secret detector: always inspect preview before consent.
"""
from __future__ import annotations

import fnmatch
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb",
    ".php", ".c", ".cpp", ".h", ".hpp", ".css", ".html", ".json",
    ".yaml", ".yml", ".toml", ".sh", ".sql", ".md", ".vue", ".svelte",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "__pycache__",
    ".next", "dist", "build", "coverage", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "target", "vendor", "site-packages", ".idea", ".vscode",
    "secrets", "credentials", "private",
}
SENSITIVE_TOKENS = {"secret", "secrets", "credential", "credentials", "private", "token", "tokens", "password", "passwords", "passwd", "apikey", "api_key", "id_rsa", "id_ed25519"}
MAX_FILE_BYTES = 120_000


def _read_bounded_regular_file(path: Path) -> bytes | None:
    """Read a regular file from one verified descriptor, never a swapped symlink.

    A pre-read path check alone is racy: the file can become a symlink to a
    secret after validation but before read_bytes(). Compare file identities
    and use O_NOFOLLOW where the operating system supports it.
    """
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            return None
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if (not stat.S_ISREG(opened.st_mode) or opened.st_dev != before.st_dev
                    or opened.st_ino != before.st_ino or opened.st_size > MAX_FILE_BYTES):
                return None
            chunks: list[bytes] = []
            size = 0
            while size <= MAX_FILE_BYTES:
                part = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - size))
                if not part:
                    break
                chunks.append(part)
                size += len(part)
            return b"".join(chunks) if size <= MAX_FILE_BYTES else None
        finally:
            os.close(fd)
    except OSError:
        return None


@dataclass
class Snapshot:
    root: str
    files: list[str]
    text: str
    truncated: bool
    eligible_files: int = 0
    omitted_files: int = 0
    selection: dict | None = None


def _blocked_component(component: str) -> bool:
    """Detect sensitive/generated names on case-insensitive and POSIX filesystems.

    Never assume .gitignore or a directory's capitalisation protects
    private code. Reject whole known directory names and sensitive tokens
    separated by hyphens, underscores or dots.
    """
    normalized = component.casefold()
    tokens = set(normalized.replace("-", "_").replace(".", "_").split("_"))
    return normalized in SKIP_DIRS or bool(tokens & SENSITIVE_TOKENS)


def _safe_parts(relative: Path) -> bool:
    return bool(relative.parts) and not any(
        part.startswith(".") or _blocked_component(part) or _sensitive(Path(part))
        for part in relative.parts
    )


def _sensitive(path: Path) -> bool:
    name = path.name.casefold()
    if name.startswith(".env") or name.startswith(".npmrc") or name.endswith((".pem", ".key", ".p12")):
        return True
    pieces = name.replace("-", "_").replace(".", "_").split("_")
    return bool(set(pieces) & SENSITIVE_TOKENS)


def _exclude(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(Path(rel).name, p) or (p.endswith("/") and rel.startswith(p)) for p in patterns)


def _git_candidates(root: Path) -> list[Path] | None:
    """Honour .gitignore and .git/info/exclude for a Git worktree root.

    If the selected directory is not a Git root, normal directory traversal
    applies. Git is invoked without a shell and never reads source contents.
    """
    # Git may live in an ancestor of a selected source subdirectory.
    # In that case `git -C` still applies the repository's ignore rules.
    try:
        # Do not use git aliases; `ls-files` is a built-in Git subcommand.
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False,
        )
    except FileNotFoundError as exc:
        if any((parent / ".git").exists() for parent in (root, *root.parents)):
            raise ValueError("Git is required to respect this repository's ignore rules") from exc
        return None
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Git listing failed; cannot safely apply ignore rules") from exc
    if result.returncode != 0:
        # In a Git working tree we MUST NOT silently fall back to os.walk:
        # doing so can include files excluded by .gitignore. A missing/corrupt
        # .git directory is also a reason to stop rather than risk disclosure.
        if any((parent / ".git").exists() for parent in (root, *root.parents)):
            raise ValueError("Git file listing failed; refusing unsafe fallback that may include ignored files")
        return None  # Ordinary directory outside a Git worktree
    if len(result.stdout) > 10_000_000:
        raise ValueError("Repository file listing exceeds 10 MB; choose a smaller review target")
    candidates = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        # Use os.fsdecode rather than lossy replacement to support unusual paths.
        relative = Path(os.fsdecode(raw))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            continue
        candidates.append(root / relative)
    return sorted(set(candidates))


def scan(path: str | Path, *, max_files: int = 20, max_chars: int = 24_000,
         exclude: list[str] | None = None, smart: bool = False, focus: str = "") -> Snapshot:
    """Return a bounded snapshot; excludes hidden/symlink/ignored paths.

    Git ignore rules apply when the selected directory is a valid Git root.
    Always inspect the file preview before uploading to a hosted model.
    """
    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"Path does not exist: {path}")
    if not (1 <= max_files <= 100 and 500 <= max_chars <= 150_000):
        raise ValueError("max_files must be 1..100 and max_chars must be 500..150000")
    if root.is_file():
        # A directly selected file must not bypass the sensitive-directory
        # filter simply because its relative path has only one component.
        if not _safe_parts(Path(root.name)) or any(
            _blocked_component(part) for part in root.parent.parts
        ):
            raise ValueError("Refusing a file in a sensitive or generated path")
        candidates = [root]
        base = root.parent
    elif root.is_dir():
        # Traverse lazily, prune hidden/generated/sensitive directories early,
        # and never follow symlinks into another project.
        def visit():
            for folder, subdirs, filenames in os.walk(root, followlinks=False):
                subdirs[:] = sorted(
                    d for d in subdirs
                    if not d.startswith(".") and not _blocked_component(d)
                    and not (Path(folder) / d).is_symlink()
                )
                for filename in sorted(filenames):
                    candidate = Path(folder) / filename
                    if candidate.is_file():
                        yield candidate
        candidates = _git_candidates(root)
        if candidates is None:
            candidates = visit()
        base = root
    else:
        raise ValueError("Expected a file or directory")

    selection = None
    if smart and root.is_dir():
        from .context import rank_candidates
        candidates, selection = rank_candidates(root, list(candidates), focus=focus)
    patterns = exclude or []
    blocks: list[str] = []
    selected: list[str] = []
    current = 0
    truncated = False
    eligible_files = 0
    for candidate in candidates:
        relpath = candidate.relative_to(base)
        relative = relpath.as_posix()
        # Source headers contain file names. Reject control characters to
        # prevent a crafted name from forging a numbered source block.
        if any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in relative):
            continue
        if (candidate.is_symlink() or not _safe_parts(relpath)
            or not candidate.resolve().is_relative_to(base)):
            continue
        if candidate.suffix.lower() not in EXTENSIONS or _sensitive(candidate):
            continue
        if _exclude(relative, patterns):
            continue
        eligible_files += 1
        try:
            if candidate.stat().st_size > MAX_FILE_BYTES:
                truncated = True
                continue
        except OSError:
            continue
        raw = _read_bounded_regular_file(candidate)
        if raw is None:
            continue
        if b"\x00" in raw:
            continue
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        # Include real line numbers for actionable findings.
        remaining = max_chars - current
        overhead = len(relative) + 90
        if remaining <= overhead or len(selected) >= max_files:
            truncated = True
            # Continue counting eligible paths without reading their contents.
            continue
        max_content = min(8_000, remaining - overhead)
        if max_content < 100:
            truncated = True
            continue
        numbered_lines = []
        line_char_count = 0
        for i, line in enumerate(content.splitlines(), 1):
            numbered = f"{i:>4} | {line}\n"
            if line_char_count + len(numbered) > max_content:
                truncated = True
                break
            numbered_lines.append(numbered)
            line_char_count += len(numbered)
        if not numbered_lines:
            continue
        block = f"\n--- FILE: {relative} ---\n" + "".join(numbered_lines) + f"--- END FILE: {relative} ---\n"
        blocks.append(block)
        selected.append(relative)
        current += len(block)
    if not selected:
        raise ValueError("No suitable source files found (check path, extensions and exclusions)")
    return Snapshot(root=str(root), files=selected, text="".join(blocks), truncated=truncated,
                    eligible_files=eligible_files, omitted_files=max(0, eligible_files - len(selected)),
                    selection=selection)
