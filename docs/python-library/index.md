# Python library

TabulaFlow's reusable Python components support custom data agents and data
applications. The package is organized into dependency layers:

```text
core < data < output < agents < app
```

- `tabulaflow.core` provides stable schema, result, serialization, and registry
  primitives.
- `tabulaflow.data` provides connectors and schema services.
- `tabulaflow.output` provides result storage, specifications, and formatting.
- `tabulaflow.agents` provides chat runtimes, extraction, and tools.

This initial page will become a curated guide to the documented public API.
Internal modules that are not documented here should be treated as unstable
during the public beta.
