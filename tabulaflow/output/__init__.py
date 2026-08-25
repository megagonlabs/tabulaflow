"""Declarative outputs, runtime resolution, and deterministic formatting.

The public API is organized by responsibility rather than re-exported here:

* :mod:`tabulaflow.output.specs` defines serializable parameters, sources,
  artifacts, and complete output declarations.
* :mod:`tabulaflow.output.store` stores materialized results and lazily resolves
  parameterized sources.
* :mod:`tabulaflow.output.resolver` turns an output declaration and selection
  into display-ready artifacts.
* :mod:`tabulaflow.output.charts`, :mod:`tabulaflow.output.maps`, and
  :mod:`tabulaflow.output.graphs` validate artifact-specific specifications.
* :mod:`tabulaflow.output.formatting` provides human- and LLM-readable formatters.
"""
