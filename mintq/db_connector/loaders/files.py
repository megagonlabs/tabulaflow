"""Load local data files (CSV / TSV / XLSX / Parquet / JSON) into a
DuckDB-backed :class:`SQLConnector`.

The DuckDB load phase runs in a subprocess (via ``python -m`` on this
module's ``__main__``) so cancellation terminates it at the OS level —
the only reliable way to stop long-running native I/O inside DuckDB.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mintq.db_connector.sql_conn import SQLConnector


# ---------------------------------------------------------------------------
# Shared constants and helpers (used by both parent and worker)
# ---------------------------------------------------------------------------


DATA_FILE_EXTENSIONS = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson"})
_DUCKDB_JSON_MAX_OBJECT_SIZE_BYTES = (4 * 1024 * 1024 * 1024) - 1


def _table_name_from_path(file_path: str, *, include_ext: bool = False) -> str:
    """Derive a clean SQL table name from a file path.

    Args:
        file_path: Path to the data file.
        include_ext: If True, append the file extension as a suffix
            (e.g. ``sales.csv`` → ``sales_csv``).
    """
    basename = os.path.basename(file_path)
    stem, ext = os.path.splitext(basename)
    name = re.sub(r"[^a-zA-Z0-9_]", "_", stem)
    name = re.sub(r"_+", "_", name).strip("_")
    if include_ext and ext:
        name = f"{name}_{ext.lstrip('.').lower()}" if name else ext.lstrip(".").lower()
    if name and name[0].isdigit():
        name = f"t_{name}"
    return name.lower() or "data"


def _assign_table_names(file_paths: list[str]) -> list[tuple[str, str]]:
    """Return ``(table_name, file_path)`` pairs with suffixed uniqueness."""
    used_names: set[str] = set()
    out: list[tuple[str, str]] = []
    for file_path in file_paths:
        base_name = _table_name_from_path(file_path, include_ext=False)
        name = base_name
        suffix = 2
        while name in used_names:
            name = f"{base_name}_{suffix}"
            suffix += 1
        used_names.add(name)
        out.append((name, file_path))
    return out


def _create_table_sql_for_file(name: str, file_path: str) -> str:
    """Build a CREATE TABLE AS SELECT statement for a DuckDB-supported data file."""
    ext = os.path.splitext(file_path)[1].lower()
    escaped = file_path.replace("'", "''")
    if ext == ".csv":
        return f"CREATE TABLE \"{name}\" AS SELECT * FROM read_csv_auto('{escaped}')"
    if ext == ".tsv":
        return f"CREATE TABLE \"{name}\" AS SELECT * FROM read_csv_auto('{escaped}', delim='\\t')"
    if ext in (".xlsx", ".xls"):
        return f"CREATE TABLE \"{name}\" AS SELECT * FROM st_read('{escaped}')"
    if ext == ".parquet":
        return f"CREATE TABLE \"{name}\" AS SELECT * FROM read_parquet('{escaped}')"
    if ext in (".json", ".jsonl", ".ndjson"):
        # Unnest first-level keys into columns while keeping nested
        # objects/arrays as JSON values.
        return (
            f'CREATE TABLE "{name}" AS SELECT * FROM read_json_auto('
            f"'{escaped}', "
            f"maximum_object_size={_DUCKDB_JSON_MAX_OBJECT_SIZE_BYTES}, "
            "maximum_depth=1, "
            "ignore_errors=true)"
        )
    raise ValueError(f"Unsupported file format: {ext}")


# ---------------------------------------------------------------------------
# Parent-side entry point
# ---------------------------------------------------------------------------


async def load_files(
    global_id: str,
    file_paths: list[str],
    *,
    db_name: str | None = None,
    data_dir: str | None = None,
    read_only: bool = True,
    enable_schema_caching: bool = False,
    enable_query_caching: bool = False,
) -> SQLConnector:
    """Create a connector from CSV, Excel, Parquet, or JSON files.

    Each file is loaded into a DuckDB table backed by a database file.
    The file is cleaned up when :meth:`SQLConnector.disconnect_async` is
    called.

    Supported formats: ``.csv``, ``.tsv``, ``.xlsx``, ``.xls``,
    ``.parquet``, ``.json``, ``.jsonl``, ``.ndjson``.

    Args:
        global_id: Globally unique identifier for this connection, also
            used as the cache key when loading the schema.
        file_paths: Paths to data files to load.
        db_name: Display name for the database. Defaults to the first
            file's stem.
        data_dir: Directory to store the DuckDB file. If ``None``, a
            system temp directory is used.
        read_only: If True, block write statements.
        enable_schema_caching: Whether to cache the inferred schema.
        enable_query_caching: Whether to cache query results.

    Returns:
        A :class:`SQLConnector` backed by a DuckDB database.
    """
    from mintq.db_connector.loaders.runner import run_loader_subprocess
    from mintq.db_connector.sql_conn import SQLConnector

    seen: set[str] = set()
    resolved: list[str] = []
    for p in file_paths:
        abs_p = os.path.abspath(os.path.expanduser(p))
        if not os.path.isfile(abs_p):
            raise FileNotFoundError(f"File not found: {p}")
        ext = os.path.splitext(abs_p)[1].lower()
        if ext not in DATA_FILE_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {ext}")
        if abs_p not in seen:
            seen.add(abs_p)
            resolved.append(abs_p)
    if not resolved:
        raise ValueError("At least one file path is required")

    if db_name is None:
        db_name = _table_name_from_path(resolved[0])

    if data_dir is not None:
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, f"{db_name}.duckdb")
    else:
        fd, db_path = tempfile.mkstemp(suffix=".duckdb")
        os.close(fd)
        os.unlink(db_path)

    table_file_map = dict(_assign_table_names(resolved))
    needs_spatial = any(os.path.splitext(p)[1].lower() in (".xlsx", ".xls") for p in resolved)
    payload = {
        "db_path": db_path,
        "install_spatial": needs_spatial,
        "tables": [{"name": name, "path": path} for name, path in table_file_map.items()],
    }

    try:
        await run_loader_subprocess("mintq.db_connector.loaders.files", payload)
    except BaseException:
        if data_dir is None and os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass
        raise

    try:
        connector = await SQLConnector.from_url_async(
            global_id=global_id,
            url=f"duckdb:///{db_path}",
            db_name=db_name,
            read_only=read_only,
            enable_schema_caching=enable_schema_caching,
            enable_query_caching=enable_query_caching,
        )
    except BaseException:
        if data_dir is None and os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass
        raise

    connector._temp_db_path = db_path

    for table in connector.schema.tables:
        source_file = table_file_map.get(table.name)
        if source_file:
            table.description = f"Imported from {os.path.basename(source_file)}"

    file_list = "\n".join(resolved)
    connector.schema.description = f"Source: local files\n\n{file_list}"

    return connector


# ---------------------------------------------------------------------------
# Subprocess worker
# ---------------------------------------------------------------------------


def _worker_main() -> int:
    """Subprocess entry point.  Opens DuckDB at ``db_path`` and runs one
    CREATE TABLE per entry in ``tables``.

    Payload schema::

        {
            "db_path": str,
            "install_spatial": bool,
            "tables": [{"name": str, "path": str}, ...]
        }
    """
    import duckdb  # deferred — only the worker needs this

    payload = json.loads(sys.stdin.read())
    db_path: str = payload["db_path"]
    install_spatial: bool = bool(payload.get("install_spatial", False))
    tables: list[dict[str, str]] = payload["tables"]

    conn = duckdb.connect(db_path)
    try:
        if install_spatial:
            conn.execute("INSTALL spatial")
            conn.execute("LOAD spatial")
        for tbl in tables:
            conn.execute(_create_table_sql_for_file(tbl["name"], tbl["path"]))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_worker_main())
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
