#!/usr/bin/env python3
"""Benchmark ``run_subagent_for_each_row`` on a synthetic 1,000-row table.

The benchmark records time spent waiting for the process-wide LLM concurrency
limit, the LLM RPM limiter, the provider, and DuckDB write-back. Run it with:

    uv run python scripts/app/benchmark_run_subagent.py

Use ``--tool-concurrency`` and ``--llm-concurrency`` in separate runs to test
which cap controls throughput. The default model and reasoning effort match the
OpenAI subagent profile used by the app.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sqlalchemy
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.settings import ModelSettings

from tabulaflow.agents import llm as llm_module
from tabulaflow.agents.config import AgentRuntimeConfig
from tabulaflow.agents.llm import make_model_settings
from tabulaflow.agents.runtime import _get_agent_runtime, initialize_agent_runtime
from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool
from tabulaflow.core.results import ExecResult
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector

MODEL = "openai:gpt-5.6-luna"


def percentile(values: list[float], fraction: float) -> float:
    """Return a nearest-rank percentile, or zero for an empty sample."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def latency_summary(values: list[float]) -> dict[str, float]:
    """Summarize a latency sample in seconds."""
    return {
        "mean": statistics.fmean(values) if values else 0.0,
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values, default=0.0),
    }


@dataclass
class LLMProbe:
    """Measurements taken around TabulaFlow's process-wide LLM throttles."""

    request_count: int = 0
    waiting_for_concurrency: int = 0
    waiting_for_rpm: int = 0
    active_provider_requests: int = 0
    max_waiting_for_concurrency: int = 0
    max_waiting_for_rpm: int = 0
    max_active_provider_requests: int = 0
    concurrency_wait_seconds: list[float] = field(default_factory=list)
    rpm_wait_seconds: list[float] = field(default_factory=list)
    provider_seconds: list[float] = field(default_factory=list)


@dataclass
class DatabaseProbe:
    """Measurements for per-row UPDATE calls made by the tool."""

    active_updates: int = 0
    max_active_updates: int = 0
    update_seconds: list[float] = field(default_factory=list)


def install_llm_probe(probe: LLMProbe) -> Any:
    """Instrument the same semaphore/limiter sequence used by ``_ThrottledModel``."""
    original = llm_module._ThrottledModel.request

    async def measured_request(
        model: llm_module._ThrottledModel,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        semaphore, limiter = _get_agent_runtime().llm_throttles()
        probe.request_count += 1

        concurrency_started = time.perf_counter()
        if semaphore is not None:
            probe.waiting_for_concurrency += 1
            probe.max_waiting_for_concurrency = max(probe.max_waiting_for_concurrency, probe.waiting_for_concurrency)
            await semaphore.acquire()
            probe.waiting_for_concurrency -= 1
        probe.concurrency_wait_seconds.append(time.perf_counter() - concurrency_started)

        try:
            rpm_started = time.perf_counter()
            if limiter is not None:
                probe.waiting_for_rpm += 1
                probe.max_waiting_for_rpm = max(probe.max_waiting_for_rpm, probe.waiting_for_rpm)
                await limiter.acquire()
                probe.waiting_for_rpm -= 1
            probe.rpm_wait_seconds.append(time.perf_counter() - rpm_started)

            provider_started = time.perf_counter()
            probe.active_provider_requests += 1
            probe.max_active_provider_requests = max(probe.max_active_provider_requests, probe.active_provider_requests)
            try:
                return await model.wrapped.request(messages, model_settings, model_request_parameters)
            finally:
                probe.active_provider_requests -= 1
                probe.provider_seconds.append(time.perf_counter() - provider_started)
        finally:
            if semaphore is not None:
                semaphore.release()

    setattr(llm_module._ThrottledModel, "request", measured_request)
    return original


def install_database_probe(connector: SQLConnector, probe: DatabaseProbe) -> Any:
    """Measure UPDATE latency, including time queued inside the connector."""
    original = connector.run_query_async

    async def measured_query(
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Any = (),
        timeout: Any = None,
    ) -> ExecResult:
        is_update = isinstance(query, sqlalchemy.sql.dml.Update)
        if not is_update:
            if timeout is None:
                return await original(query, parameters)
            return await original(query, parameters, timeout)

        started = time.perf_counter()
        probe.active_updates += 1
        probe.max_active_updates = max(probe.max_active_updates, probe.active_updates)
        try:
            if timeout is None:
                return await original(query, parameters)
            return await original(query, parameters, timeout)
        finally:
            probe.active_updates -= 1
            probe.update_seconds.append(time.perf_counter() - started)

    setattr(connector, "run_query_async", measured_query)
    return original


def diagnose(
    *,
    tool_concurrency: int,
    runtime_config: AgentRuntimeConfig,
    llm_probe: LLMProbe,
    db_probe: DatabaseProbe,
) -> str:
    """Identify the first visibly saturated stage from the collected metrics."""
    llm_cap = runtime_config.max_llm_concurrency
    provider_peak = llm_probe.max_active_provider_requests
    concurrency_p95 = percentile(llm_probe.concurrency_wait_seconds, 0.95)
    rpm_p95 = percentile(llm_probe.rpm_wait_seconds, 0.95)
    provider_p50 = percentile(llm_probe.provider_seconds, 0.50)
    update_p95 = percentile(db_probe.update_seconds, 0.95)

    if rpm_p95 > max(0.05, provider_p50 * 0.25):
        return "The process-wide LLM requests-per-minute limiter is the clearest bottleneck."
    if llm_cap is not None and provider_peak >= llm_cap and concurrency_p95 > 0.05:
        return "The process-wide LLM concurrency cap is the clearest bottleneck."
    if provider_peak >= tool_concurrency and (llm_cap is None or tool_concurrency < llm_cap):
        return "The run_subagent tool concurrency cap is the clearest bottleneck."
    if update_p95 > provider_p50 and db_probe.max_active_updates > 1:
        return "Serialized DuckDB write-back is the clearest bottleneck."
    return "No local cap clearly dominates; provider latency or provider-side throttling is most likely."


async def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    """Create the synthetic table, execute the tool, and return measurements."""
    runtime_config = AgentRuntimeConfig()
    updates: dict[str, int | None] = {}
    if args.llm_concurrency is not None:
        updates["max_llm_concurrency"] = args.llm_concurrency
    if args.llm_rpm is not None:
        updates["max_llm_requests_per_minute"] = args.llm_rpm
    if updates:
        runtime_config = runtime_config.model_copy(update=updates)
    initialize_agent_runtime(runtime_config)

    llm_probe = LLMProbe()
    original_llm_request = install_llm_probe(llm_probe)
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if args.database is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="tabulaflow-subagent-benchmark-")
        database = Path(temp_dir.name) / "workspace.duckdb"
    else:
        database = args.database.expanduser().resolve()
        database.parent.mkdir(parents=True, exist_ok=True)

    connector = await SQLConnector.from_url_async(
        global_id="run-subagent-benchmark",
        url=f"duckdb:///{database}",
        display_name="benchmark",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    db_probe = DatabaseProbe()
    original_query = install_database_probe(connector, db_probe)
    completion_times: list[float] = []
    started = 0.0

    try:
        await original_query("DROP TABLE IF EXISTS subagent_benchmark")
        await original_query(
            "CREATE TABLE subagent_benchmark AS "
            f"SELECT i::INTEGER AS id, printf('item-%04d', i) AS payload, "
            "NULL::VARCHAR AS label FROM range(1, "
            f"{args.rows + 1}) AS rows(i)"
        )
        await connector.refresh_schema_async()

        tool = RunSubagentForEachRowTool(
            connector,
            subagent_llm=MODEL,
            model_settings=make_model_settings(model=MODEL, reasoning=args.reasoning),
            max_concurrency=args.tool_concurrency,
            store_metadata=False,
        )

        def on_progress(update: Any) -> None:
            if update.completed == 0:
                return
            now = time.perf_counter()
            completion_times.append(now)
            if update.completed % args.progress_every == 0 or update.completed == update.total:
                elapsed = now - started
                print(
                    f"{update.completed:>4}/{update.total} rows  "
                    f"elapsed={elapsed:>7.1f}s  throughput={update.completed / elapsed:>6.2f} rows/s",
                    flush=True,
                )

        tool.on_progress = on_progress
        started = time.perf_counter()
        summary = await tool.execute(
            None,
            "subagent_benchmark",
            task_query="SELECT id, payload FROM subagent_benchmark ORDER BY id",
            task_instruction=("Return the payload exactly as the label. Payload: {{ payload }}"),
            key_columns=["id"],
            output_columns=["label"],
        )
        elapsed = time.perf_counter() - started
        result = await original_query(
            "SELECT count(*) AS total, count(label) AS completed, "
            "count(*) FILTER (WHERE label != payload) AS wrong "
            "FROM subagent_benchmark"
        )
        if result.error is not None or result.df is None:
            raise RuntimeError(f"failed to verify benchmark output: {result.error}")
        verification = result.df.iloc[0].to_dict()

        report: dict[str, Any] = {
            "model": MODEL,
            "reasoning": args.reasoning,
            "rows": args.rows,
            "elapsed_seconds": elapsed,
            "rows_per_second": args.rows / elapsed,
            "tool_concurrency": args.tool_concurrency,
            "llm_concurrency": runtime_config.max_llm_concurrency,
            "llm_requests_per_minute": runtime_config.max_llm_requests_per_minute,
            "summary": summary,
            "verification": verification,
            "llm": {
                "request_count": llm_probe.request_count,
                "max_waiting_for_concurrency": llm_probe.max_waiting_for_concurrency,
                "max_waiting_for_rpm": llm_probe.max_waiting_for_rpm,
                "max_active_provider_requests": llm_probe.max_active_provider_requests,
                "concurrency_wait_seconds": latency_summary(llm_probe.concurrency_wait_seconds),
                "rpm_wait_seconds": latency_summary(llm_probe.rpm_wait_seconds),
                "provider_seconds": latency_summary(llm_probe.provider_seconds),
            },
            "database": {
                "update_count": len(db_probe.update_seconds),
                "max_updates_waiting_or_running": db_probe.max_active_updates,
                "update_seconds": latency_summary(db_probe.update_seconds),
            },
        }
        report["diagnosis"] = diagnose(
            tool_concurrency=args.tool_concurrency,
            runtime_config=runtime_config,
            llm_probe=llm_probe,
            db_probe=db_probe,
        )
        return report
    finally:
        setattr(connector, "run_query_async", original_query)
        setattr(llm_module._ThrottledModel, "request", original_llm_request)
        await connector.close_async()
        if temp_dir is not None:
            temp_dir.cleanup()


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--tool-concurrency", type=int, default=200)
    parser.add_argument(
        "--llm-concurrency",
        type=int,
        help="Override TABULAFLOW_MAX_LLM_CONCURRENCY for this process",
    )
    parser.add_argument(
        "--llm-rpm",
        type=int,
        help="Override TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE for this process",
    )
    parser.add_argument("--reasoning", choices=("minimal", "low", "medium", "high"), default="medium")
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--database", type=Path, help="Keep the benchmark DuckDB at this path")
    parser.add_argument("--json-output", type=Path, help="Write the final report as JSON")
    args = parser.parse_args()
    for name in ("rows", "tool_concurrency", "progress_every"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    for name in ("llm_concurrency", "llm_rpm"):
        value = getattr(args, name)
        if value is not None and value <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    return args


def main() -> None:
    """Run the benchmark and print its report."""
    args = parse_args()
    report = asyncio.run(benchmark(args))
    rendered = json.dumps(report, indent=2, default=str)
    print(f"\n{rendered}")
    if args.json_output is not None:
        args.json_output.expanduser().resolve().write_text(f"{rendered}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
