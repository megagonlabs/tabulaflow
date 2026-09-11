# Quick start

TabulaFlow requires Python 3.11 or later. Add it to your project:

=== "uv"

    ```bash
    uv add tabulaflow
    ```

=== "pip"

    ```bash
    pip install tabulaflow
    ```

Verify the installation:

```bash
python -c "import tabulaflow; print(tabulaflow.__version__)"
```

Import schema, result, and serialization primitives from `tabulaflow.core`.
Connectors live in `tabulaflow.data`; agent runtimes live in
`tabulaflow.agents`.

See the [API reference](api-reference.md) for supported public modules.
