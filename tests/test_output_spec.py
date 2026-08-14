import pytest

from tabulaflow.output.specs import (
    OutputSpec,
    ChoiceOption,
    ChoiceParameter,
    FixedResultSource,
    NumberParameter,
    ResultMetadata,
    ParameterizedSource,
    TableArtifactSpec,
    canonical_selection_key,
    validate_parameter_value,
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
        artifacts=[TableArtifactSpec(id="table", label="Top customers", source_id="top_customers")],
    )

    assert spec.default_selection == {"metric": "revenue", "min_spend": 10_000}


def test_choice_parameter_default_is_first_choice() -> None:
    spec = OutputSpec(
        parameters=[
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="profit", label="Profit"), ChoiceOption(id="revenue", label="Revenue")],
            )
        ]
    )

    assert spec.default_selection == {"metric": "profit"}


def test_choice_parameter_rejects_explicit_default_field() -> None:
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        ChoiceParameter.model_validate(
            {
                "id": "metric",
                "label": "Metric",
                "choices": [{"id": "profit", "label": "Profit"}],
                "default": "profit",
            }
        )


def test_choice_parameter_rejects_duplicate_choice_ids() -> None:
    with pytest.raises(ValueError, match="choice ids must be unique"):
        ChoiceParameter(
            id="metric",
            label="Metric",
            choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="revenue", label="Revenue again")],
        )


def test_integer_number_parameter_defaults_and_values_are_normalized_to_int() -> None:
    parameter = NumberParameter(id="top_n", label="Top N", min=1, max=5, step=1, default=3)
    spec = OutputSpec(parameters=[parameter])

    assert spec.default_selection == {"top_n": 3}
    assert validate_parameter_value(parameter, 4.0) == 4


def test_number_parameter_rejects_off_step_values() -> None:
    parameter = NumberParameter(id="top_n", label="Top N", min=1, max=5, step=1, default=3)

    with pytest.raises(ValueError, match="not aligned to step"):
        validate_parameter_value(parameter, 3.5)


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
        source_selection={"min_spend": 50_000},
        affected_rows=3,
        row_count=20,
        columns=["customer", "total_spend"],
    )

    assert record.db_alias == "workspace"
    assert record.source_selection == {"min_spend": 50_000}
    assert record.affected_rows == 3


def test_constant_result_source_has_no_inputs() -> None:
    source = FixedResultSource(id="fixed", result_id="Q1")

    assert source.result_id == "Q1"


def test_output_spec_rejects_unknown_artifact_source() -> None:
    with pytest.raises(ValueError, match="unknown source"):
        OutputSpec(artifacts=[TableArtifactSpec(id="table", source_id="missing")])


def test_output_spec_serialization_round_trip() -> None:
    spec = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="Q1")],
        artifacts=[TableArtifactSpec(id="table", source_id="fixed")],
    )

    assert OutputSpec.model_validate_json(spec.model_dump_json()) == spec
