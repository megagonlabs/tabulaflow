"""Run a local output-pane preview server with representative result fixtures.

    uv run scripts/preview_output_pane.py --port 61211
    uv run scripts/preview_output_pane.py --port 61211 --full

The script reuses the production pane server, index shape, and record renderers,
but pushes synthetic turns directly. It is intended for browser inspection while
iterating on ``tabulaflow/app/pane.py`` and the HTML renderers.
"""

from __future__ import annotations

import argparse
import functools
import math
import signal
import struct
import tempfile
import threading
import time
from base64 import b64encode
from collections.abc import Sequence
from importlib.resources import files as resource_files
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from tabulaflow.app import pane as pane_mod
from tabulaflow.app.debug import debug_chart_fixtures
from tabulaflow.app.render.cards import render_record_card


def _record(
    *,
    record_id: str,
    label: str,
    query: str | None,
    df: pd.DataFrame | None,
    chart_spec: dict[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        record_id=record_id,
        label=label,
        query=query,
        df=df,
        chart_spec=chart_spec,
        query_lexer="sql",
    )


def _render_records(records: Sequence[SimpleNamespace], dumps_dir: Path) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for record in records:
        card = render_record_card(record, dumps_dir)
        if card is not None:
            cards.append(card)
    return cards


def _push_turn(
    pane: pane_mod.OutputPane,
    dumps_dir: Path,
    *,
    title: str,
    user: str,
    assistant: str,
    records: Sequence[SimpleNamespace] = (),
    cards: Sequence[dict[str, object]] = (),
) -> None:
    pane.push(
        {
            "title": title,
            "user": user,
            "assistant": assistant,
            "records": [*cards, *_render_records(records, dumps_dir)],
        }
    )


def _chart_cards(dumps_dir: Path, *, limit: int | None) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    fixtures = debug_chart_fixtures()
    if limit is not None:
        fixtures = fixtures[:limit]
    for record_id, label, query, df, spec in fixtures:
        card = render_record_card(
            _record(record_id=record_id, label=label, query=query, df=df, chart_spec=spec),
            dumps_dir,
        )
        if card is not None:
            cards.append(card)
    return cards


def _many_record_cards(cards: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    if not cards:
        return []
    labels = [
        "q1",
        "top_regions",
        "sales_by_product",
        "channel_mix",
        "low_stock_alerts",
        "north_america_enterprise_revenue",
        "sku",
        "monthly_active_accounts",
        "very_long_record_label_that_should_no_longer_truncate",
        "cohort_retention",
        "x",
        "warehouse_inventory_reconciliation_status",
    ]
    return [{"label": label, "views": cards[i % len(cards)]["views"]} for i, label in enumerate(labels)]


def _large_table_record(num_rows: int) -> SimpleNamespace:
    df = pd.DataFrame(
        {
            "row_id": range(1, num_rows + 1),
            "region": (["north", "south", "east", "west"] * ((num_rows // 4) + 1))[:num_rows],
            "orders": [(i * 17) % 10_000 for i in range(num_rows)],
            "revenue": [round(((i * 37) % 250_000) / 3.0, 2) for i in range(num_rows)],
            "status": (["ok", "review", "hold"] * ((num_rows // 3) + 1))[:num_rows],
        }
    )
    return _record(
        record_id="QDEBUG_VERY_LARGE",
        label="very_large_table",
        query=f"-- synthetic {num_rows:,}-row table",
        df=df,
    )


def _wav_bytes(freq_hz: float, seconds: float = 0.4, rate: int = 8000) -> bytes:
    n_samples = int(seconds * rate)
    samples = bytearray()
    amp = 12_000
    for i in range(n_samples):
        samples += struct.pack("<h", int(amp * math.sin(2 * math.pi * freq_hz * i / rate)))
    data_size = len(samples)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", data_size)
    return bytes(header + samples)


def _media_table_record() -> SimpleNamespace:
    names = ["red", "green", "blue", "amber", "violet"]
    assets = resource_files("tabulaflow.app.assets.debug")
    jpeg = [assets.joinpath(f"jpeg_{i}.jpg").read_bytes() for i in range(5)]
    gif = [assets.joinpath(f"gif_{i}.gif").read_bytes() for i in range(5)]
    pdf = [assets.joinpath(f"pdf_{i}.pdf").read_bytes() for i in range(5)]
    wav = [_wav_bytes(f) for f in (262.0, 294.0, 330.0, 349.0, 392.0)]
    mp4_bytes = assets.joinpath("sample.mp4").read_bytes()
    jpeg_b64 = [b64encode(blob).decode("ascii") for blob in jpeg]
    df = pd.DataFrame(
        {
            "name": names,
            "jpeg": jpeg,
            "gif": gif,
            "pdf": pdf,
            "wav": wav,
            "mp4": [mp4_bytes for _ in names],
            "jpeg_b64": jpeg_b64,
            "jpeg_data_uri": [f"data:image/jpeg;base64,{payload}" for payload in jpeg_b64],
            "mixed": [jpeg[0], "plain text", 42, None, "another"],
        }
    )
    return _record(
        record_id="QDEBUG_MEDIA",
        label="debug_media",
        query="-- synthetic media payloads (JPEG/GIF/PDF/WAV/MP4)",
        df=df,
    )


def _serve_fixed_port(host: str, port: int, dumps_dir: Path) -> pane_mod.OutputPane:
    pane = pane_mod.OutputPane(dumps_dir)
    handler = functools.partial(pane_mod._Handler, directory=str(dumps_dir))  # noqa: SLF001
    server = pane_mod._PaneServer((host, port), handler, pane)  # noqa: SLF001
    pane._server = server  # noqa: SLF001
    pane._port = port  # noqa: SLF001
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return pane


def _populate_pane(
    pane: pane_mod.OutputPane,
    dumps_dir: Path,
    *,
    large_rows: int,
    include_large: bool,
    include_media: bool,
    all_chart_turns: bool,
) -> None:
    chart_cards = _chart_cards(dumps_dir, limit=None if all_chart_turns else 6)

    pane.push(
        {
            "title": "text-only answer",
            "user": "Explain what this workspace is for.",
            "assistant": (
                "tabulaflow is a minimalist text-to-query toolkit for NL2SQL research. "
                "It supports interactive exploration and benchmark workflows without "
                "requiring every answer to produce a table."
            ),
            "records": [],
        }
    )

    if chart_cards:
        _push_turn(
            pane,
            dumps_dir,
            title="Compare the first four chart fixtures",
            user="Compare the first four chart fixtures and call out the useful result views.",
            assistant=(
                "I generated four cited result records. Use the record tabs to switch between fixtures, "
                "then the Chart, Data, and Query tabs to inspect each record."
            ),
            cards=chart_cards[:4],
        )
        _push_turn(
            pane,
            dumps_dir,
            title="Many-record wrapping test",
            user="Show a single turn with many records and varied label lengths.",
            assistant=(
                "This turn intentionally mixes short, medium, and long record labels to exercise "
                "wrapping and active-tab sizing without label truncation."
            ),
            cards=_many_record_cards(chart_cards),
        )

    if include_large:
        _push_turn(
            pane,
            dumps_dir,
            title="Very large table",
            user="Render a very large table so I can inspect truncation and internal scrolling.",
            assistant=(
                f"This table has {large_rows:,} source rows. The browser table renderer may cap "
                "the rendered rows and report that in the Data view caption."
            ),
            records=[_large_table_record(large_rows)],
        )

    if include_media:
        _push_turn(
            pane,
            dumps_dir,
            title="Multimedia table",
            user="Render the debug multimedia table.",
            assistant=(
                "This table exercises image, GIF, PDF, audio, video, base64 image, data URI, and mixed-content cells."
            ),
            records=[_media_table_record()],
        )

    if all_chart_turns:
        for i, card in enumerate(chart_cards[4:], start=5):
            pane.push(
                {
                    "title": card.get("label") or f"query {i}",
                    "user": f"Show fixture {i}.",
                    "assistant": "Here is the rendered chart, source data, and query for this fixture.",
                    "records": [card],
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61211)
    parser.add_argument("--large-rows", type=int, default=60_000)
    parser.add_argument("--full", action="store_true", help="Include all chart turns and expensive stress fixtures.")
    parser.add_argument("--all-chart-turns", action="store_true", help="Render every chart fixture as its own turn.")
    parser.add_argument("--large-table", action="store_true", help="Include the very large table stress fixture.")
    parser.add_argument("--media", action="store_true", help="Include the multimedia table stress fixture.")
    parser.add_argument("--no-large-table", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-media", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    dumps_dir = Path(tempfile.mkdtemp(prefix="tabulaflow-pane-preview-"))
    pane = _serve_fixed_port(args.host, args.port, dumps_dir)
    _populate_pane(
        pane,
        dumps_dir,
        large_rows=args.large_rows,
        include_large=(args.full or args.large_table) and not args.no_large_table,
        include_media=(args.full or args.media) and not args.no_media,
        all_chart_turns=args.full or args.all_chart_turns,
    )

    print(f"READY http://{args.host}:{args.port}/", flush=True)
    print(f"dumps: {dumps_dir}", flush=True)
    print("Press Ctrl-C to stop.", flush=True)

    stop = threading.Event()

    def _stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    try:
        while not stop.is_set():
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        pane.stop()


if __name__ == "__main__":
    main()
