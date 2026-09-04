.PHONY: sync
sync:
	uv sync --all-extras --all-packages --group dev
	uv run playwright install chromium

.PHONY: list-trajectories
list-trajectories:
	@uv run python -c "from datetime import datetime; from pathlib import Path; paths = sorted((Path.home() / '.tabulaflow').rglob('trajectories/trajectory.md'), key=lambda path: (path.stat().st_mtime, str(path))); print(*(f'{datetime.fromtimestamp(path.stat().st_mtime):%Y-%m-%d %H:%M:%S} {path}' for path in paths), sep='\n')"

.PHONY: mypy
mypy:
	uv run mypy tabulaflow/ tests/ scripts/

.PHONY: format
format:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: lint
lint:
	uv run ruff check .

.PHONY: lint-arch
lint-arch:
	uv run lint-imports

PYTHON_VERSIONS := 3.11 3.12 3.13

.PHONY: test
test:
	TABULAFLOW_SCHEMA_CACHE_ENABLED=0 TABULAFLOW_SCHEMA_CACHE_REQUIRED=0 TABULAFLOW_PREPROCESSOR_CACHE_ENABLED=0 TABULAFLOW_PREPROCESSOR_CACHE_REQUIRED=0 uv run pytest tests/

.PHONY: test-all-python
test-all-python:
	@set -e; \
	for v in $(PYTHON_VERSIONS); do \
		echo "=== Python $$v ==="; \
		TABULAFLOW_SCHEMA_CACHE_ENABLED=0 TABULAFLOW_SCHEMA_CACHE_REQUIRED=0 TABULAFLOW_PREPROCESSOR_CACHE_ENABLED=0 TABULAFLOW_PREPROCESSOR_CACHE_REQUIRED=0 uv run --python $$v pytest tests/; \
	done; \
	echo "=== Restoring default venv ==="; \
	uv run --python $$(cat .python-version) python --version; \
	echo "=== All Python versions passed ==="


.PHONY: test-bird-direct-prompting
test-bird-direct-prompting:
	uv run tabulaflow/research/pipelines/predict.py --agent direct_prompting --dataset bird-sql --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-cypherbench-full-schema
test-cypherbench-full-schema:
	uv run tabulaflow/research/pipelines/predict.py --agent full_schema --dataset cypherbench --databases nba --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-spider2-schema-discovery
test-spider2-schema-discovery:
	uv run tabulaflow/research/pipelines/predict.py --agent schema_discovery --dataset spider2-snow --databases AIRLINES --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-bird-schema-linking
test-bird-schema-linking:
	uv run tabulaflow/research/pipelines/predict.py --agent schema_linking --dataset bird-sql --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-spider2-schema-linking
test-spider2-schema-linking:
	uv run tabulaflow/research/pipelines/predict.py --agent schema_linking --dataset spider2-snow --databases AIRLINES --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-arcs-simple
test-arcs-simple:
	uv run tabulaflow/research/pipelines/predict.py --agent ambig_simple_sql_agent --dataset arcs --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-arcs-flat
test-arcs-flat:
	uv run tabulaflow/research/pipelines/predict.py --agent ambig_flat_sql_agent --dataset arcs --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-arcs-structured
test-arcs-structured:
	uv run tabulaflow/research/pipelines/predict.py --agent ambig_structured_sql_agent --dataset arcs --subsample-size 5 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/execute.py output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test

.PHONY: test-spider2-dbt-agent
test-spider2-dbt-agent:
	uv run tabulaflow/research/pipelines/predict.py --agent dbt_agent --dataset spider2-dbt --databases zuora001 --overwrite --output-dir output/test
	uv run tabulaflow/research/pipelines/evaluate.py output/test
