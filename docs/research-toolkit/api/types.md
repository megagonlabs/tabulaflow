# Tasks and results

Represent benchmark questions, reference queries, predictions, and experiment
results with typed models. Task families cover straightforward queries,
ambiguous questions, and dbt workflows.

## Queries

`GoldQuery` stores a reference query and accepted result variants. `PredQuery`
stores an agent prediction. Both can carry an
[`ExecResult`][tabulaflow.core.results.ExecResult].

::: tabulaflow.research.types.GoldQuery

::: tabulaflow.research.types.PredQuery

## Simple tasks

::: tabulaflow.research.types.SimpleNL2QTask

::: tabulaflow.research.types.SimpleNL2QTaskOutput

::: tabulaflow.research.types.ExtraPredInfo

## Ambiguous tasks

Ambiguous tasks specify interpretation choices or open-ended parameters. The
three output families represent an intended query, a flat collection of
interpretations, or explicitly structured ambiguity points.

::: tabulaflow.research.types.AmbigNL2QTask

::: tabulaflow.research.types.SimpleAmbigNL2QTaskOutput

::: tabulaflow.research.types.FlatAmbigNL2QTaskOutput

::: tabulaflow.research.types.StructuredAmbigNL2QTaskOutput

::: tabulaflow.research.types.ARCSAmbiguityType

::: tabulaflow.research.types.GoldAmbiguityPointFinite

::: tabulaflow.research.types.GoldAmbiguityPointInfinite

::: tabulaflow.research.types.GoldAmbiguityPoint

::: tabulaflow.research.types.PredAmbiguityPointFinite

::: tabulaflow.research.types.PredAmbiguityPointInfinite

::: tabulaflow.research.types.PredAmbiguityPoint

## dbt tasks

::: tabulaflow.research.types.DbtTask

::: tabulaflow.research.types.DbtTaskOutput

::: tabulaflow.research.types.DbtGoldTable

## Datasets and runs

`NL2QDataset` holds live connectors keyed by task database names. Close those
connectors when your program finishes. `NL2QRunResult` stores experiment data
and supports JSON serialization, directory reports, and CSV summaries.

::: tabulaflow.research.types.NL2QDataset

::: tabulaflow.research.types.NL2QRunResult

::: tabulaflow.research.types.CSVSummaryRow

::: tabulaflow.research.types.NL2QTask

::: tabulaflow.research.types.NL2QTaskOutput

## User interaction

Ambiguity-aware agents use `UserSimulatorProtocol` to request clarification
and track its usage and effort.

::: tabulaflow.research.types.UserSimulatorProtocol

::: tabulaflow.research.types.UserFreeTextQuestion

::: tabulaflow.research.types.UserFreeTextAnswer

::: tabulaflow.research.types.UserMultipleChoiceQuestion

::: tabulaflow.research.types.UserMultipleChoiceAnswer

::: tabulaflow.research.types.UserValueQuestion

::: tabulaflow.research.types.UserValueAnswer

::: tabulaflow.research.types.UserQuestion

::: tabulaflow.research.types.UserAnswer
