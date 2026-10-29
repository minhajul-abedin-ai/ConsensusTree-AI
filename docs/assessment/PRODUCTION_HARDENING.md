# Deployment policy

- ConsensusTree Studio is a **local-only desktop-style application**: binds 127.0.0.1, random bearer capability token, strict Host/Origin checks, Content Security Policy, bounded requests, source path restrictions, per-run consent, one active job, no browser-exposed API keys, and a 15-second client socket timeout.
- Do not expose port 8765 publicly or put Studio behind a public load balancer. The system has **no** user authentication, TLS termination, tenant isolation, audit-log infrastructure, job queue, or abuse prevention suitable for Internet deployment.
- The Dockerfile runs unprivileged. When running untrusted filesystem content, mount repositories read-only and restrict network access unless a provider connection is explicitly needed.
- Any future cloud version needs separate credentials storage, per-user auth, RBAC, quotas, billing reconciliation, retention controls, isolation and independently tested service security.
- Provider-reported token counts and user supplied pricing are **estimates**, not provider invoices. Provider cost dashboards/billing exports are required for financial reconciliation.
