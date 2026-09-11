# Security and privacy

TabulaFlow stores session data on your machine. It may send prompts and relevant
tool results to your model provider, but it sends no telemetry to Megagon Labs.

## Trusted local agent

TabulaFlow is not a sandbox. Its file, shell, browser, and data tools use your
permissions. Run it only in trusted environments and use least-privilege
credentials.

## Local data

TabulaFlow stores conversation history, workspace data, and logs under
`~/.tabulaflow/`. Review this directory before sharing or disposing of a
machine used with sensitive data.

## External services

Your provider's terms and retention policy apply to content sent to an LLM or
tracing service. Use only services approved for your data.

## Report a vulnerability

Please report vulnerabilities privately through
[GitHub Security Advisories](https://github.com/megagonlabs/tabulaflow/security/advisories/new),
not through a public issue.
