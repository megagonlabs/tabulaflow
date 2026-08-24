import json
import subprocess
import sys


def _loaded_modules(code: str) -> set[str]:
    script = f"{code}\nimport json, sys; print(json.dumps(sorted(sys.modules)))"
    result = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
    return set(json.loads(result.stdout))


def test_layer_package_imports_are_lightweight() -> None:
    modules = _loaded_modules(
        "import tabulaflow.core, tabulaflow.data, tabulaflow.output, "
        "tabulaflow.output.formatting, tabulaflow.agents, tabulaflow.agents.extraction, "
        "tabulaflow.agents.tools, tabulaflow.agents.modules"
    )

    assert "tabulaflow.core.schema" not in modules
    assert "tabulaflow.data.sql" not in modules
    assert "tabulaflow.output.formatting.sql_ddl" not in modules
    assert "tabulaflow.agents.tools.browser.tool" not in modules
    assert "tabulaflow.agents.extraction.entity" not in modules
    assert "tabulaflow.agents.modules.schema_preprocessor" not in modules


def test_lazy_public_exports_load_only_their_owners() -> None:
    modules = _loaded_modules(
        "from tabulaflow.data import SQLConnectorConfig; "
        "from tabulaflow.agents.tools import BaseTool; "
        "from tabulaflow.output.formatting import format_single_line_text"
    )

    assert "tabulaflow.data.config" in modules
    assert "tabulaflow.data.sql" not in modules
    assert "tabulaflow.data.neo4j" not in modules
    assert "tabulaflow.agents.tools.base" in modules
    assert "tabulaflow.agents.tools.browser.tool" not in modules
    assert "tabulaflow.output.formatting._core" in modules
    assert "tabulaflow.output.formatting.sql_ddl" not in modules


def test_all_lazy_public_exports_resolve() -> None:
    code = """
import importlib
packages = (
    "tabulaflow.core",
    "tabulaflow.data",
    "tabulaflow.data.loaders",
    "tabulaflow.output.formatting",
    "tabulaflow.agents",
    "tabulaflow.agents.chat",
    "tabulaflow.agents.extraction",
    "tabulaflow.agents.modules",
    "tabulaflow.agents.tools",
)
for package in packages:
    module = importlib.import_module(package)
    for name in module.__all__:
        getattr(module, name)
"""

    _loaded_modules(code)
