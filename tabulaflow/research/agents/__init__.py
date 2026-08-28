"""Research agent strategies, protocols, and registry."""

from tabulaflow.research.agents.registry import (
    AgentConfig,
    SimpleSQLAgentProtocol,
    AmbigSQLAgentProtocol,
    DbtAgentProtocol,
    NL2QAgent,
    agent_registry,
)
from tabulaflow.research.agents.direct_prompting import DirectPrompting
from tabulaflow.research.agents.mini_agent import MiniAgent
from tabulaflow.research.agents.sql_agent import SQLAgent
from tabulaflow.research.agents.tabulaflow_agent import TabulaflowAgent
from tabulaflow.research.agents.ambig_simple import AmbigSimpleSQLAgent
from tabulaflow.research.agents.ambig_flat import AmbigFlatSQLAgent
from tabulaflow.research.agents.ambig_structured import AmbigStructuredSQLAgent
from tabulaflow.research.agents.dbt_agent import DbtAgent
from tabulaflow.research.agents.utils import BasicAgentConfig

__all__ = [
    "SimpleSQLAgentProtocol",
    "AmbigSQLAgentProtocol",
    "DbtAgentProtocol",
    "NL2QAgent",
    "AgentConfig",
    "BasicAgentConfig",
    "DirectPrompting",
    "MiniAgent",
    "SQLAgent",
    "TabulaflowAgent",
    "AmbigSimpleSQLAgent",
    "AmbigFlatSQLAgent",
    "AmbigStructuredSQLAgent",
    "DbtAgent",
    "agent_registry",
]
