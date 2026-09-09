# Security Policy

## Reporting a vulnerability

Report security vulnerabilities privately through
[GitHub Security Advisories](https://github.com/megagonlabs/tabulaflow/security/advisories/new).
Do not disclose an unpatched vulnerability in a public issue.

The supported beta release line is `0.1.x`. Security fixes are applied to the
latest release rather than maintained on older release lines.

## Security model

TabulaFlow is a local agent, not a sandbox. Its file, shell, browser, and data
tools run with the current user's permissions. Use trusted environments,
least-privilege credentials, and version control for important files.

Session data is stored locally under `~/.tabulaflow/`. Prompts and relevant tool
results may be sent to the configured model provider. TabulaFlow sends no
telemetry to Megagon Labs.
