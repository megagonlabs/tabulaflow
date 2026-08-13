# Answer Controls Plan

Status: superseded by the clean output model in [`ultimate_output_model_plan.md`](./ultimate_output_model_plan.md) and the render pipeline in [`output_render_pipeline_plan.md`](./output_render_pipeline_plan.md).

The current model is:

```text
OutputSpec = Parameters + Sources + Artifacts + default selection

ParameterSpec = ChoiceParameter | NumberParameter
SourceSpec    = FixedResultSource | ParameterizedSource
ArtifactSpec  = TableArtifactSpec | ChartArtifactSpec | MapArtifactSpec | GraphArtifactSpec
```

Controls are derived directly from `OutputSpec.parameters`. There is no separate answer-control model in chat, no `ViewDef` layer, and no compatibility output-shape aliases.

Remaining controls work belongs in the app layer:

- project `ParameterSpec` to drawable controls once for both terminal and browser;
- add rendering for `NumberParameter` sliders/inputs;
- keep selection application as `selection -> OutputResolver.resolve(...) -> presenter`.
