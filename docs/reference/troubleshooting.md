# Troubleshooting

## The agent starts without an LLM

Confirm that `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is available in the shell
where you launch TabulaFlow. Use `/config` to inspect model selection.

## Browser tools cannot launch

Install the supported browser runtime:

```bash
uv tool run --from playwright playwright install chromium
```

## A local file cannot be found

Relative paths resolve from the directory where TabulaFlow was launched. Use
an absolute path or restart the agent from the intended project directory.

## A database connection fails

Check the connection URL, network access, and driver-specific credentials.
Avoid pasting passwords into issue reports or logs.

For reproducible defects, open a focused
[GitHub issue](https://github.com/megagonlabs/tabulaflow/issues) with the
TabulaFlow version, operating system, and sanitized error output.
