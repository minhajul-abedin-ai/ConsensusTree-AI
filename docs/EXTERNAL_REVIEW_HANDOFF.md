# Independent security assessment — third-party reviewer handoff

**Status: NOT commissioned and NOT completed.** This document is a reproducible handoff package, not a certificate or security opinion.

## Engagement scope

- Target product: ConsensusTree AI local developer workbench (Python 3.10+); do **not** expose to public networks.
- Code version: v6.2.2rc1; reviewer should verify the Git commit SHA and artifact checksums supplied when commissioned.
- Threat model: remote web origins trying to access loopback services; unauthorized local browser tabs; crafted repositories; symlink paths; malicious model-generated Markdown/HTML; leaked provider credentials; GitHub comment injection; compromised provider endpoints; unsafe third-party plugins.
- Out of scope without explicit agreement: production multi-user hosting, enterprise SSO, unrelated host operating-system weaknesses, third-party model providers' own infrastructure.

## Requested independent procedures

1. Threat-model and code review, including the trust-boundary transitions from source scanner to hosted LLM provider.
2. Targeted penetration test of loopback HTTP server for authentication bypass, CSRF, DNS rebinding, Origin/Host, browser storage, XSS, HTTP parsing and concurrency/DoS.
3. Filesystem attack tests for path traversal, symlink replacement races, Git ignored/tracked secrets and source preview/consent replay.
4. Provider transport review for credential redirection, TLS/certificate validation and unsafe custom inference base URLs.
5. Software composition and supply-chain review (dependency advisories and workflows/actions).
6. Review GitHub PR comment posting and third-party plugin installation/execution risks.
7. Reproducible PoC and severity rating for each finding; retest fixes with test logs and commit IDs.

## Required signed deliverables

- Assessment dates, assessor identity, independence/conflict-of-interest declaration, covered commit hashes, tools and methodology.
- List of findings with CWE when applicable, evidence, severity, exploitability, remediation and retest outcome.
- Explicit coverage limitations and an approval/rejection recommendation.

**No security certification or external assessment is claimed until an unrelated qualified reviewer supplies these records.**
