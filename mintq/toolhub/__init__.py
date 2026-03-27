from mintq.toolhub.base import BaseTool

__all__ = [
    "BaseTool",
    "ExecuteBashTool",
    "SearchKeywordsTool",
    "RunQueryTool",
    "FinishTool",
    "AskUserTool",
    "GetSchemaTool",
    "GetTableSchemaTool",
    "GetColumnDescriptionTool",
    "GetColumnJsonSchemaTool",
    "FileEditorTool",
    "RunDbtTool",
    "RenderPlotextChartTool",
]


def __getattr__(name: str) -> object:
    """Lazy-load tool classes to avoid circular imports."""
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
