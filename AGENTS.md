# tabulaflow

TabulaFlow is an open-source data agent built on a modular Python library.
It has three main product surface:
- A data agent application (a TUI app with browser pane for rich visualization) for everyone
- A python library for developers build custom data applications
- A research toolkit for AI researchers to run experiments
They are organized into six layers: `core <- data <- output <- agents <- {app, research}`

## Project Conventions

- Use `uv` for Python operations.
- Use Google style for all Python docstrings.
- When writing agent tools in `tabulaflow.agents.tools`, Keep `__call__` as the LLM-facing adapter; put reusable logic in `execute(...)`.
  Reusable `execute(...)` methods raise expected validation/runtime errors;
  `__call__` catches them and returns the model-facing `(error: ...)` string.
  Use structured result dataclasses only when fields have real consumers; otherwise return the output string.
  Model-facing errors should be `(error: ...)` strings, unless immediately caught and converted.
- When writing agent-facing tool description, just describe the tool's functionality and use cases,
  don't lecture the agent on how or when to use it or mention verbosely commonsense knowledge.
- For UI changes, ask me to verify it visually for you (without taking screenshot yourself) to save time.
- Do not commit code unless I explicitly ask you to.
- If there are unrelated changes in the repo that do not affect your work, just continue your work and preserve other changes.
- When writing docs, be very careful when editting the opening content in each page as those
  content has usually gone through extensive human polishing. Dont edit them unless explictly
  requested. Keep docs clean and intuitive. Use focused code snippet and examples to showcase features.
  Add sample output as collapsable if it strengthen the story. Dont add verbose text that describe
  things that are already self-explanatory.
- For documentation, validate with `uv run --group docs mkdocs build --strict` and use
  `uv run --group docs mkdocs serve --dev-addr 127.0.0.1:8000` for live reload at
  `http://127.0.0.1:8000/tabulaflow/`; because that server lacks HTTP byte-range support, test video
  seeking by building first and running
  `npx --yes serve site --listen tcp://127.0.0.1:8000 --no-clipboard` instead (no live reload),
  stopping any existing port-8000 server before switching.

## Principles

- Think from first principles.
- Think out-of-the-box. Find the cleanest and most elegant solution.
- Aim for the clean minimal ultimate shape with clear responsiblity boundaries, rather than defaulting to historical constraints.
  When existing abstractions are suboptimal, propose a refactor.
- Fail fast.
- Fix the root cause, don't just mask the symptom.
- Prioritize long term cleanliness and maintainability.
- Take the principled approach, not the one based on heuristics.
- Align with common practice. Stop and advise me when it doesn't.
  Be honest when what I say has flaws or does not make sense.
- Keep code clean, minimal and intuitive. Do not over-engineer or over-abstract.
- Do not write comments if the code is self-explanatory. Write comments for complicated or tricky logic.
- For large changes with multiple design decisions or multiple alternative implementations, discuss the design choices I need to make first.
