"""Benchmark: parquet roundtrip vs to_sql for loading HF dataset into DuckDB."""

import os
import tempfile
import time

import duckdb
from datasets import load_dataset


def bench_parquet(ds, db_path: str, table_name: str = "data") -> float:
    """Load via temp parquet file + DuckDB read_parquet."""
    tmp = tempfile.mktemp(suffix=".parquet")
    try:
        t0 = time.perf_counter()
        ds.to_parquet(tmp)
        con = duckdb.connect(db_path)
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{tmp}')")
        elapsed = time.perf_counter() - t0
        rows = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        con.close()
        print(f"  parquet: {elapsed:.3f}s ({rows:,} rows)")
        return elapsed
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def bench_to_sql(ds, db_path: str, table_name: str = "data") -> float:
    """Load via Dataset.to_sql with duckdb SQLAlchemy URL."""
    from sqlalchemy import create_engine

    t0 = time.perf_counter()
    engine = create_engine(f"duckdb:///{db_path}")
    ds.to_sql(table_name, engine)
    elapsed = time.perf_counter() - t0

    with engine.connect() as conn:
        rows = conn.execute(__import__("sqlalchemy").text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    engine.dispose()
    print(f"  to_sql:  {elapsed:.3f}s ({rows:,} rows)")
    return elapsed


def main() -> None:
    print("Loading dataset: stanfordnlp/imdb (train split)...")
    ds = load_dataset("stanfordnlp/imdb", split="train")
    print(f"  {len(ds):,} rows, {len(ds.column_names)} columns\n")

    db1 = tempfile.mktemp(suffix=".duckdb")
    db2 = tempfile.mktemp(suffix=".duckdb")

    try:
        print("Benchmark:")
        t_parquet = bench_parquet(ds, db1)
        t_sql = bench_to_sql(ds, db2)
        print(f"\n  parquet is {t_sql / t_parquet:.1f}x faster")
    finally:
        for p in (db1, db2):
            if os.path.exists(p):
                os.unlink(p)


if __name__ == "__main__":
    main()
