"""Textual TUI application for mintq interactive chat."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input

from mintq.cli.commands import COMMAND_PREFIX, SessionState, handle_command
from mintq.cli.runtime_paths import RuntimePaths, generate_session_id, prune_old_cell_dumps
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
    from mintq.toolhub.query_history import QueryHistory

logger = logging.getLogger(__name__)


class MintqApp(App[None]):
    """Interactive database chat TUI."""

    CSS_PATH = "tui.tcss"

    BINDINGS = [
        ("ctrl+c", "interrupt_or_quit", "Interrupt / Quit"),
        ("ctrl+d", "quit_only", "Quit"),
        ("escape", "toggle_focus", "Toggle focus"),
    ]

    _INTERRUPT_DOUBLE_PRESS_WINDOW = 1.0

    def __init__(self, *, model: str, agent: str) -> None:
        import asyncio

        super().__init__()
        self._model = model
        self._agent = agent
        self._session_id = generate_session_id()
        self._runtime_paths = RuntimePaths.for_session(self._session_id)
        prune_old_cell_dumps()
        self._session: SessionState | None = None
        self._session_lock = asyncio.Lock()
        self._busy = False
        self._current_worker: object | None = None
        self._last_idle_interrupt_ts: float = 0.0
        self._saved_input_placeholder: str | None = None
        self._last_quit_hint_key: str = "Ctrl+C"

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
            chat_log.mount(self._build_debug_quad_result_widget())
            chat_log.mount(self._build_debug_multi_result_widget())
            chat_log.mount(self._build_debug_huge_cell_result_widget())
            chat_log.mount(self._build_debug_result_widget())
        self.query_one("#input-bar", Input).focus()
        chat_log.scroll_end(animate=False)
        self.run_worker(self._ensure_session())

    @staticmethod
    def _debug_history_for(result: "ChatResult") -> "QueryHistory":
        """Build a QueryHistory populated with the DFs from a debug ChatResult.

        Pokes records directly into the in-memory maps because debug widgets
        have no spill connector, so the async ``add()`` path would just be an
        awkward way to do the same in-memory bookkeeping.
        """
        from mintq.schema import ExecResult, PredQuery
        from mintq.toolhub.query_history import QueryHistory, QueryRecord

        history = QueryHistory()
        for record in result.records:
            if record.df is None:
                continue
            pred_query = PredQuery(
                id=record.record_id,
                query=record.query or "",
                exec_result=ExecResult(df=record.df),
            )
            query_record = QueryRecord(
                record_id=record.record_id,
                connector_type="sql",
                db_alias="debug",
                pred_query=pred_query,
            )
            history._records[record.record_id] = query_record
            history._in_memory.append(record.record_id)
        return history

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
        cities = [
            "New York",
            "Los Angeles",
            "Chicago",
            "Houston",
            "Phoenix",
            "Philadelphia",
            "San Antonio",
            "San Diego",
            "Dallas",
            "Austin",
        ]
        store_types = ["flagship", "mall", "outlet", "pop-up", "warehouse"]
        channels = ["online", "in_store", "phone", "marketplace"]
        payment_methods = ["credit_card", "debit_card", "cash", "apple_pay", "paypal"]
        statuses = ["completed", "pending", "refunded", "cancelled", "disputed"]
        categories = [
            "Electronics",
            "Clothing",
            "Grocery",
            "Home & Garden",
            "Sports",
            "Books",
            "Toys",
            "Beauty",
            "Automotive",
            "Jewelry",
        ]
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
            "notes": [
                maybe_none(
                    (
                        f"URGENT: Escalated to regional manager due to customer complaint ref#{r:06d}. "
                        f"Original order placed on {rand_date(r)} via {channels[r % len(channels)]}. "
                        f"Customer requested full refund plus store credit for inconvenience. "
                        f"District manager {chr(65 + r % 26)}{chr(65 + (r * 7) % 26)} approved exception. "
                        f"Follow-up scheduled for next business day. See ticket SUPPORT-{r * 3:07d} for details."
                    )
                    if r % 200 == 0 or r in (3, 17, 34)
                    else (
                        f"{'Priority order. ' if r % 11 == 0 else ''}Batch {r // 100 + 1}, "
                        f"processed via {channels[r % len(channels)]}."
                    ),
                    r,
                    4,
                )
                for r in range(rows)
            ],
            "tags": [[categories[r % len(categories)], channels[r % len(channels)]] for r in range(rows)],
            "metadata_json": [
                json.dumps(
                    {
                        "source": channels[r % len(channels)],
                        "version": f"2.{r % 10}.{r % 5}",
                        "flags": {"priority": r % 11 == 0, "reviewed": r % 3 == 0},
                        "timestamps": {
                            "created": f"2024-{(r % 12) + 1:02d}-{(r % 28) + 1:02d}T{r % 24:02d}:{r % 60:02d}:00Z",
                            "updated": f"2024-{(r % 12) + 1:02d}-{min((r % 28) + 3, 28):02d}T{r % 24:02d}:{r % 60:02d}:00Z",
                        },
                        "tags": [categories[r % len(categories)], categories[(r + 3) % len(categories)]],
                        "metrics": {
                            "clicks": r * 7 % 500,
                            "impressions": r * 13 % 10000,
                            "ctr": round((r * 7 % 500) / max(1, r * 13 % 10000), 4),
                        },
                    }
                )
                for r in range(rows)
            ],
            "config_json": [
                maybe_none(
                    json.dumps(
                        {
                            "rules": [
                                {"field": "amount", "op": ">" if r % 2 == 0 else "<=", "value": 100 + r % 900},
                                {
                                    "field": "category",
                                    "op": "in",
                                    "value": [categories[r % len(categories)], categories[(r + 1) % len(categories)]],
                                },
                            ],
                            "actions": [
                                {"type": "discount", "pct": round((r % 30) * 0.5, 1)},
                                {"type": "notify", "channel": "email"},
                            ],
                            "enabled": r % 5 != 0,
                            "description": f"Auto-rule for {regions[r % len(regions)]} region, batch {r // 100 + 1}",
                        }
                    ),
                    r,
                    6,
                )
                for r in range(rows)
            ],
            "sql_snippet": [
                maybe_none(
                    f"SELECT t.id, t.name, SUM(o.amount) AS total\nFROM transactions t\nJOIN orders o ON t.id = o.txn_id\nWHERE o.status = 'completed'\n  AND o.region = '{regions[r % len(regions)]}'\nGROUP BY t.id, t.name\nHAVING SUM(o.amount) > {100 + r % 900}\nORDER BY total DESC\nLIMIT {10 + r % 40};",
                    r,
                    7,
                )
                for r in range(rows)
            ],
            "python_snippet": [
                maybe_none(
                    f"def process_batch_{r}(items: list[dict]) -> float:\n    total = 0.0\n    for item in items:\n        if item['status'] == 'completed':\n            total += item['amount'] * (1 - item.get('discount', 0))\n    return round(total, 2)",
                    r,
                    8,
                )
                for r in range(rows)
            ],
            "native_list": [[categories[r % len(categories)], r * 3, {"nested": True, "id": r}] for r in range(rows)],
            "native_dict": [
                {"id": r, "region": regions[r % len(regions)], "amounts": [round(r * 1.5, 2), round(r * 2.3, 2)]}
                for r in range(rows)
            ],
            "str_list": [str([states[r % len(states)], cities[r % len(cities)], r % 100]) for r in range(rows)],
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
        return AgentResultWidget(
            result,
            width=self.size.width - 11,
            query_history=self._debug_history_for(result),
        )

    def _build_debug_huge_cell_result_widget(self) -> AgentResultWidget:
        """Cells of varying long/wide shapes for testing CellBrowserScreen.

        - long_*: many short lines (stresses line-count / TextArea indexing)
        - wide_*: very long single lines (stresses soft-wrap recompute;
          soft_wrap auto-disables when any line > _MAX_SOFT_WRAP_LINE = 500)
        """
        import pandas as pd

        from mintq.cli.agent import ChatResult, ChatResultRecord

        def long_json(n_items: int, note_chars: int = 0) -> dict[str, object]:
            # Pretty-printed lines per item are ~8; with note_chars > 0 each
            # item also contributes a single long "note" line of that length
            # (capped by `_MAX_JSON_LEAF = 1000` in CellBrowserScreen).
            note = ("x" * note_chars) if note_chars else None
            return {
                "meta": {"n_items": n_items, "note_chars": note_chars},
                "items": [
                    {
                        "id": i,
                        "name": f"item-{i:08d}",
                        "tags": [f"t{i % 17}", f"t{i % 31}"],
                        "score": (i * 1009) % 10_000 / 100.0,
                        **({"note": note} if note else {}),
                    }
                    for i in range(n_items)
                ],
            }

        # long_* — many short lines, all well under 500-char wrap threshold.
        long_small = long_json(50)
        long_medium = long_json(1_500)
        long_huge = long_json(15_000)
        long_giant = long_json(100_000)

        # long_wide_under_* — many lines AND every "note" line is wide but
        # still under the 500-char wrap threshold (max_line ~= note_chars + 17
        # for indent=2 nesting at depth 3). Wrap stays ON.
        long_wide_under_medium = long_json(1_500, note_chars=470)
        long_wide_under_huge = long_json(15_000, note_chars=470)
        long_wide_under_giant = long_json(100_000, note_chars=470)
        # long_wide_over_* — many lines AND every "note" line exceeds the
        # threshold, so wrap auto-disables.
        long_wide_over_medium = long_json(1_500, note_chars=800)
        long_wide_over_huge = long_json(15_000, note_chars=800)
        long_wide_over_giant = long_json(100_000, note_chars=800)

        # wide_* — single line, length controls whether wrap stays on.
        wide_just_below = "a" * 480
        wide_just_above = "b" * 520
        wide_far_above = "c" * 50_000
        wide_extreme = "d" * 2_000_000

        rows: list[tuple[str, str, object]] = [
            ("long_small", "~400 lines, max_line ~30", long_small),
            ("long_medium", "~13K lines, max_line ~30", long_medium),
            ("long_huge", "~135K lines, max_line ~30", long_huge),
            ("long_giant", "~900K lines, max_line ~30 (~13 MB)", long_giant),
            ("long_wide_under_medium", "~13K lines, max_line ~487 (wrap ON)", long_wide_under_medium),
            ("long_wide_under_huge", "~135K lines, max_line ~487 (wrap ON)", long_wide_under_huge),
            ("long_wide_under_giant", "~900K lines, max_line ~487 (wrap ON, ~62 MB)", long_wide_under_giant),
            ("long_wide_over_medium", "~13K lines, max_line ~817 (wrap OFF)", long_wide_over_medium),
            ("long_wide_over_huge", "~135K lines, max_line ~817 (wrap OFF)", long_wide_over_huge),
            ("long_wide_over_giant", "~900K lines, max_line ~817 (wrap OFF, ~95 MB)", long_wide_over_giant),
            ("wide_just_below_threshold", "1 line, 480 chars (wrap ON)", wide_just_below),
            ("wide_just_above_threshold", "1 line, 520 chars (wrap OFF)", wide_just_above),
            ("wide_far_above_threshold", "1 line, 50K chars (wrap OFF)", wide_far_above),
            ("wide_extreme", "1 line, 2M chars (wrap OFF, stress)", wide_extreme),
        ]
        df = pd.DataFrame(
            {
                "label": [r[0] for r in rows],
                "shape": [r[1] for r in rows],
                "value": [r[2] for r in rows],
            }
        )
        result = ChatResult(
            text="Debug long/wide cell fixture (Enter on `value` to open CellBrowserScreen)",
            records=[
                ChatResultRecord(
                    record_id="QDEBUG_HUGE_CELL",
                    label="debug_long_wide_cells",
                    query="-- synthetic fixture: escalating cell sizes",
                    df=df,
                    chart_spec=None,
                    query_lexer="sql",
                )
            ],
            primary_record_index=0,
        )
        return AgentResultWidget(
            result,
            width=self.size.width - 11,
            query_history=self._debug_history_for(result),
        )

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
        return AgentResultWidget(
            result,
            width=self.size.width - 11,
            query_history=self._debug_history_for(result),
        )

    def _build_debug_quad_result_widget(self) -> AgentResultWidget:
        """Compact 4-record fixture exercising every view-kind combination."""
        import pandas as pd

        from mintq.cli.agent import ChatResult, ChatResultRecord

        # Record 1: Chart + Data + Query
        regions_df = pd.DataFrame(
            {
                "region": ["Northeast", "Southeast", "Midwest", "West"],
                "revenue": [1_245_300, 982_450, 1_108_720, 1_530_900],
                "orders": [8421, 6307, 7210, 10_845],
            }
        )
        regions_chart: dict[str, object] = {
            "mark": "bar",
            "encoding": {
                "x": {"field": "region", "type": "nominal"},
                "y": {"field": "revenue", "type": "quantitative"},
            },
            "title": "Revenue by Region",
        }
        regions_query = (
            "SELECT region, SUM(amount) AS revenue, COUNT(*) AS orders\n"
            "FROM sales GROUP BY region ORDER BY revenue DESC"
        )

        # Record 2: Data + Query (no chart)
        products_df = pd.DataFrame(
            {
                "sku": ["SKU-00042", "SKU-01337", "SKU-00218", "SKU-00999", "SKU-00024"],
                "product_name": [
                    "Wireless Headphones",
                    "USB-C Hub",
                    "Mechanical Keyboard",
                    "4K Monitor",
                    "Ergonomic Mouse",
                ],
                "units_sold": [1420, 980, 760, 540, 870],
                "revenue": [198_800, 39_200, 91_200, 162_000, 43_500],
            }
        )
        products_query = (
            "SELECT sku, product_name, SUM(quantity) AS units_sold, SUM(amount) AS revenue\n"
            "FROM order_items JOIN products USING (sku)\n"
            "GROUP BY sku, product_name\n"
            "ORDER BY revenue DESC LIMIT 5"
        )

        # Record 3: Chart + Data + Query — different shape
        channels_df = pd.DataFrame(
            {
                "channel": ["online", "in_store", "phone", "marketplace"],
                "avg_order": [82.4, 124.7, 61.2, 95.3],
                "tx": [12_480, 8_915, 2_204, 5_612],
            }
        )
        channels_chart: dict[str, object] = {
            "mark": "bar",
            "encoding": {
                "x": {"field": "channel", "type": "nominal"},
                "y": {"field": "tx", "type": "quantitative"},
            },
            "title": "Transactions by Channel",
        }
        channels_query = (
            "SELECT channel, AVG(amount) AS avg_order, COUNT(*) AS tx\nFROM sales GROUP BY channel ORDER BY tx DESC"
        )

        # Record 4: Query-only
        low_stock_query = (
            "SELECT sku, product_name, stock_on_hand, reorder_point\n"
            "FROM inventory\n"
            "WHERE stock_on_hand < reorder_point\n"
            "ORDER BY (reorder_point - stock_on_hand) DESC"
        )

        result = ChatResult(
            text="Debug quad-record result",
            records=[
                ChatResultRecord(
                    record_id="QDEBUG_QUAD_1",
                    label="top_regions",
                    query=regions_query,
                    df=regions_df,
                    chart_spec=regions_chart,
                    query_lexer="sql",
                ),
                ChatResultRecord(
                    record_id="QDEBUG_QUAD_2",
                    label="top_products",
                    query=products_query,
                    df=products_df,
                    chart_spec=None,
                    query_lexer="sql",
                ),
                ChatResultRecord(
                    record_id="QDEBUG_QUAD_3",
                    label="channel_mix",
                    query=channels_query,
                    df=channels_df,
                    chart_spec=channels_chart,
                    query_lexer="sql",
                ),
                ChatResultRecord(
                    record_id="QDEBUG_QUAD_4",
                    label="low_stock_alerts",
                    query=low_stock_query,
                    df=None,
                    chart_spec=None,
                    query_lexer="sql",
                ),
            ],
            primary_record_index=0,
        )
        return AgentResultWidget(
            result,
            width=self.size.width - 11,
            query_history=self._debug_history_for(result),
        )

    def _build_debug_multi_result_widget(self) -> AgentResultWidget:
        """Exercises the two-level tab UI with 15 records of varying view kinds."""
        import random

        import pandas as pd

        from mintq.cli.agent import ChatResult, ChatResultRecord

        rng = random.Random(20260423)

        # (label, sql, columns, row_hint) — one entry per record. The view mix
        # (chart / data / query) is chosen below based on the record's index so
        # we exercise every combination while stepping through.
        record_specs: list[tuple[str, str, list[str], int]] = [
            (
                "top_regions",
                "SELECT region, SUM(amount) AS revenue, COUNT(*) AS orders\nFROM sales GROUP BY region ORDER BY revenue DESC",
                ["region", "revenue", "orders"],
                5,
            ),
            (
                "top_products",
                "SELECT sku, product_name, SUM(quantity) AS units_sold, SUM(amount) AS revenue\nFROM order_items JOIN products USING (sku)\nGROUP BY sku, product_name ORDER BY revenue DESC LIMIT 8",
                ["sku", "product_name", "units_sold", "revenue"],
                8,
            ),
            (
                "low_stock_alerts",
                "SELECT sku, product_name, stock_on_hand, reorder_point\nFROM inventory\nWHERE stock_on_hand < reorder_point\nORDER BY (reorder_point - stock_on_hand) DESC",
                ["sku", "product_name", "stock", "reorder_point"],
                6,
            ),
            (
                "monthly_revenue",
                "SELECT DATE_TRUNC('month', sale_date) AS month, SUM(amount) AS revenue\nFROM sales GROUP BY 1 ORDER BY 1",
                ["month", "revenue", "orders"],
                12,
            ),
            (
                "top_customers",
                "SELECT customer_id, COUNT(*) AS orders, SUM(amount) AS lifetime_value\nFROM sales GROUP BY customer_id ORDER BY lifetime_value DESC LIMIT 10",
                ["customer_id", "orders", "lifetime_value"],
                10,
            ),
            (
                "returns_summary",
                "SELECT category, COUNT(*) AS returns, SUM(refund_amount) AS refunded\nFROM returns GROUP BY category ORDER BY refunded DESC",
                ["category", "returns", "refunded"],
                7,
            ),
            (
                "channel_performance",
                "SELECT channel, AVG(amount) AS avg_order, SUM(amount) AS revenue\nFROM sales GROUP BY channel ORDER BY revenue DESC",
                ["channel", "avg_order", "revenue"],
                4,
            ),
            (
                "state_rankings",
                "SELECT state, SUM(amount) AS revenue, RANK() OVER (ORDER BY SUM(amount) DESC) AS rank\nFROM sales GROUP BY state",
                ["state", "revenue", "rank"],
                10,
            ),
            (
                "category_growth",
                "SELECT category, revenue, revenue - LAG(revenue) OVER (PARTITION BY category ORDER BY month) AS mom_delta\nFROM monthly_category_revenue",
                ["category", "revenue", "mom_delta"],
                10,
            ),
            (
                "employee_stats",
                "SELECT employee_id, COUNT(*) AS tx, SUM(amount) AS revenue\nFROM sales GROUP BY employee_id ORDER BY revenue DESC LIMIT 12",
                ["employee_id", "tx", "revenue"],
                12,
            ),
            (
                "shipping_costs",
                "SELECT carrier, AVG(shipping_cost) AS avg_cost, SUM(shipping_cost) AS total_cost\nFROM shipments GROUP BY carrier",
                ["carrier", "avg_cost", "total_cost"],
                5,
            ),
            (
                "payment_methods",
                "SELECT payment_method, COUNT(*) AS tx, SUM(amount) AS revenue\nFROM sales GROUP BY payment_method ORDER BY revenue DESC",
                ["payment_method", "tx", "revenue"],
                5,
            ),
            (
                "refund_trends",
                "WITH monthly_refunds AS (...)\nSELECT month, refund_count, refund_amount FROM monthly_refunds ORDER BY month",
                ["month", "refund_count", "refund_amount"],
                12,
            ),
            (
                "new_signups",
                "SELECT DATE_TRUNC('week', signup_at) AS week, COUNT(*) AS signups\nFROM users GROUP BY 1 ORDER BY 1",
                ["week", "signups"],
                8,
            ),
            (
                "churn_risk",
                "SELECT customer_id, last_order_days, predicted_churn_prob\nFROM churn_model\nORDER BY predicted_churn_prob DESC LIMIT 15",
                ["customer_id", "last_order_days", "predicted_churn_prob"],
                15,
            ),
        ]

        def _make_df(columns: list[str], n_rows: int) -> pd.DataFrame:
            data: dict[str, list[Any]] = {}
            for col in columns:
                lower = col.lower()
                if lower.endswith("_id") or lower == "customer_id" or lower == "employee_id":
                    data[col] = [f"ID-{rng.randrange(10000, 99999)}" for _ in range(n_rows)]
                elif lower == "sku":
                    data[col] = [f"SKU-{rng.randrange(1, 9999):05d}" for _ in range(n_rows)]
                elif lower == "product_name":
                    names = [
                        "Wireless Headphones",
                        "USB-C Hub",
                        "Mechanical Keyboard",
                        "4K Monitor",
                        "Desk Lamp",
                        "Ergonomic Mouse",
                        "Standing Desk",
                        "Webcam",
                    ]
                    data[col] = [rng.choice(names) for _ in range(n_rows)]
                elif lower == "region":
                    data[col] = ["Northeast", "Southeast", "Midwest", "West", "Southwest"][:n_rows]
                elif lower == "state":
                    states = ["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
                    data[col] = states[:n_rows]
                elif lower == "category":
                    cats = ["Electronics", "Clothing", "Grocery", "Home", "Sports", "Books", "Toys"]
                    data[col] = [rng.choice(cats) for _ in range(n_rows)]
                elif lower == "channel":
                    data[col] = ["online", "in_store", "phone", "marketplace"][:n_rows]
                elif lower == "payment_method":
                    data[col] = ["credit_card", "debit_card", "cash", "apple_pay", "paypal"][:n_rows]
                elif lower == "carrier":
                    data[col] = ["UPS", "FedEx", "USPS", "DHL", "OnTrac"][:n_rows]
                elif lower == "month":
                    data[col] = [f"2025-{m:02d}" for m in range(1, n_rows + 1)]
                elif lower == "week":
                    data[col] = [f"2026-W{w:02d}" for w in range(1, n_rows + 1)]
                elif "rank" in lower:
                    data[col] = list(range(1, n_rows + 1))
                elif "prob" in lower:
                    data[col] = [round(rng.random(), 3) for _ in range(n_rows)]
                elif any(k in lower for k in ("revenue", "cost", "value", "amount", "refunded")):
                    data[col] = [round(rng.uniform(5_000, 250_000), 2) for _ in range(n_rows)]
                elif lower == "avg_order" or lower == "avg_cost":
                    data[col] = [round(rng.uniform(20, 400), 2) for _ in range(n_rows)]
                elif lower == "mom_delta":
                    data[col] = [round(rng.uniform(-50_000, 50_000), 2) for _ in range(n_rows)]
                elif "days" in lower:
                    data[col] = [rng.randrange(1, 180) for _ in range(n_rows)]
                else:  # generic integer counts: orders, tx, returns, signups, units_sold, stock, reorder_point, etc.
                    data[col] = [rng.randrange(10, 5000) for _ in range(n_rows)]
            return pd.DataFrame(data)

        def _chart_spec_for(columns: list[str], label: str) -> dict[str, object] | None:
            if len(columns) < 2:
                return None
            x_col = columns[0]
            y_col = None
            for c in columns[1:]:
                if any(
                    k in c.lower() for k in ("revenue", "count", "orders", "tx", "amount", "cost", "signups", "returns")
                ):
                    y_col = c
                    break
            if y_col is None:
                y_col = columns[1]
            return {
                "mark": "bar",
                "encoding": {
                    "x": {"field": x_col, "type": "nominal"},
                    "y": {"field": y_col, "type": "quantitative"},
                },
                "title": label.replace("_", " ").title(),
            }

        records: list[ChatResultRecord] = []
        for i, (label, query, columns, n_rows) in enumerate(record_specs):
            # Every 3rd record is query-only, every 2nd of the rest has a chart,
            # so the final mix is: 5 chart+data+query, 5 data+query, 5 query-only.
            if i % 3 == 2:
                df = None
                chart_spec: dict[str, object] | None = None
            else:
                df = _make_df(columns, n_rows)
                chart_spec = _chart_spec_for(columns, label) if i % 3 == 0 else None
            records.append(
                ChatResultRecord(
                    record_id=f"QDEBUG_MULTI_{i + 1}",
                    label=label,
                    query=query,
                    df=df,
                    chart_spec=chart_spec,
                    query_lexer="sql",
                )
            )

        result = ChatResult(
            text="Debug multi-record result",
            records=records,
            primary_record_index=0,
        )
        return AgentResultWidget(
            result,
            width=self.size.width - 11,
            query_history=self._debug_history_for(result),
        )

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
        return AgentResultWidget(
            result,
            width=self.size.width - 11,
            query_history=self._debug_history_for(result),
        )

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

    def action_interrupt_or_quit(self) -> None:
        """Ctrl+C:
        - If a turn is running: cancel it.
        - Else if the input has text: clear it.
        - Else (input empty): show the quit hint; a second press within the
          window quits.
        """
        if self._busy and self._current_worker is not None:
            self._current_worker.cancel()  # type: ignore[attr-defined]
            self._last_idle_interrupt_ts = 0.0
            return

        inp = self.query_one("#input-bar", Input)
        if inp.value:
            inp.value = ""
            self._last_idle_interrupt_ts = 0.0
            return

        self._confirm_idle_quit("Ctrl+C", inp)

    def action_quit_only(self) -> None:
        """Ctrl+D:
        - Never interrupts a running turn.
        - Else mirrors idle quit behavior (double press within the window).
        """
        if self._busy:
            return

        inp = self.query_one("#input-bar", Input)
        if inp.value:
            inp.value = ""
            self._last_idle_interrupt_ts = 0.0
            return

        self._confirm_idle_quit("Ctrl+D", inp)

    def _confirm_idle_quit(self, key: str, inp: Input) -> None:
        """Quit only when the same idle quit key is pressed twice."""
        import time

        now = time.monotonic()
        if (
            self._last_quit_hint_key == key
            and (now - self._last_idle_interrupt_ts) < self._INTERRUPT_DOUBLE_PRESS_WINDOW
        ):
            self._request_exit()
            return

        self._last_idle_interrupt_ts = now
        self._last_quit_hint_key = key
        if self._saved_input_placeholder is None:
            self._saved_input_placeholder = inp.placeholder
        inp.placeholder = f"Press {self._last_quit_hint_key} again to quit"
        self.set_timer(self._INTERRUPT_DOUBLE_PRESS_WINDOW, self._restore_input_placeholder)

    def _request_exit(self) -> None:
        """Single quit path: disconnect all registered connectors, then
        exit the app.  Every quit trigger (slash command, idle Ctrl+C /
        Ctrl+D double-press, …) routes through here so DB connections
        and DuckDB file locks are always released cleanly.
        """
        if self._session is None:
            self.exit()
            return
        self.run_worker(self._shutdown_then_exit(), exclusive=False, group="shutdown")

    async def _shutdown_then_exit(self) -> None:
        assert self._session is not None
        try:
            await self._session.registry.disconnect_all_async()
        except Exception:
            logger.debug("disconnect_all_async failed during exit", exc_info=True)
        finally:
            self.exit()

    def _restore_input_text(self, text: str) -> None:
        """Put `text` back into the input bar and focus it. Used after a
        cancelled turn so the user can edit and resubmit. If the input
        already has content (the user started typing something new during
        the turn), leave it alone."""
        try:
            inp = self.query_one("#input-bar", Input)
        except Exception:
            return
        if inp.value:
            return
        inp.value = text
        inp.cursor_position = len(text)
        inp.focus()

    def _restore_input_placeholder(self) -> None:
        import time

        if (time.monotonic() - self._last_idle_interrupt_ts) < self._INTERRUPT_DOUBLE_PRESS_WINDOW:
            return
        if self._saved_input_placeholder is None:
            return
        try:
            inp = self.query_one("#input-bar", Input)
        except Exception:
            return
        inp.placeholder = self._saved_input_placeholder
        self._saved_input_placeholder = None

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
        display_text = event.value.strip()
        if not display_text:
            return

        if self._busy:
            return

        inp = event.input
        text = inp.expand_paste_tokens(display_text) if isinstance(inp, HistoryInput) else display_text

        event.input.clear()

        chat_log = self.query_one("#chat-log", VerticalScroll)

        if text.startswith(COMMAND_PREFIX):
            self._busy = True
            user_msg = UserMessage(text)
            await chat_log.mount(user_msg)
            chat_log.scroll_end(animate=False)
            self._current_worker = self.run_worker(self._handle_slash_command(text, chat_log, user_msg, display_text))
            return

        session = await self._ensure_session()

        if not session.registry.list_aliases():
            await chat_log.mount(UserMessage(text))
            msg = SystemMessage(Text.from_markup("[red]No database connected.[/red] Use /connect first."))
            await chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return

        user_msg = UserMessage(text)
        await chat_log.mount(user_msg)
        chat_log.scroll_end(animate=False)

        self._busy = True
        self._current_worker = self.run_worker(
            self._run_agent(text, session, chat_log, user_msg, display_text), exclusive=True
        )

    @staticmethod
    async def _connect_spinner_label(parts: list[str]) -> str:
        """Build a spinner label for /connect."""
        return "Connecting..."

    async def _handle_slash_command(
        self,
        text: str,
        chat_log: VerticalScroll,
        user_msg: UserMessage,
        display_text: str | None = None,
    ) -> None:
        parts = text.split()
        cmd = parts[0].lower() if parts else ""
        slow = cmd in {"/connect", "/disconnect"} and len(parts) > 1

        spinner: SpinnerWidget | None = None
        if slow:
            label = "Connecting..." if cmd == "/connect" else "Disconnecting..."
            spinner = SpinnerWidget(label)
            # Await the mount: a fast-failing handle_command (e.g. validation
            # error) may return without yielding, never giving the event loop
            # a chance to process a non-awaited mount before we hit the
            # ``finally`` — leaving the spinner queued-but-not-removed.
            await chat_log.mount(spinner)
            chat_log.scroll_end(animate=False)
            # Refine label with dataset size info (non-blocking).
            if cmd == "/connect":
                refined = await self._connect_spinner_label(parts)
                if spinner._label != refined:
                    spinner.update_label(refined)

        import asyncio

        try:
            session = await self._ensure_session()
            result = await handle_command(text, session)
        except asyncio.CancelledError:
            await user_msg.remove()
            await chat_log.mount(SystemMessage("\n[dim]Interrupted[/dim]"))
            chat_log.scroll_end(animate=False)
            self._restore_input_text(display_text if display_text is not None else text)
            raise
        finally:
            self._busy = False
            self._current_worker = None
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
            self._request_exit()
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

        if result.browse is not None:
            from mintq.cli.widgets import SchemaBrowserScreen

            alias = result.browse if isinstance(result.browse, str) else None
            self.push_screen(SchemaBrowserScreen(registry=session.registry, alias=alias))
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
        user_msg: UserMessage,
        display_text: str | None = None,
    ) -> None:
        import asyncio

        progress = AgentProgressWidget()
        await chat_log.mount(progress)
        chat_log.scroll_end(animate=False)

        try:
            result: ChatResult = await session.chat_agent.run(question, progress)
        except asyncio.CancelledError:
            # Keep the partial progress widget visible — ChatAgent has already
            # frozen it via progress.freeze_as_interrupted() with the resume
            # hint and final usage.
            await chat_log.mount(SystemMessage("[dim]Interrupted[/dim]"))
            chat_log.scroll_end(animate=False)
            self._restore_input_text(display_text if display_text is not None else question)
            raise
        except Exception as e:
            await progress.remove()
            msg = SystemMessage(f"[red]Agent error:[/red] {e}")
            await chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            return
        finally:
            self._busy = False
            self._current_worker = None

        if progress._streaming_text != result.text:
            progress._streaming_text = result.text
            progress._refresh(layout=True)

        session.last_result = result
        if result.records:
            # chat-log padding (2) + scrollbar (2) + widget margin (5) + widget padding (2) = 11
            result_widget = AgentResultWidget(
                result,
                width=self.size.width - 11,
                query_history=session.chat_agent._query_history,
            )
            await chat_log.mount(result_widget)

        # Defer scroll until after layout reflow so the final content height is known.
        self.call_after_refresh(chat_log.scroll_end, animate=False)


async def run_tui(model: str, agent: str) -> None:
    """Launch the Textual TUI app."""
    app = MintqApp(model=model, agent=agent)
    await app.run_async()
