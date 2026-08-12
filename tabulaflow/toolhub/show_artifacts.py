"""Declare the artifacts a turn shows the user."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar, TypeAlias

from pydantic import BaseModel, Field
from pydantic_ai import Tool, ToolReturn

from tabulaflow.core.outputs import ChartView, GraphViewSpec, MapView, ParameterizedSource, SourceDef
from tabulaflow.toolhub.output_store import OutputStore


class ArtifactRef(BaseModel):
    id: str = Field(min_length=1, description="Id of a source or artifact to show: S*, CHART*, MAP* or GRAPH*.")
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

        Ids come from the tools that produced them: ``S*`` from a query or source, ``CHART*``, ``MAP*`` and ``GRAPH*`` from
        the render tools. Cards appear in the order given, the first one open.

        With ``dimensions``, the user gets a chooser and every card updates together as
        they switch. A source card shows the combination selected for the dimensions its
        query varied over. A ``CHART*`` card whose source varies does the same.
        A card that did not vary over a dimension shows the same rows whatever the user
        picks there, and one run over only some of a dimension's choices shows "only
        applies when …" for the rest.

        Normal answer, no chooser:
        ```python
        show_artifacts(artifacts=[{"id": "S1", "label": "player count"}])
        ```

        Panel answer, with a chooser:
        ```python
        show_artifacts(
            artifacts=[{"id": "S1", "label": "top customers"}],
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
        family = self._lookup_source(artifact.id)
        if family is None or not dimensions:
            return f"{artifact.label} ({artifact.id})"
        declared = {dim.id: [choice.id for choice in dim.choices] for dim in dimensions}
        partial = [
            f"{name}={'|'.join(choices)}"
            for name, choices in _cached_parameter_choices(self._output_store, family).items()
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
            family = self._lookup_source(artifact.id)
            if family is None:
                continue
            if not dimensions:
                problems.append(f"{artifact.id} varies over {', '.join(_cached_parameter_choices(self._output_store, family))}; declare them as dimensions")
                continue
            for name, choices in _cached_parameter_choices(self._output_store, family).items():
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
                artifact_spec = self._output_store.get_artifact(artifact.id)
                if not isinstance(artifact_spec.view, ChartView):
                    return f"unknown artifact id {artifact.id!r}"
            elif artifact.id.startswith("MAP"):
                artifact_spec = self._output_store.get_artifact(artifact.id)
                if not isinstance(artifact_spec.view, MapView):
                    return f"unknown artifact id {artifact.id!r}"
            elif artifact.id.startswith("GRAPH"):
                artifact_spec = self._output_store.get_artifact(artifact.id)
                if not isinstance(artifact_spec.view, GraphViewSpec):
                    return f"unknown artifact id {artifact.id!r}"
            elif artifact.id.startswith("S"):
                self._output_store.get_source(artifact.id)
            else:
                return f"unknown artifact id {artifact.id!r}"
        except (KeyError, ValueError):
            return f"unknown artifact id {artifact.id!r}"
        return None

    def _lookup_source(self, artifact_id: str) -> SourceDef | None:
        """The result-lookup source behind ``artifact_id``, or ``None`` for a fixed artifact."""
        try:
            if artifact_id.startswith("S"):
                source = self._output_store.get_source(artifact_id)
                return source if isinstance(source, ParameterizedSource) else None
            if artifact_id.startswith("CHART"):
                chart = self._output_store.get_artifact(artifact_id)
                if isinstance(chart.view, ChartView) and chart.view.source.startswith("S"):
                    source = self._output_store.get_source(chart.view.source)
                    return source if isinstance(source, ParameterizedSource) else None
        except KeyError:
            return None
        return None

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)


def _cached_parameter_choices(output_store: OutputStore, source: SourceDef) -> dict[str, list[str]]:
    if not isinstance(source, ParameterizedSource):
        return {}
    dimensions: dict[str, list[str]] = {parameter_id: [] for parameter_id in source.parameter_ids}
    for selection in output_store.get_cached_source_selections(source.id):
        for parameter_id in source.parameter_ids:
            value = str(selection.get(parameter_id))
            if value not in dimensions[parameter_id]:
                dimensions[parameter_id].append(value)
    return dimensions
