import pytest
from mintq.utils import extract_code


@pytest.mark.asyncio
async def test_extract_code() -> None:
    responses = [
        "SELECT * FROM users",
        "```\nSELECT * FROM users\n```",
        "```python\nSELECT * FROM users\n```",
        "```sql\nSELECT * FROM users\n```",
        "```sql\nSELECT * FROM users\n```\n",
        "```\nSELECT * FROM users\n```",
        "```\n\nSELECT * FROM users\n```",
    ]
    for response in responses:
        code = extract_code(response)
        assert code == "SELECT * FROM users"
