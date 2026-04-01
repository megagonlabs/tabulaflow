from typing import TYPE_CHECKING

from mintq.toolhub.base import BaseTool

if TYPE_CHECKING:
    from mintq.toolhub.ask_user import AskUserTool as AskUserTool
    from mintq.toolhub.execute_bash import ExecuteBashTool as ExecuteBashTool
    from mintq.toolhub.file_editor import FileEditorTool as FileEditorTool
    from mintq.toolhub.finish import FinishTool as FinishTool
    from mintq.toolhub.get_column_description import GetColumnDescriptionTool as GetColumnDescriptionTool
    from mintq.toolhub.get_column_json_schema import GetColumnJsonSchemaTool as GetColumnJsonSchemaTool
    from mintq.toolhub.get_schema import GetSchemaTool as GetSchemaTool
    from mintq.toolhub.get_table_schema import GetTableSchemaTool as GetTableSchemaTool
    from mintq.toolhub.render_chart import RenderPlotextChartTool as RenderPlotextChartTool
    from mintq.toolhub.run_dbt import RunDbtTool as RunDbtTool
    from mintq.toolhub.run_query import RunQueryTool as RunQueryTool
    from mintq.toolhub.search_keywords import SearchKeywordsTool as SearchKeywordsTool

__all__ = [
    "BaseTool",
    "AskUserTool",
    "ExecuteBashTool",
    "FileEditorTool",
    "FinishTool",
    "GetColumnDescriptionTool",
    "GetColumnJsonSchemaTool",
    "GetSchemaTool",
    "GetTableSchemaTool",
    "RenderPlotextChartTool",
    "RunDbtTool",
    "RunQueryTool",
    "SearchKeywordsTool",
]


def __getattr__(name: str) -> object:
    """Lazy-load tool classes to avoid circular imports between toolhub and agenthub."""
    _lazy = {
        "ExecuteBashTool": "mintq.toolhub.execute_bash",
        "SearchKeywordsTool": "mintq.toolhub.search_keywords",
        "RunQueryTool": "mintq.toolhub.run_query",
        "FinishTool": "mintq.toolhub.finish",
        "AskUserTool": "mintq.toolhub.ask_user",
        "GetSchemaTool": "mintq.toolhub.get_schema",
        "GetTableSchemaTool": "mintq.toolhub.get_table_schema",
        "GetColumnDescriptionTool": "mintq.toolhub.get_column_description",
        "GetColumnJsonSchemaTool": "mintq.toolhub.get_column_json_schema",
        "FileEditorTool": "mintq.toolhub.file_editor",
        "RunDbtTool": "mintq.toolhub.run_dbt",
        "RenderPlotextChartTool": "mintq.toolhub.render_chart",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name])
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'mintq.toolhub' has no attribute {name!r}")
