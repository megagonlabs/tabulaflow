from __future__ import annotations

import contextlib
import hashlib
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tabulaflow.app.pane.cards import build_query_data, render_map_data, render_record_data
from tabulaflow.app.pane.tables import TABLE_RENDER_MAX_ROWS
from tabulaflow.app.pane import CARD_ID_PREFIX, OutputPane, OutputPanePortError, _PANE_HTML
from tabulaflow.app.pane import PaneCard, PaneTurn, turn_payload
from tabulaflow.app.screens import send_table_to_output_pane
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.toolhub.render_map import MAP_RENDER_MAX_ROWS


@contextlib.contextmanager
def _bound_loopback_port() -> Iterator[int]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    try:
        yield int(sock.getsockname()[1])
    finally:
        sock.close()


def _unused_loopback_port() -> int:
    with _bound_loopback_port() as port:
        return port


def _origin_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))


def test_output_pane_serves_text_only_turn(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        pane.push(
            turn_payload(
                title="summarize",
                user="Summarize the latest result.",
                assistant="The result has three rows.",
                cards=[],
            )
        )

        assert pane.url is not None
        with urllib.request.urlopen(f"{pane.url}events", timeout=2) as response:
            data_line = ""
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_line = line[len("data: ") :]
                    break

        payload = json.loads(data_line)
        assert payload == {
            "id": 0,
            "title": "summarize",
            "user": "Summarize the latest result.",
            "assistant": "The result has three rows.",
            "cards": [],
        }
    finally:
        pane.stop()


def test_output_pane_replays_persisted_turns(tmp_path: Path) -> None:
    port = _unused_loopback_port()
    first = OutputPane(tmp_path, port=port)
    first.start()
    try:
        first.push(turn_payload(title="persisted", cards=[]))
        manifest = tmp_path / "turns.jsonl"
        assert manifest.exists()
    finally:
        first.stop()

    second = OutputPane(tmp_path, port=port)
    second.start()
    try:
        assert second.url is not None
        with urllib.request.urlopen(f"{second.url}events", timeout=2) as response:
            data_line = ""
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_line = line[len("data: ") :]
                    break

        assert json.loads(data_line) == {"id": 0, "title": "persisted", "cards": []}
    finally:
        second.stop()


def test_output_pane_uses_first_available_port_in_range(tmp_path: Path) -> None:
    with _bound_loopback_port() as occupied_port:
        available_port = _unused_loopback_port()
        pane = OutputPane(tmp_path, port_range=(occupied_port, available_port))
        pane.start()
        try:
            assert pane.url == f"http://127.0.0.1:{available_port}/{pane.token}/"
        finally:
            pane.stop()


def test_output_pane_explicit_port_is_strict(tmp_path: Path) -> None:
    with _bound_loopback_port() as occupied_port:
        pane = OutputPane(tmp_path, port=occupied_port)
        with pytest.raises(OutputPanePortError, match=str(occupied_port)):
            pane.start()


def test_output_pane_wildcard_bind_uses_loopback_browser_url(tmp_path: Path) -> None:
    available_port = _unused_loopback_port()
    pane = OutputPane(tmp_path, host="0.0.0.0", port=available_port)
    pane.start()
    try:
        assert pane.bind_host == "0.0.0.0"
        assert pane.url == f"http://127.0.0.1:{available_port}/{pane.token}/"
        with urllib.request.urlopen(pane.url, timeout=2) as response:
            assert response.status == 200
    finally:
        pane.stop()


def test_output_pane_localhost_bind_uses_loopback_browser_url(tmp_path: Path) -> None:
    available_port = _unused_loopback_port()
    pane = OutputPane(tmp_path, host="localhost", port=available_port)
    pane.start()
    try:
        assert pane.bind_host == "localhost"
        assert pane.url == f"http://127.0.0.1:{available_port}/{pane.token}/"
    finally:
        pane.stop()


def test_output_pane_public_url_gets_token_path(tmp_path: Path) -> None:
    available_port = _unused_loopback_port()
    pane = OutputPane(tmp_path, port=available_port, public_url=f"http://127.0.0.1:{available_port}/tf")
    pane.start()
    try:
        assert pane.url == f"http://127.0.0.1:{available_port}/tf/{pane.token}/"
        with urllib.request.urlopen(pane.url, timeout=2) as response:
            assert response.status == 200
    finally:
        pane.stop()


def test_output_pane_rejects_missing_or_wrong_token(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        origin = _origin_url(pane.url)
        for path in ("", "events", "wrong/events"):
            try:
                urllib.request.urlopen(f"{origin}{path}", timeout=2)
                rejected = False
            except urllib.error.HTTPError as exc:
                rejected = exc.code == 404
                body = exc.read().decode("utf-8")
            assert rejected
            assert "Output pane URL is incomplete." in body
            assert "Open the full URL shown in the tabulaflow terminal." in body
            assert pane.token not in body
    finally:
        pane.stop()


def test_record_card_includes_data_view_meta(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [10, 20]})
    card = render_record_data(
        SimpleNamespace(
            df=df,
            chart_spec=None,
            query=None,
            label="sales",
            record_id="r1",
            query_lexer="sql",
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["data"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["table"]["meta"] == "2 rows · 2 columns"
    assert payload["table"]["columns"][1]["role"] == "number"
    assert payload["dataset"]["rows"][0]["c1"] == 10


def test_map_and_table_row_caps_are_aligned() -> None:
    assert TABLE_RENDER_MAX_ROWS == MAP_RENDER_MAX_ROWS


def test_record_card_preserves_null_cells(tmp_path: Path) -> None:
    df = pd.DataFrame({"name": ["valid", None], "score": [0.019593312555829002, None]})
    card = render_record_data(
        SimpleNamespace(
            df=df,
            chart_spec=None,
            query=None,
            label="nulls",
            record_id="r1",
            query_lexer="sql",
        ),
        tmp_path,
    )

    assert card is not None
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["dataset"]["rows"][1] == {"c0": None, "c1": None}
    assert payload["table"]["columns"][1]["role"] == "number"


def _map_card(map_spec: dict, sources: dict[str, pd.DataFrame], tmp_path: Path, *, label: str = "map") -> dict:
    card = render_map_data(
        SimpleNamespace(map_id="MAP1", label=label, map_spec=map_spec, sources=sources),
        tmp_path,
    )
    assert card is not None
    assert card["id"].startswith(CARD_ID_PREFIX)
    return card


def test_map_card_writes_points_payload(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["San Francisco", "Oakland"],
            "latitude": [37.7749, 37.8044],
            "longitude": [-122.4194, -122.2712],
        }
    )
    card = _map_card(
        {"layers": [{"type": "points", "source": "Q1", "lat": "latitude", "lng": "longitude", "label": "city"}]},
        {"Q1": df},
        tmp_path,
        label="locations",
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["provider"] == "maplibre"
    assert payload["map"]["layers"] == [
        {"type": "points", "source": "Q1", "lat": "c1", "lng": "c2", "label": "c0"},
    ]
    assert "tileUrl" not in payload["map"]
    assert payload["datasets"]["Q1"]["rows"][0]["c1"] == 37.7749
    assert payload["datasets"]["Q1"]["rows"][0]["c2"] == -122.4194


def test_map_card_preserves_blank_coordinate_strings_for_map_renderer(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["Missing", "San Francisco"],
            "latitude": ["", "37.7749"],
            "longitude": ["", "-122.4194"],
        }
    )
    card = _map_card(
        {"layers": [{"type": "points", "source": "Q1", "lat": "latitude", "lng": "longitude", "label": "city"}]},
        {"Q1": df},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["datasets"]["Q1"]["rows"][0]["c1"] == ""
    assert payload["datasets"]["Q1"]["rows"][0]["c2"] == ""


def test_map_card_writes_layered_single_source_payload(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["San Francisco"],
            "latitude": [37.7749],
            "longitude": [-122.4194],
            "region": ["Bay Area"],
            "boundary_geojson": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-122.52, 37.70],
                                [-122.35, 37.70],
                                [-122.35, 37.84],
                                [-122.52, 37.84],
                                [-122.52, 37.70],
                            ]
                        ],
                    },
                    "properties": {"kind": "region"},
                }
            ],
        }
    )
    card = _map_card(
        {
            "layers": [
                {
                    "type": "geojson",
                    "source": "Q1",
                    "geojson": "boundary_geojson",
                    "label": "region",
                    "tooltip": ["region"],
                    "color": {"field": "region"},
                },
                {
                    "type": "points",
                    "source": "Q1",
                    "lat": "latitude",
                    "lng": "longitude",
                    "label": "city",
                    "tooltip": ["city"],
                },
            ]
        },
        {"Q1": df},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["type"] == "geojson"
    assert payload["map"]["layers"][0]["source"] == "Q1"
    assert payload["map"]["layers"][0]["geojson"] == "c4"
    assert payload["map"]["layers"][0]["label"] == "c3"
    assert payload["map"]["layers"][0]["tooltip"] == ["c3"]
    assert payload["map"]["layers"][0]["color"] == {"field": "c3"}
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "source": "Q1",
        "lat": "c1",
        "lng": "c2",
        "label": "c0",
        "tooltip": ["c0"],
    }


def test_map_card_writes_multi_source_datasets(tmp_path: Path) -> None:
    boundaries = pd.DataFrame(
        {
            "area": ["Bay Area"],
            "boundary_geojson": [{"type": "Point", "coordinates": [-122.4, 37.7]}],
        }
    )
    points = pd.DataFrame({"city": ["San Francisco"], "latitude": [37.7749], "longitude": [-122.4194]})
    card = _map_card(
        {
            "layers": [
                {"type": "geojson", "source": "Q1", "geojson": "boundary_geojson", "label": "area"},
                {"type": "points", "source": "Q2", "lat": "latitude", "lng": "longitude", "label": "city"},
            ]
        },
        {"Q1": boundaries, "Q2": points},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    # Each layer reads from its own source's compact field names.
    assert payload["map"]["layers"][0] == {"type": "geojson", "source": "Q1", "geojson": "c1", "label": "c0"}
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "source": "Q2",
        "lat": "c1",
        "lng": "c2",
        "label": "c0",
    }
    assert set(payload["datasets"]) == {"Q1", "Q2"}
    assert payload["datasets"]["Q2"]["rows"][0]["c1"] == 37.7749


def test_map_card_writes_inline_point_layer(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "route_geojson": [
                {
                    "type": "LineString",
                    "coordinates": [[-122.42, 37.77], [-122.27, 37.80]],
                }
            ],
            "route_name": ["Route"],
        }
    )
    card = _map_card(
        {
            "layers": [
                {"type": "geojson", "source": "Q1", "geojson": "route_geojson", "label": "route_name"},
                {
                    "type": "points",
                    "points": [{"lat": 37.8044, "lng": -122.2712, "label": "Destination", "kind": "destination"}],
                    "label": "label",
                    "tooltip": ["label", "kind"],
                },
            ]
        },
        {"Q1": df},
        tmp_path,
        label="route",
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["geojson"] == "c0"
    assert payload["map"]["layers"][0]["label"] == "c1"
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "points": [{"lat": 37.8044, "lng": -122.2712, "label": "Destination", "kind": "destination"}],
        "label": "label",
        "tooltip": ["label", "kind"],
    }


def test_manual_table_send_includes_data_view_meta(tmp_path: Path) -> None:
    calls: list[tuple[Path, dict[str, object]]] = []
    statuses: list[object] = []

    class FakeApp:
        _runtime_paths = SimpleNamespace(pane_dir=tmp_path)

        def view_card_in_pane(self, card: object, **kwargs: object) -> bool:
            calls.append((Path(f"{card['id']}.data.json"), kwargs))  # type: ignore[index]
            return True

    df = pd.DataFrame({"sample_id": ["ex-0001", "ex-0002"], "answer": ["A", "B"]})
    path = send_table_to_output_pane(df, "manual_table", FakeApp(), status=statuses.append)

    assert path is not None
    assert path.exists()
    payload = json.loads(path.read_text())
    assert payload["table"]["meta"] == "2 rows · 2 columns"
    assert calls == [(Path(path.name), {"title": "manual_table"})]
    assert str(statuses[-1]) == "sent to output pane"


def test_pane_labels_manual_table_turn_as_preview() -> None:
    assert "turn.source === 'manual'" in _PANE_HTML
    assert "return 'table preview';" in _PANE_HTML


def test_pane_omits_text_only_turn_meta() -> None:
    assert "'text only'" not in _PANE_HTML
    assert "metaText ? title.textContent + ' · ' + metaText : title.textContent" in _PANE_HTML


def test_pane_table_renderer_does_not_max_height_short_tables() -> None:
    renderer_path = files("tabulaflow.app.pane.assets.pane").joinpath("pane-render.js")
    renderer = renderer_path.read_text(encoding="utf-8")
    renderer_version = hashlib.sha256(renderer_path.read_bytes()).hexdigest()[:12]
    assert "maxHeight: viewportCap" not in renderer
    assert "estimatedTableHeight > viewportCap" in renderer
    assert "opts.height = viewportCap" in renderer
    assert ".turnview.manual-preview { height: calc(100vh - 82px); min-height: 460px;" in _PANE_HTML
    assert f"/assets/pane/pane-render.js?v={renderer_version}" in _PANE_HTML
    assert "fetch(card.id + '.data.json')" in _PANE_HTML
    assert "new EventSource('events')" in _PANE_HTML
    assert "__PANE_RENDER_VERSION__" not in _PANE_HTML
    assert "20260630-table-sizing" not in _PANE_HTML


def test_pane_chart_shell_matches_vega_background() -> None:
    assert ".view-shell.view-chart,\n.view-shell.view-map { background: var(--card); }" in _PANE_HTML
    assert ".tf-chart-view,\n.tf-vis-stage { background: var(--card); }" in _PANE_HTML


def test_pane_chart_theme_is_client_side() -> None:
    renderer = files("tabulaflow.app.pane.assets.pane").joinpath("pane-render.js").read_text(encoding="utf-8")
    assert "--chart-grid: #3a4352;" in _PANE_HTML
    assert "--chart-category-0: #3EB489;" in _PANE_HTML
    assert "function vegaDarkConfig()" in renderer
    assert "spec.config = deepMerge(vegaDarkConfig(), spec.config || {});" in renderer
    assert "cssVar('--chart-category-0', accent)" in renderer


def test_pane_map_view_is_maplibre_based() -> None:
    renderer = files("tabulaflow.app.pane.assets.pane").joinpath("pane-render.js").read_text(encoding="utf-8")
    maplibre_assets = files("tabulaflow.app.pane.assets.maplibre")
    style = json.loads(maplibre_assets.joinpath("shortbread-light.json").read_text(encoding="utf-8"))
    assert '<link rel="stylesheet" href="/assets/maplibre/maplibre-gl.css">' in _PANE_HTML
    assert '<script src="/assets/maplibre/maplibre-gl.js"></script>' in _PANE_HTML
    assert maplibre_assets.joinpath("maplibre-gl.js").is_file()
    assert maplibre_assets.joinpath("maplibre-gl.css").is_file()
    assert maplibre_assets.joinpath("LICENSE.txt").is_file()
    assert maplibre_assets.joinpath("shortbread-light.json").is_file()
    assert maplibre_assets.joinpath("osm-bright-sprite.json").is_file()
    assert maplibre_assets.joinpath("osm-bright-sprite.png").is_file()
    assert maplibre_assets.joinpath("osm-bright-sprite@2x.json").is_file()
    assert maplibre_assets.joinpath("osm-bright-sprite@2x.png").is_file()
    assert maplibre_assets.joinpath("osm-bright-sprite-source.txt").is_file()
    assert maplibre_assets.joinpath("tf-route-sprite.json").is_file()
    assert maplibre_assets.joinpath("tf-route-sprite.png").is_file()
    assert maplibre_assets.joinpath("tf-route-sprite@2x.json").is_file()
    assert maplibre_assets.joinpath("tf-route-sprite@2x.png").is_file()
    assert maplibre_assets.joinpath("tf-route-sprite-source.txt").is_file()
    assert maplibre_assets.joinpath("tf-airport-icon-draft.svg").is_file()
    assert maplibre_assets.joinpath("continent-labels.geojson").is_file()
    assert maplibre_assets.joinpath("ocean-labels.geojson").is_file()
    assert maplibre_assets.joinpath("airport-labels.geojson").is_file()
    assert maplibre_assets.joinpath("natural-earth-airports-source.txt").is_file()
    assert maplibre_assets.joinpath("natural-earth-admin0-boundaries.geojson").is_file()
    assert maplibre_assets.joinpath("natural-earth-admin1-boundaries.geojson").is_file()
    assert style["sources"]["osm"]["url"] == "https://vector.openstreetmap.org/shortbread_v1/tilejson.json"
    assert style["sources"]["continent-labels"] == {
        "type": "geojson",
        "data": "/assets/maplibre/continent-labels.geojson",
    }
    assert style["sources"]["ocean-labels"] == {
        "type": "geojson",
        "data": "/assets/maplibre/ocean-labels.geojson",
    }
    assert style["sources"]["airport-labels"] == {
        "type": "geojson",
        "data": "/assets/maplibre/airport-labels.geojson",
    }
    assert style["sources"]["natural-earth-admin0-boundaries"] == {
        "type": "geojson",
        "data": "/assets/maplibre/natural-earth-admin0-boundaries.geojson",
    }
    assert style["sources"]["natural-earth-admin1-boundaries"] == {
        "type": "geojson",
        "data": "/assets/maplibre/natural-earth-admin1-boundaries.geojson",
    }
    assert "Natural Earth" not in json.dumps(style["sources"])
    assert style["sources"]["osm"]["attribution"] == (
        '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>'
    )
    assert "OSM Bright" not in style["sources"]["osm"]["attribution"]
    assert style["glyphs"] == "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf"
    assert style["sprite"] == [
        {"id": "default", "url": "osm-bright-sprite"},
        {"id": "tf", "url": "tf-route-sprite"},
    ]
    assert "openmaptiles.github.io/osm-bright-gl-style/sprite" not in json.dumps(style)
    sprite = json.loads(maplibre_assets.joinpath("osm-bright-sprite.json").read_text(encoding="utf-8"))
    assert {"road_1", "road_6", "us-interstate_1", "us-interstate_3", "us-highway_1", "us-highway_3"} <= set(sprite)
    route_sprite = json.loads(maplibre_assets.joinpath("tf-route-sprite.json").read_text(encoding="utf-8"))
    assert set(route_sprite) == {"airport_11", "us-interstate_1", "us-interstate_2", "us-interstate_3"}
    assert route_sprite["airport_11"]["width"] == 20
    assert route_sprite["airport_11"]["height"] == 20
    assert route_sprite["airport_11"]["pixelRatio"] == 1
    assert route_sprite["us-interstate_1"]["width"] == 26
    assert route_sprite["us-interstate_2"]["width"] == 26
    assert route_sprite["us-interstate_3"]["width"] == 32
    assert {route_sprite[key]["height"] for key in ("us-interstate_1", "us-interstate_2", "us-interstate_3")} == {30}
    assert {entry["pixelRatio"] for entry in route_sprite.values()} == {1}
    route_sprite_2x = json.loads(maplibre_assets.joinpath("tf-route-sprite@2x.json").read_text(encoding="utf-8"))
    assert route_sprite_2x["airport_11"]["width"] == 40
    assert route_sprite_2x["airport_11"]["height"] == 40
    assert route_sprite_2x["airport_11"]["pixelRatio"] == 2
    assert route_sprite_2x["us-interstate_1"]["width"] == 52
    assert route_sprite_2x["us-interstate_2"]["width"] == 52
    assert route_sprite_2x["us-interstate_3"]["width"] == 64
    assert {route_sprite_2x[key]["height"] for key in ("us-interstate_1", "us-interstate_2", "us-interstate_3")} == {60}
    assert {entry["pixelRatio"] for entry in route_sprite_2x.values()} == {2}
    assert any(layer.get("source-layer") == "streets" for layer in style["layers"])
    assert any(layer.get("source-layer") == "place_labels" for layer in style["layers"])
    layer_by_id = {str(layer.get("id")): layer for layer in style["layers"]}
    layer_ids = [str(layer.get("id")) for layer in style["layers"]]

    def assert_match_labels_are_homogeneous(expression: object) -> None:
        if not isinstance(expression, list):
            return
        if expression and expression[0] == "match" and len(expression) >= 5:
            label_types: set[type[object]] = set()
            for label in expression[2:-2:2]:
                labels = label if isinstance(label, list) else [label]
                label_types.update(type(value) for value in labels)
            assert len(label_types) <= 1
        for item in expression:
            assert_match_labels_are_homogeneous(item)

    def assert_interpolate_array_outputs_are_literals(expression: object) -> None:
        if not isinstance(expression, list):
            return
        if expression and expression[0] == "interpolate" and len(expression) >= 6:
            for output in expression[4::2]:
                if isinstance(output, list):
                    assert output and output[0] == "literal"
        for item in expression:
            assert_interpolate_array_outputs_are_literals(item)

    def assert_layer_order(*ids: str) -> None:
        assert [layer_ids.index(layer_id) for layer_id in ids] == sorted(layer_ids.index(layer_id) for layer_id in ids)

    for layer in style["layers"]:
        assert_match_labels_are_homogeneous(layer)
        assert_interpolate_array_outputs_are_literals(layer)

    assert_layer_order(
        "background",
        "ocean",
        "landcover-glacier",
        "landuse-residential",
        "landuse-commercial",
        "landuse-industrial",
        "landuse-cemetery",
        "landuse-hospital",
        "landuse-school",
        "landuse-railway",
        "landcover-wood",
        "landcover-grass",
        "landcover-wetland",
        "landcover-rock",
        "landcover-farmland",
        "landcover-grass-park",
        "dam-polygons",
        "dam-lines",
        "waterway_tunnel",
        "waterway-other",
        "waterway-other-intermittent",
        "waterway-stream-canal",
        "waterway-stream-canal-intermittent",
        "waterway-river",
        "waterway-river-intermittent",
        "water",
        "water-intermittent",
        "landcover-ice-shelf",
        "landcover-sand",
        "building",
        "building-top",
    )
    assert_layer_order(
        "tunnel-service-track-casing",
        "tunnel-motorway-link-casing",
        "tunnel-minor-casing",
        "tunnel-link-casing",
        "tunnel-secondary-tertiary-casing",
        "tunnel-trunk-primary-casing",
        "tunnel-motorway-casing",
        "tunnel-path-steps-casing",
        "tunnel-path-steps",
        "tunnel-path",
        "tunnel-motorway-link",
        "tunnel-service-track",
        "tunnel-link",
        "tunnel-minor",
        "tunnel-secondary-tertiary",
        "tunnel-trunk-primary",
        "tunnel-motorway",
        "tunnel-railway",
        "ferry",
        "aeroway-taxiway-casing",
        "aeroway-runway-casing",
        "aeroway-area",
        "aeroway-taxiway",
        "aeroway-runway",
        "road_area_pier",
        "road_pier",
        "highway-area",
    )
    assert_layer_order(
        "highway-path-steps-casing",
        "highway-motorway-link-casing",
        "highway-link-casing",
        "highway-minor-casing",
        "highway-secondary-tertiary-casing",
        "highway-primary-casing",
        "highway-trunk-casing",
        "highway-motorway-casing",
        "highway-path",
        "highway-path-steps",
        "highway-motorway-link",
        "highway-link",
        "highway-minor",
        "highway-secondary-tertiary",
        "highway-primary",
        "highway-trunk",
        "highway-motorway",
        "railway-transit",
        "railway-transit-hatching",
        "railway-service",
        "railway-service-hatching",
        "railway",
        "railway-hatching",
        "bridges",
        "bridge-motorway-link-casing",
        "bridge-link-casing",
        "bridge-secondary-tertiary-casing",
        "bridge-trunk-primary-casing",
        "bridge-motorway-casing",
        "bridge-minor-casing",
        "bridge-path-casing",
        "bridge-path-steps",
        "bridge-path",
        "bridge-motorway-link",
        "bridge-link",
        "bridge-minor",
        "bridge-secondary-tertiary",
        "bridge-trunk-primary",
        "bridge-motorway",
        "bridge-railway",
        "bridge-railway-hatching",
        "cablecar",
        "cablecar-dash",
    )
    assert_layer_order(
        "boundary-land-level-4-fallback",
        "boundary-land-level-4",
        "boundary-land-level-2-fallback",
        "boundary-land-level-2",
        "boundary-land-disputed",
        "waterway-name",
        "water-name-lakeline",
        "water-name-ocean",
        "water-name-other",
        "road_oneway",
        "road_oneway_opposite",
        "poi-level-3",
        "poi-level-2",
        "poi-level-1",
        "poi-railway",
        "highway-name-path",
        "highway-name-minor",
        "highway-name-major",
        "highway-shield",
        "highway-shield-us-interstate",
        "highway-shield-us-highway",
        "highway-shield-long-ref",
        "ferry-labels",
        "airport-label-major",
        "place-other",
        "place-island",
        "place-village",
        "place-town",
        "place-city",
        "place-city-medium",
        "place-city-small",
        "place-city-capital",
        "place-state",
        "place-country-other",
        "place-country-3",
        "place-country-2",
        "place-country-1",
        "place-continent",
    )

    place_city_capital = layer_by_id["place-city-capital"]
    place_city = layer_by_id["place-city"]
    place_city_medium = layer_by_id["place-city-medium"]
    place_city_small = layer_by_id["place-city-small"]
    place_town = layer_by_id["place-town"]
    place_village = layer_by_id["place-village"]
    place_other = layer_by_id["place-other"]
    place_island = layer_by_id["place-island"]
    local_place_text_field = [
        "case",
        ["all", ["has", "name"], ["has", "name_en"], ["!=", ["get", "name"], ["get", "name_en"]]],
        ["format", ["get", "name"], {}, "\n", {}, ["get", "name_en"], {}],
        ["coalesce", ["get", "name"], ["get", "name_en"]],
    ]
    place_continent = layer_by_id["place-continent"]
    state_labels = layer_by_id["place-state"]
    country_global_labels = layer_by_id["place-country-1"]
    country_regional_labels = layer_by_id["place-country-2"]
    country_other_labels = layer_by_id["place-country-other"]
    country_local_labels = layer_by_id["place-country-3"]
    assert place_continent["source"] == "continent-labels"
    assert place_continent["maxzoom"] == 2
    assert place_continent["layout"]["text-transform"] == "uppercase"
    assert place_continent["paint"]["text-halo-width"] == 2
    assert layer_by_id["water-name-ocean"]["source"] == "ocean-labels"
    assert layer_by_id["water-name-ocean"]["layout"]["text-transform"] == "uppercase"
    assert layer_by_id["water-name-ocean"]["layout"]["text-letter-spacing"] == 0.2
    assert place_other["minzoom"] == 12
    assert place_other["filter"] == [
        "match",
        ["get", "kind"],
        ["suburb", "quarter", "neighbourhood", "hamlet", "locality"],
        True,
        False,
    ]
    assert place_other["layout"]["text-transform"] == "uppercase"
    assert place_other["layout"]["text-letter-spacing"] == 0.1
    assert place_other["layout"]["text-field"] == local_place_text_field
    assert place_island["minzoom"] == 10
    assert "maxzoom" not in place_island
    assert place_island["filter"] == ["==", ["get", "kind"], "island"]
    assert place_island["layout"]["text-field"] == local_place_text_field
    assert place_island["layout"]["text-font"] == ["Noto Sans Italic"]
    assert place_island["layout"]["text-size"] == ["interpolate", ["exponential", 1.2], ["zoom"], 10, 10, 14, 14]
    assert place_island["paint"]["text-color"] == "#4f5f54"
    assert place_village["minzoom"] == 11
    assert place_village["filter"] == ["==", ["get", "kind"], "village"]
    assert place_village["layout"]["text-field"] == local_place_text_field
    assert place_village["layout"]["text-size"] == [
        "interpolate",
        ["exponential", 1.2],
        ["zoom"],
        11,
        11,
        15,
        17,
    ]
    assert place_town["minzoom"] == 10
    assert place_town["filter"] == ["==", ["get", "kind"], "town"]
    assert place_town["layout"]["text-field"] == local_place_text_field
    assert place_town["layout"]["text-size"] == ["interpolate", ["exponential", 1.2], ["zoom"], 10, 12, 15, 19]
    assert place_city_capital["minzoom"] == 4
    assert place_city_capital["filter"] == [
        "all",
        ["==", ["get", "kind"], "capital"],
    ]
    assert place_city_capital["layout"]["icon-image"] == "star_11"
    assert place_city_capital["layout"]["text-anchor"] == "left"
    assert place_city_capital["layout"]["text-field"] == local_place_text_field
    assert place_city_capital["layout"]["text-font"] == ["Noto Sans Bold"]
    assert place_city["minzoom"] == 4
    assert place_city["filter"] == [
        "all",
        ["match", ["get", "kind"], ["city", "state_capital"], True, False],
        [">=", ["to-number", ["get", "population"], 0], 1000000],
        ["match", ["to-string", ["get", "capital"]], ["2", "true", "yes"], False, True],
    ]
    assert place_city["layout"]["text-field"] == local_place_text_field
    assert place_city["layout"]["text-font"] == ["Noto Sans Bold"]
    assert place_city["layout"]["text-size"] == [
        "interpolate",
        ["exponential", 1.2],
        ["zoom"],
        4,
        13,
        7,
        18,
        11,
        26,
    ]
    assert place_city_medium["minzoom"] == 6
    assert place_city_medium["filter"] == [
        "all",
        ["match", ["get", "kind"], ["city", "state_capital"], True, False],
        [">=", ["to-number", ["get", "population"], 0], 250000],
        ["<", ["to-number", ["get", "population"], 0], 1000000],
        ["match", ["to-string", ["get", "capital"]], ["2", "true", "yes"], False, True],
    ]
    assert place_city_medium["layout"]["text-field"] == local_place_text_field
    assert place_city_medium["layout"]["text-font"] == ["Noto Sans Bold"]
    assert place_city_medium["layout"]["text-size"] == [
        "interpolate",
        ["exponential", 1.2],
        ["zoom"],
        6,
        12,
        10,
        18,
        14,
        23,
    ]
    assert place_city_small["minzoom"] == 8
    assert place_city_small["filter"] == [
        "all",
        ["match", ["get", "kind"], ["city", "state_capital"], True, False],
        ["<", ["to-number", ["get", "population"], 0], 250000],
        ["match", ["to-string", ["get", "capital"]], ["2", "true", "yes"], False, True],
    ]
    assert place_city_small["layout"]["text-field"] == local_place_text_field
    assert place_city_small["layout"]["text-font"] == ["Noto Sans Regular"]
    assert place_city_small["layout"]["text-size"] == [
        "interpolate",
        ["exponential", 1.2],
        ["zoom"],
        8,
        11,
        12,
        16,
        15,
        20,
    ]
    assert layer_by_id["landcover-glacier"]["source-layer"] == "land"
    assert layer_by_id["landcover-glacier"]["filter"] == ["==", ["get", "kind"], "glacier"]
    assert layer_by_id["landcover-ice-shelf"]["filter"] == ["==", ["get", "kind"], "ice_shelf"]
    assert layer_by_id["landuse-residential"]["filter"] == [
        "match",
        ["get", "kind"],
        ["residential", "suburb", "neighbourhood"],
        True,
        False,
    ]
    assert layer_by_id["landcover-wood"]["filter"] == [
        "match",
        ["get", "kind"],
        ["forest", "wood"],
        True,
        False,
    ]
    assert layer_by_id["landcover-grass"]["filter"] == [
        "match",
        ["get", "kind"],
        [
            "grass",
            "grassland",
            "meadow",
            "park",
            "recreation_ground",
            "garden",
            "playground",
            "golf_course",
            "scrub",
            "heath",
        ],
        True,
        False,
    ]
    assert layer_by_id["landcover-grass"]["paint"]["fill-color"] == [
        "match",
        ["get", "kind"],
        ["scrub", "heath"],
        "#d9e3bf",
        "#c8ddb3",
    ]
    assert layer_by_id["landcover-wetland"]["filter"] == [
        "match",
        ["get", "kind"],
        ["marsh", "swamp", "bog", "wet_meadow"],
        True,
        False,
    ]
    assert layer_by_id["landcover-wetland"]["paint"]["fill-color"] == "#c5ddd6"
    assert layer_by_id["landcover-rock"]["filter"] == [
        "match",
        ["get", "kind"],
        ["bare_rock", "scree", "shingle"],
        True,
        False,
    ]
    assert layer_by_id["landcover-rock"]["paint"]["fill-color"] == "#d5c7b7"
    assert layer_by_id["landcover-farmland"]["filter"] == [
        "match",
        ["get", "kind"],
        ["farmland", "farmyard", "orchard"],
        True,
        False,
    ]
    assert layer_by_id["landcover-farmland"]["paint"]["fill-color"] == "#e1d6aa"
    assert layer_by_id["landcover-sand"]["paint"]["fill-color"] == "#e6d29c"
    assert layer_by_id["landcover-grass-park"]["source-layer"] == "sites"
    assert layer_by_id["landcover-grass-park"]["filter"] == [
        "match",
        ["get", "kind"],
        ["park", "garden", "playground"],
        True,
        False,
    ]
    assert layer_by_id["landuse-commercial"]["paint"]["fill-color"] == "rgba(255, 210, 210, 0.28)"
    assert layer_by_id["landuse-industrial"]["paint"]["fill-color"] == "rgba(255, 235, 170, 0.34)"
    assert layer_by_id["landuse-railway"]["paint"]["fill-color"] == "rgba(218, 210, 201, 0.48)"
    assert layer_by_id["landuse-school"]["filter"] == [
        "match",
        ["get", "kind"],
        ["school", "university", "college"],
        True,
        False,
    ]
    assert layer_by_id["landuse-hospital"]["filter"] == ["==", ["get", "kind"], "hospital"]
    assert layer_by_id["landuse-cemetery"]["filter"] == ["==", ["get", "kind"], "cemetery"]
    assert "water-offset" not in layer_by_id
    assert layer_by_id["water"]["source-layer"] == "water_polygons"
    assert layer_by_id["water"]["paint"]["fill-color"] == "#b9d7ed"
    assert layer_by_id["water-intermittent"]["filter"] == ["==", ["get", "intermittent"], True]
    assert layer_by_id["water-intermittent"]["paint"]["fill-opacity"] == 0.7
    assert "water-pattern" not in layer_by_id
    assert layer_by_id["building"]["source-layer"] == "buildings"
    assert layer_by_id["building-top"]["source-layer"] == "buildings"
    assert layer_by_id["building-top"]["paint"]["fill-translate"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        14,
        ["literal", [0, 0]],
        16,
        ["literal", [-2, -2]],
    ]
    assert state_labels["minzoom"] == 4
    assert state_labels["maxzoom"] == 10
    assert state_labels["filter"] == [
        "all",
        ["==", ["to-number", ["get", "admin_level"], 0], 4],
        [">=", ["to-number", ["get", "way_area"], 0], 50000000000],
    ]
    assert state_labels["layout"]["text-transform"] == "uppercase"
    assert state_labels["layout"]["text-letter-spacing"] == 0.1
    assert country_global_labels["minzoom"] == 0
    assert country_global_labels["maxzoom"] == 8
    assert country_global_labels["filter"] == [
        "all",
        ["==", ["to-number", ["get", "admin_level"], 0], 2],
        [">=", ["to-number", ["get", "way_area"], 0], 8000000000000],
    ]
    assert country_global_labels["layout"]["text-size"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        0,
        11,
        4,
        17,
        7,
        19,
    ]
    assert country_global_labels["paint"]["text-halo-blur"] == 1
    assert country_regional_labels["minzoom"] == 2
    assert country_regional_labels["filter"] == [
        "all",
        ["==", ["to-number", ["get", "admin_level"], 0], 2],
        [">=", ["to-number", ["get", "way_area"], 0], 1000000000000],
        ["<", ["to-number", ["get", "way_area"], 0], 8000000000000],
    ]
    assert country_other_labels["minzoom"] == 3
    assert country_other_labels["layout"]["text-font"] == ["Noto Sans Italic"]
    assert country_other_labels["filter"] == [
        "all",
        ["==", ["to-number", ["get", "admin_level"], 0], 2],
        ["<", ["to-number", ["get", "way_area"], 0], 1000000000000],
        ["has", "iso_a2"],
        ["==", ["get", "iso_a2"], ""],
    ]
    assert country_local_labels["minzoom"] == 3
    assert country_local_labels["filter"] == [
        "all",
        ["==", ["to-number", ["get", "admin_level"], 0], 2],
        ["<", ["to-number", ["get", "way_area"], 0], 1000000000000],
    ]
    assert layer_by_id["tunnel-motorway"]["filter"] == [
        "all",
        ["==", ["get", "tunnel"], True],
        ["==", ["get", "kind"], "motorway"],
        ["!=", ["get", "link"], True],
    ]
    assert layer_by_id["tunnel-link-casing"]["filter"] == [
        "all",
        ["==", ["get", "tunnel"], True],
        ["==", ["get", "link"], True],
        ["match", ["get", "kind"], ["trunk", "primary", "secondary", "tertiary"], True, False],
    ]
    assert layer_by_id["tunnel-service-track"]["filter"] == [
        "all",
        ["==", ["get", "tunnel"], True],
        ["match", ["get", "kind"], ["service", "track"], True, False],
    ]
    assert layer_by_id["tunnel-motorway-link"]["filter"] == [
        "all",
        ["==", ["get", "tunnel"], True],
        ["==", ["get", "link"], True],
        ["==", ["get", "kind"], "motorway"],
    ]
    assert layer_by_id["tunnel-path"]["filter"] == [
        "all",
        ["==", ["get", "tunnel"], True],
        ["match", ["get", "kind"], ["path", "footway", "cycleway"], True, False],
    ]
    assert layer_by_id["highway-motorway"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["!=", ["get", "link"], True],
        ["==", ["get", "kind"], "motorway"],
    ]
    assert layer_by_id["highway-link"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["==", ["get", "link"], True],
        ["match", ["get", "kind"], ["trunk", "primary", "secondary", "tertiary"], True, False],
    ]
    assert layer_by_id["highway-motorway-link"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["==", ["get", "link"], True],
        ["==", ["get", "kind"], "motorway"],
    ]
    assert layer_by_id["highway-path"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["match", ["get", "kind"], ["path", "footway", "cycleway"], True, False],
    ]
    assert layer_by_id["highway-path-steps"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["==", ["get", "kind"], "steps"],
    ]
    assert layer_by_id["waterway-other"]["source-layer"] == "water_lines"
    assert layer_by_id["waterway-other"]["minzoom"] == 9
    assert layer_by_id["waterway_tunnel"]["filter"] == [
        "all",
        ["==", ["get", "tunnel"], True],
        ["match", ["get", "kind"], ["river", "stream", "canal", "drain", "ditch"], True, False],
    ]
    assert layer_by_id["waterway-river"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "intermittent"], True],
        ["==", ["get", "kind"], "river"],
    ]
    assert layer_by_id["waterway-stream-canal"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "intermittent"], True],
        ["match", ["get", "kind"], ["stream", "canal", "drain", "ditch"], True, False],
    ]
    assert layer_by_id["waterway-other"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "intermittent"], True],
        ["match", ["get", "kind"], ["river", "stream", "canal", "drain", "ditch"], False, True],
    ]
    assert layer_by_id["waterway-river-intermittent"]["filter"][2] == ["==", ["get", "intermittent"], True]
    assert layer_by_id["waterway-stream-canal-intermittent"]["filter"][2] == ["==", ["get", "intermittent"], True]
    assert layer_by_id["waterway-other-intermittent"]["filter"][2] == ["==", ["get", "intermittent"], True]
    assert layer_by_id["dam-polygons"]["source-layer"] == "dam_polygons"
    assert layer_by_id["dam-lines"]["source-layer"] == "dam_lines"
    assert layer_by_id["road_area_pier"]["source-layer"] == "pier_polygons"
    assert layer_by_id["road_pier"]["source-layer"] == "pier_lines"
    assert layer_by_id["highway-area"]["source-layer"] == "street_polygons"
    assert layer_by_id["aeroway-area"]["source-layer"] == "street_polygons"
    assert layer_by_id["aeroway-area"]["filter"] == [
        "match",
        ["get", "kind"],
        ["runway", "taxiway"],
        True,
        False,
    ]
    assert layer_by_id["aeroway-runway-casing"]["filter"] == ["==", ["get", "kind"], "runway"]
    assert layer_by_id["aeroway-runway"]["paint"]["line-width"] == [
        "interpolate",
        ["exponential", 1.5],
        ["zoom"],
        11,
        4,
        17,
        50,
    ]
    assert layer_by_id["aeroway-taxiway-casing"]["filter"] == ["==", ["get", "kind"], "taxiway"]
    assert layer_by_id["aeroway-taxiway"]["paint"]["line-opacity"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        11,
        0,
        12,
        1,
    ]
    assert layer_by_id["bridges"]["source-layer"] == "bridges"
    assert layer_by_id["cablecar"]["source-layer"] == "aerialways"
    assert layer_by_id["cablecar-dash"]["source-layer"] == "aerialways"
    assert layer_by_id["cablecar-dash"]["paint"]["line-dasharray"] == [2, 3]
    assert layer_by_id["railway-transit"]["filter"] == [
        "all",
        ["==", ["get", "rail"], True],
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["match", ["get", "kind"], ["tram", "subway", "light_rail", "monorail"], True, False],
    ]
    assert layer_by_id["railway-service"]["filter"] == [
        "all",
        ["==", ["get", "rail"], True],
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["has", "service"],
    ]
    assert layer_by_id["railway"]["filter"] == [
        "all",
        ["==", ["get", "rail"], True],
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["!", ["has", "service"]],
        ["match", ["get", "kind"], ["tram", "subway", "light_rail", "monorail"], False, True],
    ]
    assert layer_by_id["railway-transit-hatching"]["paint"]["line-dasharray"] == [0.2, 8]
    assert layer_by_id["railway-service-hatching"]["paint"]["line-dasharray"] == [0.2, 8]
    assert layer_by_id["railway-hatching"]["paint"]["line-dasharray"] == [0.2, 8]
    assert layer_by_id["bridge-motorway"]["filter"] == [
        "all",
        ["==", ["get", "bridge"], True],
        ["==", ["get", "kind"], "motorway"],
        ["!=", ["get", "link"], True],
    ]
    assert layer_by_id["bridge-link"]["filter"] == [
        "all",
        ["==", ["get", "bridge"], True],
        ["==", ["get", "link"], True],
        ["match", ["get", "kind"], ["trunk", "primary", "secondary", "tertiary"], True, False],
    ]
    assert layer_by_id["bridge-motorway-link"]["filter"] == [
        "all",
        ["==", ["get", "bridge"], True],
        ["==", ["get", "link"], True],
        ["==", ["get", "kind"], "motorway"],
    ]
    assert layer_by_id["bridge-path"]["filter"] == [
        "all",
        ["==", ["get", "bridge"], True],
        ["match", ["get", "kind"], ["path", "footway", "cycleway"], True, False],
    ]
    assert layer_by_id["bridge-railway-hatching"]["paint"]["line-dasharray"] == [0.2, 8]
    assert layer_by_id["highway-primary"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["!=", ["get", "link"], True],
        ["==", ["get", "kind"], "primary"],
    ]
    assert layer_by_id["highway-trunk"]["filter"] == [
        "all",
        ["!=", ["get", "tunnel"], True],
        ["!=", ["get", "bridge"], True],
        ["!=", ["get", "link"], True],
        ["==", ["get", "kind"], "trunk"],
    ]
    assert layer_by_id["highway-secondary-tertiary-casing"]["paint"]["line-color"] == "#dcb36f"
    assert layer_by_id["highway-minor-casing"]["minzoom"] == 12
    assert layer_by_id["boundary-land-level-4-fallback"]["source"] == "natural-earth-admin1-boundaries"
    assert layer_by_id["boundary-land-level-4-fallback"]["minzoom"] == 2
    assert layer_by_id["boundary-land-level-4-fallback"]["maxzoom"] == 7
    assert layer_by_id["boundary-land-level-4-fallback"]["layout"] == {
        "line-join": "round",
        "visibility": "visible",
    }
    assert layer_by_id["boundary-land-level-4-fallback"]["paint"] == {
        "line-color": "#333333",
        "line-dasharray": [3, 1, 1, 1],
        "line-width": ["interpolate", ["exponential", 1.4], ["zoom"], 4, 0.35, 5, 0.8, 12, 2.4],
    }
    assert layer_by_id["boundary-land-level-4"]["minzoom"] == 7
    assert layer_by_id["boundary-land-level-4"]["filter"] == [
        "all",
        [">=", ["to-number", ["get", "admin_level"], 0], 3],
        ["<=", ["to-number", ["get", "admin_level"], 0], 8],
        ["!=", ["get", "maritime"], True],
        ["!=", ["get", "maritime"], 1],
    ]
    assert layer_by_id["boundary-land-level-4"]["layout"] == {
        "line-join": "round",
        "visibility": "visible",
    }
    assert layer_by_id["boundary-land-level-4"]["paint"]["line-color"] == "#333333"
    assert layer_by_id["boundary-land-level-4"]["paint"]["line-dasharray"] == [3, 1, 1, 1]
    assert layer_by_id["boundary-land-level-4"]["paint"]["line-width"] == [
        "interpolate",
        ["exponential", 1.4],
        ["zoom"],
        4,
        0.35,
        5,
        0.8,
        12,
        2.4,
    ]
    assert layer_by_id["boundary-land-level-2-fallback"]["source"] == "natural-earth-admin0-boundaries"
    assert layer_by_id["boundary-land-level-2-fallback"]["minzoom"] == 1
    assert layer_by_id["boundary-land-level-2-fallback"]["maxzoom"] == 2
    assert layer_by_id["boundary-land-level-2-fallback"]["layout"] == {
        "line-cap": "round",
        "line-join": "round",
        "visibility": "visible",
    }
    assert layer_by_id["boundary-land-level-2-fallback"]["paint"] == {
        "line-color": "#333333",
        "line-width": ["interpolate", ["linear"], ["zoom"], 0, 0.4, 4, 0.65, 6, 1, 12, 2.4],
    }
    assert layer_by_id["boundary-land-level-2"]["filter"] == [
        "all",
        ["==", ["to-number", ["get", "admin_level"], 0], 2],
        ["!=", ["get", "maritime"], True],
        ["!=", ["get", "maritime"], 1],
        ["!=", ["get", "disputed"], True],
        ["!=", ["get", "disputed"], 1],
    ]
    assert layer_by_id["boundary-land-level-2"]["layout"] == {
        "line-cap": "round",
        "line-join": "round",
        "visibility": "visible",
    }
    assert layer_by_id["boundary-land-level-2"]["paint"]["line-color"] == "#333333"
    assert layer_by_id["boundary-land-level-2"]["paint"]["line-width"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        0,
        0.4,
        4,
        0.65,
        6,
        1,
        12,
        2.4,
    ]
    assert layer_by_id["boundary-land-disputed"]["filter"] == [
        "all",
        ["!=", ["get", "maritime"], True],
        ["!=", ["get", "maritime"], 1],
        ["any", ["==", ["get", "disputed"], True], ["==", ["get", "disputed"], 1]],
    ]
    assert layer_by_id["boundary-land-disputed"]["layout"] == {
        "line-cap": "round",
        "line-join": "round",
        "visibility": "visible",
    }
    assert layer_by_id["boundary-land-disputed"]["paint"]["line-color"] == "#333333"
    assert layer_by_id["boundary-land-disputed"]["paint"]["line-dasharray"] == [1, 3]
    assert layer_by_id["boundary-land-disputed"]["paint"]["line-width"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        0,
        0.4,
        4,
        0.65,
        6,
        1,
        12,
        2.4,
    ]
    assert "boundary-water" not in layer_by_id
    assert layer_by_id["road_oneway"]["filter"] == [
        "all",
        ["==", ["get", "oneway"], True],
        [
            "match",
            ["get", "kind"],
            ["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "service"],
            True,
            False,
        ],
    ]
    assert layer_by_id["road_oneway"]["layout"]["text-field"] == ">"
    assert layer_by_id["road_oneway_opposite"]["layout"]["text-field"] == "<"
    assert layer_by_id["highway-shield"]["source-layer"] == "street_labels"
    assert layer_by_id["highway-shield"]["minzoom"] == 8
    explicit_us_route_prefix_filter = [
        "any",
        ["==", ["slice", ["upcase", ["get", "ref"]], 0, 2], "I-"],
        ["==", ["slice", ["upcase", ["get", "ref"]], 0, 2], "I "],
        ["==", ["slice", ["upcase", ["get", "ref"]], 0, 3], "US-"],
        ["==", ["slice", ["upcase", ["get", "ref"]], 0, 3], "US "],
    ]
    important_route_kind_filter = ["match", ["get", "kind"], ["motorway", "trunk"], True, False]
    assert layer_by_id["highway-shield"]["filter"] == [
        "all",
        ["has", "ref"],
        important_route_kind_filter,
        ["==", ["to-number", ["get", "ref_rows"], 1], 1],
        [">", ["to-number", ["get", "ref_cols"], ["length", ["get", "ref"]]], 0],
        ["<=", ["to-number", ["get", "ref_cols"], ["length", ["get", "ref"]]], 6],
        ["!", explicit_us_route_prefix_filter],
    ]
    assert layer_by_id["highway-shield"]["layout"]["symbol-spacing"] == 220
    assert layer_by_id["highway-shield"]["layout"]["icon-image"] == [
        "concat",
        "road_",
        ["to-string", ["to-number", ["get", "ref_cols"], ["length", ["get", "ref"]]]],
    ]
    assert layer_by_id["highway-shield"]["layout"]["icon-size"] == 0.95
    assert layer_by_id["highway-shield"]["layout"]["text-field"] == ["get", "ref"]
    assert layer_by_id["highway-shield"]["layout"]["text-size"] == 10
    assert layer_by_id["highway-shield"]["layout"]["text-rotation-alignment"] == "viewport"
    assert layer_by_id["highway-shield-us-interstate"]["minzoom"] == 7
    assert layer_by_id["highway-shield-us-interstate"]["filter"] == [
        "all",
        ["has", "ref"],
        important_route_kind_filter,
        ["==", ["to-number", ["get", "ref_rows"], 1], 1],
        [
            "any",
            ["==", ["slice", ["upcase", ["get", "ref"]], 0, 2], "I-"],
            ["==", ["slice", ["upcase", ["get", "ref"]], 0, 2], "I "],
        ],
        [">", ["length", ["slice", ["get", "ref"], 2]], 0],
        ["<=", ["length", ["slice", ["get", "ref"], 2]], 3],
    ]
    assert layer_by_id["highway-shield-us-interstate"]["layout"]["icon-image"] == [
        "concat",
        "tf:us-interstate_",
        ["to-string", ["length", ["slice", ["get", "ref"], 2]]],
    ]
    assert layer_by_id["highway-shield-us-interstate"]["layout"]["icon-size"] == 0.8
    assert layer_by_id["highway-shield-us-interstate"]["layout"]["text-field"] == ["slice", ["get", "ref"], 2]
    assert layer_by_id["highway-shield-us-interstate"]["layout"]["text-font"] == ["Noto Sans Bold"]
    assert layer_by_id["highway-shield-us-interstate"]["layout"]["text-size"] == 10
    assert layer_by_id["highway-shield-us-interstate"]["layout"]["text-offset"] == [0, 0.05]
    assert layer_by_id["highway-shield-us-interstate"]["paint"]["text-color"] == "#ffffff"
    assert layer_by_id["highway-shield-us-highway"]["minzoom"] == 9
    assert layer_by_id["highway-shield-us-highway"]["filter"] == [
        "all",
        ["has", "ref"],
        important_route_kind_filter,
        ["==", ["to-number", ["get", "ref_rows"], 1], 1],
        [
            "any",
            ["==", ["slice", ["upcase", ["get", "ref"]], 0, 3], "US-"],
            ["==", ["slice", ["upcase", ["get", "ref"]], 0, 3], "US "],
        ],
        [">", ["length", ["slice", ["get", "ref"], 3]], 0],
        ["<=", ["length", ["slice", ["get", "ref"], 3]], 3],
    ]
    assert layer_by_id["highway-shield-us-highway"]["layout"]["icon-image"] == [
        "concat",
        "us-highway_",
        ["to-string", ["length", ["slice", ["get", "ref"], 3]]],
    ]
    assert layer_by_id["highway-shield-us-highway"]["layout"]["icon-size"] == 1.15
    assert layer_by_id["highway-shield-us-highway"]["layout"]["text-field"] == ["slice", ["get", "ref"], 3]
    assert layer_by_id["highway-shield-us-highway"]["layout"]["text-size"] == 10
    assert layer_by_id["highway-shield-long-ref"]["filter"] == [
        "all",
        ["has", "ref"],
        important_route_kind_filter,
        [">", ["to-number", ["get", "ref_cols"], ["length", ["get", "ref"]]], 6],
        ["!", explicit_us_route_prefix_filter],
    ]
    assert layer_by_id["highway-shield-long-ref"]["layout"]["text-field"] == ["get", "ref"]
    assert "highway-shield-us-other" not in layer_by_id
    assert layer_by_id["highway-name-major"]["minzoom"] == 12.2
    assert layer_by_id["highway-name-major"]["filter"] == [
        "match",
        ["get", "kind"],
        ["trunk", "primary", "secondary", "tertiary"],
        True,
        False,
    ]
    assert layer_by_id["highway-name-major"]["layout"]["text-field"] == [
        "coalesce",
        ["get", "name_en"],
        ["get", "name"],
    ]
    assert layer_by_id["highway-name-minor"]["minzoom"] == 15
    assert layer_by_id["highway-name-minor"]["filter"] == [
        "match",
        ["get", "kind"],
        ["residential", "unclassified", "service", "track"],
        True,
        False,
    ]
    assert layer_by_id["highway-name-path"]["minzoom"] == 15.5
    assert layer_by_id["highway-name-path"]["filter"] == [
        "match",
        ["get", "kind"],
        ["path", "footway", "cycleway"],
        True,
        False,
    ]
    assert "motorway-exit-labels" not in layer_by_id
    assert layer_by_id["water-name-lakeline"]["minzoom"] == 5
    assert layer_by_id["water-name-lakeline"]["filter"] == [
        ">=",
        ["to-number", ["get", "way_area"], 0],
        50000000000,
    ]
    assert layer_by_id["water-name-other"]["minzoom"] == 10
    assert layer_by_id["water-name-other"]["filter"] == [
        "all",
        [">=", ["to-number", ["get", "way_area"], 0], 1000000],
        ["<", ["to-number", ["get", "way_area"], 0], 50000000000],
    ]
    assert layer_by_id["highway-name-major"]["layout"]["text-size"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        12.2,
        12,
        14,
        13,
        16,
        15,
    ]
    assert layer_by_id["highway-name-minor"]["layout"]["text-size"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        15,
        12,
        16,
        13,
    ]
    assert layer_by_id["water-name-lakeline"]["layout"]["text-size"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        5,
        12,
        10,
        14,
        16,
        16,
    ]
    assert layer_by_id["water-name-other"]["layout"]["text-size"] == [
        "interpolate",
        ["linear"],
        ["zoom"],
        10,
        12,
        13,
        14,
        16,
        15,
    ]
    assert layer_by_id["ferry"]["source-layer"] == "ferries"
    assert layer_by_id["ferry"]["minzoom"] == 11
    assert layer_by_id["ferry"]["paint"]["line-dasharray"] == [2, 2]
    assert layer_by_id["ferry-labels"]["source-layer"] == "ferries"
    assert layer_by_id["ferry-labels"]["layout"]["symbol-placement"] == "line"
    assert layer_by_id["waterway-name"]["source-layer"] == "water_lines_labels"
    assert layer_by_id["waterway-name"]["minzoom"] == 13
    assert layer_by_id["waterway-name"]["layout"]["text-letter-spacing"] == 0.2
    assert layer_by_id["poi-railway"]["source-layer"] == "public_transport"
    assert layer_by_id["airport-label-major"]["source"] == "airport-labels"
    assert layer_by_id["airport-label-major"]["minzoom"] == 10
    assert layer_by_id["airport-label-major"]["filter"] == ["has", "iata"]
    assert layer_by_id["airport-label-major"]["layout"]["icon-image"] == "tf:airport_11"
    assert layer_by_id["airport-label-major"]["layout"]["icon-size"] == 1
    assert layer_by_id["airport-label-major"]["layout"]["text-anchor"] == "top"
    assert layer_by_id["airport-label-major"]["layout"]["text-offset"] == [0, 0.85]
    assert layer_by_id["airport-label-major"]["layout"]["text-field"] == [
        "coalesce",
        ["get", "name_en"],
        ["get", "name"],
        ["get", "iata"],
    ]
    assert layer_by_id["airport-label-major"]["layout"]["visibility"] == "visible"
    assert layer_by_id["airport-label-major"]["paint"]["text-color"] == "#3f6fd8"
    assert layer_by_id["poi-railway"]["minzoom"] == 13
    assert layer_by_id["poi-railway"]["filter"] == ["has", "name"]
    assert layer_by_id["poi-railway"]["layout"]["text-anchor"] == "top"
    assert layer_by_id["poi-level-1"]["source-layer"] == "pois"
    assert layer_by_id["poi-level-1"]["minzoom"] == 14
    assert layer_by_id["poi-level-1"]["maxzoom"] == 15
    assert layer_by_id["poi-level-1"]["filter"] == ["has", "name"]
    assert layer_by_id["poi-level-2"]["minzoom"] == 15
    assert layer_by_id["poi-level-2"]["maxzoom"] == 16
    assert layer_by_id["poi-level-3"]["minzoom"] == 16
    assert layer_by_id["poi-level-3"]["paint"]["text-halo-blur"] == 0.5
    assert "if (kind === 'map') return TF.renderMap(node, data);" in _PANE_HTML
    assert "function afterVisible(entry)" in _PANE_HTML
    assert "function afterHidden(entry)" in _PANE_HTML
    assert "entry.handle.afterVisible" in _PANE_HTML
    assert "entry.handle.afterHidden" in _PANE_HTML
    assert "renderMap: renderMap" in renderer
    assert "new maplibregl.Map({" in renderer
    assert "style: style" in renderer
    assert "new maplibregl.AttributionControl({ compact: false })" in renderer
    assert "map.addSource(sourceId, { type: 'geojson'" in renderer
    assert "function addCircleLayer(map, id, sourceId)" in renderer
    assert "function addGeoJsonLayers(map, id, sourceId)" in renderer
    assert "new maplibregl.Marker({ element: node, anchor: 'bottom' })" in renderer
    assert "new maplibregl.Popup({" in renderer
    assert "map.fitBounds(dataBounds" in renderer
    assert "map.setCenter([centerLng, centerLat]);" in renderer
    assert "function destroyMap()" in renderer
    assert "afterHidden: destroyMap" in renderer
    assert "if (map) map.remove();" in renderer
    assert "L.map" not in renderer
    assert "L.tileLayer" not in renderer
    assert "/assets/leaflet" not in renderer
    assert "function mapLayers(mapData)" in renderer
    assert "if (value == null || typeof value === 'boolean') return null;" in renderer
    assert "if (typeof value === 'string' && value.trim() === '') return null;" in renderer
    assert "function formatNumber(value)" in renderer
    assert "function displayValue(value)" in renderer
    assert "num: function (cell)" in renderer
    assert "escapeHtml(formatNumber(v))" in renderer
    assert "function detailValueHtml(value)" in renderer
    assert "function tooltipUrlLabel(url)" in renderer
    assert "return text.slice(0, 40) + '...' + text.slice(-13);" in renderer
    assert "function tooltipLink(href)" in renderer
    assert "+ '\" title=\"' + escapeAttr(href)" in renderer
    assert "var urls = typeof value === 'string' ? asUrls(text) : null;" in renderer
    assert "detailValueHtml(value) + '</td></tr>'" in renderer
    assert "if (mapData.lat && mapData.lng)" not in renderer
    assert "mapData.center" not in renderer
    assert "mapData.zoom" not in renderer
    assert "mapData.tileUrl" not in renderer
    assert "mapData.attribution" not in renderer
    assert "mapData.maxZoom" not in renderer
    assert "buildGeoJsonFeatures(layer, rows, labels)" in renderer
    assert "function bindLayerDetails(map, layerIds, popupState)" in renderer
    assert "map.queryRenderedFeatures(event.point, { layers: layerIds })" in renderer
    assert "var detailLayerIds = [];" in renderer
    assert "popupState.hoverHtml !== html" in renderer
    assert "function geometryAnchor(geometry)" in renderer
    assert "__tfAnchorLng: lng" in renderer
    assert "__tfAnchorLat: lat" in renderer
    assert "__tfAnchorLng: anchor ? anchor[0] : null" in renderer
    assert "function mapFeatureAnchor(feature, fallback)" in renderer
    assert "popupState.hoverAnchor !== hoverAnchor" in renderer
    assert "popupState.hover.setLngLat(lngLat)" not in renderer
    assert "function scheduleHoverPopupClose(map, popupState)" in renderer
    assert "function bindHoverPopupPointer(map, popup, popupState)" in renderer
    assert "element.addEventListener('mouseenter'" in renderer
    assert "element.addEventListener('mouseleave'" in renderer
    assert "popupState.hoverOverPopup = false;\n      scheduleHoverPopupClose(map, popupState);" in renderer
    assert "setTimeout(function ()" in renderer
    assert "}, 60);" in renderer
    assert "syncHoverPopup(map, mapFeatureAnchor(feature, event.lngLat), html, popupState)" in renderer
    assert "setClickPopup(map, mapFeatureAnchor(feature, event.lngLat), html, popupState)" in renderer
    assert "if (popupState.click) {\n      clearHoverPopup(map, popupState);" in renderer
    assert "function setClickPopup(map, lngLat, html, popupState)" in renderer
    assert "if (popupState.click === popup) popupState.click = null;" in renderer
    assert "tf-map-popup-title" in renderer
    assert "field !== labelField" in renderer
    assert "detailHtml(row, tooltip, labels, label, labelField)" in renderer
    assert "detailHtml(props, layer.tooltip || layer.label, labels, label, layer.label)" in renderer
    assert "var pointRows = Array.isArray(layer.points) ? layer.points : rows;" in renderer
    assert "var latField = Array.isArray(layer.points) ? 'lat' : String(layer.lat || '');" in renderer
    assert "var radius = sizeFor(layer.size, row, pointRows, 6);" in renderer
    assert "__tfPinHitRadius: Math.max(24, 26 * pinScale)" in renderer
    assert "function addPinHitLayer(map, id, sourceId)" in renderer
    assert "'circle-radius': ['coalesce', ['get', '__tfPinHitRadius'], 26]" in renderer
    assert "'circle-opacity': 0" in renderer
    assert "'circle-translate': [0, -20]" in renderer
    assert "var pinHitId = sourceId + '-pin-hit';" in renderer
    assert "detailLayerIds.push(pinHitId);" in renderer
    assert "closeButton: !!closeButton" in renderer
    assert "className: className" in renderer
    assert "title || popup.replace" not in renderer
    assert "label == null ? popup.replace" not in renderer
    assert "function mapPinSvg(color)" in renderer
    assert "function pinColorRamp(color)" in renderer
    assert "function mixHex(a, b, amount)" in renderer
    assert "top: mixHex(base, '#ffffff', 0.46)" in renderer
    assert "outline: mixHex(base, '#000000', 0.24)" in renderer
    assert "function mapPinElement(color, scale, title)" in renderer
    assert "node.className = 'tf-map-pin';" in renderer
    assert "node.setAttribute('aria-label', title)" in renderer
    assert "node.title = title" not in renderer
    assert "data:image/svg+xml;charset=UTF-8," in renderer
    assert "--map-default: #4285f4;" in _PANE_HTML
    assert "--map-route: #1558d6;" in _PANE_HTML
    for index, color in enumerate(("#4285f4", "#ea4335", "#fbbc04", "#34a853", "#a142f4", "#fbbc54", "#46bdc6", "#7cb342")):
        assert f"--map-category-{index}: {color};" in _PANE_HTML
    assert "--map-pin-default: #ea4335;" in _PANE_HTML
    assert "--map-pin-top: #ff6f61;" in _PANE_HTML
    assert "--map-pin-bottom: #d93025;" in _PANE_HTML
    assert "--map-pin-outline: #a52714;" in _PANE_HTML
    assert "--map-pin-hole: #f8fafc;" in _PANE_HTML
    assert "--map-pin-inner: #fff4f2;" in _PANE_HTML
    assert "function cssVar(name, fallback)" in renderer
    assert "var mapDefaultColor = cssVar('--map-default', '#4285f4');" in renderer
    assert "var mapRouteColor = cssVar('--map-route'" in renderer
    assert "var mapPalette = [" in renderer
    assert "cssVar('--map-category-0', mapDefaultColor)" in renderer
    assert "var mapPinDefaultColor = cssVar('--map-pin-default', '#ea4335');" in renderer
    assert "var mapPinTop = cssVar('--map-pin-top'" in renderer
    assert "var mapPinBottom = cssVar('--map-pin-bottom'" in renderer
    assert "var mapPinOutline = cssVar('--map-pin-outline'" in renderer
    assert "var mapPinHole = cssVar('--map-pin-hole'" in renderer
    assert "var mapPinInner = cssVar('--map-pin-inner'" in renderer
    assert "var mapStyleUrl = '/assets/maplibre/shortbread-light.json';" in renderer
    assert "var mapStyleSpriteUrl = '/assets/maplibre/osm-bright-sprite';" in renderer
    assert "var mapStyleRouteSpriteUrl = '/assets/maplibre/tf-route-sprite';" in renderer
    assert "function absoluteUrl(path)" in renderer
    assert "fetch(mapStyleUrl).then(function (response)" in renderer
    assert "{ id: 'default', url: absoluteUrl(mapStyleSpriteUrl) }" in renderer
    assert "{ id: 'tf', url: absoluteUrl(mapStyleRouteSpriteUrl) }" in renderer
    assert "var mapInitToken = 0;" in renderer
    assert "if (initToken !== mapInitToken || map || !container.isConnected) return;" in renderer
    assert "var maxLegendEntries = 12;" in renderer
    assert "function buildLegendSection(layer, items, labels, swatchType, fallbackColor)" in renderer
    assert "function legendSwatchTypeForFeatures(features)" in renderer
    assert "function clearLegend(container)" in renderer
    assert "function renderLegend(container, sections)" in renderer
    assert "encoding.domain.filter(function (value) { return seen[String(value)]; })" in renderer
    assert "return encoding.domain.slice(0, maxLegendEntries + 1);" not in renderer
    assert "clearLegend(container);" in renderer
    assert "clearLegend(stageNode);" in renderer
    assert "node.className = 'tf-map-legend';" in renderer
    assert "renderLegend(stageNode, legendSections);" in renderer
    assert "pointData.features,\n            labels," in renderer
    assert "pointData.rows,\n            labels," not in renderer
    assert "pointData.markerType === 'pin' ? 'pin' : 'circle'" in renderer
    assert "legendSwatchTypeForFeatures(features)" in renderer
    assert "values.length < 2 || values.length > maxLegendEntries" in renderer
    assert "#ea4335" in renderer
    assert "#4285f4" in renderer
    assert "#1558d6" in renderer
    assert "markerType === 'pin' ? mapPinDefaultColor : mapDefaultColor" in renderer
    assert "function geometryType(feature)" in renderer
    assert "function isLineFeature(feature)" in renderer
    assert "type === 'LineString' || type === 'MultiLineString'" in renderer
    assert "__tfLineWidth: line ? 5 : 2" in renderer
    assert "#5bd0a8" not in renderer
    assert "#2f9a74" not in renderer
    assert "rgba(255,255,255,0.35)" not in renderer
    assert "L.marker" not in renderer
    assert "encoding.range" not in renderer
    assert "map.resize();" in renderer
    assert ".tf-map-stage { position: relative; height: min(560px, 68vh); min-height: 420px;" in _PANE_HTML
    assert ".tf-map-view .maplibregl-map { background: var(--card);" in _PANE_HTML
    assert ".tf-map-legend {\n    position: absolute; top: 12px; right: 12px; z-index: 5;" in _PANE_HTML
    assert "background: rgba(255, 255, 255, 0.62); color: #111827;" in _PANE_HTML
    assert ".tf-map-legend-swatch-pin::before" in _PANE_HTML
    assert ".tf-map-legend-swatch-line" in _PANE_HTML
    assert ".tf-map-legend-swatch-polygon" in _PANE_HTML
    assert ".tf-map-pin {" in _PANE_HTML
    assert "pointer-events: none; transform: translateY(1px);" in _PANE_HTML
    assert ".tf-map-view .maplibregl-popup.tf-map-detail-tooltip .maplibregl-popup-content," in _PANE_HTML
    assert (
        ".tf-map-view .maplibregl-popup.tf-map-detail-tooltip .maplibregl-popup-content { pointer-events: auto; }"
        in _PANE_HTML
    )
    assert "padding: 9px 14px 9px 12px; background: #fff; border: 0; border-radius: 12px;" in _PANE_HTML
    assert ".tf-map-view .maplibregl-popup.tf-map-detail-popup .maplibregl-popup-tip { display: none; }" in _PANE_HTML
    assert "max-width: min(420px, 72vw); color: #111827;" in _PANE_HTML
    assert "overflow-wrap: anywhere;" in _PANE_HTML
    assert "min-width: 220px; max-width: min(420px, 72vw);" in _PANE_HTML
    assert ".cell-link:focus { outline: none; }" in _PANE_HTML
    assert ".tf-map-view .maplibregl-canvas:focus { outline: none; }" in _PANE_HTML
    assert ".tf-map-view .maplibregl-popup-anchor-bottom-right .maplibregl-popup-tip" not in _PANE_HTML
    assert ".tf-map-view .maplibregl-ctrl-attrib," in _PANE_HTML
    assert ".leaflet-" not in _PANE_HTML


def test_pane_table_scrollbars_use_dark_theme() -> None:
    assert "--scrollbar-track: #1a1d23;" in _PANE_HTML
    assert "--scrollbar-thumb: #3a4049;" in _PANE_HTML
    assert "* { scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);" in _PANE_HTML
    assert ".tabulator-tableholder {\n    overscroll-behavior: none;" in _PANE_HTML
    assert "scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);" in _PANE_HTML
    assert "::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb);" in _PANE_HTML


def test_pane_short_tables_keep_bottom_inset() -> None:
    renderer = files("tabulaflow.app.pane.assets.pane").joinpath("pane-render.js").read_text(encoding="utf-8")
    assert "rows.length <= 12 ? 'tf-table-wrap pane-short' : 'tf-table-wrap'" in renderer
    assert ".tf-table-wrap.pane-short { padding-bottom: 16px; box-sizing: border-box; }" in _PANE_HTML


def test_pane_manual_tables_use_fixed_panel() -> None:
    renderer = files("tabulaflow.app.pane.assets.pane").joinpath("pane-render.js").read_text(encoding="utf-8")
    assert "container.closest && container.closest('.manual-preview')" in renderer
    assert "container.closest('.view-shell')" in renderer
    assert "panelHeight > 0 ? panelHeight" in renderer
    assert "panelHeight > 0 || rows.length > 100" in renderer
    assert "table.setHeight(height)" in renderer
    assert "requestAnimationFrame(fitFixedPanelHeight)" in renderer
    assert ".turnview.manual-preview { height: calc(100vh - 82px); min-height: 460px;" in _PANE_HTML
    assert ".manual-preview .cardpane { flex: 1 1 auto; min-height: 0;" in _PANE_HTML
    assert ".manual-preview .view-shell { flex: 1 1 auto; min-height: 360px; overflow: hidden; }" in _PANE_HTML
    assert ".manual-preview .tf-table-view,\n.manual-preview .tf-table-wrap { height: 100%;" in _PANE_HTML
    assert ".manual-preview .tf-table-wrap.pane-short { padding-bottom: 0; }" in _PANE_HTML
    assert ".manual-preview .tf-table-view .tabulator { height: 100% !important; }" in _PANE_HTML
    assert "max-height: calc(100% - 38px) !important;" in _PANE_HTML


def test_pane_tables_keep_last_row_gridline() -> None:
    assert (
        ".tabulator-row:last-child .tabulator-cell {\n    border-bottom: 1px solid rgba(58, 67, 82, 0.48);"
        in _PANE_HTML
    )
    assert ".tabulator-row:last-child .tabulator-cell.tabulator-row-header" in _PANE_HTML
def test_view_card_in_pane_marks_turn_as_manual(tmp_path: Path) -> None:
    pushed: list[PaneTurn] = []

    class FakePane:
        url = "http://127.0.0.1:61111/"

        def push(self, turn: PaneTurn) -> None:
            pushed.append(turn)

    app = TabulaflowApp(model="openai-responses:gpt-5", agent="sql_agent", reasoning_effort="medium")
    app._pane = FakePane()  # type: ignore[assignment]  # noqa: SLF001

    card: PaneCard = {"id": "rec_orders", "label": None, "views": ["data"]}
    assert app.view_card_in_pane(card, title="orders")
    assert pushed == [
        {
            "title": "orders",
            "source": "manual",
            "cards": [{"id": "rec_orders", "label": None, "views": ["data"]}],
        }
    ]


def test_query_payload_contains_language_and_dracula_highlight() -> None:
    payload = build_query_data('print("Hello, world!")', lexer="python")

    query = payload["query"]
    assert isinstance(query, dict)
    assert query["language"] == "Python"
    assert "#8BE9FD" in str(query["html"])  # Dracula builtin/token color.


def test_record_card_writes_structured_data_instead_of_html(tmp_path: Path) -> None:
    df = pd.DataFrame({"cat": ["a", "b"], "n": [3, 5]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "cat"}, "y": {"field": "n"}}}
    card = render_record_data(
        SimpleNamespace(df=df, chart_spec=spec, query=None, label="x", record_id="r1", query_lexer="sql"),
        tmp_path,
    )
    assert card is not None
    assert card["views"] == ["chart", "data"]
    payload_path = tmp_path / f"{card['id']}.data.json"
    payload = json.loads(payload_path.read_text())
    assert set(payload) == {"dataset", "table", "chart"}
    assert payload["dataset"]["rows"] == [{"c0": "a", "c1": 3}, {"c0": "b", "c1": 5}]
    assert payload["chart"]["spec"]["encoding"]["x"] == {"field": "c0", "title": "cat"}
    assert payload_path.stat().st_size < 100_000


def test_output_pane_serves_card_data_only_under_token(tmp_path: Path) -> None:
    df = pd.DataFrame({"cat": ["a"], "n": [3]})
    card = render_record_data(
        SimpleNamespace(df=df, chart_spec=None, query=None, label="x", record_id="r1", query_lexer="sql"),
        tmp_path,
    )
    assert card is not None

    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        with urllib.request.urlopen(f"{pane.url}{card['id']}.data.json", timeout=2) as resp:
            payload = json.loads(resp.read())
        assert payload["dataset"]["rows"] == [{"c0": "a", "c1": 3}]

        try:
            urllib.request.urlopen(f"{_origin_url(pane.url)}{card['id']}.data.json", timeout=2)
            rejected = False
        except urllib.error.HTTPError as exc:
            rejected = exc.code == 404
        assert rejected
    finally:
        pane.stop()


def test_pane_serves_bundled_assets_cached(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        with urllib.request.urlopen(pane.url, timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-store"
            assert resp.headers.get("Referrer-Policy") == "no-referrer"

        origin = _origin_url(pane.url)
        with urllib.request.urlopen(f"{origin}assets/vega/vega-embed.min.js", timeout=2) as resp:
            body = resp.read()
            cache = resp.headers.get("Cache-Control")
        expected = files("tabulaflow.app.pane.assets").joinpath("vega").joinpath("vega-embed.min.js").read_bytes()
        assert body == expected
        assert cache is not None and "immutable" in cache

        with urllib.request.urlopen(f"{origin}assets/maplibre/maplibre-gl.js", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") is not None and "immutable" in resp.headers.get(
                "Cache-Control", ""
            )
            assert b"MapLibre GL JS" in resp.read()

        with urllib.request.urlopen(f"{origin}assets/maplibre/shortbread-light.json", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert b"vector.openstreetmap.org/shortbread_v1/tilejson.json" in resp.read()

        maplibre_assets = files("tabulaflow.app.pane.assets").joinpath("maplibre")
        with urllib.request.urlopen(f"{origin}assets/maplibre/osm-bright-sprite.json", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert resp.headers.get("Content-Type") == "application/json; charset=utf-8"
            sprite = json.loads(resp.read())
        assert {"road_1", "us-interstate_1", "us-highway_1"} <= set(sprite)

        with urllib.request.urlopen(f"{origin}assets/maplibre/osm-bright-sprite.png", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") is not None and "immutable" in resp.headers.get(
                "Cache-Control", ""
            )
            assert resp.headers.get("Content-Type") == "image/png"
            body = resp.read()
        assert body == maplibre_assets.joinpath("osm-bright-sprite.png").read_bytes()
        assert body.startswith(b"\x89PNG\r\n\x1a\n")

        with urllib.request.urlopen(f"{origin}assets/maplibre/tf-route-sprite.json", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert resp.headers.get("Content-Type") == "application/json; charset=utf-8"
            route_sprite = json.loads(resp.read())
        assert set(route_sprite) == {"airport_11", "us-interstate_1", "us-interstate_2", "us-interstate_3"}
        assert route_sprite["airport_11"]["width"] == 20
        assert route_sprite["us-interstate_1"]["width"] == 26
        assert route_sprite["us-interstate_2"]["width"] == 26
        assert route_sprite["us-interstate_3"]["width"] == 32

        with urllib.request.urlopen(f"{origin}assets/maplibre/tf-route-sprite.png", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") is not None and "immutable" in resp.headers.get(
                "Cache-Control", ""
            )
            assert resp.headers.get("Content-Type") == "image/png"
            body = resp.read()
        assert body == maplibre_assets.joinpath("tf-route-sprite.png").read_bytes()
        assert body.startswith(b"\x89PNG\r\n\x1a\n")

        with urllib.request.urlopen(f"{origin}assets/maplibre/continent-labels.geojson", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert resp.headers.get("Content-Type") == "application/json; charset=utf-8"
            continent_labels = json.loads(resp.read())
        assert continent_labels["type"] == "FeatureCollection"
        assert {feature["properties"]["name"] for feature in continent_labels["features"]} >= {
            "Africa",
            "Asia",
            "Europe",
            "North America",
        }

        with urllib.request.urlopen(f"{origin}assets/maplibre/ocean-labels.geojson", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert resp.headers.get("Content-Type") == "application/json; charset=utf-8"
            ocean_labels = json.loads(resp.read())
        assert ocean_labels["type"] == "FeatureCollection"
        assert {feature["properties"]["name"] for feature in ocean_labels["features"]} >= {
            "Atlantic Ocean",
            "Pacific Ocean",
        }

        with urllib.request.urlopen(f"{origin}assets/maplibre/airport-labels.geojson", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert resp.headers.get("Content-Type") == "application/json; charset=utf-8"
            airport_labels = json.loads(resp.read())
        assert airport_labels["type"] == "FeatureCollection"
        assert len(airport_labels["features"]) > 800
        airport_by_iata = {feature["properties"]["iata"]: feature for feature in airport_labels["features"]}
        assert {"ATL", "LAX", "LHR", "SFO"} <= set(airport_by_iata)
        assert airport_by_iata["SFO"]["properties"]["name"] == "San Francisco Int'l"
        assert airport_by_iata["SFO"]["properties"]["scalerank"] == 2
        assert {feature["geometry"]["type"] for feature in airport_labels["features"]} == {"Point"}

        with urllib.request.urlopen(
            f"{origin}assets/maplibre/natural-earth-admin0-boundaries.geojson", timeout=2
        ) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert resp.headers.get("Content-Type") == "application/json; charset=utf-8"
            admin0_boundaries = json.loads(resp.read())
        assert admin0_boundaries["type"] == "FeatureCollection"
        assert len(admin0_boundaries["features"]) > 100
        assert {feature["geometry"]["type"] for feature in admin0_boundaries["features"]} <= {
            "LineString",
            "MultiLineString",
        }

        with urllib.request.urlopen(
            f"{origin}assets/maplibre/natural-earth-admin1-boundaries.geojson", timeout=2
        ) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert resp.headers.get("Content-Type") == "application/json; charset=utf-8"
            admin1_boundaries = json.loads(resp.read())
        assert admin1_boundaries["type"] == "FeatureCollection"
        assert len(admin1_boundaries["features"]) > 500
        assert {feature["geometry"]["type"] for feature in admin1_boundaries["features"]} <= {
            "LineString",
            "MultiLineString",
        }

        try:
            urllib.request.urlopen(f"{origin}assets/does-not-exist.js", timeout=2)
            missing_is_404 = False
        except urllib.error.HTTPError as exc:
            missing_is_404 = exc.code == 404
        assert missing_is_404

        with urllib.request.urlopen(f"{origin}assets/pane/pane-render.js", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert b"renderTable" in resp.read()
    finally:
        pane.stop()
