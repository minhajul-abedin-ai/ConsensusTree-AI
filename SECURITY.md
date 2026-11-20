# Security and privacy

**Experimental software. Do not rely on it as a standalone secret scanner, vulnerability auditor or sandbox.**

Hosted provider calls or client plugins can receive code, diffs and questions. `--dry-run` prints file names, but source must be inspected independently. A small set of known secret patterns is blocked unless `--allow-sensitive` is supplied; many secrets will be missed. `.gitignore` rules are not fully parsed.

- Use environment variables for provider API keys and a least-privilege GitHub token; never commit them. `doctor` prints key presence only.
- Default GitHub PR comment mode is preview; `--confirm` performs a real post. Be sure the intended PR and text are correct. Redirects from GitHub comment POST are refused.
- Local `verify --unsafe-execute` runs **arbitrary Python test code in that repository**. Only invoke on code you already trust, ideally inside a disposable, isolated environment that you operate.
- The HTML dashboard renders untrusted text using DOM text operations and escapes JSON embedded in the HTML template. Avoid running unknown alternative dashboards.
- Third-party plugins are executable Python code, loaded only when explicitly named. Vet the package and pin dependencies.
- Model transcripts, code snapshots and imported test logs remain untrusted and susceptible to prompt injection. Model agreement is not verification. Imported evidence JSON can be forged.
- Some provider calls and URLs rely on those providers' APIs. Check current provider data handling, retention and billing terms before uploading private code.

Report vulnerabilities privately through GitHub's security advisory interface **after** a public repository is created. Never put sensitive exploit details or access tokens in public issues.

## v6 Local Studio threat model

The `consensustree studio` web interface is for **single-user localhost use only**. It binds to `127.0.0.1`, uses a random per-launch capability token, checks request Host and Origin, rejects paths outside the pre-selected source root and requires explicit consent to send code to an AI provider. Access-token URLs must not be shared. No API key should be pasted into the interface. A basic content pattern check is not a comprehensive secret scanner; review snapshots carefully before submission.

This does **not** constitute a security audit, user authentication system for teams, sandboxed file execution, or a production web deployment. The live browser-server connection was not fully exercised by Chromium in the authoring environment due to local-network browser restrictions; the HTTP endpoints and browser UI were tested separately. The exported HTML viewer is an offline tool, not a hosted service.

## v6.2.1 additional protections

Studio source consent binds both the reviewed location and exact excerpt. Git metadata that exists but cannot be read will block source selection rather than bypass ignore rules. Control characters in source path names are excluded. Neither protection is an exhaustive credential scanner or security audit.

## v6.3.0 PR automation trust boundary

The optional credentialed workflow uses GitHub's `pull_request_target` event, trusted base SHA checkout and data-only diff reading. It never checks out or executes the PR head. It is **disabled unless** an administrator sets `CONSENSUSTREE_AUTO_REVIEW=true` and adds an appropriate API key secret. Fork PRs are excluded. Administrators must validate the real workflow and their GitHub Actions policy before enabling it; do not assume automated scans are a substitute for independent security review.

The CLI rejects HTTP-based remote Ollama endpoints to reduce accidental transmission of local source over plaintext connections (local HTTP loopback remains supported). This is a guardrail, not a guarantee of end-to-end confidentiality, and TLS configuration is the operator's responsibility.

## Dependency-review workflow availability

GitHub's `actions/dependency-review-action` requires GitHub Dependency Graph support for this repository. A pull-request run on 12 November 2026 failed with `Dependency review is not supported on this repository`. This is a GitHub feature/configuration limitation, **not** a successful vulnerability audit.

Until an administrator verifies support, the workflow's `dependency-review` job is intentionally skipped and the `dependency-review-capability-notice` job emits an explicit warning on pull requests. Unit/security regression tests and CodeQL continue separately. **Do not interpret a green workflow as evidence that dependency-review scanning ran.**

To enable the real dependency-review gate:

1. In repository **Settings → Security → Code security and analysis**, enable/verify the **Dependency graph** and check that GitHub Dependency Review is supported for the repository.
2. Under **Settings → Secrets and variables → Actions → Variables**, create `DEPENDENCY_REVIEW_ENABLED` with the exact value `true`.
3. Open a pull request and verify the `dependency-review` job actually executes and succeeds. If the job reports unsupported again, remove the variable and investigate the GitHub account/repository feature availability rather than claiming coverage.

The opt-in variable does not enable GitHub's platform feature by itself. Dependency review is not a substitute for external security assessment.
