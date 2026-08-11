import pytest

from tabulaflow.core import (
    OutputSpec,
    ArtifactSpec,
    ChoiceOption,
    ChoiceParameter,
    ConstantResultPlan,
    NumberParameter,
    QueryPlan,
    ResultLookupPlan,
    ResultRecord,
    ResultVariant,
    SourceDef,
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
            SourceDef(
                id="top_customers",
                parameter_ids=["metric", "min_spend"],
                plan=QueryPlan(db_alias="workspace", query_template="SELECT 1"),
            )
        ],
        artifacts=[ArtifactSpec(id="table", label="Top customers", view=TableView(source="top_customers"))],
    )

    assert spec.default_selection == {"metric": "revenue", "min_spend": 10_000}


def test_canonical_selection_key_is_stable() -> None:
    assert canonical_selection_key({"metric": "profit", "min_spend": 50_000}) == canonical_selection_key(
        {"min_spend": 50_000, "metric": "profit"}
    )


def test_result_lookup_plan_uses_canonical_selection_keys() -> None:
    key = canonical_selection_key({"metric": "profit"})
    source = SourceDef(
        id="top_customers_by_metric",
        parameter_ids=["metric"],
        plan=ResultLookupPlan(variants=[ResultVariant(selection={"metric": "profit"}, result_id="Q2")]),
    )

    assert isinstance(source.plan, ResultLookupPlan)
    assert canonical_selection_key(source.plan.variants[0].selection) == key
    assert source.plan.variants[0].result_id == "Q2"


def test_result_record_owns_query_provenance() -> None:
    record = ResultRecord(
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
    source = SourceDef(id="fixed", plan=ConstantResultPlan(result_id="Q1"))

    assert source.parameter_ids == []
    assert isinstance(source.plan, ConstantResultPlan)


def test_output_spec_rejects_unknown_artifact_source() -> None:
    with pytest.raises(ValueError, match="unknown source"):
        OutputSpec(artifacts=[ArtifactSpec(id="table", view=TableView(source="missing"))])


def test_output_spec_serialization_round_trip() -> None:
    spec = OutputSpec(
        sources=[SourceDef(id="fixed", plan=ConstantResultPlan(result_id="Q1"))],
        artifacts=[ArtifactSpec(id="table", view=TableView(source="fixed"))],
    )

    assert OutputSpec.model_validate_json(spec.model_dump_json()) == spec
