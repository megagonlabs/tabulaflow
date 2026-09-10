# Configuration

Run `/config` inside the Data Agent to select model presets and inspect current
settings. Environment variables configure providers and optional integrations.

## Model credentials

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
```

Only credentials for providers you use are required.

## Command-line options

```bash
tabulaflow --help
```

The CLI includes options for the model preset, service tier, schema caching,
logging, and browser output pane. Prefer `/config` for interactive model
selection.

## Local state

Session state is stored beneath `~/.tabulaflow/`. See
[Security and privacy](security-and-privacy.md) before using sensitive data.
