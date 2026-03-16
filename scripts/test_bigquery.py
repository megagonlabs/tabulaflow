#!/usr/bin/env -S uv run
"""Test BigQuery connectivity using Application Default Credentials."""

from google.cloud import bigquery

# Uses GOOGLE_APPLICATION_CREDENTIALS from environment (e.g. .envrc)
client = bigquery.Client()

sql_query = (
    "SELECT name FROM `bigquery-public-data.usa_names.usa_1910_2013` "
    "WHERE state = 'TX' LIMIT 10"
)
query_job = client.query(sql_query)
rows = query_job.result()

for row in rows:
    print(row.name)
