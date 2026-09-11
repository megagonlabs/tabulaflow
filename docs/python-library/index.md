# Python library

Use TabulaFlow's Python components to build data agents and applications. The
package follows these dependency layers:

```text
core < data < output < agents < app
```

- `tabulaflow.core` provides stable schema, result, serialization, and registry
  primitives.
- `tabulaflow.data` provides connectors and schema services.
- `tabulaflow.output` provides result storage, specifications, and formatting.
- `tabulaflow.agents` provides chat runtimes, extraction, and tools.

During the public beta, treat modules not listed in the API reference as
internal and subject to change.
