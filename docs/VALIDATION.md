# Version 5.3 validation and release audit

## What has been checked

- Python unittest suite with mocked provider results; includes legacy v1 tests plus v2–v5.3 behavior.
- Offline CLI fixture, source scanner dry-run, Git-diff dry-run in a temporary Git repository.
- Hierarchical call accounting, request budgets, safe HTML serialization and XSS-breakout cases.
- Best-effort secret warnings that do not echo matched values; source processing halts unless overridden.
- Explicit test execution consent and separate provenance disclaimers for imported test output.
- GitHub comment preview is no-network, uses explicit confirm to post, and redirects are refused.
- Explicit plugin loading and fixture client call path; no live provider keys required.
- Self-contained dashboard HTML; no third-party scripts or telemetry.
- Offline benchmark fixture reader with path traversal rejection.

## What has NOT been validated

- Live OpenAI/Gemini/Anthropic API responses, model drift, rate limits and costs.
- Actual Ollama inference, real GitHub comment posting, Docker build or hosted cloud deployment.
- Prompt injection defenses under realistic adversarial code, a formal independent security audit.
- Accuracy, recall or precision of AI bug findings compared with expert-labelled datasets.
- Improvement compared with single-model review or existing council/evaluation products.
- Usability, adoption, contributor engagement, installs, retention, or GitHub star growth.
- Plugin safety; third-party plugins execute locally, by user consent.
- Comprehensive secret detection or `.gitignore` rules. Do not use this as a security boundary.

## Release stage

**Developer preview / experimental**. Suitable for personal testing, code contributions and demonstrations. It is **not yet ready for a claim of production-ready vulnerability scanning, verified decisions or superior review accuracy**.

## Conditions before promoting to beta

1. Run integration tests using real provider keys under controlled billing limits.
2. Run on clean Linux, macOS, and Windows systems; verify Docker image builds and sample commands.
3. Conduct an independent dependency and static security assessment and prompt-injection red team.
4. Build at least 50 independently labelled bug-fix or review cases, compare against one-model and existing-tool baselines, and publish failure cases.
5. Onboard at least 10 external developers and address usability failures from their feedback.

## Star-goal assessment

A 10,000-star target is **not fulfilled by having five versions**. It requires a publicly accessible repository with at least 10,000 actual stars. No public project link, usage cohort, independent benchmark, or tracked star count was supplied during this build. Treat the goal as **unachieved/unverified** until GitHub itself confirms it.

## v5.3 browser checks

- Chromium smoke tests exercised at desktop and mobile sizes, including local JSON import, export, navigation, themed modes, groups, injection-text handling and zero external network requests.
- A mobile horizontal overflow defect was identified and corrected, then retested at widths 360, 390, 414, 768, 1024 and 1440 pixels.
- Static scripts and styles have SHA-256 CSP hashes.
- Browser tests do not establish accessibility conformance, universal browser compatibility, or security certification.

## v6 RC1 local Studio validation (28 October 2026)

- Implemented a localhost-only web workbench alongside, not replacing, the v5.3 offline report explorer.
- 70 Python tests passed on Python 3.13.5, including actual local HTTP endpoint tests with fake model completions and an Ollama-compatible fake HTTP API. No billed inference calls were made.
- The separately labelled offline UI showcase passed Playwright/Chromium checks at 360, 390, 768, 1024 and 1440 pixel widths, covering navigation, mock review flow, consent, JSON download, mode switch and theme. No horizontal overflow detected.
- The built Python wheel includes `studio.py`, `studio_template.html` and `dashboard_template.html`. Source code compiles, and CLI smoke checks pass.
- **Important test boundary:** Chromium in the authoring environment refused direct navigation to localhost pages. The HTTP server and the visual browser UI were tested separately, not in one connected end-to-end Chromium session. This gap remains for a fresh-machine smoke test.
- Live provider calls, hosted deployment, Safari/Firefox, platform matrix, security certification and independent accuracy benchmarks are still unverified. See [STUDIO.md](STUDIO.md).


## Additional v6.2 checks (28 October 2026)

- 96 Python unittest tests passed, including 13 v6.2 regressions.
- Five responsive Chromium viewport checks passed with mocked HTTP endpoints and a partial-council warning check.
- Evidence presence is lexical; correctness and true detection performance have not been independently benchmarked.
- Provider contracts remain mocked. Actual OpenAI, Gemini, Anthropic and Ollama inference smoke tests are NOT completed.
- No external security assessment, cross-platform installation certification or public GitHub adoption has been performed.

## v6.2.1 adversarial regressions

`tests/test_v621_hardening.py` checks cross-folder replay attempts, broken Git metadata, ignored-file selection and filename delimiter spoofing. These local tests do not establish AI defect-detection precision or real provider compatibility.
