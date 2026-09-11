# Quick start

TabulaFlow requires Python 3.11 or later. Add it to your project environment:

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

Stable schema, result, and serialization primitives are exported from
`tabulaflow.core`. Connectors and agent runtime APIs live in
`tabulaflow.data` and `tabulaflow.agents` respectively.

Continue to the [API reference](api-reference.md) for the documented public
surface.
