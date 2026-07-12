"""LLM-based text summarizer for long descriptions."""

from __future__ import annotations

import logging
from tabulaflow.core.llm import make_agent, reasoning_model_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are a technical writer that summarizes the given text concisely.
- Preserve key information and omit unimportant details.
- Target {max_words} words or fewer.
"""


class TextSummarizer:
    """Summarize long text using an LLM."""

    def __init__(
        self,
        llm: str = "openai-responses:gpt-5-mini",
        max_words: int = 500,
        model_settings: dict[str, object] | None = None,
    ) -> None:
        self.llm = llm
        self.max_words = max_words
        self.model_settings = model_settings

    async def summarize(self, text: str) -> str:
        """Return a summarized version of the input text."""

        settings: dict[str, object] = dict(reasoning_model_settings("low"))
        if self.model_settings:
            settings.update(self.model_settings)
        agent = make_agent(
            self.llm, instructions=_SYSTEM_PROMPT.format(max_words=self.max_words), model_settings=settings
        )
        result = await agent.run(text)
        return result.output
