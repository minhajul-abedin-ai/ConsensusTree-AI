# Independent security assessment request — scope and evidence requirements

**This document is a handoff, not an external certification or a penetration-test report.**

## Scope

Assess v6.2.5 RC1 source and its local-only Studio, user-approved repository source scanner, all four provider API adapters, GitHub PR workflow, automated GitHub comments, CI supply chain, and privacy preflight. Test Linux, Windows and macOS as relevant.

Priority scenarios: DNS rebinding, Host/Origin/capability-token bypass, CSRF, unauthorized localhost requests, slow HTTP requests, symlink and path races, Git diff option injection, malicious PR metadata, compromised PR-content prompt injection, token exfiltration, redirect handling, secrets in source previews/reports, malicious plugin execution, dependency supply chain and malicious GitHub Actions changes.

## Rules of engagement

- Tester uses a sandbox repository, dummy keys and pre-agreed test infrastructure.
- No actual third-party private repositories or live production secrets.
- Do not run arbitrary untrusted repository tests unless sandboxed and separately approved.
- Do not claim production-grade security from passing unit tests.

## Required deliverables from assessor

1. Named independent assessor and organizational affiliation, engagement date, scope and tested commit SHA.
2. Reproducible proof for each finding, severity (with reason), affected files, exploit prerequisites and remediation.
3. Evidence of retesting each remediated high/critical finding, plus unresolved risk list.
4. Signed report and explicit statement of tools, methodology and testing limitations.
5. Approval or rejection decision for the proposed release/deployment context.

No external assessor has completed this engagement in the current development session.
