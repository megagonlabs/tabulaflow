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

.PHONY: test-simple
test-simple:
	uv run mintq/run_model.py --model simple_zero_shot --debug
	uv run mintq/evaluate.py

.PHONY: test-agent
test-agent:
	uv run mintq/run_model.py --model sql_agent --debug
	uv run mintq/evaluate.py
