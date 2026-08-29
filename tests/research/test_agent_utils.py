import pytest

from tabulaflow.research.agents.utils import extract_code, get_max_steps_capability


def test_extract_code() -> None:
    responses = [
        "SELECT * FROM users",
        "```\nSELECT * FROM users\n```",
        "```python\nSELECT * FROM users\n```",
        "```sql\nSELECT * FROM users\n```",
        "```sql\nSELECT * FROM users\n```\n",
        "```\nSELECT * FROM users\n```",
        "```\n\nSELECT * FROM users\n```",
        "This is the SQL code:\n```sql\nSELECT * FROM users\n```",
        "This is the SQL code:\n```sql\nSELECT * FROM users\n```. "
        "This is another SQL code:\n```sql\nSELECT * FROM products\n```",
    ]

    for response in responses:
        assert extract_code(response) == "SELECT * FROM users"


def test_max_steps_capability_rejects_nonpositive_limit() -> None:
    with pytest.raises(ValueError, match="max_steps must be at least 1"):
        get_max_steps_capability(0)
