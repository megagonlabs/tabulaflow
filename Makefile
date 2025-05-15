.PHONY: sync
sync:
	uv sync --all-extras --all-packages --group dev

.PHONY: mypy
mypy:
	uv run mypy mintq/
