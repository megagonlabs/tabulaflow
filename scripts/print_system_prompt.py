"""Print the composed system prompt exactly as the chat agent sends it.

    uv run scripts/print_system_prompt.py

Builds a real ``ChatAgent`` (empty registry, cwd as project dir) so the output
includes the runtime ``## Session`` tail, not just the static prompt file.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from tabulaflow.chat.agent import ChatAgent
from tabulaflow.core.db_connector.db_registry import DBRegistry


def main() -> None:
    agent = ChatAgent(
        registry=DBRegistry(),
        model="openai-responses:gpt-5",
        reasoning_effort="medium",
        project_dir=Path(os.getcwd()),
        scratch_dir=Path(tempfile.gettempdir()) / "tabulaflow-scratch",
    )
    print(agent._system_prompt)


if __name__ == "__main__":
    main()
