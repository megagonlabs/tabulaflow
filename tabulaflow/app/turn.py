"""App-level live turn helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from tabulaflow.core.outputs import OutputSpec, ParameterId
from tabulaflow.toolhub.output_resolver import OutputResolver, ResolvedOutput
from tabulaflow.toolhub.output_store import OutputStore


@dataclass(frozen=True)
class TurnOutput:
    """One turn's output spec and the store that can resolve it."""

    output: OutputSpec
    output_store: OutputStore

    async def resolve(self, selection: Mapping[ParameterId, object] | None = None) -> ResolvedOutput:
        """Resolve the turn output for a surface-local selection."""
        return await OutputResolver(self.output_store).resolve(self.output, selection)
