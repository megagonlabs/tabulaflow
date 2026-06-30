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
from tabulaflow.app.pane_types import PaneRecord, PaneSource, record_payload, turn_payload
from tabulaflow.app.render.cards import render_record_data


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


def _render_records(records: Sequence[SimpleNamespace], pane_dir: Path) -> list[PaneRecord]:
    cards: list[PaneRecord] = []
    for record in records:
        card = render_record_data(record, pane_dir)
        if card is not None:
            cards.append(card)
    return cards


def _push_turn(
    pane: pane_mod.OutputPane,
    pane_dir: Path,
    *,
    title: str,
    user: str,
    assistant: str,
    records: Sequence[SimpleNamespace] = (),
    cards: Sequence[PaneRecord] = (),
    source: PaneSource | None = None,
) -> None:
    pane.push(
        turn_payload(
            title=title,
            user=user,
            assistant=assistant,
            records=[*cards, *_render_records(records, pane_dir)],
            source=source,
        )
    )


def _long_result_response(summary: str) -> str:
    return "\n\n".join(
        [
            summary,
            (
                "I kept the written response above the artifacts because it should provide context "
                "before the user starts inspecting the cited records. The result panel below should "
                "feel attached to this explanation, but not crowded against it."
            ),
            (
                "Each record can expose multiple views. The Chart view is useful for scanning shape "
                "and trend, the Data view is useful for checking exact rows, and the Query view keeps "
                "the generated source available for audit."
            ),
            (
                "This longer preview response is meant to exercise the spacing between user bubble, "
                "assistant text, and result controls. It should remain readable as prose while leaving "
                "the first panel visible soon after the text ends."
            ),
        ]
    )


def _chart_cards(pane_dir: Path, *, limit: int | None) -> list[PaneRecord]:
    cards: list[PaneRecord] = []
    fixtures = debug_chart_fixtures()
    if limit is not None:
        fixtures = fixtures[:limit]
    for record_id, label, query, df, spec in fixtures:
        card = render_record_data(
            _record(record_id=record_id, label=label, query=query, df=df, chart_spec=spec),
            pane_dir,
        )
        if card is not None:
            cards.append(card)
    return cards


def _many_record_cards(cards: Sequence[PaneRecord]) -> list[PaneRecord]:
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
    return [
        record_payload(record_id=cards[i % len(cards)]["id"], label=label, views=cards[i % len(cards)]["views"])
        for i, label in enumerate(labels)
    ]


def _manual_table_card(pane_dir: Path) -> PaneRecord:
    df = pd.DataFrame(
        {
            "sample_id": [f"ex-{i:04d}" for i in range(1, 13)],
            "domain": ["geography", "general", "math", "science", "history", "math"] * 2,
            "question": [
                "What is the smallest country in the world?",
                "What is the freezing point of water in Fahrenheit?",
                "What is the smallest prime number?",
                "What is the chemical symbol for gold?",
                "In what year did World War II end?",
                "How many sides does a hexagon have?",
            ]
            * 2,
            "expected_answer": ["Vatican City", "32", "2", "Au", "1945", "6"] * 2,
        }
    )
    card = render_record_data(_record(record_id="manual", label="", query=None, df=df), pane_dir)
    assert card is not None
    return card


def _wide_manual_table_card(pane_dir: Path) -> PaneRecord:
    rows = 1_000
    cols = 60
    data: dict[str, list[object]] = {
        "row_id": list(range(1, rows + 1)),
        "segment": [f"segment_{i % 8}" for i in range(rows)],
        "status": [["ok", "review", "hold", "blocked"][i % 4] for i in range(rows)],
    }
    for col in range(1, cols - len(data) + 1):
        data[f"metric_{col:02d}"] = [round(((row * (col + 7)) % 100_000) / 37.0, 2) for row in range(rows)]
    df = pd.DataFrame(data)
    card = render_record_data(_record(record_id="wide_manual", label="", query=None, df=df), pane_dir)
    assert card is not None
    return card


def _push_manual_table_turn(pane: pane_mod.OutputPane, pane_dir: Path) -> None:
    pane.push(
        turn_payload(
            title="manual_table",
            source="manual",
            records=[_manual_table_card(pane_dir)],
        )
    )
    pane.push(
        turn_payload(
            title="wide_manual_table",
            source="manual",
            records=[_wide_manual_table_card(pane_dir)],
        )
    )


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


def _large_agent_table_record() -> SimpleNamespace:
    rows = 1_000
    data: dict[str, list[object]] = {
        "row_id": list(range(1, rows + 1)),
        "segment": [f"segment_{i % 8}" for i in range(rows)],
        "status": [["ok", "review", "hold", "blocked"][i % 4] for i in range(rows)],
    }
    for col in range(1, 10):
        data[f"metric_{col:02d}"] = [round(((row * (col + 5)) % 50_000) / 29.0, 2) for row in range(rows)]
    return _record(
        record_id="QDEBUG_LARGE_AGENT_TABLE",
        label="large_agent_table",
        query="-- synthetic 1,000-row agent result table",
        df=pd.DataFrame(data),
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


def _serve_fixed_port(host: str, port: int, pane_dir: Path) -> pane_mod.OutputPane:
    pane = pane_mod.OutputPane(pane_dir)
    handler = functools.partial(pane_mod._Handler, directory=str(pane_dir))  # noqa: SLF001
    server = pane_mod._PaneServer((host, port), handler, pane)  # noqa: SLF001
    pane._server = server  # noqa: SLF001
    pane._port = port  # noqa: SLF001
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return pane


def _populate_pane(
    pane: pane_mod.OutputPane,
    pane_dir: Path,
    *,
    large_rows: int,
    include_large: bool,
    include_media: bool,
    all_chart_turns: bool,
) -> None:
    chart_cards = _chart_cards(pane_dir, limit=None if all_chart_turns else 6)

    pane.push(
        turn_payload(
            title="long text-only answer",
            user="Explain the output pane experience in detail.",
            assistant="\n\n".join(
                [
                    (
                        "The output pane mirrors the agent's useful artifacts in a browser surface. "
                        "It is intentionally separate from the terminal so large tables, charts, query "
                        "text, and longer written answers can breathe without crowding the TUI."
                    ),
                    (
                        "A text-only turn should still feel complete. The user message anchors the "
                        "request, and the assistant response takes the full content width so it reads "
                        "like a document rather than a chat bubble."
                    ),
                    (
                        "When cited records are present, each result gets the same inspection model: "
                        "record selection first, then the Chart, Data, and Query views. This keeps the "
                        "mental model predictable even when one turn contains many records."
                    ),
                    (
                        "The browser pane should also handle idle and transitional states cleanly. "
                        "Before the first output arrives, it shows a quiet empty state. After output "
                        "arrives, the turn rail becomes a stable navigation surface rather than a log "
                        "that constantly reshapes the current view."
                    ),
                    (
                        "Long text needs extra scroll breathing room at the bottom. Without that padding, "
                        "the last paragraph lands against the viewport edge, which makes reading and "
                        "selection feel cramped."
                    ),
                    (
                        "This fixture is deliberately verbose so the preview has enough vertical content "
                        "to test scrolling, bottom padding, and transcript spacing without relying on a "
                        "table or chart view."
                    ),
                    (
                        "The desired behavior is simple: the final paragraph should be scrollable past "
                        "the bottom edge a bit, the sidebar should stay fixed, and the message rhythm "
                        "should remain calm even when the response is long."
                    ),
                ]
                * 3
            ),
            records=[],
        )
    )

    if chart_cards:
        _push_manual_table_turn(pane, pane_dir)
        _push_turn(
            pane,
            pane_dir,
            title="Large agent table",
            user="Show a large table as a normal agent result.",
            assistant=(
                "This is a normal agent result record with 1,000 rows, so the Data view should use "
                "the compact output-pane table frame and internal scrolling."
            ),
            records=[_large_agent_table_record()],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Single chart result",
            user="Show one chart result with its supporting data and query.",
            assistant=_long_result_response(
                "I generated one chart result. Use the Chart, Data, and Query tabs to inspect the "
                "visualization, the backing rows, and the generated SQL."
            ),
            cards=chart_cards[:1],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Compare the first four chart fixtures",
            user="Compare the first four chart fixtures and call out the useful result views.",
            assistant=_long_result_response(
                "I generated four cited result records. Use the record tabs to switch between fixtures, "
                "then the Chart, Data, and Query tabs to inspect each record."
            ),
            cards=chart_cards[:4],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Many-record wrapping test",
            user="Show a single turn with many records and varied label lengths.",
            assistant=_long_result_response(
                "This turn intentionally mixes short, medium, and long record labels to exercise "
                "wrapping and active-tab sizing without label truncation."
            ),
            cards=_many_record_cards(chart_cards),
        )

    if include_large:
        _push_turn(
            pane,
            pane_dir,
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
            pane_dir,
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
                turn_payload(
                    title=card["label"] or f"query {i}",
                    user=f"Show fixture {i}.",
                    assistant="Here is the rendered chart, source data, and query for this fixture.",
                    records=[card],
                )
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

    pane_dir = Path(tempfile.mkdtemp(prefix="tabulaflow-pane-preview-"))
    pane = _serve_fixed_port(args.host, args.port, pane_dir)
    _populate_pane(
        pane,
        pane_dir,
        large_rows=args.large_rows,
        include_large=(args.full or args.large_table) and not args.no_large_table,
        include_media=(args.full or args.media) and not args.no_media,
        all_chart_turns=args.full or args.all_chart_turns,
    )

    print(f"READY http://{args.host}:{args.port}/", flush=True)
    print(f"pane: {pane_dir}", flush=True)
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
