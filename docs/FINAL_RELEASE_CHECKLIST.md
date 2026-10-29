# ConsensusTree AI v6.3.0rc1 — publication and release readiness

**Intended release:** a free, public, MIT-licensed experimental developer prerelease. This is not a hosted production service.

## Current GitHub publication status

Checked 29 October 2026:

- The public repository contains the project source, tests, examples, documentation and GitHub workflows on `main`.
- The latest observed cross-platform CI run passed all 12 Ubuntu, macOS and Windows jobs across Python 3.10–3.13: [CI run](https://github.com/minhajul-abedin-ai/ConsensusTree-AI/actions/runs/40807862179).
- CodeQL completed successfully on the same commit: [CodeQL run](https://github.com/minhajul-abedin-ai/ConsensusTree-AI/actions/runs/40807862161).
- The first CI run failed; cross-platform fixes were pushed and the later run passed.
- No Git tag or GitHub Release exists yet. The repository's `main` branch is not protected.
- The dependency-review workflow has not run; it is configured for pull requests or manual dispatch, and there are no pull requests.
- Repository topics are not set yet.

## Publication tasks

- [x] Create the public `ConsensusTree-AI` repository and publish the unpacked source, including `.github/` and `src/`.
- [x] Run repository CI and CodeQL on GitHub's hosted runners and address the initial CI failures.
- [x] Run an offline package/install and demo check in the authoring environment.
- [ ] Protect `main`; require the CI checks before merging changes.
- [ ] Review and enable suitable repository security features, including Dependabot alerts and security advisories; confirm GitHub secret-scanning status.
- [ ] Add accurate repository topics to improve relevant discovery.
- [ ] Create a prerelease tag and GitHub Release for `v6.3.0rc1`, titled **Experimental developer preview — not independently audited**. This release should preserve the experimental status below.
- [ ] Keep `CONSENSUSTREE_AUTO_REVIEW` disabled until its privileged workflow has been separately reviewed and tested on a disposable repository and pull request.

A static token-pattern scan of the submitted source did not identify recognized credential values. This is not an exhaustive secret scan. Do not commit provider keys or private source data.

## Gates before claiming production-grade code review

- [ ] Make authorized live requests to OpenAI, Gemini, Anthropic and Ollama; record provider/model access, failures, billing, request limits and stability. Never place credentials in issue comments or source.
- [ ] Have independent reviewers label a representative held-out set of real defects and fixed controls. Measure precision, recall, false positives, costs and latency against a comparable single-model baseline. The supplied synthetic suite does not establish these metrics.
- [ ] Commission an independent security assessment, resolve serious findings and document its scope.
- [ ] Validate the optional GitHub PR workflow in a separate test repository. Check permissions, secret restrictions, base-branch trust, comment idempotency and cost. Keep it disabled until this is complete.
- [x] Confirm the automated matrix runs on GitHub-hosted Ubuntu, macOS and Windows runners for Python 3.10–3.13.
- [ ] Test interactive installation and use on developer-owned systems; hosted CI does not replace broader user testing.
- [ ] Collect consent, privacy and error feedback from independent developers.

## Safety boundaries

The Studio is for single-user localhost use. Do not expose it through a public proxy: it has no multi-user authentication, tenant boundaries or production hosting controls. AI output is a hypothesis that requires human verification.

The optional pull-request reviewer uses `pull_request_target`, trusted base code and data-only Git diff inspection. It does not check out or execute PR-head code. It remains privileged automation and requires independent review before enabling. GitHub Actions event policies may also affect its behavior.

## Claims supported by the current evidence

- **Supported:** “Local-first open-source AI council and code-review prototype”; “MIT-licensed”; “AI-generated suggestions require verification”; “supports multiple providers through local adapters.”
- **Not established:** measured review accuracy or superiority; zero false positives; enterprise readiness; independent security certification; safe autonomous reviews; no-cost third-party API use.

