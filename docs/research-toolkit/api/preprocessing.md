# Preprocessing

See [Running experiments](../running-experiments.md#configure-concurrency-and-caching)
for cache configuration.

## Prepare reusable inputs

With preprocessing caching enabled, prepare ER diagrams before prediction to
reuse them across runs:

```python
from tabulaflow.research.pipelines import preprocess_async
from tabulaflow.research.preprocessing import ERDiagramSynthesizer

preprocessor = ERDiagramSynthesizer()
await preprocess_async(dataset, [preprocessor])
print("Preparation usage:", preprocessor.usage())
```

This fills caches for agents using the same inputs and preprocessor configuration.
Preprocessing can make model calls; report its usage separately from inference.

`read_write` reuses entries and stores misses, `refresh` recomputes and replaces
entries, `cache_only` requires existing entries, and `off` bypasses the cache.

## Contracts and pipeline

`preprocess_async(...)` dispatches by `input_type`: a SQL connector or an
`NL2QDataset`. Caching uses
[`AgentRuntimeConfig`][tabulaflow.agents.config.AgentRuntimeConfig].

::: tabulaflow.research.pipelines.preprocess.preprocess_async

::: tabulaflow.research.preprocessing.registry.preprocessor_registry

::: tabulaflow.research.preprocessing.registry.ConnectorPreprocessorProtocol

::: tabulaflow.research.preprocessing.registry.DatasetPreprocessorProtocol

## Built-in preprocessing

::: tabulaflow.research.preprocessing.schema.SchemaPreprocessor

::: tabulaflow.research.preprocessing.column_profiler.ColumnProfiler

::: tabulaflow.research.preprocessing.fk_predictor.ForeignKeyPredictor

::: tabulaflow.research.preprocessing.question_embedding.QuestionEmbedder

::: tabulaflow.research.preprocessing.erd.ERDiagramSynthesizer

::: tabulaflow.research.preprocessing.registry.DBSummaryPreprocessor

## Preprocessing results

::: tabulaflow.research.preprocessing.erd.ERDiagram

::: tabulaflow.research.preprocessing.erd.ERDConceptualEntity

::: tabulaflow.research.preprocessing.erd.EntitySourceTable

::: tabulaflow.research.preprocessing.erd.ERDRelationship

::: tabulaflow.research.preprocessing.erd.ERDRelationshipParticipant

::: tabulaflow.research.preprocessing.erd.MermaidERDiagramFormatter

::: tabulaflow.research.preprocessing.question_embedding.QuestionEmbedderOutput

::: tabulaflow.research.preprocessing.question_embedding.QuestionSkeleton

::: tabulaflow.research.preprocessing.column_profiler.LLMOutput
    options:
      show_root_full_path: true
