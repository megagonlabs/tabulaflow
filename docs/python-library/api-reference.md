# API reference

The library's public interfaces are grouped by package layer. Signatures,
fields, and method documentation are generated from the Python source.

| Layer | APIs |
| --- | --- |
| [Core](api/core.md) | Schemas, execution results, DataFrame serialization, and class registries |
| [Data](api/data.md) | Connections, connector configuration, source registries, and file loaders |
| [Output](api/output.md) | Stored results, artifact specifications, parameter resolution, and formatting |
| [Agents](api/agents.md) | Chat sessions, events, model configuration, reusable tools, and extraction |

Import shared schema and result types from `tabulaflow.core`. Connector
entry points are available from `tabulaflow.data`; output APIs use explicit
submodules such as `tabulaflow.output.specs` and `tabulaflow.output.store`.

Benchmark tasks, research strategies, and evaluation contracts are documented
in the [research API reference](../research-toolkit/api-reference.md).

The APIs listed here form the documented library surface. Other implementation
details, including modules and members prefixed with `_`, are internal.
