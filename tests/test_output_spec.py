import pytest

from tabulaflow.core import (
    OutputSpec,
    ArtifactSpec,
    ChoiceOption,
    ChoiceParameter,
    FixedResultSource,
    NumberParameter,
    ResultMetadata,
    ParameterizedSource,
    TableView,
    canonical_selection_key,
)


def test_output_spec_fills_default_selection_and_validates_references() -> None:
    spec = OutputSpec(
        parameters=[
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
            ),
            NumberParameter(id="min_spend", label="Minimum spend", min=0, max=100_000, step=5_000, default=10_000),
        ],
        sources=[
            ParameterizedSource(
                id="top_customers",
                parameter_ids=["metric", "min_spend"],
                db_alias="workspace",
                query_template="SELECT 1",
            )
        ],
        artifacts=[ArtifactSpec(id="table", label="Top customers", view=TableView(source="top_customers"))],
    )

    assert spec.default_selection == {"metric": "revenue", "min_spend": 10_000}


def test_canonical_selection_key_is_stable() -> None:
    assert canonical_selection_key({"metric": "profit", "min_spend": 50_000}) == canonical_selection_key(
        {"min_spend": 50_000, "metric": "profit"}
    )


def test_parameterized_source_keeps_query_template() -> None:
    key = canonical_selection_key({"metric": "profit"})
    source = ParameterizedSource(
        id="top_customers_by_metric",
        parameter_ids=["metric"],
        db_alias="workspace",
        query_template="SELECT * FROM customers WHERE metric = {{ metric }}",
    )

    assert key == '{"metric":"profit"}'
    assert source.query_template == "SELECT * FROM customers WHERE metric = {{ metric }}"


def test_result_record_owns_query_provenance() -> None:
    record = ResultMetadata(
        id="Q2",
        db_alias="workspace",
        query="SELECT * FROM customers WHERE total_spend >= 50000",
        parameter_values={"min_spend": 50_000},
        row_count=20,
        columns=["customer", "total_spend"],
    )

    assert record.db_alias == "workspace"
    assert record.parameter_values == {"min_spend": 50_000}


def test_constant_result_source_has_no_inputs() -> None:
    source = FixedResultSource(id="fixed", result_id="Q1")

    assert source.result_id == "Q1"


def test_output_spec_rejects_unknown_artifact_source() -> None:
    with pytest.raises(ValueError, match="unknown source"):
        OutputSpec(artifacts=[ArtifactSpec(id="table", view=TableView(source="missing"))])


def test_output_spec_serialization_round_trip() -> None:
    spec = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="Q1")],
        artifacts=[ArtifactSpec(id="table", view=TableView(source="fixed"))],
    )

    assert OutputSpec.model_validate_json(spec.model_dump_json()) == spec
