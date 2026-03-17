#!/usr/bin/env -S uv run
"""Test BigQuery cross-project introspection for stackoverflow_plus.

stackoverflow_plus spans two projects:
  - bigquery-public-data.stackoverflow
  - fh-bigquery.hackernews
"""

import os
from sqlalchemy import create_engine, inspect

CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
BILLING_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "vertexai-434121")


def test_current_approach():
    """(1) Current approach: URL = bigquery://primary_project/first_dataset."""
    print("=" * 60)
    print("Test 1: bigquery://bigquery-public-data/stackoverflow")
    print("=" * 60)
    engine = create_engine(
        "bigquery://bigquery-public-data/stackoverflow",
        credentials_path=CREDENTIALS,
        billing_project_id=BILLING_PROJECT,
    )
    insp = inspect(engine)

    for schema in ["stackoverflow", "hackernews"]:
        tables = insp.get_table_names(schema=schema)
        print(f"  {schema}: {len(tables)} tables — {tables[:5]}")

    engine.dispose()


def test_no_project_no_dataset():
    """(2) No project/dataset in URL: bigquery://."""
    print()
    print("=" * 60)
    print("Test 2: bigquery://")
    print("=" * 60)
    engine = create_engine(
        "bigquery://",
        credentials_path=CREDENTIALS,
        billing_project_id=BILLING_PROJECT,
    )
    insp = inspect(engine)

    for schema in ["stackoverflow", "hackernews"]:
        tables = insp.get_table_names(schema=schema)
        print(f"  {schema}: {len(tables)} tables — {tables[:5]}")

    # Also test cross-project query
    with engine.connect() as conn:
        r1 = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM `bigquery-public-data.stackoverflow.posts_questions`"
        )
        print(f"  bigquery-public-data.stackoverflow.posts_questions count: {r1.fetchone()[0]}")

        r2 = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM `fh-bigquery.hackernews.full`"
        )
        print(f"  fh-bigquery.hackernews.full count: {r2.fetchone()[0]}")

    engine.dispose()


if __name__ == "__main__":
    test_current_approach()
    test_no_project_no_dataset()
