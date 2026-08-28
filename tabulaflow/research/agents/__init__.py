"""Research agent strategies, protocols, and registry."""

from tabulaflow.research.agents.registry import (
    SimpleAgentProtocol,
    AmbigSQLAgentProtocol,
    DbtAgentProtocol,
    agent_registry,
)
from tabulaflow.research.agents.direct_prompt import DirectPromptAgent
from tabulaflow.research.agents.full_schema import FullSchemaAgent
from tabulaflow.research.agents.schema_linking import SchemaLinkingAgent
from tabulaflow.research.agents.schema_discovery import SchemaDiscoveryAgent
from tabulaflow.research.agents.ambig_simple import AmbigSimpleSQLAgent
from tabulaflow.research.agents.ambig_flat import AmbigFlatSQLAgent
from tabulaflow.research.agents.ambig_structured import AmbigStructuredSQLAgent
from tabulaflow.research.agents.dbt import DbtAgent
from tabulaflow.research.agents.utils import BasicAgentConfig

__all__ = [
    "SimpleAgentProtocol",
    "AmbigSQLAgentProtocol",
    "DbtAgentProtocol",
    "BasicAgentConfig",
    "DirectPromptAgent",
    "FullSchemaAgent",
    "SchemaLinkingAgent",
    "SchemaDiscoveryAgent",
    "AmbigSimpleSQLAgent",
    "AmbigFlatSQLAgent",
    "AmbigStructuredSQLAgent",
    "DbtAgent",
    "agent_registry",
]
