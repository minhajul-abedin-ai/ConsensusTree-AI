# ConsensusTree AI v6.2.3 RC1 — release and security audit

Date: 28 October 2026. **Status:** developer release candidate, **not** a stable production security tool.

## Concrete fixes

1. **Filesystem trust boundary:** previously `Path.read_bytes()` could read a file after a symlink swap between path validation and reading. The new descriptor-based reader validates file type and identity, uses `O_NOFOLLOW` where supported, and enforces a 120 KB upper bound. On platforms without `O_NOFOLLOW`, the identity check reduces risk but is not a comprehensive filesystem-race guarantee. This implementation is not a sandbox against malicious processes that can mutate parent directories at the exact time of review.
2. **Git-diff sample privacy:** previously files inside `secrets/` or similar skipped directories could be selected in `pr-review` even though normal `scan()` excluded those paths. The diff filter now applies sensitive-directory checks and rejects malicious filenames. Always examine the diff for secrets; pattern checks are not exhaustive.
3. **Benchmark integrity:** `parse_verdict()` previously accepted repeated identical verdict lines or a verdict followed by additional text. It now counts those as abstentions instead of claiming confident predictions. This may reduce coverage, which is the honest outcome.
4. **Provider resilience:** non-string text blocks are skipped and a response exceeding 4 MB now fails explicitly rather than being parsed as a truncated result.
5. **Communication:** report footers no longer incorrectly say the tool never runs tests or checks secrets; those features exist but have significant limits.

## Local evidence and how to reproduce

```bash
python -m pip install -e .
python -m unittest discover -s tests -q
python -m compileall -q src tests
python tests/browser_studio_v623_optional.py  # optional: playwright + Chromium required
consensustree doctor
consensustree quickstart --dir /tmp/ct-demo
consensustree review examples --dry-run
python -m consensustree.validation live --output /tmp/ct-live-status.json  # no real calls
```

The browser test uses a **mock** provider and mock fetch responses. It does not certify live browser-to-provider operation. Supported Python versions declared: 3.10+; this audit reflects the actual version and operating system named in the accompanying release report, not every OS and Python combination.

## Outstanding release gates

- No successful genuine OpenAI/Gemini/Claude/Ollama provider invocation is recorded for this build; configured accounts or a running Ollama backend are needed.
- The 50-case benchmark is author-labelled synthetic data. Genuine model predictions and an independently reviewed holdout dataset are required before claiming improvement over a single model.
- The included internal adversarial tests are **not an independent external security assessment**. An assessor must separately validate the code and issue their own findings.
- No public GitHub star count or adoption result has been verified; 10,000+ stars is a separate community goal.

## Security scope

The server is intended for a private localhost session, not public hosting. Source preview and consent reduce accidental disclosure but cannot detect every credential. User-selected project tests can execute arbitrary code and must run only on trusted repositories. Treat model outputs as unverified suggestions.
