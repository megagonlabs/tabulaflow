# Contributing

Bug reports and focused pull requests are welcome. Open an issue before a large
change so its scope and design can be agreed on first.

## Development setup

TabulaFlow requires Python 3.11 or later and uses
[`uv`](https://docs.astral.sh/uv/) for Python operations.

```bash
git clone https://github.com/megagonlabs/tabulaflow.git
cd tabulaflow
make sync
```

## Checks

Run the relevant tests while developing, then run the full project checks:

```bash
make lint
make mypy
make lint-arch
make test
```

Use `make format` to apply Ruff formatting and safe lint fixes. Keep changes
focused, update documentation for user-visible behavior, and never include API
keys, credentials, private data, caches, or experiment outputs.

Submit changes from a short-lived branch into `main`. Describe the motivation,
behavioral changes, and verification in the pull request.

## Documentation

Preview the documentation with the optional `docs` dependency group:

```bash
uv run --group docs mkdocs serve
```

Check the documentation before submitting changes:

```bash
uv run --group docs mkdocs build --strict
```

API references in `docs/python-library/api/` and `docs/research-toolkit/api/`
select public objects with mkdocstrings directives. Update signatures and
docstrings in the Python source; keep reference introductions and examples
in Markdown. Add new reference pages to `mkdocs.yml`.
