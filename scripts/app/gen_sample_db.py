"""Generate the bundled sample SQLite database shipped with tabulaflow.

One database, four tables — three synthetic banner-example domains plus one raw
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
* ``nyc_taxi_zones`` — raw NYC Open Data taxi zone polygons. Preserves the source
  columns from the ``8meu-9t5y`` export: ``the_geom``, ``shape_leng``,
  ``shape_area``, ``zone``, ``locationid``, and ``borough``.

Output is deterministic (seeded), so regenerating produces a byte-identical file.
The generated ``sample.sqlite`` is committed and shipped via package-data; this
script is the source of truth — run it to regenerate / audit.

    uv run scripts/app/gen_sample_db.py
"""

from __future__ import annotations

import json
import random
import sqlite3
import string
from pathlib import Path

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
    return rng.choices(names, weights=weights)[0]


def _gen_transactions(rng: random.Random) -> list[tuple]:
    cat_weights = [c[4] for c in _CATS]
    rows: list[tuple] = []
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
    rows.sort(key=lambda r: r[0])
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


def _gen_reviews(rng: random.Random) -> list[tuple]:
    rows: list[tuple] = []
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


def _gen_eval(rng: random.Random) -> list[tuple]:
    rows: list[tuple] = []
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
# NYC taxi zones
# ---------------------------------------------------------------------------


def _gen_nyc_taxi_zones() -> list[tuple]:
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

    cur.execute(
        "CREATE TABLE nyc_taxi_zones (the_geom TEXT, shape_leng REAL, shape_area REAL, zone TEXT, "
        "locationid INTEGER, borough TEXT)"
    )
    cur.executemany("INSERT INTO nyc_taxi_zones VALUES (?, ?, ?, ?, ?, ?)", _gen_nyc_taxi_zones())

    conn.commit()
    tables = ("bank_transactions", "product_reviews", "model_eval_results", "nyc_taxi_zones")
    counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    print(f"wrote {_OUT.relative_to(Path.cwd())}  ({_OUT.stat().st_size // 1024} KB)")
    print("  tables:", ", ".join(f"{t}={n}" for t, n in counts.items()))


if __name__ == "__main__":
    main()
