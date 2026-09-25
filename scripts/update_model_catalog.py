from datetime import datetime, timezone

import httpx

from tabulaflow import __version__
from tabulaflow.app.model_catalog import (
    MODEL_CATALOG_BUNDLED_PATH,
    MODEL_CATALOG_URL,
    _BundledCatalog,
    _parse_catalog,
    _release_cutoff,
)


def main() -> None:
    response = httpx.get(
        MODEL_CATALOG_URL,
        headers={"Accept": "application/json", "User-Agent": f"tabulaflow/{__version__}"},
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()
    snapshot_date = datetime.now(timezone.utc).date()
    catalog = _BundledCatalog(
        snapshot_date=snapshot_date,
        release_cutoff=_release_cutoff(snapshot_date),
        models=_parse_catalog(response.json()),
    )
    MODEL_CATALOG_BUNDLED_PATH.write_text(catalog.model_dump_json() + "\n")


if __name__ == "__main__":
    main()
