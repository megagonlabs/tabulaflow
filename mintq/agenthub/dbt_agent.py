"""Stub dbt agent for testing the pipeline."""

import logging
import os
from typing import ClassVar

from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import BasicAgentConfig
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import DbtTask, DbtTaskOutput

logger = logging.getLogger(__name__)


def _find_duckdb_file(directory: str) -> str | None:
    """Return the path of the first ``.duckdb`` file in *directory*, or ``None``."""
    for f in os.listdir(directory):
        if f.endswith(".duckdb"):
            return os.path.join(directory, f)
    return None


@agent_registry.register
class DbtAgent:
    name: ClassVar = "dbt_agent"
    task_type: ClassVar = "dbt"
    output_type: ClassVar = "dbt"
    config_cls: ClassVar[type[BaseAgentConfig]] = BasicAgentConfig

    def __init__(self, config: BasicAgentConfig):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "DbtAgent":
        return cls(config)

    async def predict_async(self, task: DbtTask, db_connector: BaseSQLDBConnector) -> DbtTaskOutput:
        logger.info("dbt_agent: no-op for %s (working_dir=%s)", task.qid, task.working_dir)
        pred_db_path = _find_duckdb_file(task.working_dir) if task.working_dir else None
        return DbtTaskOutput(**task.model_dump(), pred_db_path=pred_db_path)
