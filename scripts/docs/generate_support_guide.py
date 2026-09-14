"""Generate the bundled support PDF with an illustrative settings screenshot.

Run with ``uv run python scripts/docs/generate_support_guide.py``.
Requires Playwright's Chromium browser (``uv run playwright install chromium``).
"""

import asyncio
import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright


SETTINGS = """
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Example Dock settings</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font: 18px Arial, sans-serif; color: #20252b; background: white; }
  .settings { width: 720px; padding: 32px; border: 1px solid #ced4da; }
  header { padding-bottom: 24px; border-bottom: 1px solid #ced4da; font-weight: bold; }
  nav { margin: 24px 0; color: #52616c; }
  h1 { font-size: 26px; margin: 0 0 24px; }
  .row { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
  .label { font-weight: bold; }
  .hint { color: #52616c; margin: 10px 0 0; }
  .toggle { width: 54px; height: 30px; border-radius: 15px; background: #858b91; padding: 4px; }
  .toggle::before { content: ""; display: block; width: 22px; height: 22px; border-radius: 50%; background: white; }
  .state { display: flex; align-items: center; gap: 12px; }
  footer { margin-top: 28px; padding-top: 20px; border-top: 1px solid #ced4da; color: #52616c; }
</style>
<section class="settings">
  <header>Example Dock</header>
  <nav>Dock settings / Power</nav>
  <h1>Power</h1>
  <div class="row">
    <div><div class="label">Laptop charging</div><p class="hint">Supply power through the host USB-C port.</p></div>
    <div class="state"><span>Off</span><div class="toggle" role="switch" aria-checked="false" aria-label="Laptop charging"></div></div>
  </div>
  <footer>Dock connected &middot; External power connected</footer>
</section>
</html>
"""


async def main() -> None:
    destination = Path(__file__).resolve().parents[2] / "docs/examples/support/dock-guide.pdf"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page(viewport={"width": 800, "height": 600}, device_scale_factor=2)
            await page.set_content(SETTINGS)
            panel = await page.locator(".settings").bounding_box()
            control = await page.locator(".state").bounding_box()
            assert panel is not None and control is not None
            screenshot = await page.locator(".settings").screenshot()
            bitmap = Image.open(BytesIO(screenshot)).convert("RGB")
            scale = bitmap.width / panel["width"]
            left = (control["x"] - panel["x"] - 10) * scale
            top = (control["y"] - panel["y"] - 10) * scale
            right = left + (control["width"] + 20) * scale
            bottom = top + (control["height"] + 20) * scale

            # Bake the callouts into the screenshot, not a separate PDF overlay.
            draw = ImageDraw.Draw(bitmap)
            red = "#d32f2f"
            draw.rectangle((left, top, right, bottom), outline=red, width=round(3 * scale))
            tip_x, tip_y = (left + right) / 2, top - 5 * scale
            draw.line((tip_x - 60 * scale, tip_y - 60 * scale, tip_x, tip_y), fill=red, width=round(4 * scale))
            draw.polygon(
                [(tip_x, tip_y), (tip_x - 18 * scale, tip_y - 5 * scale), (tip_x - 5 * scale, tip_y - 18 * scale)],
                fill=red,
            )
            annotated = BytesIO()
            bitmap.save(annotated, format="PNG")
            encoded = base64.b64encode(annotated.getvalue()).decode("ascii")
            await page.set_content(f"""
                <!doctype html>
                <html lang="en">
                <meta charset="utf-8">
                <title>USB-C dock: charging help</title>
                <style>
                  body {{ font: 14px/1.6 Arial, sans-serif; color: #20252b; margin: 0; }}
                  h1 {{ font-size: 28px; }}
                  h2 {{ font-size: 18px; margin-top: 26px; }}
                  img {{ width: 100%; height: auto; }}
                  .caption, footer {{ color: #52616c; font-size: 12px; }}
                </style>
                <h1>USB-C dock: charging help</h1>
                <p>A connected dock can transfer data while laptop charging is disabled.</p>
                <h2>1. Check the power settings</h2>
                <p>Open <strong>Dock settings &gt; Power</strong>. The screenshot shows
                the laptop charging control in its disabled state. Enable the highlighted control.</p>
                <img src="data:image/png;base64,{encoded}" alt="Example Dock power settings">
                <p class="caption">Illustrative screenshot of the fictional Example Dock utility.</p>
                <h2>2. Reconnect the laptop</h2>
                <p>Disconnect and reconnect the host USB-C cable after changing the setting.</p>
                <h2>3. Contact support</h2>
                <p>If you have tried both steps and charging still fails, request a technical-support
                ticket for your delivered order. Include the order number and steps already tried.</p>
                <footer>This fictional guide is a TabulaFlow documentation fixture, not a real product manual.</footer>
                </html>
            """)
            await page.pdf(
                path=str(destination),
                format="A4",
                print_background=True,
                margin={"top": "18mm", "bottom": "18mm", "left": "18mm", "right": "18mm"},
            )
        finally:
            await browser.close()
    print(destination)


if __name__ == "__main__":
    asyncio.run(main())
