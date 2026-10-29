# ConsensusTree AI 6.2.5 RC1 — engineering and validation record

**Status:** Developer release candidate. Not an independently audited production service.

## Changes

- Smart bounded source selection (`consensustree review --smart-context --focus authentication .`) ranks changed files, nearby tests, and approximate direct dependencies. It obeys Git ignore rules, filters sensitive names, caps import analysis, and reports sampled/omitted counts. **Not** a complete semantic index or exhaustive whole-repository review.
- Model adapters now extract **provider-reported** input/output token usage from OpenAI, Gemini, Anthropic, and Ollama responses. `consensustree review ... --pricing-file rates.json` optionally computes an estimated USD cost from user supplied rates. **Not** provider invoices, current prices, or verified actual billed amounts.
- Optional `.github/workflows/ai-pr-review.yml` reviews *same-repository* PR diffs using trusted base-branch implementation, without executing PR code. Requires administrator opt-in repository variable `CONSENSUSTREE_AUTO_REVIEW=true` and an OpenAI API secret. Fork PRs are not processed. It updates its own existing bot comment to avoid duplication. The workflow is not claimed to have run on GitHub yet.
- `python -m consensustree.production_benchmark` runs the actual production Council for each opted-in benchmark case and records separate single-reviewer output. Human assessor scoring accepts only declarations by two distinct assessors and exposes disagreements and missing decisions. **No independently verified accuracy result exists without actual provider calls and external adjudicators.**
- The Studio continues to be a private loopback-only local application. Idle connections now have a 15-second timeout. No unsupported hosted multi-user deployment or cloud authentication has been introduced.
- Additional supply-chain check workflow and an external-assessor handoff document.

## Audit gates (local)

- Unit/regression tests: `python -m unittest discover -s tests -v`.
- Package: build wheel, install from isolated directory and run offline CLI commands.
- PR automation: event/SHA/consent validation and mocked end-to-end tests; GitHub Actions must run on a real repo to validate permissions.
- Live providers: `python -m consensustree.validation live --execute --timeout 2 --output live-status.json` (may incur API charges if keys exist). This environment did not provide hosted keys or a working Ollama backend.
- Accuracy: `python -m consensustree.production_benchmark run --execute --max-cases 2` **only after consent for billable requests**. Two genuinely external assessors must score outputs. No real result is claimed.
- External security review: not performed. See `docs/assessment/EXTERNAL_SECURITY_HANDOFF.md`.

## Production restrictions

- The Studio is **not** an Internet-facing service. It offers no accounts, SSO, tenant isolation, hosted billing or persistent audit log. Do not expose it through a public reverse proxy or bind it to `0.0.0.0`.
- The GitHub workflow runs only after explicit opt-in, on internal PRs, and is intentionally restricted to four model calls per PR. PR content is sent to the selected provider; repository administrators must ensure this is permitted.
- Source selection is a best-effort privacy safeguard, not a DLP scanner. Review all changed code before enabling automated third-party transmission.
- AI-detected defects remain hypotheses, even when file:line references exist.
