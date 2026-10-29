## 6.3.0rc1 — final GitHub prerelease hardening (2026-10-29)

- Trust boundary correction for credentialed PR workflow: trusted default-branch trigger, trusted base checkout assertion, fetch PR head as data only, and explicit administrator opt-in.
- Reject remote plaintext Ollama endpoints and invalid transport timeouts.
- Reject unexpectedly large model completions, including those returned by plugins, before they can propagate into synthesis.
- Add targeted regression coverage and an honest publication gate checklist.
- No third-party security certification, paid provider smoke test, or independent quality benchmark is claimed.

# 6.2.5 RC1 — engineering validation improvements

See docs/RELEASE_6_2_5.md for scope, test evidence and remaining external gates.

## 6.2.4rc1 — Privacy and truthful coverage (29 October 2026)
- Case-normalized directory exclusions across ordinary and Git-backed scanning.
- Enforced shared privacy preflight on CLI `ask` and `debate` questions.
- Fixed stale sidebar version and invalid duplicate class attributes.
- Show counts of selected, eligible and omitted source files in previews.
- Added targeted regression tests. Real-provider and independent security validation remain outstanding.

## 6.2.3rc1 — safer source sampling, Git-diff privacy, strict benchmark results (28 October 2026)

- Read files using bounded regular-file descriptors and inode identity checks; reject symlink swaps.
- Exclude sensitive folders, control-character and undecodable names from Git-diff reviews.
- Treat malformed/duplicated/nonfinal LLM verdicts as benchmark abstentions.
- Reject provider responses over 4 MB and tolerate mixed-type content safely.
- Correct report language about limited scans and optional tests.
- Add 13 new regression tests (138 total), plus optional Chromium smoke tests.
- This remains a local-only release candidate: live provider verification, independent labels and external security assessment remain outstanding.

## 6.2.2rc1 — validation harness and internal hostile-input tests (28 October 2026)

- Added explicit opt-in real-provider probes. No keys or response contents are saved in probe results.
- Added 50 author-labelled code cases and bounded 5-request-per-case single-vs-council benchmark protocol.
- Added confusion matrix, precision, recall, false positives, abstention and coverage reporting.
- Fixed benchmark request-budget accounting: count attempted calls before network execution.
- Added 14 local adversarial security tests and 9 validation/metric tests.
- Prepared external security reviewer handoff; this build has **not** received independent external certification.

## 6.2.1rc1 — additional safety and consent hardening (28 October 2026)

- Bind browser source-sharing fingerprints to the selected canonical target path **and** exact source excerpt. Prevent cross-folder consent replay when two subprojects contain identical files.
- Fail closed if Git file listing fails in a worktree with Git metadata. Do not silently traverse ignored files when ignore rules cannot be trusted.
- Reject candidate source paths with control characters, avoiding forged file delimiters in prompt snapshots.
- Add six targeted regression tests and update the older fingerprint contract test. Verify five responsive Chromium sizes against mocked endpoints.
- Developer release candidate only: no live-provider, independent accuracy or public-production security certification.

# Changelog

## 6.2.0rc1 (2026-10-28)

- Added explicit **execution-completeness gates**: 3/3 (or 3 per group), chair status, group counts and failed steps. Partial runs are not presented as complete councils. This is NOT factual verification of AI claims.
- Detect and flag citations to **unknown source filenames** in addition to known-file line numbers. Reference audits remain lexical and can miss some citation formats.
- Added centralized `ModelSpec` validation so CLI and SDK reject invalid model identifiers before constructing provider URLs.
- Removed the duplicated source-reference integrity section in Markdown reports.
- Improved browser results for incomplete council runs, source-reference warnings, and basic question-secret-check disclosure.
- Added 13 regression tests and a 5-viewport Chromium UI smoke test with mocked endpoints.
- This candidate has no real paid-provider calls, no independently measured bug-detection accuracy and no external penetration test.

## 6.1.0rc1 (2026-10-28)

- Fixed role assignment when one or two models are configured; three specialist calls always run.
- Added bounded, deterministic **source-reference presence** checks (explicitly not factual verification).
- Added optional per-specialist model selection in the browser workbench.
- Added actual reviewed source excerpts to the consent preview and removed absolute local paths from model prompts.
- Added Git ignore-rule support when scanning Git repositories and nested subfolders.
- Hardened Git revision validation, question secret warnings, and Studio configuration validation.
- Added HTTP and Chromium regression coverage; results are mocked, not paid provider calls.

## 6.0.0rc1 — Local interactive web workbench (28 October 2026)
- Added `consensustree studio` localhost-only browser app: token-authenticated HTTP API, source preview and hash-check, explicit consent, one active job, standard/hierarchical councils, progress, JSON and HTML exports.
- Preserved the separate self-contained offline Decision Studio (`dashboard`) and created a clearly fictional, stand-alone interactive UI showcase.
- Added Host / Origin / token checks, root-path containment, body limits, no web-entered API keys, no active-model calls until explicit approval, and basic sensitive-content blocking.
- Blocked all redirects in the provider HTTP adapter to reduce risk of credentials leaking to redirect destinations.
- Added HTTP integration tests using a mocked model client, Ollama HTTP transport tests against a fake local server and optional Chromium UI checks.
- This release does **not** claim external provider interoperability, model accuracy or formal security certification.

## 5.3.0 — Decision Studio refresh and defensive hardening
- Redesigned offline HTML into a responsive, polished decision workspace with dark/light themes, clickable council graph, searchable expert/group views, evidence panel and JSON audit trail.
- Added local-only JSON report import, drag-and-drop, restore sample and JSON export.
- Pinned inlined script and style content with SHA-256 CSP hashes; preserved safe, untrusted text rendering.
- Added fictional, clearly disclosed hierarchical showcase with desktop/mobile previews and dedicated usage documentation.
- Added v5.3 regression tests and cross-size Chromium interaction checks; fixed horizontal overflow on small screens.
- Fixed stale hard-coded CLI --version output; version now follows package metadata.
- No live model accuracy, deployment, cross-browser or user adoption claims are made.


## 5.2.0 — Quality and developer experience
- Added no-network `doctor` and one-command offline HTML `quickstart`.
- Added more CLI option validation and privacy dry-run visibility.
- 44 local automated tests passing in the authoring environment.

## 5.1.0 — Hardening
- Rejected redirects for authenticated GitHub PR comment calls.
- Imported test evidence is labelled user-provided and unauthenticated.
- Added hardening and integration tests.

## 5.0.0 — Plugins, PR comments and evaluation fixtures
- Explicit plugin entry-point registration; sample provider fixture.
- Manual GitHub comment preview and explicit post with `--confirm`.
- Best-effort obvious secret-pattern warnings.
- Saved report phrase-coverage evaluation (not an accuracy benchmark).

## 4.0.0 — Local dashboard and metering
- Interactive, offline HTML report explorer and call-count limiter.
- Approximate token input estimates and Dockerfile.

## 3.0.0 — Hierarchical council
- Multiple independent specialist groups, intermediate chairs, overall synthesis and group budgeting.

## 2.0.0 — Developer review
- Local Git-diff review and explicit opt-in local unittest evidence capture.

## 1.0.0 — Foundation
- Multi-provider CLI, 3-agent specialist council, Markdown/JSON reports and file scan bounds.
