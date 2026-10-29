# ConsensusTree AI v6.3.0rc1 — public release gates

**Intended release:** free, public, MIT-licensed **experimental prerelease**, not a hosted production service.

## Verified in the authoring environment (2026-10-29)

- Python 3.13, 177/177 deterministic unit/integration/regression tests passed.
- Chromium: responsive UI at 360, 390, 768, 1024 and 1440 pixels; mocked-API review, consent, report export and partial-run warnings passed.
- Python package: built as a wheel and installed to a separate target directory; offline demonstration and diagnostics ran successfully.
- GitHub Actions: workflow YAML parsed and trust-boundary invariants covered by tests. **No live Actions run is claimed.**
- Source ZIP: excludes `.git`, `__pycache__`, build output, test caches, and `.env` files; static scans did not find recognized credential token values. This does **not** prove an exhaustive secret scan.

## Blockers to claiming a production-grade code reviewer

- [ ] Run actual successful, logged, authorized requests against **OpenAI, Gemini, Claude and Ollama**; verify provider model access, errors, billing, request limits and real-world stability. Do not put credentials in issue comments or source code.
- [ ] Have separate external reviewers adjudicate a representative held-out set of real defects and fixed controls. Measure precision, recall, false positives, costs and latency against a comparable single-model baseline. The supplied 50-case synthetic suite does **not** prove these metrics.
- [ ] Commission an independent security assessment; resolve serious findings and document scope. This project and its own automated tests cannot certify their own independence.
- [ ] Execute GitHub Actions on a separate test repository and PR. Validate permissions, PR secret restrictions, default-branch trust model, bot comment idempotency and billing. Do **not** enable `CONSENSUSTREE_AUTO_REVIEW` in an unfamiliar public repository.
- [ ] Verify installation and app interactions on actual macOS, Linux and Windows machines; matrix CI is included but not yet externally observed running.
- [ ] Observe actual use and collect consent/privacy and error reports from at least several independent developers.

## Publication steps for the experimental GitHub prerelease

1. Create a **Public** repository named `ConsensusTree-AI` with no newly initialized README/license/gitignore. Upload the **unpacked** project source, including `.github/` and `src/`.
2. Inspect all source code and images before pushing, using GitHub's secret scanning and your own review. No default API tokens should be committed.
3. Confirm CI and CodeQL run from GitHub's servers and address failures. Protect the `main` branch, require PR reviews and enable security advisories.
4. Run a local, offline smoke test: `python -m pip install -e . && consensustree doctor && consensustree quickstart`.
5. Publish as a prerelease `v6.3.0rc1` with title **Experimental developer preview — not independently audited**. Keep `CONSENSUSTREE_AUTO_REVIEW` **unset/false** until the opt-in workflow has been tested on a disposable PR and provider costs are understood.
6. Never expose `consensustree studio` through a public proxy. It is intended only for single-user loopback access and has no multi-user authentication, tenant boundaries, or production hosting security.

## GitHub event security note

The optional PR review workflow is triggered by `pull_request_target`, which GitHub runs with trusted default-branch workflow source and a credentialed context. The workflow explicitly checks out the trusted base SHA, fetches the head SHA *only as Git objects*, and never builds or executes PR head contents. Fork PRs are skipped and a repository variable opt-in is required. **This remains a privileged automation that must be independently reviewed, observed in real GitHub Actions runs, and may be affected by current GitHub Actions event policies.** Alternative is to leave it disabled and use the local CLI for manual PR review.

## Marketing claims: permitted vs unsupported

- **Permitted:** 'Local-first open-source AI council and code-review prototype', 'MIT-licensed', 'AI-generated suggestions require verification', 'Supports multiple providers via local adapters'.
- **Not supported:** 'AI reviews are accurate / better than alternatives', 'enterprise-grade', 'zero false positives', 'audited security', 'fully autonomous safe code reviews', '10,000 stars achieved', 'cost free to use third-party model APIs'.
