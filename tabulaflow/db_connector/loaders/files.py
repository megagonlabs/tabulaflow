"""Load local data files (CSV / TSV / XLSX / Parquet / JSON) into a
DuckDB-backed :class:`SQLConnector`.

The DuckDB load runs in-process via the SQLConnector's normal query path,
so cancellation propagates through ``ThrottledEngine.aclose`` (DuckDB
``interrupt()`` reliably aborts local CREATE TABLE operations).
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulaflow.db_connector.sql_conn import SQLConnector


DATA_FILE_EXTENSIONS = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson"})
_DUCKDB_JSON_MAX_OBJECT_SIZE_BYTES = 1024 * 1024 * 1024


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

    Each file is loaded into a DuckDB table.  Supported formats:
    ``.csv``, ``.tsv``, ``.xlsx``, ``.xls``, ``.parquet``, ``.json``,
    ``.jsonl``, ``.ndjson``.

    File ownership: ``load_files`` claims the path
    ``<data_dir>/<db_name>.duckdb`` (or a fresh temp file when
    ``data_dir`` is None).  **Any existing file at that path is silently
    deleted before the load** — the DB is always (re)built from
    scratch.  Don't point ``data_dir``+``db_name`` at a file you want to
    preserve.  When ``data_dir`` is None the temp file is also deleted
    by :meth:`SQLConnector.disconnect_async`.

    Concurrency precondition: the caller must ensure ``(data_dir,
    db_name)`` is unique across live :class:`SQLConnector` instances in
    the process.  Two simultaneous ``load_files`` calls resolving to the
    same path will corrupt each other (the second's unlink-existing
    step deletes the first's open DB file).  The tabulaflow CLI guarantees
    this via the alias-uniqueness check on ``/connect``.

    Atomicity: ``load_files`` either returns a successfully-loaded
    :class:`SQLConnector` or leaves no DB file at the target path.  Any
    failure mid-load (cancellation, exception, error from the loader)
    unlinks the partial file before re-raising.  Cancellation
    propagates through the SQLConnector's standard query path —
    DuckDB's ``conn.interrupt()`` aborts the in-flight ``CREATE TABLE``.

    Read-only enforcement: the DuckDB connection is always opened
    read-write (DDL is required for the load).  ``read_only=True`` is
    enforced at the SQLConnector layer — write statements via
    :meth:`SQLConnector.run_query_async` are blocked.  This is sufficient
    when the calling session is the sole owner of the cache file.

    Args:
        global_id: Globally unique identifier for this connection, also
            used as the cache key when loading the schema.
        file_paths: Paths to data files to load.
        db_name: Display name for the database. Defaults to the first
            file's stem.
        data_dir: Directory to store the DuckDB file.  If ``None``, a
            system temp directory is used and the file is unlinked on
            disconnect.
        read_only: If True, block write statements at the SQLConnector
            layer.  The underlying DuckDB connection is always opened
            read-write so the loader can issue CREATE TABLE statements.
        enable_schema_caching: Whether to cache the inferred schema.
        enable_query_caching: Whether to cache query results.

    Returns:
        A :class:`SQLConnector` backed by a DuckDB database.
    """
    from tabulaflow.db_connector.sql_conn import SQLConnector

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

    # Always start from a fresh DB.  A partial file may exist from a
    # prior call that was cancelled mid-load; CREATE TABLE would fail
    # against it with "Table already exists".
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except OSError:
            pass

    table_file_map = dict(_assign_table_names(resolved))
    needs_spatial = any(os.path.splitext(p)[1].lower() in (".xlsx", ".xls") for p in resolved)
    duckdb_init_sql = ["INSTALL spatial; LOAD spatial;"] if needs_spatial else None

    try:
        connector = await SQLConnector.from_url_async(
            global_id=global_id,
            url=f"duckdb:///{db_path}",
            db_name=db_name,
            read_only=False,  # need DDL for the load; SQLConnector.read_only set below
            enable_schema_caching=enable_schema_caching,
            enable_query_caching=enable_query_caching,
            duckdb_init_sql=duckdb_init_sql,
        )
    except BaseException:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass
        raise

    try:
        for name, file_path in table_file_map.items():
            result = await connector.run_query_async(_create_table_sql_for_file(name, file_path))
            if result.error is not None:
                raise RuntimeError(f"Failed to load {file_path}: {result.error.message}")
        await connector.refresh_schema_async()
    except BaseException:
        await connector.disconnect_async()
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass
        raise

    connector.read_only = read_only

    # The DuckDB cache file is loader-owned: the source CSV/parquet/Excel
    # files are the truth; this file is regenerable.  Delete it on
    # disconnect so ``data_dir`` directories don't accumulate stale caches.
    cache_path = db_path

    def _cleanup_cache() -> None:
        try:
            os.unlink(cache_path)
        except OSError:
            pass

    connector.register_disconnect_hook(_cleanup_cache)

    for table in connector.schema.tables:
        source_file = table_file_map.get(table.name)
        if source_file:
            table.description = f"Imported from {os.path.basename(source_file)}"

    file_list = "\n".join(resolved)
    connector.schema.description = f"Source: local files\n\n{file_list}"

    return connector
