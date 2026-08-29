import jinja2
import pandas as pd

from tabulaflow.research.agents.ensemblers.dbt import DBT_CANDIDATE_TEMPLATE, DBT_LLM_ENSEMBLE_SYSTEM_PROMPT
from tabulaflow.research.agents.ensemblers.utils import execution_result_key, format_execution_result


def test_execution_result_key_ignores_column_and_row_order_and_duplicates() -> None:
    first = pd.DataFrame({"b": [2.0, None, 2.0], "a": ["y", "x", "y"]})
    second = pd.DataFrame({"a": ["x", "y"], "b": [None, 2.0]})

    assert execution_result_key(first) == execution_result_key(second)


def test_execution_result_key_rounds_float_values() -> None:
    first = pd.DataFrame({"value": [1.0000001]})
    second = pd.DataFrame({"value": [1.0000002]})

    assert execution_result_key(first) == execution_result_key(second)


def test_format_execution_result_handles_empty_and_nonempty_results() -> None:
    assert format_execution_result(pd.DataFrame({"value": []})) == "(empty result)"

    formatted = format_execution_result(pd.DataFrame({"value": [1, 2]}))
    assert "value" in formatted
    assert "(2 rows)" in formatted


def test_dbt_ensemble_prompt_includes_database_and_build_status() -> None:
    system_prompt = jinja2.Template(DBT_LLM_ENSEMBLE_SYSTEM_PROMPT).render(
        dataset_instructions=None,
        db_document="source schema",
    )
    candidate = jinja2.Template(DBT_CANDIDATE_TEMPLATE).render(
        number=1,
        dbt_run_success="unknown",
        model_files={},
        output_schema="",
    )

    assert "<db_document>\nsource schema\n</db_document>" in system_prompt
    assert "<dbt_run_success>unknown</dbt_run_success>" in candidate
