"""Data source loaders that produce SQLConnector instances."""

from mintq.db_connector.loaders.files import DATA_FILE_EXTENSIONS, load_files
from mintq.db_connector.loaders.huggingface import (
    is_hf_dataset_url,
    load_hf_dataset,
    parse_hf_dataset_url,
)

__all__ = [
    "DATA_FILE_EXTENSIONS",
    "is_hf_dataset_url",
    "load_files",
    "load_hf_dataset",
    "parse_hf_dataset_url",
]
