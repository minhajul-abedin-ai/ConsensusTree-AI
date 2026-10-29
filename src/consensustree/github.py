"""Explicit, opt-in GitHub pull request comment posting.

The --confirm switch must be supplied; this never runs automatically.
"""
from __future__ import annotations
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def pr_comment(repo: str, pr_number: int, report: str | Path, *, confirm: bool = False) -> dict:
    if not REPO_RE.fullmatch(repo) or any(x in (".", "..") or x.startswith(".") for x in repo.split("/")):
        raise ValueError("Expected repo owner/name with ordinary GitHub characters")
    if not 1 <= pr_number <= 2_147_483_647:
        raise ValueError("PR number must be positive")
    path = Path(report).expanduser()
    if path.stat().st_size > 100_000:
        raise ValueError("Report exceeds 100KB; select a shorter report before posting")
    message = path.read_text(encoding="utf-8")
    if not message.strip():
        raise ValueError("Empty report")
    # GitHub issue comment body size limit and avoiding surprising large posts.
    body = "### ConsensusTree AI review (unverified AI suggestions)\n\n" + message
    if len(body) > 60_000:
        raise ValueError("Report exceeds 60,000 characters")
    if not confirm:
        return {"posted": False, "preview": body[:500], "bytes": len(body.encode("utf-8")),
                "destination": f"{repo}#{pr_number}"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise ValueError("GITHUB_TOKEN is required when --confirm is supplied")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
        data=json.dumps({"body": body}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
                 "User-Agent": "ConsensusTree-AI"}, method="POST")
    try:
        with urllib.request.build_opener(_NoRedirect()).open(req, timeout=20) as response:
            output = json.loads(response.read(100_000))
        return {"posted": True, "url": output.get("html_url"), "destination": f"{repo}#{pr_number}"}
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise ValueError("GitHub comment request failed; verify PR, token permissions and connectivity") from exc


MARKER = "<!-- consensustree-review-v1 -->"


def upsert_bot_pr_comment(repo: str, pr_number: int, report: str | Path, *, token: str) -> dict:
    """Update an existing own bot comment instead of posting duplicates.

    Only comments by the GitHub Actions bot with our exact marker are touched.
    No redirect following is permitted for requests carrying tokens.
    """
    if not REPO_RE.fullmatch(repo) or any(x in {".", ".."} or x.startswith(".") for x in repo.split("/")):
        raise ValueError("Invalid GitHub repository")
    if not 1 <= pr_number <= 2_147_483_647 or not token:
        raise ValueError("Invalid PR number or missing GitHub token")
    content_path = Path(report)
    if content_path.stat().st_size > 100_000:
        raise ValueError("Review report too large")
    body = MARKER + "\n### ConsensusTree AI code review (unverified suggestions)\n\n" + content_path.read_text(encoding="utf-8")
    if not body.strip() or len(body) > 60_000:
        raise ValueError("Invalid report size")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "ConsensusTree-AI"}
    endpoint = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        existing = None
        # Scan at most 200 comments, bounded to avoid abuse and large responses.
        for page in (1, 2):
            req = urllib.request.Request(f"{endpoint}?per_page=100&page={page}", headers=headers)
            with opener.open(req, timeout=15) as response:
                buf = response.read(500_001)
            if len(buf) > 500_000:
                raise ValueError("GitHub comments response exceeds limit")
            rows = json.loads(buf)
            if not isinstance(rows, list):
                raise ValueError("Malformed GitHub comments list")
            for row in rows:
                if (isinstance(row, dict) and row.get("user", {}).get("login") == "github-actions[bot]"
                        and isinstance(row.get("body"), str) and row["body"].startswith(MARKER)):
                    existing = row.get("id")
                    break
            if existing or len(rows) < 100:
                break
        if existing is not None:
            if type(existing) is not int or existing <= 0:
                raise ValueError("Invalid comment ID")
            url = f"https://api.github.com/repos/{repo}/issues/comments/{existing}"
            method = "PATCH"
        else:
            url = endpoint
            method = "POST"
        req = urllib.request.Request(url, data=json.dumps({"body": body}).encode(),
                                     headers={**headers, "Content-Type": "application/json"}, method=method)
        with opener.open(req, timeout=20) as response:
            response_body = response.read(100_001)
        if len(response_body) > 100_000:
            raise ValueError("GitHub write response exceeds limit")
        saved = json.loads(response_body)
        return {"posted": True, "action": "updated" if existing else "created", "url": saved.get("html_url")}
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise ValueError("GitHub API request failed") from exc
