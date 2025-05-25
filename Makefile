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
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run mintq/run_model.py --model simple_zero_shot --debug --dataset $$dataset; \
		uv run mintq/evaluate.py --debug; \
	done

.PHONY: test-agent
test-agent:
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run mintq/run_model.py --model sql_agent --debug --dataset $$dataset; \
		uv run mintq/evaluate.py --debug; \
	done

.PHONY: test-spider2-agent
test-spider2-agent:
	uv run mintq/run_model.py --model sql_agent --dataset spider2-snow --debug
	uv run mintq/evaluate.py --debug

.PHONY: test-beaver-agent
test-beaver-agent:
	uv run mintq/run_model.py --model sql_agent --dataset beaver --debug
	uv run mintq/evaluate.py --debug
