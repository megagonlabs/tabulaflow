from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import genai_prices
import pytest
from pydantic_ai.messages import BinaryContent, ModelRequest, UserPromptPart

from tabulaflow.agents.trace import Trajectory, Usage, compute_api_cost


def test_compute_api_cost_uses_genai_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    calc_price = Mock(return_value=SimpleNamespace(total_price=Decimal("1.23")))
    monkeypatch.setattr(genai_prices, "calc_price", calc_price)

    cost = compute_api_cost("google-cloud:gemini-test", input_tokens=10, output_tokens=20)

    assert cost == Decimal("1.23")
    usage = calc_price.call_args.args[0]
    assert usage.input_tokens == 10
    assert usage.output_tokens == 20
    assert calc_price.call_args.kwargs == {"model_ref": "gemini-test", "provider_id": "google"}


def test_compute_api_cost_returns_zero_for_unknown_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(genai_prices, "calc_price", Mock(side_effect=LookupError))

    assert compute_api_cost("openai:unknown", input_tokens=10, output_tokens=20) == 0


def test_usage_create_preserves_decimal_value_of_float() -> None:
    usage = Usage.create(api_cost_usd=0.1)

    assert usage.api_cost_usd == Decimal("0.1")


def test_usage_create_requires_model_for_requests() -> None:
    with pytest.raises(ValueError, match="llm is required"):
        Usage.create(api_requests=1)


def test_trajectory_describes_media_without_serializing_bytes() -> None:
    trajectory = Trajectory.from_pydantic_ai_messages(
        [
            ModelRequest(
                parts=[UserPromptPart(content=["inspect", BinaryContent(b"secret payload", media_type="image/png")])]
            )
        ]
    )

    content = trajectory.messages[0].content  # type: ignore[union-attr]
    assert "inspect" in content
    assert "[Image: image/png" in content
    assert "secret payload" not in content
