# Troubleshooting

## The agent starts without an LLM

Check that `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set in the shell where you
launch TabulaFlow. Run `/config` to inspect the selected model.

## Browser tools cannot launch

Install the supported browser runtime:

```bash
uv tool run --from playwright playwright install chromium
```

## A local file cannot be found

Relative paths start from the directory where you launched TabulaFlow. Use an
absolute path or restart the agent from the right project directory.

## A database connection fails

Check the connection URL, network access, and driver credentials. Keep
passwords out of issue reports and logs.

If the problem continues, open a focused [GitHub
issue](https://github.com/megagonlabs/tabulaflow/issues). Include your
TabulaFlow version, operating system, and sanitized error output.
