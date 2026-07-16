from tabulaflow.chat.agent import _TextStreamRouter, _extract_result_refs


def test_extract_result_refs_reads_artifacts_block() -> None:
    text = """<artifacts>
[[artifact:Q3:rows]]
</artifacts>
There are 3 rows."""

    display_text, refs = _extract_result_refs(text)

    assert display_text == "There are 3 rows."
    assert refs == [("Q3", "rows")]


def test_extract_result_refs_ignores_prose_inside_artifacts_block() -> None:
    text = """<artifacts>
I found the result.
[[artifact:Q3:rows]]
</artifacts>
There are 3 rows."""

    display_text, refs = _extract_result_refs(text)

    assert display_text == "There are 3 rows."
    assert refs == [("Q3", "rows")]


def test_extract_result_refs_allows_empty_artifacts_block() -> None:
    text = """<artifacts>
</artifacts>
The connection succeeded."""

    display_text, refs = _extract_result_refs(text)

    assert display_text == "The connection succeeded."
    assert refs == []


def test_extract_result_refs_strips_and_resolves_inline_refs_after_block() -> None:
    text = """<artifacts>
[[artifact:Q3:rows]]
</artifacts>
See [[artifact:Q3:rows]] and [[artifact:MAP1:store locations]]."""

    display_text, refs = _extract_result_refs(text)

    assert display_text == "See  and ."
    assert refs == [("Q3", "rows"), ("MAP1", "store locations")]


def test_extract_result_refs_does_not_special_case_legacy_separator() -> None:
    text = """I'm tabulaflow, an interactive data assistant.

---
I'm tabulaflow. Ask me anything about your data."""

    display_text, refs = _extract_result_refs(text)

    assert display_text == text
    assert refs == []


def test_text_stream_router_waits_for_artifacts_block() -> None:
    router = _TextStreamRouter()

    assert router.feed("<art") == ""
    assert router.feed("ifacts>\n[[artifact:Q3:rows]]\n") == ""
    assert router.feed("</artifacts>\nThere") == "There"
    assert router.is_answer
    assert router.feed(" are 3 rows.") == " are 3 rows."


def test_text_stream_router_routes_plain_prose_as_narration() -> None:
    router = _TextStreamRouter()

    assert router.feed("Thinking out loud.") == "Thinking out loud."
    assert not router.is_answer
