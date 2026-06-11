.PHONY: sync
sync:
	uv sync --all-extras --all-packages --group dev

.PHONY: mypy
mypy:
	uv run mypy tabulaflow/ tests/

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
	TABULAFLOW_SCHEMA_CACHE_ENABLED=0 TABULAFLOW_SCHEMA_CACHE_REQUIRED=0 TABULAFLOW_PREPROCESSOR_CACHE_ENABLED=0 TABULAFLOW_PREPROCESSOR_CACHE_REQUIRED=0 uv run pytest -s tests/

.PHONY: test-all-python
test-all-python:
	@set -e; \
	for v in $(PYTHON_VERSIONS); do \
		echo "=== Python $$v ==="; \
		TABULAFLOW_SCHEMA_CACHE_ENABLED=0 TABULAFLOW_SCHEMA_CACHE_REQUIRED=0 TABULAFLOW_PREPROCESSOR_CACHE_ENABLED=0 TABULAFLOW_PREPROCESSOR_CACHE_REQUIRED=0 uv run --python $$v pytest -s tests/; \
	done; \
	echo "=== Restoring default venv ==="; \
	uv run --python $$(cat .python-version) python --version; \
	echo "=== All Python versions passed ==="

.PHONY: exp
exp:
	uv run scripts/arcs/print_exp.py 2>&1 | tee log/exp.out

.PHONY: test-simple
test-simple:
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run tabulaflow/research/pipelines/run_agent.py --agent simple_zero_shot --debug --dataset $$dataset; \
		uv run tabulaflow/research/pipelines/populate_exec_results.py --debug; \
		uv run tabulaflow/research/pipelines/evaluate.py --debug; \
	done

.PHONY: test-agent
test-agent:
	set -e; \
	for dataset in bird-sql spider2-snow beaver; do \
		uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --debug --dataset $$dataset; \
		uv run tabulaflow/research/pipelines/populate_exec_results.py --debug; \
		uv run tabulaflow/research/pipelines/evaluate.py --debug; \
	done


.PHONY: test-bird-direct-prompting
test-bird-direct-prompting:
	uv run tabulaflow/research/pipelines/run_agent.py --agent direct_prompting --dataset bird-sql --debug --num_few_shot_examples 0
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug


.PHONY: test-spider2-direct-prompting
test-spider2-direct-prompting:
	uv run tabulaflow/research/pipelines/run_agent.py --agent direct_prompting --dataset spider2-snow --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug


.PHONY: test-cypherbench-direct-prompting
test-cypherbench-direct-prompting:
	uv run tabulaflow/research/pipelines/run_agent.py --agent direct_prompting --dataset cypherbench --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug


.PHONY: test-cypherbench-mini-agent
test-cypherbench-mini-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent mini_agent --dataset cypherbench --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug


.PHONY: test-bird-mini-agent
test-bird-mini-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent mini_agent --dataset bird-sql --debug --num_few_shot_examples 0
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug	


.PHONY: test-spider2-mini-agent
test-spider2-mini-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent mini_agent --dataset spider2-snow --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug	


.PHONY: test-bird-tabulaflow-agent
test-bird-tabulaflow-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent tabulaflow_agent --dataset bird-sql --debug --num_few_shot_examples 0
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug	


.PHONY: test-spider2-tabulaflow-agent
test-spider2-tabulaflow-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent tabulaflow_agent --dataset spider2-snow --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug	


.PHONY: test-spider2-dbs-tabulaflow-agent
test-spider2-dbs-tabulaflow-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent tabulaflow_agent --dataset spider2-snow --databases $(DBS) --llm openai-responses:gpt-5 --openai_reasoning_effort medium --batch_size 100 --overwrite
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug	

.PHONY: test-spider2-get-json-schema-tabulaflow-agent
test-spider2-get-json-schema-tabulaflow-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent tabulaflow_agent --dataset spider2-snow --llm openai-responses:gpt-5 --openai_reasoning_effort medium --batch_size 100 --overwrite --qids sf_bq010 sf_bq001 sf_bq002 sf_bq003 sf_bq004 sf_bq008 sf_bq268 sf_bq270 sf_bq091 sf_bq033 sf_bq209 sf_bq027 sf_bq210 sf_bq212 sf_bq214 sf_bq127 sf_bq215 sf_bq036 sf_bq182 sf_bq248 sf_bq193 sf_bq255 sf_bq359 sf_bq291 sf_bq348 sf_bq253 sf_bq068 sf_bq092 sf_bq065 sf_bq063 sf_bq028 sf_bq090 sf_bq442 sf_bq102 sf_bq445 sf_bq103 sf_bq124 sf_bq366 sf_bq346 sf_bq421 sf_bq451 sf_bq452 sf_bq453 sf_bq412 sf_bq423 sf_bq070 sf_bq324 sf_ga001 sf_ga002 sf_ga007 sf_ga031 sf_ga032 sf_ga006 sf_ga009 sf_ga014 sf_ga012
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent
test-bird-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-a199-agent
test-bird-a199-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --num_few_shot_examples 0 --do_schema_linking 0 --do_postprocessing 0 --agent sql_agent --dataset bird-sql --split a199 --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --batch_size 50 --log_level INFO
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug


.PHONY: test-bird-postprocessor
test-bird-postprocessor:
	uv run tabulaflow/research/pipelines/run_agent.py --overwrite --num_few_shot_examples 0 --TMP_resume_exp_for_postprocessor output/206_gpt-5-mini-medium-percentage/ --agent sql_agent --dataset bird-sql --split dev_20240627 --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --batch_size 50 --log_level INFO
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent-qids
test-bird-agent-qids:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --qids $(QIDS) --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --batch_size 50
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-challenging-agent
test-bird-challenging-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --difficulty challenging --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --batch_size 50
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-moderate-agent
test-bird-moderate-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --difficulty moderate --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --batch_size 50
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird25-agent
test-bird25-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --split dev_20251106 --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --batch_size 50
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent-gpt-5
test-bird-agent-gpt-5:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent-gpt-5-mini
test-bird-agent-gpt-5-mini:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-thrombosis-agent-gpt-5-mini
test-bird-thrombosis-agent-gpt-5-mini:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --databases thrombosis_prediction --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent-gpt-5-mini-minimal
test-bird-agent-gpt-5-mini-minimal:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort minimal
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-ambrosia-simple
test-ambrosia-simple:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset ambrosia-s --split test --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-ambrosia-flat
test-ambrosia-flat:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset ambrosia-s --split test --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-ambrosia-structured
test-ambrosia-structured:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset ambrosia-s --split test --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-ambrosia-structured-with-taxonomy
test-ambrosia-structured-with-taxonomy:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset ambrosia-s --split test --debug --include_taxonomy
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple
test-arcs-simple:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-patience-1
test-arcs-simple-patience-1:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --user_patience 1
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-gpt-5-low
test-arcs-simple-gpt-5-low:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort low
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-gpt-5-medium
test-arcs-simple-gpt-5-medium:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-gpt-5-high
test-arcs-simple-gpt-5-high:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort high
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-qwen
test-arcs-simple-qwen:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-coder-480b-a35b-instruct
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-flat
test-arcs-flat:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset arcs --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-flat-gpt-5-medium
test-arcs-flat-gpt-5-medium:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-flat-all-query
test-arcs-flat-all-query:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset arcs --debug --no_query_for_intended_only
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured
test-arcs-structured:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-with-taxonomy
test-arcs-structured-with-taxonomy:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --include_taxonomy
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-minimal
test-arcs-structured-gpt-5-minimal:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort minimal
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-low
test-arcs-structured-gpt-5-low:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort low
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-medium
test-arcs-structured-gpt-5-medium:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-high
test-arcs-structured-gpt-5-high:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort high
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gold-phrases
test-arcs-structured-gold-phrases:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --use_gold_phrases
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gold-ambiguity-points
test-arcs-structured-gold-ambiguity-points:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --use_gold_ambiguity_points
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-all-query
test-arcs-structured-all-query:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --no_query_for_intended_only
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-deepseek
test-arcs-structured-deepseek:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/deepseek-r1-0528
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gemini
test-arcs-structured-gemini:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm google-vertex:gemini-2.0-flash
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gemini-3
test-arcs-structured-gemini-3:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm google-vertex:gemini-3-pro-preview
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gemini-2.5-flash
test-arcs-structured-gemini-2.5-flash:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm google-vertex:gemini-2.5-flash
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-claude
test-arcs-structured-claude:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm anthropic:claude-sonnet-4-5-20250929
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen-together
test-arcs-structured-qwen-together:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm together:Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen
test-arcs-structured-qwen:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-coder-480b-a35b-instruct
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen-235b-instruct
test-arcs-structured-qwen-235b-instruct:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-235b-a22b-instruct-2507
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen-235b-thinking
test-arcs-structured-qwen-235b-thinking:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-235b-a22b-thinking-2507
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-kimi-k2-thinking
test-arcs-structured-kimi-k2-thinking:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/kimi-k2-thinking
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-glm-4p6
test-arcs-structured-glm-4p6:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/glm-4p6
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-minimax-m2
test-arcs-structured-minimax-m2:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/minimax-m2
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen3-8b
test-arcs-structured-qwen3-8b:
	TABULAFLOW_MAX_LLM_CONCURRENCY=1 TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-8b
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gptoss
test-arcs-structured-gptoss:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/gpt-oss-120b
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-llama
test-arcs-structured-llama:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/llama-v3p1-405b-instruct
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-kimi
test-arcs-structured-kimi:
	uv run tabulaflow/research/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/kimi-k2-instruct
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-spider2-dbt-agent
test-spider2-dbt-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent dbt_agent --dataset spider2-dbt --debug  --llm openai-responses:gpt-5.3-codex --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-spider2-dbt-bash-agent
test-spider2-dbt-bash-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent dbt_agent --dataset spider2-dbt --debug --use_bash_tool --llm openai-responses:gpt-5.3-codex --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-spider2-dbt-bash-agent-qids
test-spider2-dbt-bash-agent-qids:
	uv run tabulaflow/research/pipelines/run_agent.py --agent dbt_agent --dataset spider2-dbt --debug --llm openai-responses:gpt-5.3-codex --openai_reasoning_effort medium --qids $(QIDS)
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: test-spider2-agent
test-spider2-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset spider2-snow --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium
	uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug
	uv run tabulaflow/research/pipelines/analyze_errors.py --debug

.PHONY: test-beaver-agent
test-beaver-agent:
	uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset beaver --debug
	uv run tabulaflow/research/pipelines/evaluate.py --debug

.PHONY: diff-schema
diff-schema:
	@bash -c 'diff -u --color=always <(uv run scripts/print_schema.py --no_description --file cache/schemas/bird-sql+$(DB).json) <(uv run scripts/print_schema.py --no_description --file cache/preprocessors/schema_preprocessor/bird-sql+$(DB).json) || true'

.PHONY: sqlite
sqlite:
	sqlite3 data/BIRD-SQL/dev_20240627/dev_databases/$(DB)/$(DB).sqlite

.PHONY: last-trajectory
last-trajectory:
	@dir=$$(ls -td ~/.tabulaflow/sessions/*/trajectories 2>/dev/null | head -n 1); \
	[ -n "$$dir" ] && find "$$dir" -type f -exec stat -f '%m %N' {} + | sort -rn | cut -d' ' -f2-

.PHONY: list-trajectories
list-trajectories:
	@ls -tr ~/.tabulaflow/sessions/*/trajectories/trajectory.md 2>/dev/null
