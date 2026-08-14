"""Declare the artifacts a turn shows the user."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar, TypeAlias

from pydantic import BaseModel, Field
from pydantic_ai import Tool, ToolReturn

from tabulaflow.output.specs import ChartArtifactSpec, GraphArtifactSpec, MapArtifactSpec
from tabulaflow.output.store import OutputStore


class ArtifactRef(BaseModel):
    id: str = Field(min_length=1, description="Id of a source or artifact to show: S*, CHART*, MAP* or GRAPH*.")
    label: str = Field(min_length=1, description="Short human-readable name for the card, never the id itself.")


Artifacts: TypeAlias = Annotated[list[ArtifactRef], Field(max_length=20)]


@dataclass(frozen=True)
class ArtifactBundle:
    """The artifacts one ``show_artifacts`` call declared, in display order.

    Travels on the tool return's ``metadata`` — host-facing, never sent to the
    model — so the turn's cards need no state on the tool itself.
    """

    artifacts: tuple[ArtifactRef, ...]


class ShowArtifactsTool:
    """Declare which sources or artifacts a turn shows, each with a display label."""

    name: ClassVar = "show_artifacts"

    def __init__(self, output_store: OutputStore) -> None:
        self._output_store = output_store

    async def __call__(self, artifacts: Artifacts) -> ToolReturn:
        """Show the user a set of results, each as a labelled card.

        Ids come from the tools that produced them: ``S*`` from a query or source,
        ``CHART*``, ``MAP*`` and ``GRAPH*`` from render tools. Cards appear in the
        order given, the first one open. Parameter controls are inferred from the
        selected sources and artifacts.

        Args:
            artifacts: The results to show, in display order.
        """
        problems = [problem for artifact in artifacts if (problem := await self._problem(artifact)) is not None]
        if problems:
            return ToolReturn(return_value=f"(error: {'; '.join(problems)})")
        bundle = ArtifactBundle(artifacts=tuple(artifacts))
        shown = ", ".join(f"{artifact.label} ({artifact.id})" for artifact in artifacts) or "nothing"
        return ToolReturn(return_value=f"showing {shown}", metadata=bundle)

    async def _problem(self, artifact: ArtifactRef) -> str | None:
        """Why ``artifact`` cannot be shown, or ``None`` when it can."""
        if artifact.label == artifact.id:
            return f"{artifact.id} needs a human-readable label, not its id"
        try:
            if artifact.id.startswith("CHART"):
                artifact_spec = self._output_store.get_artifact(artifact.id)
                if not isinstance(artifact_spec, ChartArtifactSpec):
                    return f"unknown artifact id {artifact.id!r}"
            elif artifact.id.startswith("MAP"):
                artifact_spec = self._output_store.get_artifact(artifact.id)
                if not isinstance(artifact_spec, MapArtifactSpec):
                    return f"unknown artifact id {artifact.id!r}"
            elif artifact.id.startswith("GRAPH"):
                artifact_spec = self._output_store.get_artifact(artifact.id)
                if not isinstance(artifact_spec, GraphArtifactSpec):
                    return f"unknown artifact id {artifact.id!r}"
            elif artifact.id.startswith("S"):
                self._output_store.get_source(artifact.id)
            else:
                return f"unknown artifact id {artifact.id!r}"
        except (KeyError, ValueError):
            return f"unknown artifact id {artifact.id!r}"
        return None

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
