"""Generate the bundled sample SQLite database shipped with tabulaflow.

One database, five tables — four synthetic banner-example domains plus one raw
map dataset:

* ``bank_transactions`` — personal spending (Analysis: "Analyze and visualize my
  monthly spending"). Raw, messy merchant strings (no category column — that's
  what the categorize transform derives), realistic amounts, several accounts,
  recurring subscriptions, and refunds (negative amounts).
* ``product_reviews`` — product reviews (Transform: "Tag each review's sentiment
  and flag any mentioning a refund"). Varied, product-aware text; some mention
  returns/refunds.
* ``model_eval_results`` — model-eval results (Transform: "Label each failed
  sample's error pattern as retrieval, reasoning, or output formatting"). Each
  row is one QA sample with a pass/fail flag; the failures are crafted to look
  like retrieval / reasoning / formatting errors so the labeling has real signal.
* ``expense_documents`` — realistic synthetic receipt images and scanned invoice
  PDFs for multimodal query, transformation, and extraction examples.
* ``nyc_taxi_zones`` — raw NYC Open Data taxi zone polygons. Preserves the source
  columns from the ``8meu-9t5y`` export: ``the_geom``, ``shape_leng``,
  ``shape_area``, ``zone``, ``locationid``, and ``borough``.

Output is deterministic (seeded), so regenerating produces a byte-identical file.
The generated ``sample.sqlite`` is committed and shipped via package-data; this
script is the source of truth — run it to regenerate / audit.

    uv run scripts/app/generate_sample_database.py
"""

from __future__ import annotations

import json
import io
import random
import sqlite3
import string
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont

_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "tabulaflow" / "app" / "assets" / "samples"
_OUT = _SAMPLE_DIR / "sample.sqlite"
_NYC_TAXI_ZONES_JSON = _SAMPLE_DIR / "nyc_taxi_zones.json"
_SEED = 7
_YEAR = 2025  # fixed range keeps the file deterministic

_ALNUM = string.ascii_uppercase + string.digits


def _uid(rng: random.Random, prefix: str, n: int, seen: set[str]) -> str:
    """A unique opaque id like ``TXN8F2A7C019`` — realistic, not a 1..N sequence."""
    while True:
        token = prefix + "".join(rng.choices(_ALNUM, k=n))
        if token not in seen:
            seen.add(token)
            return token


# ---------------------------------------------------------------------------
# transactions
# ---------------------------------------------------------------------------

# (category, merchants as they appear on a statement, typical amount mean, spread,
#  relative frequency weight). Category is NOT stored — it only shapes amounts and
#  how often each merchant appears; deriving it is the job of the transform example.
_CATS = [
    (
        "Coffee",
        ["TST* BLUE BOTTLE 4412", "STARBUCKS 0291", "PHILZ COFFEE #6", "SQ *RITUAL COFFEE", "PEET'S #1183"],
        6.5,
        2.5,
        26,
    ),
    (
        "Dining",
        [
            "TST* TACO NIGHT",
            "SQ *JOE'S PIZZA",
            "DOORDASH*THAI BASIL",
            "CHIPOTLE 2244",
            "SHAKE SHACK #77",
            "UBER EATS *SUSHI",
            "TST* RAMEN HOUSE",
        ],
        31.0,
        16.0,
        22,
    ),
    (
        "Groceries",
        ["TRADER JOE'S #412", "WHOLE FOODS MKT 10293", "SAFEWAY #1567", "COSTCO WHSE #088", "INSTACART*WHOLE FOODS"],
        74.0,
        38.0,
        13,
    ),
    (
        "Transport",
        [
            "UBER *TRIP HELP.UBER",
            "LYFT *RIDE WED",
            "SHELL OIL 5723",
            "CLIPPER BAYAREA",
            "CHEVRON 0099231",
            "SFMTA PARKING",
        ],
        21.0,
        16.0,
        12,
    ),
    (
        "Shopping",
        [
            "AMZN MKTP US*2X4K9",
            "AMZN MKTP US*RT91Q",
            "TARGET 00024518",
            "BEST BUY #109",
            "UNIQLO US 0042",
            "IKEA EMERYVILLE",
        ],
        58.0,
        52.0,
        11,
    ),
    ("Entertainment", ["AMC ONLINE 6035", "SQ *THE INDEPENDENT", "STEAM PURCHASE", "EVENTBRITE*COMEDY"], 27.0, 15.0, 7),
    ("Health", ["WALGREENS #4512", "CVS/PHARMACY #08812", "ONE MEDICAL", "SQ *YOGA FLOW"], 34.0, 24.0, 6),
    ("Travel", ["UNITED 0162348815", "AIRBNB * HMQK4P", "MARRIOTT BONVOY SF", "ALASKA AIR 0272"], 290.0, 170.0, 3),
]
# Recurring subscriptions: (merchant, exact amount, day-of-month).
_SUBS = [
    ("NETFLIX.COM", 15.99, 4),
    ("Spotify USA", 11.99, 9),
    ("OPENAI *CHATGPT SUBSCR", 20.00, 1),
]
# Monthly bills (recurring, variable amount).
_BILLS = [
    ("PG&E E-PAYMENT", 95.0, 40.0, 11),
    ("AT&T *WIRELESS", 85.0, 12.0, 24),
]
_ACCOUNTS = [("Visa ••4821", 60), ("Amex ••1009", 27), ("Checking", 13)]
_MONTH_DAYS = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31}


def _money(rng: random.Random, mean: float, spread: float) -> float:
    amt = max(1.0, rng.gauss(mean, spread))
    # ~30% of charges land on a ".99/.49/.00" psychological price point.
    if rng.random() < 0.30:
        return round(amt) - rng.choice([0.01, 0.51, 0.0])
    return round(amt, 2)


def _account(rng: random.Random) -> str:
    names, weights = zip(*_ACCOUNTS)
    return cast(str, rng.choices(names, weights=weights)[0])


def _gen_transactions(rng: random.Random) -> list[tuple[object, ...]]:
    cat_weights = [c[4] for c in _CATS]
    rows: list[tuple[object, ...]] = []
    for month in range(1, 7):  # Jan–Jun
        days = _MONTH_DAYS[month]
        for merchant, amount, day in _SUBS:
            rows.append((f"{_YEAR}-{month:02d}-{min(day, days):02d}", merchant, round(amount, 2), _account(rng)))
        for merchant, mean, spread, day in _BILLS:
            rows.append((f"{_YEAR}-{month:02d}-{min(day, days):02d}", merchant, _money(rng, mean, spread), "Checking"))
        for _ in range(rng.randint(8, 13)):  # discretionary
            idx = rng.choices(range(len(_CATS)), weights=cat_weights)[0]
            _, merchants, mean, spread, _w = _CATS[idx]
            day = rng.randint(1, days)
            rows.append(
                (f"{_YEAR}-{month:02d}-{day:02d}", rng.choice(merchants), _money(rng, mean, spread), _account(rng))
            )
        for _ in range(rng.choices([0, 1], weights=[55, 45])[0]):  # refunds
            _, merchants, mean, spread, _w = rng.choice([c for c in _CATS if c[0] in ("Shopping", "Dining", "Travel")])
            day = rng.randint(1, days)
            merchant = rng.choice(merchants) + " REFUND"
            rows.append((f"{_YEAR}-{month:02d}-{day:02d}", merchant, -_money(rng, mean, spread), _account(rng)))
    rng.shuffle(rows)
    rows.sort(key=lambda row: cast(str, row[0]))
    seen: set[str] = set()
    return [(_uid(rng, "TXN", 9, seen), *r) for r in rows]


# ---------------------------------------------------------------------------
# reviews
# ---------------------------------------------------------------------------

_PRODUCTS = [
    "Wireless Earbuds Pro",
    'Standing Desk 48"',
    "Pour-Over Coffee Maker",
    "Trail Running Shoes",
    "Mechanical Keyboard",
    "Everyday Backpack",
    "Noise-Cancelling Headphones",
    "Smart Water Bottle",
    "Cast-Iron Skillet",
    "Yoga Mat",
    "Portable SSD 1TB",
    "LED Desk Lamp",
]
_POS = [
    "Absolutely love the {p} — exceeded my expectations and the build quality is excellent.",
    "Great value. The {p} arrived a day early and works flawlessly. Highly recommend.",
    "Best purchase I've made this year. The {p} is exactly as described.",
    "Five stars. Using the {p} every day and it has held up perfectly.",
    "Comfortable, well-made, and worth every penny. Very happy with the {p}.",
    "The {p} is even better in person. Setup was painless and it looks premium.",
    "Solid product. The {p} does everything I hoped and the battery lasts ages.",
]
_NEU = [
    "The {p} is fine. Does the job but nothing about it stands out.",
    "Decent for the price, though the {p} feels a little cheaper than the photos suggest.",
    "It's okay. The {p} works, but setup took longer than I expected.",
    "Average. The {p} is functional but I probably wouldn't buy it again.",
    "Mixed feelings — the {p} is fine day to day but the instructions were useless.",
]
_NEG = [
    "The {p} stopped working after two weeks. Requested a refund and still waiting.",
    "Poor quality. The {p} broke on day one — I returned it and got my money back.",
    "Not as advertised. The {p} is flimsy and I've asked for a full refund.",
    "Disappointed. The {p} arrived damaged; customer service was no help.",
    "Waste of money. The {p} died within a month and won't hold a charge.",
    "Returned it. The {p} was the wrong size and the refund process was painful.",
    "One star. The {p} looks nothing like the listing — sending it back for a refund.",
]
_REVIEWERS = [
    "A. Nguyen",
    "jdoe92",
    "M. Patel",
    "skater_kid",
    "Priya R.",
    "tomh",
    "L. Schmidt",
    "quietcoder",
    "Dana W.",
    "bgriffin",
]


def _gen_reviews(rng: random.Random) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    seen: set[str] = set()
    for _ in range(30):
        review_id = _uid(rng, "R", 10, seen)  # Amazon-style review id
        rating = rng.choices([5, 4, 3, 2, 1], weights=[32, 24, 15, 12, 17])[0]
        product = rng.choice(_PRODUCTS)
        bucket = _POS if rating >= 4 else _NEU if rating == 3 else _NEG
        text = rng.choice(bucket).format(p=product)
        month = rng.randint(1, 8)
        date = f"{_YEAR}-{month:02d}-{rng.randint(1, _MONTH_DAYS[month]):02d}"
        verified = rng.choices([1, 0], weights=[88, 12])[0]
        helpful = max(0, round(rng.gauss(6 if rating <= 2 else 3, 5)))  # angry reviews get more votes
        rows.append((review_id, product, rating, text, date, rng.choice(_REVIEWERS), verified, helpful))
    return rows


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------

# (domain, question, expected_answer, a plausible reasoning-style wrong answer)
_QA = [
    ("geography", "What is the capital of Australia?", "Canberra", "Sydney"),
    ("geography", "Which river is the longest in the world?", "Nile", "Amazon"),
    ("geography", "What is the smallest country in the world?", "Vatican City", "Monaco"),
    ("geography", "On which continent is the Sahara Desert?", "Africa", "Asia"),
    ("geography", "What is the capital of Canada?", "Ottawa", "Toronto"),
    ("science", "What is the chemical symbol for gold?", "Au", "Gd"),
    ("science", "What planet is known as the Red Planet?", "Mars", "Jupiter"),
    ("science", "What gas do plants absorb from the atmosphere?", "Carbon dioxide", "Oxygen"),
    ("science", "How many bones are in the adult human body?", "206", "201"),
    ("science", "What is the powerhouse of the cell?", "Mitochondria", "Ribosome"),
    ("science", "At what temperature does water boil at sea level (C)?", "100", "90"),
    ("history", "In what year did World War II end?", "1945", "1944"),
    ("history", "Who was the first president of the United States?", "George Washington", "Thomas Jefferson"),
    ("history", "What year did the Apollo 11 moon landing happen?", "1969", "1972"),
    ("history", "Which ancient civilization built the pyramids of Giza?", "Egyptians", "Mayans"),
    ("history", "In what year did the Berlin Wall fall?", "1989", "1991"),
    ("literature", "Who wrote 'Pride and Prejudice'?", "Jane Austen", "Charlotte Bronte"),
    ("literature", "Who wrote 'Romeo and Juliet'?", "William Shakespeare", "Christopher Marlowe"),
    ("literature", "Who painted the Mona Lisa?", "Leonardo da Vinci", "Michelangelo"),
    (
        "literature",
        "In which novel does the character Atticus Finch appear?",
        "To Kill a Mockingbird",
        "The Great Gatsby",
    ),
    ("math", "What is the square root of 144?", "12", "14"),
    ("math", "What is the smallest prime number?", "2", "1"),
    ("math", "How many sides does a hexagon have?", "6", "8"),
    ("math", "What is 15% of 200?", "30", "35"),
    ("math", "What is the value of pi to two decimal places?", "3.14", "3.12"),
    ("sports", "How many players are on a soccer team on the field?", "11", "9"),
    ("sports", "In which sport would you perform a slam dunk?", "Basketball", "Volleyball"),
    ("general", "How many continents are there?", "7", "5"),
    ("general", "What is the largest mammal?", "Blue whale", "African elephant"),
    ("general", "What is the freezing point of water in Fahrenheit?", "32", "0"),
]
# Failure styles -> how to turn the right answer into a wrong model_answer.
_RETRIEVAL = [
    "I couldn't find any information about that.",
    "I don't have enough context to answer this question.",
    "Sorry, that information isn't available in the provided documents.",
    "Unknown.",
]


def _gen_eval(rng: random.Random) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for i in range(40):
        sample_id = f"ex-{i + 1:04d}"  # eval-dataset style sample id
        domain, question, expected, reasoning_wrong = rng.choice(_QA)
        if rng.random() < 0.65:  # correct
            rows.append((sample_id, domain, question, expected, expected, 1))
            continue
        style = rng.choices(["reasoning", "formatting", "retrieval"], weights=[45, 30, 25])[0]
        if style == "reasoning":
            answer = reasoning_wrong
        elif style == "formatting":  # right content, wrong shape (fails exact match)
            answer = rng.choice(
                [f"The answer is {expected}.", f"**{expected}**", f"{expected} (approximately)", f"  {expected}\n"]
            )
        else:  # retrieval / refusal
            answer = rng.choice(_RETRIEVAL)
        rows.append((sample_id, domain, question, expected, answer, 0))
    return rows


# ---------------------------------------------------------------------------
# expense documents
# ---------------------------------------------------------------------------

_INK = "#172033"
_MUTED = "#657083"
_MINT = "#2f9e78"
_PAPER = "#fffdf8"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    *,
    size: int,
    fill: str = _INK,
    anchor: str | None = None,
    bold: bool = False,
) -> None:
    draw.text(xy, value, font=_font(size), fill=fill, anchor=anchor, stroke_width=1 if bold else 0)


def _receipt_png(
    merchant: str,
    subtitle: str,
    receipt_no: str,
    date: str,
    items: list[tuple[str, str]],
    subtotal: str,
    tax: str,
    total: str,
    card: str,
    accent: str,
) -> bytes:
    image = Image.new("RGB", (1000, 1500), "#e8edf1")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((94, 66, 922, 1450), radius=22, fill="#c8cfd5")
    draw.rounded_rectangle((78, 50, 906, 1434), radius=22, fill=_PAPER)
    draw.rounded_rectangle((126, 100, 858, 112), radius=6, fill=accent)

    _text(draw, (492, 174), merchant, size=48, anchor="mm", bold=True)
    _text(draw, (492, 228), subtitle, size=23, fill=_MUTED, anchor="mm")
    _text(draw, (492, 260), "San Francisco, CA 94107", size=21, fill=_MUTED, anchor="mm")
    draw.line((126, 315, 858, 315), fill="#d8dde3", width=2)

    _text(draw, (126, 354), f"RECEIPT  {receipt_no}", size=24, bold=True)
    _text(draw, (858, 354), date, size=24, anchor="ra")
    _text(draw, (126, 422), "ITEM", size=20, fill=_MUTED, bold=True)
    _text(draw, (858, 422), "AMOUNT", size=20, fill=_MUTED, anchor="ra", bold=True)

    y = 476
    for name, amount in items:
        _text(draw, (126, y), name, size=25)
        _text(draw, (858, y), amount, size=25, anchor="ra")
        y += 64
    draw.line((126, y + 4, 858, y + 4), fill="#d8dde3", width=2)
    y += 60
    for label, amount in (("Subtotal", subtotal), ("Sales tax", tax)):
        _text(draw, (570, y), label, size=24, fill=_MUTED)
        _text(draw, (858, y), amount, size=24, anchor="ra")
        y += 54
    draw.rounded_rectangle((540, y - 8, 858, y + 66), radius=10, fill=accent)
    _text(draw, (566, y + 29), "TOTAL", size=28, fill="white", anchor="lm", bold=True)
    _text(draw, (832, y + 29), total, size=31, fill="white", anchor="rm", bold=True)

    y += 130
    _text(draw, (126, y), f"VISA {card}", size=23)
    _text(draw, (858, y), "APPROVED", size=21, fill=accent, anchor="ra", bold=True)
    _text(draw, (126, y + 48), "Auth code  842193", size=19, fill=_MUTED)
    draw.line((126, 1300, 858, 1300), fill="#d8dde3", width=2)
    _text(draw, (492, 1350), "Thank you — we appreciate your business.", size=22, fill=_MUTED, anchor="mm")
    _text(draw, (492, 1385), "Questions? hello@example.test", size=18, fill=_MUTED, anchor="mm")

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=False)
    return output.getvalue()


def _invoice_page(
    company: str,
    tagline: str,
    invoice_no: str,
    issued: str,
    due: str,
    client: tuple[str, str, str],
    lines: list[tuple[str, str, str, str]],
    subtotal: str,
    tax: str,
    total: str,
    accent: str,
) -> Image.Image:
    image = Image.new("RGB", (1275, 1650), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1275, 18), fill=accent)
    draw.rounded_rectangle((78, 74, 154, 150), radius=18, fill=accent)
    _text(draw, (116, 112), company[0], size=42, fill="white", anchor="mm", bold=True)
    _text(draw, (182, 91), company, size=42, bold=True)
    _text(draw, (182, 137), tagline, size=20, fill=_MUTED)
    _text(draw, (1195, 99), "INVOICE", size=46, fill=accent, anchor="ra", bold=True)
    _text(draw, (1195, 147), invoice_no, size=23, fill=_MUTED, anchor="ra")

    draw.rounded_rectangle((78, 224, 1197, 390), radius=18, fill="#f4f7f8")
    _text(draw, (112, 264), "BILL TO", size=18, fill=_MUTED, bold=True)
    _text(draw, (112, 305), client[0], size=27, bold=True)
    _text(draw, (112, 344), client[1], size=21, fill=_MUTED)
    _text(draw, (112, 374), client[2], size=21, fill=_MUTED)
    _text(draw, (820, 266), "ISSUED", size=18, fill=_MUTED, bold=True)
    _text(draw, (1160, 266), issued, size=21, anchor="ra")
    _text(draw, (820, 320), "DUE", size=18, fill=_MUTED, bold=True)
    _text(draw, (1160, 320), due, size=21, anchor="ra", bold=True)

    y = 474
    draw.rounded_rectangle((78, y, 1197, y + 58), radius=8, fill=_INK)
    for x, value, anchor in (
        (104, "DESCRIPTION", None),
        (790, "QTY", "ra"),
        (960, "RATE", "ra"),
        (1170, "AMOUNT", "ra"),
    ):
        _text(draw, (x, y + 29), value, size=18, fill="white", anchor=anchor or "lm", bold=True)
    y += 92
    for description, qty, rate, amount in lines:
        _text(draw, (104, y), description, size=22)
        _text(draw, (790, y), qty, size=22, anchor="ra")
        _text(draw, (960, y), rate, size=22, anchor="ra")
        _text(draw, (1170, y), amount, size=22, anchor="ra")
        draw.line((96, y + 42, 1178, y + 42), fill="#e2e7eb", width=2)
        y += 82

    y = max(y + 24, 960)
    for label, amount in (("Subtotal", subtotal), ("Tax", tax)):
        _text(draw, (870, y), label, size=22, fill=_MUTED)
        _text(draw, (1170, y), amount, size=22, anchor="ra")
        y += 54
    draw.rounded_rectangle((824, y - 12, 1197, y + 72), radius=12, fill=accent)
    _text(draw, (854, y + 30), "TOTAL DUE", size=24, fill="white", anchor="lm", bold=True)
    _text(draw, (1168, y + 30), total, size=29, fill="white", anchor="rm", bold=True)

    draw.line((78, 1420, 1197, 1420), fill="#dce2e6", width=2)
    _text(draw, (78, 1470), "PAYMENT DETAILS", size=18, fill=_MUTED, bold=True)
    _text(draw, (78, 1510), "ACH · Routing 021000021 · Account ending 7742", size=20)
    _text(draw, (78, 1560), "Please include the invoice number with your payment.", size=19, fill=_MUTED)
    _text(draw, (1197, 1560), "billing@example.test", size=19, fill=_MUTED, anchor="ra")
    return image


def _scanned_pdf(page: Image.Image, title: str) -> bytes:
    output = io.BytesIO()
    page.save(
        output,
        format="PDF",
        resolution=150,
        title=title,
        author="TabulaFlow Sample Data",
        creator="TabulaFlow",
        creationDate="D:20250101000000Z",
        modDate="D:20250101000000Z",
    )
    return output.getvalue()


def _gen_expense_documents() -> list[tuple[str, str, bytes]]:
    receipts = [
        (
            "doc-001",
            "harbor-and-pine-receipt.png",
            _receipt_png(
                "HARBOR & PINE",
                "Coffee Roasters · 88 Townsend Street",
                "HP-10482",
                "2025-05-14  08:42 AM",
                [("2  Oat milk latte", "$11.50"), ("1  Almond croissant", "$4.75"), ("1  House granola", "$8.25")],
                "$24.50",
                "$2.07",
                "$26.57",
                "•••• 4821",
                _MINT,
            ),
        ),
        (
            "doc-002",
            "northstar-office-supply-receipt.png",
            _receipt_png(
                "NORTHSTAR SUPPLY",
                "Office & Studio · 241 Brannan Street",
                "NS-77519",
                "2025-06-03  02:17 PM",
                [("2  Grid notebooks", "$25.00"), ("1  Archival pen set", "$18.50"), ("1  USB-C hub", "$42.00")],
                "$85.50",
                "$7.22",
                "$92.72",
                "•••• 1009",
                "#4f6fca",
            ),
        ),
        (
            "doc-003",
            "mission-bay-cab-receipt.png",
            _receipt_png(
                "MISSION BAY CAB",
                "Ride receipt · Permit A-2917",
                "MB-39014",
                "2025-06-18  07:26 PM",
                [("Metered fare", "$28.40"), ("Airport surcharge", "$5.50"), ("Driver gratuity", "$6.78")],
                "$40.68",
                "$0.00",
                "$40.68",
                "•••• 4821",
                "#d26a3f",
            ),
        ),
    ]
    invoices = [
        (
            "doc-004",
            "luma-studio-invoice.pdf",
            _scanned_pdf(
                _invoice_page(
                    "Luma Studio",
                    "Brand and digital design",
                    "LS-2025-0418",
                    "April 18, 2025",
                    "May 18, 2025",
                    ("Alder & Finch LLC", "Attn: Morgan Lee", "155 Montgomery St · San Francisco, CA"),
                    [
                        ("Product launch art direction", "12 hr", "$165.00", "$1,980.00"),
                        ("Landing page design", "1", "$2,400.00", "$2,400.00"),
                        ("Social media asset kit", "1", "$850.00", "$850.00"),
                    ],
                    "$5,230.00",
                    "$444.55",
                    "$5,674.55",
                    _MINT,
                ),
                "Luma Studio Invoice LS-2025-0418",
            ),
        ),
        (
            "doc-005",
            "cloudline-energy-statement.pdf",
            _scanned_pdf(
                _invoice_page(
                    "Cloudline Energy",
                    "Commercial renewable power",
                    "CE-883104",
                    "June 1, 2025",
                    "June 21, 2025",
                    ("Juniper Workshop", "Account 0048-1930", "600 Illinois St · San Francisco, CA"),
                    [
                        ("Renewable electricity · 1,840 kWh", "1", "$0.184/kWh", "$338.56"),
                        ("Grid delivery", "1", "$96.20", "$96.20"),
                        ("Clean-energy credit", "1", "-$24.00", "-$24.00"),
                    ],
                    "$410.76",
                    "$0.00",
                    "$410.76",
                    "#4f6fca",
                ),
                "Cloudline Energy Statement CE-883104",
            ),
        ),
    ]
    return receipts + invoices


# ---------------------------------------------------------------------------
# NYC taxi zones
# ---------------------------------------------------------------------------


def _gen_nyc_taxi_zones() -> list[tuple[object, ...]]:
    rows = json.loads(_NYC_TAXI_ZONES_JSON.read_text(encoding="utf-8"))
    rows.sort(key=lambda r: int(r["locationid"]))
    return [
        (
            json.dumps(row["the_geom"], ensure_ascii=False, separators=(",", ":")),
            float(row["shape_leng"]),
            float(row["shape_area"]),
            row["zone"],
            int(row["locationid"]),
            row["borough"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def main() -> None:
    rng = random.Random(_SEED)
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.unlink(missing_ok=True)
    conn = sqlite3.connect(_OUT)
    cur = conn.cursor()

    cur.execute(
        "CREATE TABLE bank_transactions (txn_id TEXT PRIMARY KEY, date TEXT, merchant TEXT, amount REAL, account TEXT)"
    )
    cur.executemany("INSERT INTO bank_transactions VALUES (?, ?, ?, ?, ?)", _gen_transactions(rng))

    cur.execute(
        "CREATE TABLE product_reviews (review_id TEXT PRIMARY KEY, product TEXT, rating INTEGER, review_text TEXT, "
        "review_date TEXT, reviewer TEXT, verified_purchase INTEGER, helpful_votes INTEGER)"
    )
    cur.executemany("INSERT INTO product_reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?)", _gen_reviews(rng))

    cur.execute(
        "CREATE TABLE model_eval_results (sample_id TEXT PRIMARY KEY, domain TEXT, question TEXT, expected_answer TEXT, "
        "model_answer TEXT, is_correct INTEGER)"
    )
    cur.executemany("INSERT INTO model_eval_results VALUES (?, ?, ?, ?, ?, ?)", _gen_eval(rng))

    cur.execute("CREATE TABLE expense_documents (document_id TEXT PRIMARY KEY, filename TEXT, content BLOB)")
    cur.executemany("INSERT INTO expense_documents VALUES (?, ?, ?)", _gen_expense_documents())

    cur.execute(
        "CREATE TABLE nyc_taxi_zones (the_geom TEXT, shape_leng REAL, shape_area REAL, zone TEXT, "
        "locationid INTEGER, borough TEXT)"
    )
    cur.executemany("INSERT INTO nyc_taxi_zones VALUES (?, ?, ?, ?, ?, ?)", _gen_nyc_taxi_zones())

    conn.commit()
    tables = ("bank_transactions", "product_reviews", "model_eval_results", "expense_documents", "nyc_taxi_zones")
    counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    print(f"wrote {_OUT}  ({_OUT.stat().st_size // 1024} KB)")
    print("  tables:", ", ".join(f"{t}={n}" for t, n in counts.items()))


if __name__ == "__main__":
    main()
