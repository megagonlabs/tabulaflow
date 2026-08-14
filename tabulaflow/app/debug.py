"""Debug visual fixtures — sample result widgets for exercising the UI.

Only used when the ``DEBUG`` env var is set (see ``debug_enabled``). Kept out of
``tui.py`` so the production ``TabulaflowApp`` carries no demo scaffolding.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tabulaflow.app.display import CardGroup, build_resolved_output_card_views
from tabulaflow.app.widgets import AgentResultWidget
from tabulaflow.core.outputs import ResultMetadata
from tabulaflow.toolhub.output_resolver import ResolvedArtifact, ResolvedChartArtifact, ResolvedOutput, ResolvedTableArtifact, UnavailableArtifact
from tabulaflow.toolhub.output_store import ResultPayload


@dataclass(frozen=True)
class DebugTablePayload:
    result_id: str
    label: str
    query: str | None
    df: "pd.DataFrame | None"
    query_lexer: str = "sql"
    graph: "GraphView | None" = None


@dataclass(frozen=True)
class DebugChartPayload(DebugTablePayload):
    chart_id: str = "CHARTDEBUG"
    chart_spec: dict[str, object] | None = None


def _debug_cards(payloads: list[DebugTablePayload], width: int) -> list[CardGroup]:
    artifacts: list[ResolvedArtifact] = []
    for payload in payloads:
        result_payload = ResultPayload(
            metadata=ResultMetadata(
                id=payload.result_id,
                db_alias="debug",
                query=payload.query or "",
                connector_type="property_graph" if payload.query_lexer == "cypher" else "sql",
                row_count=len(payload.df) if payload.df is not None else None,
                columns=[str(column) for column in payload.df.columns] if payload.df is not None else None,
            ),
            df=payload.df,
            graph=payload.graph,
        )
        if isinstance(payload, DebugChartPayload) and payload.chart_spec is not None:
            if payload.df is None:
                artifacts.append(
                    UnavailableArtifact(
                        artifact_id=payload.chart_id,
                        label=payload.label,
                        reason="Source returned no tabular data",
                        status="error",
                    )
                )
                continue
            artifacts.append(
                ResolvedChartArtifact(
                    artifact_id=payload.chart_id,
                    label=payload.label,
                    source_id=payload.result_id,
                    payload=result_payload,
                    spec=payload.chart_spec,
                )
            )
        else:
            if payload.df is None and payload.graph is None:
                artifacts.append(
                    UnavailableArtifact(
                        artifact_id=payload.result_id,
                        label=payload.label,
                        reason="Source returned no displayable data",
                        status="error",
                    )
                )
                continue
            artifacts.append(
                ResolvedTableArtifact(
                    artifact_id=payload.result_id,
                    label=payload.label,
                    source_id=payload.result_id,
                    payload=result_payload,
                )
            )
    return build_resolved_output_card_views(ResolvedOutput(selection={}, artifacts=artifacts), width)

if TYPE_CHECKING:
    import pandas as pd
    from textual.containers import VerticalScroll

    from tabulaflow.app.tui import TabulaflowApp
    from tabulaflow.core.types import GraphView


def debug_enabled() -> bool:
    raw = os.getenv("DEBUG")
    if raw is None:
        return False
    return raw.strip().lower() not in {"", "0", "false", "no", "off"}


def _build_debug_result_widget(app: TabulaflowApp) -> AgentResultWidget:
    import pandas as pd

    from tabulaflow.chat import ChatResult

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
        # Three bool columns, each with a different non-null pattern and
        # null injections — verifies ✔ / ✘ / italic-dash rendering for
        # all three states.
        "is_return": [maybe_none(r % 17 == 0, r, 11) for r in range(rows)],
        "is_gift": [maybe_none(r % 23 == 0, r, 9) for r in range(rows)],
        "is_loyalty_member": [maybe_none(r % 3 != 0, r, 14) for r in range(rows)],
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

    cards = [
        DebugTablePayload(
            result_id="QDEBUG",
            label="debug_4000x60",
            query=debug_query,
            df=df,
            query_lexer="sql",
        )
    ]
    result = ChatResult(text="Debug startup table")
    return AgentResultWidget(
        result,
        _debug_cards(cards, app.size.width - 11),
        width=app.size.width - 11,
    )


def _build_debug_huge_cell_result_widget(app: TabulaflowApp) -> AgentResultWidget:
    """Cells of varying long/wide shapes for testing CellBrowserScreen.

    - long_*: many short lines (stresses line-count / TextArea indexing)
    - wide_*: very long single lines (stresses soft-wrap recompute;
      soft_wrap auto-disables when any line > _MAX_SOFT_WRAP_LINE = 500)
    """
    import pandas as pd

    from tabulaflow.chat import ChatResult

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
    cards = [
        DebugTablePayload(
            result_id="QDEBUG_HUGE_CELL",
            label="debug_long_wide_cells",
            query="-- synthetic fixture: escalating cell sizes",
            df=df,
            query_lexer="sql",
        )
    ]
    result = ChatResult(
        text="Debug long/wide cell fixture (Enter on `value` to open CellBrowserScreen)"
    )
    return AgentResultWidget(
        result,
        _debug_cards(cards, app.size.width - 11),
        width=app.size.width - 11,
    )


def _build_debug_media_result_widget(app: TabulaflowApp) -> AgentResultWidget:
    """Synthetic table with image/audio/PDF/SVG payloads.

    Exercises the per-column media renderer used by the data browser's
    ``B`` (Open Table in Browser) shortcut. Each row uses a different
    color so the rendered thumbnails are visually distinct.
    """
    import io
    import struct
    import math
    from base64 import b64encode

    import pandas as pd
    from PIL import Image, ImageDraw

    from tabulaflow.chat import ChatResult

    def wav_bytes(freq_hz: float, seconds: float = 0.4, rate: int = 8000) -> bytes:
        # Minimal PCM WAV: header + 16-bit mono samples of a sine tone.
        n = int(seconds * rate)
        samples = bytearray()
        amp = 12_000
        for i in range(n):
            val = int(amp * math.sin(2 * math.pi * freq_hz * i / rate))
            samples += struct.pack("<h", val)
        data_size = len(samples)
        header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
        header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
        header += b"data" + struct.pack("<I", data_size)
        return bytes(header + samples)

    def pdf_bytes(label: str) -> bytes:
        img = Image.new("RGB", (240, 120), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)
        draw.text((12, 50), f"PDF: {label}", fill=(20, 20, 20))
        buf = io.BytesIO()
        img.save(buf, format="PDF")
        return buf.getvalue()

    colors = [
        ((220, 30, 30), "red"),
        ((30, 160, 30), "green"),
        ((30, 60, 220), "blue"),
        ((200, 160, 20), "amber"),
        ((150, 30, 200), "violet"),
    ]
    notes = [262.0, 294.0, 330.0, 349.0, 392.0]  # C D E F G

    names = [name for _, name in colors]
    from importlib.resources import files as _debug_files

    # Real photos (5 vendored JPEGs from picsum.photos at varied aspect
    # ratios) — exercises non-square sources and verifies that the cell
    # box hugs each image's natural dimensions.
    jpeg = [
        _debug_files("tabulaflow.app.assets.debug").joinpath(f"jpeg_{i}.jpg").read_bytes() for i in range(len(colors))
    ]
    # Five real animated GIFs at varied sizes — exercises both inline
    # (small ones) and sibling-file spill (large ones >256 KB).
    gif = [
        _debug_files("tabulaflow.app.assets.debug").joinpath(f"gif_{i}.gif").read_bytes() for i in range(len(colors))
    ]
    # Five real public-domain PDFs vendored under assets/debug —
    # exercises the PDF anchor renderer and click-to-open in new tab.
    pdf = [
        _debug_files("tabulaflow.app.assets.debug").joinpath(f"pdf_{i}.pdf").read_bytes() for i in range(len(colors))
    ]
    wav = [wav_bytes(f) for f in notes]

    # MP4 is annoying to encode at runtime (needs ffmpeg). One short clip
    # is vendored as a static asset; every row reuses it.
    mp4_bytes = _debug_files("tabulaflow.app.assets.debug").joinpath("sample.mp4").read_bytes()
    mp4 = [mp4_bytes for _ in colors]

    # Base64-encoded JPEG variants exercise the base64-string path
    # (column whose values are strings that decode to a known media MIME).
    jpeg_b64 = [b64encode(b).decode("ascii") for b in jpeg]
    jpeg_data_uri = [f"data:image/jpeg;base64,{s}" for s in jpeg_b64]

    # Mixed column: one JPEG, rest text — should NOT be detected as media
    # (under the 60% sniff threshold).
    mixed = [jpeg[0], "plain text", 42, None, "another"]

    df = pd.DataFrame(
        {
            "name": names,
            "jpeg": jpeg,
            "gif": gif,
            "pdf": pdf,
            "wav": wav,
            "mp4": mp4,
            "jpeg_b64": jpeg_b64,
            "jpeg_data_uri": jpeg_data_uri,
            "mixed": mixed,
        }
    )

    query = "-- synthetic media payloads (JPEG/GIF/PDF/WAV/MP4)"
    cards = [
        DebugTablePayload(
            result_id="QDEBUG_MEDIA",
            label="debug_media",
            query=query,
            df=df,
            query_lexer="sql",
        )
    ]
    result = ChatResult(text="Debug startup media table")
    return AgentResultWidget(
        result,
        _debug_cards(cards, app.size.width - 11),
        width=app.size.width - 11,
    )


def _build_debug_small_result_widget(app: TabulaflowApp) -> AgentResultWidget:
    import pandas as pd

    from tabulaflow.chat import ChatResult

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
    cards = [
        DebugTablePayload(
            result_id="QDEBUG_SMALL",
            label="debug_5x3_multiline",
            query=query,
            df=df,
            query_lexer="sql",
        )
    ]
    result = ChatResult(text="Debug startup small table")
    return AgentResultWidget(
        result,
        _debug_cards(cards, app.size.width - 11),
        width=app.size.width - 11,
    )


def _build_debug_quad_result_widget(app: TabulaflowApp) -> AgentResultWidget:
    """Compact 4-artifact fixture exercising every view-kind combination."""
    import pandas as pd

    from tabulaflow.chat import ChatResult

    # Artifact 1: chart artifact — Chart + Data + Query
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
        "SELECT region, SUM(amount) AS revenue, COUNT(*) AS orders\nFROM sales GROUP BY region ORDER BY revenue DESC"
    )

    # Artifact 2: card — Data + Query
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

    # Artifact 3: chart artifact — different shape
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

    # Artifact 4: card — Query-only
    low_stock_query = (
        "SELECT sku, product_name, stock_on_hand, reorder_point\n"
        "FROM inventory\n"
        "WHERE stock_on_hand < reorder_point\n"
        "ORDER BY (reorder_point - stock_on_hand) DESC"
    )

    cards: list[DebugTablePayload] = [
        DebugChartPayload(
            chart_id="CHARTDEBUG_QUAD_1",
            result_id="QDEBUG_QUAD_1",
            label="top_regions",
            chart_spec=regions_chart,
            query=regions_query,
            df=regions_df,
            query_lexer="sql",
        ),
        DebugTablePayload(
            result_id="QDEBUG_QUAD_2",
            label="top_products",
            query=products_query,
            df=products_df,
            query_lexer="sql",
        ),
        DebugChartPayload(
            chart_id="CHARTDEBUG_QUAD_3",
            result_id="QDEBUG_QUAD_3",
            label="channel_mix",
            chart_spec=channels_chart,
            query=channels_query,
            df=channels_df,
            query_lexer="sql",
        ),
        DebugTablePayload(
            result_id="QDEBUG_QUAD_4",
            label="low_stock_alerts",
            query=low_stock_query,
            df=None,
            query_lexer="sql",
        ),
    ]
    result = ChatResult(text="Debug quad-card result")
    return AgentResultWidget(
        result,
        _debug_cards(cards, app.size.width - 11),
        width=app.size.width - 11,
    )


def _build_debug_multi_result_widget(app: TabulaflowApp) -> AgentResultWidget:
    """Exercises the two-level tab UI with 15 cards of varying view kinds."""
    import random

    import pandas as pd

    from tabulaflow.chat import ChatResult

    rng = random.Random(20260423)

    # (label, sql, columns, row_hint) — one entry per card. The view mix
    # (chart / data / query) is chosen below based on the card's index so
    # we exercise every combination while stepping through.
    card_specs: list[tuple[str, str, list[str], int]] = [
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

    cards: list[DebugTablePayload] = []
    for i, (label, query, columns, n_rows) in enumerate(card_specs):
        # Every 3rd artifact is query-only, every 2nd of the rest is a chart,
        # so the final mix is: 5 chart+data+query, 5 data+query, 5 query-only.
        df = None if i % 3 == 2 else _make_df(columns, n_rows)
        chart_spec = _chart_spec_for(columns, label) if i % 3 == 0 and df is not None else None
        if chart_spec is not None:
            cards.append(
                DebugChartPayload(
                    chart_id=f"CHARTDEBUG_MULTI_{i + 1}",
                    result_id=f"QDEBUG_MULTI_{i + 1}",
                    label=label,
                    chart_spec=chart_spec,
                    query=query,
                    df=df,
                    query_lexer="sql",
                )
            )
        else:
            cards.append(
                DebugTablePayload(
                    result_id=f"QDEBUG_MULTI_{i + 1}",
                    label=label,
                    query=query,
                    df=df,
                    query_lexer="sql",
                )
            )

    result = ChatResult(text="Debug multi-card result")
    return AgentResultWidget(
        result,
        _debug_cards(cards, app.size.width - 11),
        width=app.size.width - 11,
    )


def debug_chart_fixtures() -> list[tuple[str, str, str, pd.DataFrame, dict[str, object]]]:
    """Canonical debug chart specs: ``(result_id, label, query, df, spec)``.

    Shared by the TUI debug gallery and output-pane preview fixtures. Covers
    every render path: plotext-renderable (bar/line/scatter) and beyond-plotext
    (stacked/pie/facet/heatmap).
    """
    import pandas as pd

    return [
        (
            "QDEBUG_CHART_BAR",
            "debug_bar",
            "SELECT genre AS category, COUNT(*) AS count\nFROM movies\nGROUP BY genre\nORDER BY count DESC",
            pd.DataFrame(
                {
                    "category": ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller"],
                    "count": [42, 35, 58, 21, 29, 18, 33],
                }
            ),
            {
                "mark": "bar",
                "encoding": {
                    "x": {"field": "category", "type": "nominal"},
                    "y": {"field": "count", "type": "quantitative"},
                },
                "title": "Movies by Genre",
            },
        ),
        (
            "QDEBUG_CHART_LINE",
            "debug_line",
            "SELECT month, SUM(revenue) AS revenue\nFROM sales\nGROUP BY month\nORDER BY month",
            pd.DataFrame(
                {"month": list(range(1, 13)), "revenue": [120, 135, 128, 160, 172, 168, 190, 205, 198, 210, 225, 240]}
            ),
            {
                "mark": "line",
                "encoding": {
                    "x": {"field": "month", "type": "quantitative"},
                    "y": {"field": "revenue", "type": "quantitative"},
                },
                "title": "Monthly Revenue",
            },
        ),
        (
            "QDEBUG_CHART_SCATTER",
            "debug_scatter",
            "SELECT budget_m AS budget, gross_m AS gross\nFROM movies",
            pd.DataFrame(
                {
                    "budget": [10, 25, 40, 55, 70, 90, 120, 150, 180, 200],
                    "gross": [30, 55, 42, 120, 160, 140, 300, 280, 420, 510],
                }
            ),
            {
                "mark": "point",
                "encoding": {
                    "x": {"field": "budget", "type": "quantitative"},
                    "y": {"field": "gross", "type": "quantitative"},
                },
                "title": "Budget vs Gross",
            },
        ),
        (
            "QDEBUG_CHART_STACKED",
            "debug_stacked",
            "SELECT quarter, region, SUM(sales) AS sales\nFROM sales\nGROUP BY quarter, region",
            pd.DataFrame(
                {
                    "quarter": ["Q1", "Q1", "Q2", "Q2", "Q3", "Q3", "Q4", "Q4"],
                    "region": ["North", "South"] * 4,
                    "sales": [120, 90, 150, 110, 170, 130, 200, 160],
                }
            ),
            {
                "mark": "bar",
                "encoding": {
                    "x": {"field": "quarter", "type": "nominal"},
                    "y": {"field": "sales", "type": "quantitative"},
                    "color": {"field": "region", "type": "nominal"},
                },
                "title": "Quarterly Sales by Region",
            },
        ),
        (
            "QDEBUG_CHART_PIE",
            "debug_pie",
            "SELECT vendor, share\nFROM market_share",
            pd.DataFrame({"vendor": ["AWS", "Azure", "GCP", "Other"], "share": [42, 28, 18, 12]}),
            {
                "mark": "arc",
                "encoding": {
                    "theta": {"field": "share", "type": "quantitative"},
                    "color": {"field": "vendor", "type": "nominal"},
                },
                "title": "Cloud Market Share",
            },
        ),
        (
            "QDEBUG_CHART_FACET",
            "debug_facet",
            "SELECT month, region, SUM(revenue) AS revenue\nFROM sales\nGROUP BY month, region",
            pd.DataFrame(
                [
                    {"month": m, "region": r, "revenue": (i + 1) * base + (20 if r == "West" else 0)}
                    for r, base in (("West", 40), ("East", 30))
                    for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun"])
                ]
            ),
            {
                "facet": {"field": "region", "type": "nominal", "columns": 2},
                "spec": {
                    "mark": "line",
                    "encoding": {
                        "x": {"field": "month", "type": "ordinal"},
                        "y": {"field": "revenue", "type": "quantitative"},
                    },
                },
                "title": "Revenue by Month, per Region",
            },
        ),
        (
            "QDEBUG_CHART_HEATMAP",
            "debug_heatmap",
            "SELECT day, hour, COUNT(*) AS value\nFROM events\nGROUP BY day, hour",
            pd.DataFrame(
                [
                    {"day": d, "hour": h, "value": (idx * 7 + h * 3) % 11}
                    for idx, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"])
                    for h in range(0, 24, 3)
                ]
            ),
            {
                "mark": "rect",
                "encoding": {
                    "x": {"field": "hour", "type": "ordinal"},
                    "y": {"field": "day", "type": "nominal"},
                    "color": {"field": "value", "type": "quantitative"},
                },
                "title": "Activity Heatmap",
            },
        ),
        (
            "QDEBUG_CHART_SLIDER",
            "debug_slider",
            "SELECT month, SUM(revenue) AS revenue\nFROM sales\nGROUP BY month\nORDER BY month",
            pd.DataFrame(
                {"month": list(range(1, 13)), "revenue": [120, 90, 150, 60, 175, 130, 200, 80, 160, 110, 220, 140]}
            ),
            {
                "params": [
                    {
                        "name": "min_revenue",
                        "value": 0,
                        "bind": {"input": "range", "min": 0, "max": 220, "step": 10, "name": "Min revenue: "},
                    }
                ],
                "transform": [{"filter": "datum.revenue >= min_revenue"}],
                "mark": "bar",
                "encoding": {
                    "x": {"field": "month", "type": "ordinal"},
                    "y": {"field": "revenue", "type": "quantitative"},
                },
                "title": "Revenue by Month (drag the slider)",
            },
        ),
        (
            "QDEBUG_CHART_HOVER_LINE",
            "debug_hover_line",
            "SELECT month, SUM(revenue) AS revenue\nFROM sales\nGROUP BY month\nORDER BY month",
            pd.DataFrame(
                {"month": list(range(1, 13)), "revenue": [120, 135, 128, 160, 172, 168, 190, 205, 198, 210, 225, 240]}
            ),
            {
                "encoding": {"x": {"field": "month", "type": "ordinal"}},
                "layer": [
                    {
                        "mark": {"type": "line", "point": False},
                        "encoding": {"y": {"field": "revenue", "type": "quantitative"}},
                    },
                    {
                        "params": [
                            {
                                "name": "hover",
                                "select": {
                                    "type": "point",
                                    "on": "pointerover",
                                    "nearest": True,
                                    "clear": "pointerout",
                                    "fields": ["month"],
                                },
                            }
                        ],
                        "mark": {"type": "point", "size": 90, "filled": True},
                        "encoding": {
                            "y": {"field": "revenue", "type": "quantitative"},
                            "opacity": {"condition": {"param": "hover", "empty": False, "value": 1}, "value": 0},
                        },
                    },
                ],
                "title": "Monthly Revenue (hover the line)",
            },
        ),
    ]


def _build_debug_chart_result_widget(app: TabulaflowApp) -> AgentResultWidget:
    """A gallery of chart specs covering every render path.

    Step through the cards (↑↓) to exercise each: simple bar/line/scatter
    preview inline via plotext; stacked-bar/pie/facet/heatmap show the
    "open in browser" card (Enter → ``b`` renders the real chart).
    """
    from tabulaflow.chat import ChatResult

    cards: list[DebugTablePayload] = [
        DebugChartPayload(
            chart_id=f"CHARTDEBUG_{i + 1}",
            result_id=rid,
            label=label,
            chart_spec=spec,
            query=query,
            df=df,
            query_lexer="sql",
        )
        for i, (rid, label, query, df, spec) in enumerate(debug_chart_fixtures())
    ]
    result = ChatResult(
        text="Debug charts — simple specs preview inline; rich specs show a card (Enter, then `b` to open in browser).",
        
    )
    return AgentResultWidget(
        result,
        _debug_cards(cards, app.size.width - 11),
        width=app.size.width - 11,
    )


def mount_debug_widgets(app: TabulaflowApp, chat_log: VerticalScroll) -> None:
    """Mount the sample result widgets (called from ``on_mount`` when DEBUG is set).

    Each fixture is built independently and a failure is logged and skipped
    rather than aborting the whole debug mount — e.g. the media fixture needs
    Pillow (a dev-only dependency), so it's simply absent if Pillow isn't
    installed instead of taking the other fixtures (charts, tables) down with it.
    """
    builders = (
        _build_debug_small_result_widget,
        _build_debug_chart_result_widget,
        _build_debug_quad_result_widget,
        _build_debug_multi_result_widget,
        _build_debug_huge_cell_result_widget,
        _build_debug_media_result_widget,
        _build_debug_result_widget,
    )
    for build in builders:
        try:
            chat_log.mount(build(app))
        except Exception as exc:  # noqa: BLE001 — debug-only; one bad fixture shouldn't blank the rest
            app.log(f"debug fixture {build.__name__} skipped: {exc!r}")
