"""Run-query tool backed by a DBRegistry, letting agents target any source."""

from typing import ClassVar

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Tool

from mintq.config import mintq_config
from mintq.db_connector.db_registry import DBRegistry
from mintq.toolhub.utils import format_sqlalchemy_error_msg
from mintq.utils import format_df

_UNSET = object()


def _detect_result_hints(df: pd.DataFrame) -> list[str]:
    """Detect common problematic result patterns and return actionable hints."""
    hints: list[str] = []
    cols_lower = [str(c).lower() for c in df.columns]

    if cols_lower == ["anonymous block"]:
        hints.append(
            "hint: The result contains only an 'anonymous block' column — this means the anonymous block "
            "(DECLARE … BEGIN … END) executed but did not return the inner query's result set. "
            "To fix this, declare a RESULTSET variable, assign it with `res := (EXECUTE IMMEDIATE :sql);`, "
            "and add `RETURN TABLE(res);` before END."
        )

    return hints


class RegistryRunQueryToolMetrics(BaseModel):
    num_calls: int = 0
    error_timeout: int = 0
    error_query_failed: int = 0
    error_read_only_violation: int = 0


class LLMParameter(BaseModel):
    parameter_name: str = Field(
        description="The parameter name that corresponds to the placeholder in the query (e.g. :name in SQL, $name in Cypher)."
    )
    parameter_value: int | float | str = Field(description="The intended value of the parameter.")


class RegistryRunQueryTool:
    """Execute a query against any registered database.

    The agent specifies which database to target via ``db_alias``.  The tool
    resolves the alias through a ``DBRegistry`` and executes the query on
    the corresponding connector.
    """

    name: ClassVar = "run_query"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        enable_params: bool = False,
        timeout: int | None | object = _UNSET,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            enable_params: Whether to expose the ``parameters`` argument to
                the LLM.
            timeout: Query timeout in seconds.  Defaults to
                ``mintq_config.query_timeout``.
            max_visible_rows: Maximum rows shown in the formatted output.
            max_cell_width: Maximum character width per cell in the formatted
                output.
            floatfmt: Float format string passed to tabulate.
        """
        self.registry = registry
        self.enable_params = enable_params
        self.timeout: int | None = mintq_config.query_timeout if timeout is _UNSET else timeout  # type: ignore[assignment]
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._metrics = RegistryRunQueryToolMetrics()

    async def _run_with_params(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] = [],
    ) -> str:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
            parameters: Query parameters.  A list of dictionaries, each
                containing a ``parameter_name`` and a ``parameter_value`` field.
        """
        return await self._execute(db_alias, query, parameters)

    async def _run_no_params(self, db_alias: str, query: str) -> str:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
        """
        return await self._execute(db_alias, query, [])

    async def _execute(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter],
    ) -> str:
        self._metrics.num_calls += 1

        try:
            connector = self.registry.get(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"

        param_dict = {p.parameter_name: p.parameter_value for p in parameters}
        try:
            exec_result = await connector.run_query_async(
                query,
                parameters=param_dict,
                timeout=self.timeout,
            )
            if exec_result.df is None:
                assert exec_result.error is not None
                if exec_result.error.exc_type == "ReadOnlyViolationError":
                    self._metrics.error_read_only_violation += 1
                    return f"(query failed: {exec_result.error.message})"
                elif exec_result.error.exc_type == "TimeoutError":
                    self._metrics.error_timeout += 1
                    return "(query timed out)"
                else:
                    self._metrics.error_query_failed += 1
                    return f"(query failed: {format_sqlalchemy_error_msg(exec_result.error.message)})"

            df = exec_result.df
            if df.empty:
                return "(warning: query executed successfully, but results are empty, the query might be incorrect)"

            res = format_df(
                df,
                max_visible_rows=self.max_visible_rows,
                max_cell_width=self.max_cell_width,
                floatfmt=self.floatfmt,
            )
            res += f"\n({len(df)} rows)"
            res += (
                f"\n\n(display configuration: max_visible_rows={self.max_visible_rows}, "
                f"max_cell_width={self.max_cell_width}, floatfmt='{self.floatfmt}'. "
                f"Full execution results have been recorded.)"
            )

            for hint in _detect_result_hints(df):
                res += f"\n({hint})"

            return res
        except Exception as e:
            self._metrics.error_query_failed += 1
            return f"(query failed: {e})"

    async def __call__(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] | None = None,
    ) -> str:
        if parameters is not None:
            return await self._run_with_params(db_alias, query, parameters)
        return await self._run_no_params(db_alias, query)

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._run_with_params if self.enable_params else self._run_no_params
        return Tool(fn, name=self.name)

    def metrics(self) -> RegistryRunQueryToolMetrics:
        return self._metrics
