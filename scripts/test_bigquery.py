#!/usr/bin/env -S uv run
"""Test BigQuery connectivity using SQLAlchemy without passing credentials."""

from sqlalchemy import create_engine, text

engine = create_engine("bigquery://")
with engine.connect() as conn:
    rows = conn.execute(
        text(
            "SELECT name FROM `bigquery-public-data.usa_names.usa_1910_2013` "
            "WHERE state = 'TX' LIMIT 10"
        )
    )
    for row in rows:
        print(row.name)
