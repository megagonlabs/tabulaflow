from tabulaflow.app.pane import pane_panel_for_output
from tabulaflow.core import ChoiceOption, ChoiceParameter, NumberParameter, OutputSpec


def test_pane_panel_for_output_projects_parameters_to_browser_contract() -> None:
    output = OutputSpec(
        parameters=[
            ChoiceParameter(id="metric", label="Metric", choices=[ChoiceOption(id="revenue", label="Revenue")]),
            NumberParameter(id="limit", label="Limit", min=1, max=10, step=1, default=5, display="input"),
        ]
    )

    assert pane_panel_for_output(output) == {
        "controls": [
            {
                "kind": "choice",
                "id": "metric",
                "label": "Metric",
                "choices": [{"id": "revenue", "label": "Revenue"}],
            },
            {
                "kind": "number",
                "id": "limit",
                "label": "Limit",
                "min": 1,
                "max": 10,
                "step": 1,
                "default": 5,
                "display": "input",
                "unit": None,
            },
        ],
        "default_selection": {"metric": "revenue", "limit": 5},
    }
