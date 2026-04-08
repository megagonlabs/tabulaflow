"""Textual TUI application for mintq interactive chat."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input

from mintq.cli.commands import COMMAND_PREFIX, SessionState, handle_command
from mintq.cli.runtime_paths import RuntimePaths, generate_session_id
from mintq.cli.widgets import (
    AgentProgressWidget,
    AgentResultWidget,
    BannerWidget,
    HistoryInput,
    SpinnerWidget,
    SystemMessage,
    UserMessage,
)

if TYPE_CHECKING:
    from mintq.cli.agent import ChatResult

logger = logging.getLogger(__name__)


class MintqApp(App[None]):
    """Interactive database chat TUI."""

    CSS_PATH = "tui.tcss"

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("escape", "toggle_focus", "Toggle focus"),
    ]

    def __init__(self, *, model: str, agent: str) -> None:
        import asyncio

        super().__init__()
        self._model = model
        self._agent = agent
        self._session_id = generate_session_id()
        self._runtime_paths = RuntimePaths.for_session(self._session_id)
        self._session: SessionState | None = None
        self._session_lock = asyncio.Lock()
        self._busy = False

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-log")
        yield HistoryInput(
            history_path=self._runtime_paths.history_path,
            placeholder="Ask a question or type /help",
            id="input-bar",
        )

    def on_mount(self) -> None:
        self._setup_logging()
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.mount(BannerWidget(model=self._model))
        if self._debug_enabled():
            chat_log.mount(self._build_debug_small_result_widget())
            chat_log.mount(self._build_debug_chart_result_widget())
            chat_log.mount(self._build_debug_result_widget())
        self.query_one("#input-bar", Input).focus()
        chat_log.scroll_end(animate=False)
        self.run_worker(self._ensure_session())

    @staticmethod
    def _debug_enabled() -> bool:
        raw = os.getenv("DEBUG")
        if raw is None:
            return False
        return raw.strip().lower() not in {"", "0", "false", "no", "off"}

    def _build_debug_result_widget(self) -> AgentResultWidget:
        import pandas as pd

        from mintq.cli.agent import ChatResult, ChatResultRecord

        rows = 4000
        cols = 60
        col_names = [f"col_{i + 1:02d}" for i in range(cols)]
        data = {name: [f"{name}_r{r + 1:04d}" for r in range(rows)] for name in col_names}
        df = pd.DataFrame(data)
        debug_query = """\
WITH monthly_sales AS (
    SELECT
        s.store_id,
        st.store_name,
        st.region,
        st.state,
        st.city,
        st.zip_code,
        st.store_type,
        st.open_date AS store_open_date,
        dm.district_manager_name,
        dm.district_manager_email,
        DATE_TRUNC('month', s.sale_date) AS sale_month,
        COUNT(DISTINCT s.transaction_id) AS num_transactions,
        COUNT(DISTINCT s.customer_id) AS unique_customers,
        COUNT(DISTINCT s.product_id) AS unique_products,
        COUNT(DISTINCT s.employee_id) AS active_employees,
        SUM(s.quantity) AS total_units,
        SUM(s.amount) AS gross_revenue,
        SUM(s.cost_of_goods) AS total_cogs,
        SUM(s.discount_amount) AS total_discounts,
        SUM(s.tax_amount) AS total_tax,
        SUM(s.shipping_cost) AS total_shipping,
        SUM(s.amount - s.discount_amount) AS net_revenue,
        SUM(s.amount - s.cost_of_goods) AS gross_profit,
        AVG(s.amount) AS avg_transaction_value,
        MEDIAN(s.amount) AS median_transaction_value,
        STDDEV(s.amount) AS stddev_transaction_value,
        MAX(s.amount) AS max_transaction_value,
        MIN(s.amount) AS min_transaction_value,
        SUM(CASE WHEN s.channel = 'online' THEN s.amount ELSE 0 END) AS online_revenue,
        SUM(CASE WHEN s.channel = 'in_store' THEN s.amount ELSE 0 END) AS in_store_revenue,
        SUM(CASE WHEN s.is_return THEN s.amount ELSE 0 END) AS return_amount,
        COUNT(CASE WHEN s.is_return THEN 1 END) AS return_count,
        COUNT(CASE WHEN s.payment_method = 'credit_card' THEN 1 END) AS cc_transactions,
        COUNT(CASE WHEN s.payment_method = 'cash' THEN 1 END) AS cash_transactions
    FROM sales s
    JOIN stores st ON s.store_id = st.store_id
    LEFT JOIN district_managers dm ON st.district_id = dm.district_id
    WHERE s.sale_date >= '2024-01-01'
      AND s.sale_date < '2025-01-01'
      AND s.status = 'completed'
    GROUP BY s.store_id, st.store_name, st.region, st.state, st.city,
             st.zip_code, st.store_type, st.open_date,
             dm.district_manager_name, dm.district_manager_email,
             DATE_TRUNC('month', s.sale_date)
),
ranked AS (
    SELECT
        ms.*,
        ROW_NUMBER() OVER (PARTITION BY region ORDER BY gross_revenue DESC) AS region_revenue_rank,
        RANK() OVER (PARTITION BY state ORDER BY net_revenue DESC) AS state_revenue_rank,
        DENSE_RANK() OVER (PARTITION BY city ORDER BY unique_customers DESC) AS city_customer_rank,
        SUM(gross_revenue) OVER (PARTITION BY store_id ORDER BY sale_month) AS cumul_gross_revenue,
        SUM(net_revenue) OVER (PARTITION BY store_id ORDER BY sale_month) AS cumul_net_revenue,
        SUM(gross_profit) OVER (PARTITION BY store_id ORDER BY sale_month) AS cumul_gross_profit,
        LAG(gross_revenue, 1) OVER (PARTITION BY store_id ORDER BY sale_month) AS prev_month_revenue,
        LAG(unique_customers, 1) OVER (PARTITION BY store_id ORDER BY sale_month) AS prev_month_customers,
        LEAD(gross_revenue, 1) OVER (PARTITION BY store_id ORDER BY sale_month) AS next_month_revenue,
        AVG(gross_revenue) OVER (
            PARTITION BY store_id ORDER BY sale_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_avg_revenue,
        AVG(unique_customers) OVER (
            PARTITION BY region ORDER BY sale_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_avg_customers,
        AVG(gross_profit) OVER (
            PARTITION BY store_id ORDER BY sale_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_avg_profit,
        SUM(gross_revenue) OVER (PARTITION BY region, sale_month) AS region_month_total,
        SUM(gross_revenue) OVER (PARTITION BY sale_month) AS company_month_total
    FROM monthly_sales ms
)
SELECT
    store_id,
    store_name,
    region,
    state,
    city,
    zip_code,
    store_type,
    store_open_date,
    district_manager_name,
    district_manager_email,
    sale_month,
    num_transactions,
    unique_customers,
    unique_products,
    active_employees,
    total_units,
    gross_revenue,
    total_cogs,
    total_discounts,
    total_tax,
    total_shipping,
    net_revenue,
    gross_profit,
    avg_transaction_value,
    median_transaction_value,
    stddev_transaction_value,
    max_transaction_value,
    min_transaction_value,
    online_revenue,
    in_store_revenue,
    return_amount,
    return_count,
    cc_transactions,
    cash_transactions,
    region_revenue_rank,
    state_revenue_rank,
    city_customer_rank,
    cumul_gross_revenue,
    cumul_net_revenue,
    cumul_gross_profit,
    prev_month_revenue,
    prev_month_customers,
    next_month_revenue,
    rolling_3m_avg_revenue,
    rolling_3m_avg_customers,
    rolling_3m_avg_profit,
    region_month_total,
    company_month_total,
    ROUND(gross_profit / NULLIF(gross_revenue, 0) * 100, 2) AS gross_margin_pct,
    ROUND(total_discounts / NULLIF(gross_revenue, 0) * 100, 2) AS discount_pct,
    ROUND(return_amount / NULLIF(gross_revenue, 0) * 100, 2) AS return_rate_pct,
    ROUND(online_revenue / NULLIF(gross_revenue, 0) * 100, 2) AS online_share_pct,
    ROUND((gross_revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0) * 100, 2) AS mom_revenue_growth_pct, ROUND((unique_customers - prev_month_customers) / NULLIF(prev_month_customers, 0) * 100, 2) AS mom_customer_growth_pct,
    ROUND(gross_revenue / NULLIF(unique_customers, 0), 2) AS revenue_per_customer,
    ROUND(total_units / NULLIF(num_transactions, 0), 2) AS units_per_transaction,
    ROUND(gross_revenue / NULLIF(active_employees, 0), 2) AS revenue_per_employee,
    ROUND(gross_revenue / NULLIF(region_month_total, 0) * 100, 2) AS region_share_pct,
    ROUND(gross_revenue / NULLIF(company_month_total, 0) * 100, 2) AS company_share_pct,
    DATEDIFF('month', store_open_date, sale_month) AS store_age_months
FROM ranked
WHERE region_revenue_rank <= 50
ORDER BY region, gross_revenue DESC, sale_month
LIMIT 4000"""

        result = ChatResult(
            text="Debug startup table",
            records=[
                ChatResultRecord(
                    record_id="QDEBUG",
                    label="debug_4000x60",
                    query=debug_query,
                    df=df,
                    chart_spec=None,
                    query_lexer="sql",
                )
            ],
            primary_record_index=0,
        )
        return AgentResultWidget(result, width=self.size.width - 11)

    def _build_debug_small_result_widget(self) -> AgentResultWidget:
        import pandas as pd

        from mintq.cli.agent import ChatResult, ChatResultRecord

        df = pd.DataFrame(
            [
                ["alpha", "line1\nline2", "ok"],
                ["beta", "single", "multi\na\nb"],
                ["gamma", "x\ny", "42"],
                ["delta", "normal", "note\nwrapped"],
                ["epsilon", "left", "right"],
            ],
            columns=["name", "details", "status"],
        )
        query = "\n".join(
            [
                "SELECT name, details, status",
                "FROM debug_small_table",
                "LIMIT 5",
            ]
        )
        result = ChatResult(
            text="Debug startup small table",
            records=[
                ChatResultRecord(
                    record_id="QDEBUG_SMALL",
                    label="debug_5x3_multiline",
                    query=query,
                    df=df,
                    chart_spec=None,
                    query_lexer="sql",
                )
            ],
            primary_record_index=0,
        )
        return AgentResultWidget(result, width=self.size.width - 11)

    def _build_debug_chart_result_widget(self) -> AgentResultWidget:
        import pandas as pd

        from mintq.cli.agent import ChatResult, ChatResultRecord

        df = pd.DataFrame(
            {
                "category": ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller"],
                "count": [42, 35, 58, 21, 29, 18, 33],
            }
        )
        chart_spec: dict[str, object] = {
            "mark": "bar",
            "encoding": {
                "x": {"field": "category", "type": "nominal"},
                "y": {"field": "count", "type": "quantitative"},
            },
            "title": "Movies by Genre",
        }
        query = "SELECT genre AS category, COUNT(*) AS count\nFROM movies\nGROUP BY genre\nORDER BY count DESC"
        result = ChatResult(
            text="Debug chart",
            records=[
                ChatResultRecord(
                    record_id="QDEBUG_CHART",
                    label="debug_bar_chart",
                    query=query,
                    df=df,
                    chart_spec=chart_spec,
                    query_lexer="sql",
                )
            ],
            primary_record_index=0,
        )
        return AgentResultWidget(result, width=self.size.width - 11)

    def _setup_logging(self) -> None:
        from logging.handlers import RotatingFileHandler

        log_dir = self._runtime_paths.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._runtime_paths.cli_log_path

        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.INFO)
        file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        root.addHandler(file_handler)
        logging.captureWarnings(True)

        for name in (
            "LiteLLM",
            "litellm",
            "httpx",
            "httpcore",
            "urllib3",
            "grpc",
            "google",
            "google.auth",
            "google.api_core",
            "textual",
        ):
            lg = logging.getLogger(name)
            lg.handlers.clear()
            lg.propagate = True
            lg.setLevel(logging.CRITICAL)

        os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
        os.environ.setdefault("GLOG_minloglevel", "3")

    def action_toggle_focus(self) -> None:
        """Toggle focus between input bar and result widgets."""
        inp = self.query_one("#input-bar", Input)
        if inp.has_focus:
            # Jump to the last result widget
            results = self.query(AgentResultWidget)
            if results:
                results.last().focus()
                results.last().scroll_visible()
        else:
            inp.focus()

    async def _ensure_session(self) -> SessionState:
        """Get or create the session, initializing in a thread to avoid blocking the UI."""
        if self._session is not None:
            return self._session
        import asyncio

        async with self._session_lock:
            if self._session is not None:
                return self._session
            loop = asyncio.get_running_loop()
            self._session = await loop.run_in_executor(
                None,
                SessionState,
                self._model,
                self._agent,
                self._session_id,
                self._runtime_paths.trajectories_dir,
                self._runtime_paths.workspace_db_path,
            )
            await self._session.connect_workspace_db()
            return self._session

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        if self._busy:
            return

        event.input.clear()

        chat_log = self.query_one("#chat-log", VerticalScroll)

        if text.startswith(COMMAND_PREFIX):
            self._busy = True
            chat_log.mount(UserMessage(text))
            chat_log.scroll_end(animate=False)
            self.run_worker(self._handle_slash_command(text, chat_log))
            return

        session = await self._ensure_session()

        if not session.registry.list_aliases():
            chat_log.mount(UserMessage(text))
            msg = SystemMessage("[red]No database connected.[/red] Use /connect first.")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return

        chat_log.mount(UserMessage(text))
        chat_log.scroll_end(animate=False)

        self._busy = True
        self.run_worker(self._run_agent(text, session, chat_log), exclusive=True)

    async def _handle_slash_command(
        self,
        text: str,
        chat_log: VerticalScroll,
    ) -> None:
        parts = text.split()
        cmd = parts[0].lower() if parts else ""
        slow = cmd in {"/connect", "/disconnect"}

        spinner: SpinnerWidget | None = None
        if slow:
            label = "Connecting..." if cmd == "/connect" else "Disconnecting..."
            spinner = SpinnerWidget(label)
            chat_log.mount(spinner)
            chat_log.scroll_end(animate=False)

        try:
            session = await self._ensure_session()
            result = await handle_command(text, session)
        finally:
            self._busy = False
            if spinner is not None:
                await spinner.remove()

        self._show_command_result(result, session, chat_log)

    def _show_command_result(
        self,
        result: object,
        session: SessionState,
        chat_log: VerticalScroll,
    ) -> None:
        from mintq.cli.commands import CommandResult

        assert isinstance(result, CommandResult)

        if result.should_quit:
            self.exit()
            return

        if result.password_prompt:
            msg = SystemMessage(
                "[dim]Password-protected connections: include the password in the URL "
                "or set it via environment variables.[/dim]"
            )
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return

        if result.should_clear:
            chat_log.remove_children()
            chat_log.mount(BannerWidget(model=session.model))
            return

        if result.output is not None:
            msg = SystemMessage(result.output)
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

    async def _run_agent(
        self,
        question: str,
        session: SessionState,
        chat_log: VerticalScroll,
    ) -> None:
        progress = AgentProgressWidget()
        chat_log.mount(progress)
        chat_log.scroll_end(animate=False)

        try:
            result: ChatResult = await session.chat_agent.run(question, progress)
        except Exception as e:
            await progress.remove()
            msg = SystemMessage(f"[red]Agent error:[/red] {e}")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return
        finally:
            self._busy = False

        if progress._streaming_text != result.text:
            progress._streaming_text = result.text
            progress._refresh(layout=True)

        session.last_result = result
        if result.records:
            # chat-log padding (2) + scrollbar (2) + widget margin (5) + widget padding (2) = 11
            result_widget = AgentResultWidget(result, width=self.size.width - 11)
            chat_log.mount(result_widget)
            chat_log.scroll_end(animate=False)


async def run_tui(model: str, agent: str) -> None:
    """Launch the Textual TUI app."""
    app = MintqApp(model=model, agent=agent)
    await app.run_async()
