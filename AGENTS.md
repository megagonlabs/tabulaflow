# tabulaflow

TabulaFlow is an open-source data agent built on a modular Python library.
It has three main product surface:
- A data agent application (a TUI app with browser output pane for rich visualization) for everyone
- A python library for developers build custom data applications
- A research toolkit for AI researchers to run experiments
They are organized into six layers: `core <- data <- output <- agents <- {app, research}`

## Project Conventions

- Use `uv` for all Python operations

## Guidelines

- Always think from first principles and aim for the clean minimal ultimate shape, rather than defaulting to historical constraints.
- Think out-of-the-box. Find the cleanest and most elegant solution.
- Fail fast.
- Fix the root cause, don't just mask the symptom.
- Prioritize long term cleanliness and maintainability.
- When a change moves responsibility between modules, move related helpers to the new owning module in the same change.
- Take the principled approach, not the one based on heuristics.
- Before writing code, always assess whether the idea aligns with common practice and if not, stop and provide such feedback to the user.
- Use Google style for all Python docstrings.
- Keep code clean, minimal and intuitive. Do not over-engineer or over-abstract.
- Do not write comments if the code is self-explanatory. Only write comments for complicated or tricky logic.
- For large changes with multiple design decisions or multiple alternative implementations, discuss with me first.
- Be honest when what I say has flaws or does not make sense.
- When writing agent-facing tool description, just describe the tool's functionality and use cases, don't lecture the agent on how or when to use it or mention verbosely commonsense knowledge.
- The repo has not been published yet, so always do a clean break and remove unused code, refactor to better architecture if necessary. Optimize for long-term cleanliness over compatibility.
- When the current architecture or abstraction is not optimal for the new feature, stop and discuss with me first on a refactoring plan. You can suggest removal of current features if that can lead to a cleaner architecture.
- Do not commit code unless I explicitly ask you to.
- For UI changes, ask me to verify it visually for you (without taking screenshot yourself) to save time.

## Toolhub Development Principles

- Keep `__call__` as the LLM-facing adapter; put reusable logic in `execute(...)`.
- Reusable `execute(...)` methods raise expected validation/runtime errors;
  `__call__` catches them and returns the model-facing `(error: ...)` string.
- Use structured result dataclasses only when fields have real consumers; otherwise return the output string.
- Do not bridge awaited calls with shared `last_*` state; return per-call data from `execute(...)`.
- Registry tools resolve aliases, call the underlying `execute(...)`, and convert results to `ToolReturn` metadata.
- Model-facing errors should be `(error: ...)` strings, unless immediately caught and converted.
- Reserve/increment user-visible ids before awaits that can interleave.
- Prefer small tool-specific dataclasses; do not add broad result hierarchies.
- Rebuild cached per-alias tools when an alias is rebound.
- Keep metrics in the shared execution path.
- In tests, assert `ToolReturn.return_value` is a string before searching it.
