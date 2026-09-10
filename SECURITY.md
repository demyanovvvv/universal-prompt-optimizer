# Security Policy

## Reporting a vulnerability

Please report security issues privately through the repository owner's GitHub
security contact or a private GitHub Security Advisory. Do not include API
keys, access tokens, private prompts, proprietary source code, or other secrets
in a public issue.

Include the affected version, operating system, shell, agent, model, adapter,
and a minimal reproduction that contains only synthetic data.

## Security expectations

- The installer is local-only and must not transmit prompts, files, telemetry,
  credentials, or runtime state.
- Hooks must preserve the original request unless their documented contract
  explicitly allows a safe context addition.
- Runtime state files may contain model/session identifiers and should remain
  ignored by Git.
- Never commit generated backups, hook state, credentials, or test fixtures
  containing real user data.
- Destructive, external, credential-sensitive, or materially scope-expanding
  actions require the host agent's normal approval boundary.
