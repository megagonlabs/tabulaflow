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

.PHONY: test
test:
	uv run pytest -s tests/

.PHONY: test-simple
test-simple:
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run mintq/pipelines/run_agent.py --agent simple_zero_shot --debug --dataset $$dataset; \
		uv run mintq/pipelines/populate_exec_results.py --debug; \
		uv run mintq/pipelines/evaluate.py --debug; \
	done

.PHONY: test-agent
test-agent:
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run mintq/pipelines/run_agent.py --agent sql_agent --debug --dataset $$dataset; \
		uv run mintq/pipelines/populate_exec_results.py --debug; \
		uv run mintq/pipelines/evaluate.py --debug; \
	done

.PHONY: test-bird-agent
test-bird-agent:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple
test-arcs-simple:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-flat
test-arcs-flat:
	uv run mintq/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset arcs --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-flat-all-query
test-arcs-flat-all-query:
	uv run mintq/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset arcs --debug --no_query_for_intended_only
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured
test-arcs-structured:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-all-query
test-arcs-structured-all-query:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --no_query_for_intended_only
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-fireworks
test-arcs-structured-fireworks:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/deepseek-v3p1
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-spider2-agent
test-spider2-agent:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset spider2-snow --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-beaver-agent
test-beaver-agent:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset beaver --debug
	uv run mintq/pipelines/evaluate.py --debug
