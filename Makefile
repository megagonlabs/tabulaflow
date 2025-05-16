.PHONY: sync
sync:
	uv sync --all-extras --all-packages --group dev

.PHONY: mypy
mypy:
	uv run mypy mintq/

.PHONY: format
format:
	uv run ruff format mintq/
	uv run ruff check --fix mintq/

.PHONY: lint
lint:
	uv run ruff check mintq/
