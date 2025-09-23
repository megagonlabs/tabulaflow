.PHONY: sync
sync:
	uv sync --all-extras --all-packages --group dev

.PHONY: mypy
mypy:
	uv run mypy mintq/ tests/ scripts/

.PHONY: format
format:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: lint
lint:
	uv run ruff check .

.PHONY: test-simple
test-simple:
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run mintq/pipelines/run_agent.py --model simple_zero_shot --debug --dataset $$dataset; \
		uv run mintq/pipelines/evaluate.py --debug; \
	done

.PHONY: test-agent
test-agent:
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run mintq/pipelines/run_agent.py --model sql_agent --debug --dataset $$dataset; \
		uv run mintq/pipelines/evaluate.py --debug; \
	done

.PHONY: test-bird-multi-agent-v1
test-bird-multi-agent-v1:
	uv run mintq/pipelines/run_agent.py --model sql_multi_agent_v1 --dataset bird-sql --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-bird-agent
test-bird-agent:
	uv run mintq/pipelines/run_agent.py --model sql_agent --dataset bird-sql --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-bird-agent-v1
test-bird-agent-v1:
	uv run mintq/pipelines/run_agent.py --model sql_agent_v1 --dataset bird-sql --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-bird-agent-v2
test-bird-agent-v2:
	uv run mintq/pipelines/run_agent.py --model sql_agent_v2 --dataset bird-sql --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-spider2-agent
test-spider2-agent:
	uv run mintq/pipelines/run_agent.py --model sql_agent --dataset spider2-snow --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-beaver-agent
test-beaver-agent:
	uv run mintq/pipelines/run_agent.py --model sql_agent --dataset beaver --debug
	uv run mintq/pipelines/evaluate.py --debug
