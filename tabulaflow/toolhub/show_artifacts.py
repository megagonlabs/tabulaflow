"""Declare the artifacts a turn shows the user."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar, TypeAlias

from pydantic import BaseModel, Field
from pydantic_ai import Tool, ToolReturn

from tabulaflow.core.outputs import ChartView
from tabulaflow.toolhub.output_store import QueryFamily, OutputStore


class ArtifactRef(BaseModel):
    id: str = Field(min_length=1, description="Id of a result to show: Q*, QS*, CHART*, MAP* or GRAPH*.")
    label: str = Field(min_length=1, description="Short human-readable name for the card, never the id itself.")


class Choice(BaseModel):
    id: str = Field(min_length=1, description="Choice id, as used by the query template that varied over it.")
    label: str = Field(min_length=1, description="How this reading reads to the user, e.g. 'Last 90 days'.")


class Dimension(BaseModel):
    id: str = Field(min_length=1, description="Dimension id, as declared when running the query combinations.")
    label: str = Field(min_length=1, description="Short phrase naming the ambiguity, e.g. 'Time period'.")
    choices: list[Choice] = Field(min_length=2, description="Readings of this dimension, best reading first.")


Artifacts: TypeAlias = Annotated[list[ArtifactRef], Field(max_length=20)]
Dimensions: TypeAlias = Annotated[list[Dimension], Field(max_length=4)]


@dataclass(frozen=True)
class ArtifactBundle:
    """The artifacts one ``show_artifacts`` call declared, in display order.

    Travels on the tool return's ``metadata`` — host-facing, never sent to the
    model — so the turn's cards need no state on the tool itself.

    ``dimensions`` is empty for an ordinary turn. When set, every card is shown at
    one choice per dimension and the user switches between them; a card resolves
    at a point using only the dimensions its own query varied over.
    """

    artifacts: tuple[ArtifactRef, ...]
    dimensions: tuple[Dimension, ...] = ()


class ShowArtifactsTool:
    """Declare which recorded results a turn shows, each with a display label.

    Validates the ids against ``OutputStore`` and hands the host the declared
    bundle via the tool return's metadata.

    Attributes:
        output_store: Where the cited ids are resolved.
    """

    name: ClassVar = "show_artifacts"

    def __init__(self, output_store: OutputStore) -> None:
        self._output_store = output_store

    async def __call__(self, artifacts: Artifacts, dimensions: Dimensions = []) -> ToolReturn:
        """Show the user a set of results, each as a labelled card.

        Ids come from the tools that produced them: ``Q*`` from a query, ``QS*`` from a
        query run over dimension combinations, ``CHART*``, ``MAP*`` and ``GRAPH*`` from
        the render tools. Cards appear in the order given, the first one open.

        With ``dimensions``, the user gets a chooser and every card updates together as
        they switch. A ``QS*`` card shows the combination selected for the dimensions its
        query varied over. A ``CHART*`` card whose source is ``QS*`` varies the same way.
        A card that did not vary over a dimension shows the same rows whatever the user
        picks there, and one run over only some of a dimension's choices shows "only
        applies when …" for the rest.

        Normal answer, no chooser:
        ```python
        show_artifacts(artifacts=[{"id": "Q1", "label": "player count"}])
        ```

        Panel answer, with a chooser:
        ```python
        show_artifacts(
            artifacts=[{"id": "QS1", "label": "top customers"}],
            dimensions=[
                {
                    "id": "period",
                    "label": "Time period",
                    "choices": [
                        {"id": "completed_qtr", "label": "Last completed quarter"},
                        {"id": "last_90_days", "label": "Last 90 days"},
                    ],
                }
            ],
        )
        ```

        Args:
            artifacts: The results to show, in display order.
            dimensions: Ambiguities the user may switch between, best reading first.
                Omit it, or pass an empty list, for a normal answer with no chooser.
        """
        problems = [problem for artifact in artifacts if (problem := await self._problem(artifact)) is not None]
        problems += self._panel_problems(artifacts, dimensions)
        if problems:
            return ToolReturn(return_value=f"(error: {'; '.join(problems)})")
        bundle = ArtifactBundle(artifacts=tuple(artifacts), dimensions=tuple(dimensions))
        shown = ", ".join(self._describe(artifact, dimensions) for artifact in artifacts) or "nothing"
        return ToolReturn(return_value=f"showing {shown}", metadata=bundle)

    def _describe(self, artifact: ArtifactRef, dimensions: Dimensions) -> str:
        """``label (id)``, naming the choices a partially covered card is limited to."""
        family = self._family(artifact.id)
        if family is None or not dimensions:
            return f"{artifact.label} ({artifact.id})"
        declared = {dim.id: [choice.id for choice in dim.choices] for dim in dimensions}
        partial = [
            f"{name}={'|'.join(choices)}"
            for name, choices in family.dimensions.items()
            if len(choices) < len(declared.get(name, choices))
        ]
        limits = f" — only applies at {', '.join(partial)}" if partial else ""
        return f"{artifact.label} ({artifact.id}{limits})"

    def _panel_problems(self, artifacts: Artifacts, dimensions: Dimensions) -> list[str]:
        """Why ``dimensions`` and the cards' own dimensions cannot form a panel."""
        declared = {dim.id: {choice.id for choice in dim.choices} for dim in dimensions}
        if len(declared) != len(dimensions):
            return ["dimension ids must be unique"]
        first = {dim.id: dim.choices[0].id for dim in dimensions}
        problems: list[str] = []
        varied: set[str] = set()
        for artifact in artifacts:
            family = self._family(artifact.id)
            if family is None:
                continue
            if not dimensions:
                problems.append(f"{artifact.id} varies over {', '.join(family.dimensions)}; declare them as dimensions")
                continue
            for name, choices in family.dimensions.items():
                if name not in declared:
                    problems.append(f"{artifact.id} varies over {name!r}, which is not a declared dimension")
                    continue
                varied.add(name)
                if undeclared := sorted(set(choices) - declared[name]):
                    problems.append(f"{artifact.id} ran {name}={','.join(undeclared)}, not declared for {name!r}")
                elif first[name] not in choices:
                    # The panel opens on the first choice of every dimension and the answer
                    # text describes it, so every card has to have something to show there.
                    problems.append(
                        f"{artifact.id} does not apply at {name}={first[name]}, the first choice of {name!r}; "
                        "declare a reading it covers first"
                    )
        problems += [f"dimension {name!r} is not varied over by any card" for name in declared if name not in varied]
        return problems

    async def _problem(self, artifact: ArtifactRef) -> str | None:
        """Why ``artifact`` cannot be shown, or ``None`` when it can."""
        if artifact.label == artifact.id:
            return f"{artifact.id} needs a human-readable label, not its id"
        try:
            if artifact.id.startswith("CHART"):
                self._output_store.get_chart(artifact.id)
            elif artifact.id.startswith("MAP"):
                self._output_store.get_map(artifact.id)
            elif artifact.id.startswith("GRAPH"):
                self._output_store.get_graph(artifact.id)
            elif artifact.id.startswith("QS"):
                self._output_store.get_family(artifact.id)
            else:
                await self._output_store.get(artifact.id)
        except (KeyError, ValueError):
            return f"unknown artifact id {artifact.id!r}"
        return None

    def _family(self, artifact_id: str) -> QueryFamily | None:
        """The query family behind ``artifact_id``, or ``None`` for a fixed artifact."""
        try:
            if artifact_id.startswith("QS"):
                return self._output_store.get_family(artifact_id)
            if artifact_id.startswith("CHART"):
                chart = self._output_store.get_chart(artifact_id)
                if isinstance(chart.view, ChartView) and chart.view.source.startswith("QS"):
                    return self._output_store.get_family(chart.view.source)
        except KeyError:
            return None
        return None

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
