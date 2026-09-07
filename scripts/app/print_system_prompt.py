"""Print the composed system prompt exactly as the chat agent sends it.

    uv run scripts/app/print_system_prompt.py

Builds a real ``ChatSession`` (empty registry, cwd as project dir) so the output
includes the runtime ``## Session`` tail, not just the static prompt file.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from tabulaflow.agents.chat.session import ChatSession
from tabulaflow.data.registry import DataConnectorRegistry


def main() -> None:
    agent = ChatSession(
        registry=DataConnectorRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
        project_dir=Path(os.getcwd()),
        scratch_dir=Path(tempfile.gettempdir()) / "tabulaflow-scratch",
    )
    print(agent._system_prompt)


if __name__ == "__main__":
    main()
