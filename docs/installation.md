# Installation

TabulaFlow requires Python 3.11 or later and supports macOS and Linux.

## Install the Data Agent

[`uv`](https://docs.astral.sh/uv/) is the recommended installation method:

```bash
uv tool install tabulaflow
uv tool run --from playwright playwright install chromium
```

The Chromium installation is required only for browser tools.

## Install as a Python library

=== "uv"

    ```bash
    uv add tabulaflow
    ```

=== "pip"

    ```bash
    pip install tabulaflow
    ```

## Verify the installation

```bash
tabulaflow --help
tabulaflow benchmark list
```

Continue to the [quick start](data-agent/quick-start.md) to launch the agent with bundled
sample data.
