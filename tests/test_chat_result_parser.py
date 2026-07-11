from tabulaflow.chat.agent import _extract_result_refs


def test_extract_result_refs_hides_narration_before_separator() -> None:
    text = """I'm tabulaflow, an interactive data assistant.

---
I'm tabulaflow. Ask me anything about your data."""

    display_text, refs = _extract_result_refs(text)

    assert display_text == "I'm tabulaflow. Ask me anything about your data."
    assert refs == []


def test_extract_result_refs_keeps_refs_when_prefix_has_narration() -> None:
    text = """I found the result.
[[artifact:Q3:rows]]
---
There are 3 rows."""

    display_text, refs = _extract_result_refs(text)

    assert display_text == "There are 3 rows."
    assert refs == [("Q3", "rows")]
