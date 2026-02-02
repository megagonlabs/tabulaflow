.PHONY: sync
sync:
	uv sync --all-extras --all-packages --group dev

.PHONY: mypy
mypy:
	uv run mypy mintq/ tests/

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

.PHONY: exp
exp:
	uv run scripts/arcs/print_exp.py 2>&1 | tee log/exp.out

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
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-bird-challenging-agent
test-bird-challenging-agent:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --difficulty challenging --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-bird-moderate-agent
test-bird-moderate-agent:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --difficulty moderate --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-bird25-agent
test-bird25-agent:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --split dev_20251106 --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent-gpt-5
test-bird-agent-gpt-5:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent-gpt-5-mini
test-bird-agent-gpt-5-mini:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-bird-thrombosis-agent-gpt-5-mini
test-bird-thrombosis-agent-gpt-5-mini:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --databases thrombosis_prediction --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-bird-agent-gpt-5-mini-minimal
test-bird-agent-gpt-5-mini-minimal:
	uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug --llm openai-responses:gpt-5-mini --openai_reasoning_effort minimal --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug
	uv run mintq/pipelines/analyze_errors.py --debug

.PHONY: test-ambrosia-simple
test-ambrosia-simple:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset ambrosia-s --split test --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-ambrosia-flat
test-ambrosia-flat:
	uv run mintq/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset ambrosia-s --split test --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-ambrosia-structured
test-ambrosia-structured:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset ambrosia-s --split test --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-ambrosia-structured-with-taxonomy
test-ambrosia-structured-with-taxonomy:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset ambrosia-s --split test --debug --include_taxonomy
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple
test-arcs-simple:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-patience-1
test-arcs-simple-patience-1:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --user_patience 1
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-gpt-5-low
test-arcs-simple-gpt-5-low:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort low --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-gpt-5-medium
test-arcs-simple-gpt-5-medium:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-gpt-5-high
test-arcs-simple-gpt-5-high:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort high --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-simple-qwen
test-arcs-simple-qwen:
	uv run mintq/pipelines/run_agent.py --agent ambig_simple_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-coder-480b-a35b-instruct
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-flat
test-arcs-flat:
	uv run mintq/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset arcs --debug
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-flat-gpt-5-medium
test-arcs-flat-gpt-5-medium:
	uv run mintq/pipelines/run_agent.py --agent ambig_flat_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium --openai_reasoning_summary detailed
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

.PHONY: test-arcs-structured-with-taxonomy
test-arcs-structured-with-taxonomy:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --include_taxonomy
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-minimal
test-arcs-structured-gpt-5-minimal:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort minimal --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-low
test-arcs-structured-gpt-5-low:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort low --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-medium
test-arcs-structured-gpt-5-medium:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort medium --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gpt-5-high
test-arcs-structured-gpt-5-high:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm openai-responses:gpt-5 --openai_reasoning_effort high --openai_reasoning_summary detailed
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gold-phrases
test-arcs-structured-gold-phrases:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --use_gold_phrases
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gold-ambiguity-points
test-arcs-structured-gold-ambiguity-points:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --use_gold_ambiguity_points
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-all-query
test-arcs-structured-all-query:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --no_query_for_intended_only
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-deepseek
test-arcs-structured-deepseek:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/deepseek-r1-0528
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gemini
test-arcs-structured-gemini:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm google-vertex:gemini-2.0-flash
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gemini-3
test-arcs-structured-gemini-3:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm google-vertex:gemini-3-pro-preview
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gemini-2.5-flash
test-arcs-structured-gemini-2.5-flash:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm google-vertex:gemini-2.5-flash
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-claude
test-arcs-structured-claude:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm anthropic:claude-sonnet-4-5-20250929
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen-together
test-arcs-structured-qwen-together:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm together:Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen
test-arcs-structured-qwen:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-coder-480b-a35b-instruct
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen-235b-instruct
test-arcs-structured-qwen-235b-instruct:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-235b-a22b-instruct-2507
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen-235b-thinking
test-arcs-structured-qwen-235b-thinking:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-235b-a22b-thinking-2507
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-kimi-k2-thinking
test-arcs-structured-kimi-k2-thinking:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/kimi-k2-thinking
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-glm-4p6
test-arcs-structured-glm-4p6:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/glm-4p6
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-minimax-m2
test-arcs-structured-minimax-m2:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/minimax-m2
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-qwen3-8b
test-arcs-structured-qwen3-8b:
	MINTQ_MAX_LLM_CONCURRENCY=1 MINTQ_MAX_LLM_REQUESTS_PER_MINUTE=60 uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/qwen3-8b
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-gptoss
test-arcs-structured-gptoss:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/gpt-oss-120b
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-llama
test-arcs-structured-llama:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/llama-v3p1-405b-instruct
	uv run mintq/pipelines/populate_exec_results.py --debug
	uv run mintq/pipelines/evaluate.py --debug

.PHONY: test-arcs-structured-kimi
test-arcs-structured-kimi:
	uv run mintq/pipelines/run_agent.py --agent ambig_structured_sql_agent --dataset arcs --debug --llm fireworks:accounts/fireworks/models/kimi-k2-instruct
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

.PHONY: diff-schema
diff-schema:
	@bash -c 'diff -u --color=always <(uv run scripts/pprint_schema.py --no_description --file cache/schemas/bird-sql+$(DB).json) <(uv run scripts/pprint_schema.py --no_description --file cache/preprocessors/schema_preprocessor/bird-sql+$(DB).json) || true'

.PHONY: sqlite
sqlite:
	sqlite3 data/BIRD-SQL/dev_20240627/dev_databases/$(DB)/$(DB).sqlite
