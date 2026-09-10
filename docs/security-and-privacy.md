# Security and privacy

TabulaFlow stores session data locally. Prompts and relevant tool results may
be sent to the configured model provider. TabulaFlow sends no telemetry to
Megagon Labs.

## Trusted local agent

TabulaFlow is not a sandbox. Its file, shell, browser, and data tools operate
with the current user's permissions. Run it only in trusted environments and
use least-privilege credentials.

## Local data

Session state is stored beneath `~/.tabulaflow/`. The directory can include
conversation history, workspace data, and operational logs. Review it before
sharing or disposing of a machine used with sensitive data.

## External services

Content sent to an LLM or tracing provider is governed by that provider's
terms and retention policy. Configure only services approved for your data.

## Report a vulnerability

Report vulnerabilities privately through
[GitHub Security Advisories](https://github.com/megagonlabs/tabulaflow/security/advisories/new),
not through a public issue.
