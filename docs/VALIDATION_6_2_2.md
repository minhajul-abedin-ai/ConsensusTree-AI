# v6.2.2 validation protocol and known limits

## Track A — Real API compatibility

Run `python -m consensustree.validation live` to record *not-run* status without making any network calls. When authorized to spend API credits, set your own keys locally, then invoke `python -m consensustree.validation live --execute --providers openai gemini anthropic ollama`. One short model completion is attempted per selected configured provider. Errors are reported by class only; raw responses and credentials are not stored. A mocked client NEVER sets `live_verified: true`.

**Pass criterion:** `live_verified: true` and `status: passed` for each actual provider. The environment used for this release has no hosted API keys and no reachable Ollama instance; the probes are not complete.

## Track B — Code-review accuracy

`benchmarks/accuracy_cases.json` includes 50 synthetic **author-labelled** Python examples: 25 unsafe and 25 safer counterparts in 10 risk families. They are small teaching examples, not an independently adjudicated real-world corpus. A genuine third-party quality result requires an external reviewer to independently validate labels, sample cases representative of real user repositories, record multiple random seeds and compare single-model and council under identical provider versions.

Run `python -m consensustree.validation accuracy --execute --provider PROVIDER --model MODEL --max-cases 2 --max-calls 10` after configuring your model; a complete 50-case run requires 250 calls (one single specialist and four council calls per case). Increase caps **only** after approving the provider's pricing and budget. Each case's expected label stays out of model prompts. The evaluator strictly parses `VERDICT: ISSUE` or `VERDICT: NO_ISSUE`; unmatched responses are *abstentions* and are never silently classified. It reports TP/FP/TN/FN, precision, recall, F1, specificity, and coverage.

**Benchmark integrity caveat:** this controlled protocol uses the same `LLMClient` provider transport and a three-specialist-plus-chair topology, but DOES NOT execute the exact production `Council.review_snapshot()` function with its ordinary free-form Markdown prompts. Thus the benchmark is useful for prototyping accuracy measurement, but **does not prove deployed ConsensusTree council accuracy**. Successful provider calls are necessary to generate any empirical scores.

## Track C — Internal security assessment

Run `python -m unittest discover -s tests -p test_security_assessment.py -v`. Tests exercise local HTTP authentication, Host/Origin controls, path traversal, oversized bodies, malformed JSON, consent, secret warnings, XSS escaping, response headers, and remote Ollama URL blocking. A pass confirms these scenarios, **not** broad penetration-test coverage. Tests use an injected fake model and should never contact an external API. The audit does not cover unknown dependency CVEs, side-channel weaknesses, a malicious local user, credentials leaked inside otherwise normal source content, symlink races, hostile repository execution, or security of a public hosted service (which is unsupported).

### External assessor handoff

See `docs/EXTERNAL_REVIEW_HANDOFF.md`. An independent assessor must test a separately verified revision and sign the findings before the project can claim external security review.
