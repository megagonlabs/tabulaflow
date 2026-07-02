from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


ASSET_DIR = Path(__file__).resolve().parents[1] / "tabulaflow" / "app" / "assets" / "maplibre"
SVG_SOURCE = ASSET_DIR / "tf-interstate-shield-draft.svg"
SPRITE_NAME = "tf-route-sprite"
ICONS = [
    ("us-interstate_1", "shield-2", 24, 30),
    ("us-interstate_2", "shield-2", 24, 30),
    ("us-interstate_3", "shield-3", 28, 30),
]


def _extract_defs(svg: str) -> str:
    start = svg.index("<defs>")
    end = svg.index("</defs>") + len("</defs>")
    return svg[start:end]


def _shield_svg(defs: str, symbol_id: str, width: int, height: int) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  {defs}
  <use href="#{symbol_id}" width="{width}" height="{height}"/>
</svg>
"""


def _render_svg(page, svg: str, width: int, height: int, pixel_ratio: int) -> Image.Image:
    render_width = width * pixel_ratio
    render_height = height * pixel_ratio
    page.set_viewport_size({"width": render_width, "height": render_height})
    page.set_content(
        f"""<!doctype html>
<html>
<head>
  <style>
    html, body {{
      background: transparent;
      margin: 0;
      overflow: hidden;
    }}
    svg {{
      display: block;
      height: {render_height}px;
      width: {render_width}px;
    }}
  </style>
</head>
<body>{svg}</body>
</html>""",
    )
    locator = page.locator("svg")
    with tempfile.NamedTemporaryFile(suffix=".png") as screenshot:
        locator.screenshot(path=screenshot.name, omit_background=True)
        image = Image.open(screenshot.name).convert("RGBA")
        return image.copy()


def _build_sprite(pixel_ratio: int) -> None:
    source = SVG_SOURCE.read_text(encoding="utf-8")
    defs = _extract_defs(source)
    gap = 3 * pixel_ratio

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(device_scale_factor=1)
        try:
            rendered = [
                (name, _render_svg(page, _shield_svg(defs, symbol_id, width, height), width, height, pixel_ratio))
                for name, symbol_id, width, height in ICONS
            ]
        finally:
            browser.close()

    total_width = sum(image.width for _, image in rendered) + gap * (len(rendered) - 1)
    total_height = max(image.height for _, image in rendered)
    sheet = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    metadata: dict[str, dict[str, int]] = {}

    x = 0
    for name, image in rendered:
        sheet.alpha_composite(image, (x, 0))
        metadata[name] = {
            "width": image.width,
            "height": image.height,
            "x": x,
            "y": 0,
            "pixelRatio": pixel_ratio,
        }
        x += image.width + gap

    suffix = "" if pixel_ratio == 1 else "@2x"
    sheet.save(ASSET_DIR / f"{SPRITE_NAME}{suffix}.png")
    (ASSET_DIR / f"{SPRITE_NAME}{suffix}.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    _build_sprite(1)
    _build_sprite(2)


if __name__ == "__main__":
    main()
