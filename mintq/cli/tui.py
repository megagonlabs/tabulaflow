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

        import datetime
        import json
        import math
        import random

        random.seed(42)
        rows = 4000

        regions = ["Northeast", "Southeast", "Midwest", "West", "Southwest"]
        states = ["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
                  "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin"]
        store_types = ["flagship", "mall", "outlet", "pop-up", "warehouse"]
        channels = ["online", "in_store", "phone", "marketplace"]
        payment_methods = ["credit_card", "debit_card", "cash", "apple_pay", "paypal"]
        statuses = ["completed", "pending", "refunded", "cancelled", "disputed"]
        categories = ["Electronics", "Clothing", "Grocery", "Home & Garden",
                      "Sports", "Books", "Toys", "Beauty", "Automotive", "Jewelry"]
        base_date = datetime.date(2024, 1, 1)
        base_dt = datetime.datetime(2024, 1, 1, 8, 0, 0)

        def rand_date(r: int) -> datetime.date:
            return base_date + datetime.timedelta(days=r % 365)

        def rand_datetime(r: int) -> datetime.datetime:
            return base_dt + datetime.timedelta(days=r % 365, hours=r % 24, minutes=r % 60)

        def maybe_none(val: object, r: int, freq: int = 20) -> object:
            return None if r % freq == 0 else val

        data: dict[str, list[object]] = {
            "store_id": [1000 + r % 500 for r in range(rows)],
            "transaction_id": [f"TXN-{r + 1:08d}" for r in range(rows)],
            "store_name": [f"Store #{1000 + r % 500}" for r in range(rows)],
            "region": [regions[r % len(regions)] for r in range(rows)],
            "state": [states[r % len(states)] for r in range(rows)],
            "city": [cities[r % len(cities)] for r in range(rows)],
            "zip_code": [f"{10000 + r % 90000}" for r in range(rows)],
            "store_type": [store_types[r % len(store_types)] for r in range(rows)],
            "channel": [channels[r % len(channels)] for r in range(rows)],
            "payment_method": [payment_methods[r % len(payment_methods)] for r in range(rows)],
            "status": [statuses[r % len(statuses)] for r in range(rows)],
            "category": [categories[r % len(categories)] for r in range(rows)],
            "sale_date": [rand_date(r) for r in range(rows)],
            "sale_datetime": [rand_datetime(r) for r in range(rows)],
            "store_open_date": [datetime.date(2015 + r % 10, (r % 12) + 1, (r % 28) + 1) for r in range(rows)],
            "customer_id": [maybe_none(50000 + r * 3, r) for r in range(rows)],
            "employee_id": [200 + r % 80 for r in range(rows)],
            "product_id": [f"SKU-{r % 2000:05d}" for r in range(rows)],
            "quantity": [1 + r % 25 for r in range(rows)],
            "unit_price": [round(0.99 + (r % 500) * 1.5, 2) for r in range(rows)],
            "amount": [round(10.0 + (r % 1000) * 4.73, 2) for r in range(rows)],
            "cost_of_goods": [round(5.0 + (r % 800) * 2.91, 2) for r in range(rows)],
            "discount_amount": [maybe_none(round((r % 50) * 0.75, 2), r, 5) for r in range(rows)],
            "tax_amount": [round(0.5 + (r % 300) * 0.42, 2) for r in range(rows)],
            "shipping_cost": [maybe_none(round((r % 40) * 1.25, 2), r, 8) for r in range(rows)],
            "is_return": [r % 17 == 0 for r in range(rows)],
            "is_gift": [r % 23 == 0 for r in range(rows)],
            "is_loyalty_member": [r % 3 != 0 for r in range(rows)],
            "loyalty_points": [maybe_none(r * 7 % 10000, r, 3) for r in range(rows)],
            "net_revenue": [round(10.0 + (r % 1000) * 4.73 - (r % 50) * 0.75, 2) for r in range(rows)],
            "gross_profit": [round(5.0 + (r % 500) * 1.82, 2) for r in range(rows)],
            "gross_margin_pct": [round(20.0 + (r % 60) * 0.8, 2) for r in range(rows)],
            "discount_pct": [maybe_none(round((r % 30) * 0.5, 2), r, 5) for r in range(rows)],
            "return_rate_pct": [round((r % 15) * 0.3, 2) for r in range(rows)],
            "online_share_pct": [round(10.0 + (r % 80) * 0.9, 2) for r in range(rows)],
            "mom_revenue_growth_pct": [maybe_none(round(-15.0 + (r % 60) * 0.7, 2), r, 12) for r in range(rows)],
            "yoy_revenue_growth_pct": [maybe_none(round(-25.0 + (r % 80) * 0.9, 2), r, 15) for r in range(rows)],
            "revenue_per_customer": [round(50.0 + (r % 400) * 2.3, 2) for r in range(rows)],
            "units_per_transaction": [round(1.0 + (r % 10) * 0.3, 2) for r in range(rows)],
            "avg_basket_size": [round(25.0 + (r % 200) * 1.1, 2) for r in range(rows)],
            "num_transactions": [10 + r % 500 for r in range(rows)],
            "unique_customers": [5 + r % 300 for r in range(rows)],
            "unique_products": [3 + r % 150 for r in range(rows)],
            "active_employees": [2 + r % 30 for r in range(rows)],
            "region_revenue_rank": [1 + r % 50 for r in range(rows)],
            "state_revenue_rank": [1 + r % 100 for r in range(rows)],
            "cumul_gross_revenue": [round((r + 1) * 473.21, 2) for r in range(rows)],
            "rolling_3m_avg_revenue": [maybe_none(round(1000.0 + (r % 500) * 8.3, 2), r, 10) for r in range(rows)],
            "store_age_months": [6 + r % 120 for r in range(rows)],
            "latitude": [round(25.0 + (r % 2000) * 0.01, 6) for r in range(rows)],
            "longitude": [round(-125.0 + (r % 5000) * 0.01, 6) for r in range(rows)],
            "customer_email": [maybe_none(f"user{r % 3000}@example.com", r, 7) for r in range(rows)],
            "manager_name": [f"Manager {chr(65 + r % 26)}{chr(65 + (r * 7) % 26)}" for r in range(rows)],
            "manager_email": [f"mgr{r % 80}@corp.example.com" for r in range(rows)],
            "notes": [maybe_none(
                (
                    f"URGENT: Escalated to regional manager due to customer complaint ref#{r:06d}. "
                    f"Original order placed on {rand_date(r)} via {channels[r % len(channels)]}. "
                    f"Customer requested full refund plus store credit for inconvenience. "
                    f"District manager {chr(65 + r % 26)}{chr(65 + (r * 7) % 26)} approved exception. "
                    f"Follow-up scheduled for next business day. See ticket SUPPORT-{r * 3:07d} for details."
                ) if r % 200 == 0 or r in (3, 17, 34) else (
                    f"{'Priority order. ' if r % 11 == 0 else ''}Batch {r // 100 + 1}, "
                    f"processed via {channels[r % len(channels)]}."
                ),
                r, 4,
            ) for r in range(rows)],
            "tags": [[categories[r % len(categories)], channels[r % len(channels)]] for r in range(rows)],
            "metadata_json": [
                json.dumps({
                    "source": channels[r % len(channels)],
                    "version": f"2.{r % 10}.{r % 5}",
                    "flags": {"priority": r % 11 == 0, "reviewed": r % 3 == 0},
                    "timestamps": {
                        "created": f"2024-{(r % 12) + 1:02d}-{(r % 28) + 1:02d}T{r % 24:02d}:{r % 60:02d}:00Z",
                        "updated": f"2024-{(r % 12) + 1:02d}-{min((r % 28) + 3, 28):02d}T{r % 24:02d}:{r % 60:02d}:00Z",
                    },
                    "tags": [categories[r % len(categories)], categories[(r + 3) % len(categories)]],
                    "metrics": {"clicks": r * 7 % 500, "impressions": r * 13 % 10000, "ctr": round((r * 7 % 500) / max(1, r * 13 % 10000), 4)},
                }) for r in range(rows)
            ],
            "config_json": [maybe_none(
                json.dumps({
                    "rules": [
                        {"field": "amount", "op": ">" if r % 2 == 0 else "<=", "value": 100 + r % 900},
                        {"field": "category", "op": "in", "value": [categories[r % len(categories)], categories[(r + 1) % len(categories)]]},
                    ],
                    "actions": [{"type": "discount", "pct": round((r % 30) * 0.5, 1)}, {"type": "notify", "channel": "email"}],
                    "enabled": r % 5 != 0,
                    "description": f"Auto-rule for {regions[r % len(regions)]} region, batch {r // 100 + 1}",
                }), r, 6,
            ) for r in range(rows)],
            "sql_snippet": [maybe_none(
                f"SELECT t.id, t.name, SUM(o.amount) AS total\nFROM transactions t\nJOIN orders o ON t.id = o.txn_id\nWHERE o.status = 'completed'\n  AND o.region = '{regions[r % len(regions)]}'\nGROUP BY t.id, t.name\nHAVING SUM(o.amount) > {100 + r % 900}\nORDER BY total DESC\nLIMIT {10 + r % 40};",
                r, 7,
            ) for r in range(rows)],
            "python_snippet": [maybe_none(
                f"def process_batch_{r}(items: list[dict]) -> float:\n    total = 0.0\n    for item in items:\n        if item['status'] == 'completed':\n            total += item['amount'] * (1 - item.get('discount', 0))\n    return round(total, 2)",
                r, 8,
            ) for r in range(rows)],
            "native_list": [
                [categories[r % len(categories)], r * 3, {"nested": True, "id": r}]
                for r in range(rows)
            ],
            "native_dict": [
                {"id": r, "region": regions[r % len(regions)], "amounts": [round(r * 1.5, 2), round(r * 2.3, 2)]}
                for r in range(rows)
            ],
            "str_list": [
                str([states[r % len(states)], cities[r % len(cities)], r % 100])
                for r in range(rows)
            ],
            "str_dict": [
                str({"key": f"item_{r}", "value": round(r * 0.7, 2), "tags": [categories[r % len(categories)]]})
                for r in range(rows)
            ],
            "score": [maybe_none(round(math.sin(r * 0.1) * 50 + 50, 4), r, 25) for r in range(rows)],
            "rating": [round(1.0 + (r % 40) * 0.1, 1) for r in range(rows)],
            "weight_kg": [maybe_none(round(0.1 + (r % 200) * 0.25, 3), r, 9) for r in range(rows)],
        }
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
                self._runtime_paths.data_dir,
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

    @staticmethod
    async def _connect_spinner_label(parts: list[str]) -> str:
        """Build a spinner label for /connect."""
        return "Connecting..."

    async def _handle_slash_command(
        self,
        text: str,
        chat_log: VerticalScroll,
    ) -> None:
        parts = text.split()
        cmd = parts[0].lower() if parts else ""
        slow = cmd in {"/connect", "/disconnect"} and len(parts) > 1

        spinner: SpinnerWidget | None = None
        if slow:
            # Remove bottom margin on user message for tight command output.
            children = list(chat_log.children)
            if children and isinstance(children[-1], UserMessage):
                children[-1].styles.margin = (1, 0, 0, 0)
            label = "Connecting..." if cmd == "/connect" else "Disconnecting..."
            spinner = SpinnerWidget(label)
            chat_log.mount(spinner)
            chat_log.scroll_end(animate=False)
            # Refine label with dataset size info (non-blocking).
            if cmd == "/connect":
                refined = await self._connect_spinner_label(parts)
                if spinner._label != refined:
                    spinner.update_label(refined)

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

        # Defer scroll until after layout reflow so the final content height is known.
        self.call_after_refresh(chat_log.scroll_end, animate=False)


async def run_tui(model: str, agent: str) -> None:
    """Launch the Textual TUI app."""
    app = MintqApp(model=model, agent=agent)
    await app.run_async()
