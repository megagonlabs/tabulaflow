"""Research evaluation metrics, aggregators, and registry."""

from tabulaflow.research.metrics.registry import (
    NL2QMetric,
    metric_registry,
    MetricAggregator,
)
from tabulaflow.research.metrics.aggregators import (
    SimpleAverageAggregator,
    RealScoreAggregator,
    ByDBAggregator,
    ByAmbigPointNumAggregator,
    SimpleInferenceMetricsAggregator,
)
from tabulaflow.research.metrics.simple_ex import SimpleEx
from tabulaflow.research.metrics.spider2_ex import Spider2Ex
from tabulaflow.research.metrics.bird_sql_ex import BirdSQLEx
from tabulaflow.research.metrics.bird_sql_ex_soft import BirdSQLExSoft
from tabulaflow.research.metrics.executable import Executable
from tabulaflow.research.metrics.gold_executable import GoldExecutable
from tabulaflow.research.metrics.gold_result_not_empty import GoldResultNotEmpty
from tabulaflow.research.metrics.pred_success import PredSuccess
from tabulaflow.research.metrics.ambig_point_stats import AmbigPointStats
from tabulaflow.research.metrics.gold_ambig_point_stats import GoldAmbigPointStats
from tabulaflow.research.metrics.found_one import FoundOne
from tabulaflow.research.metrics.raw_pred_bird_sql_ex import RawPredBirdSQLEx
from tabulaflow.research.metrics.raw_pred_simple_ex import RawPredSimpleEx
from tabulaflow.research.metrics.schema_linking_stats import SchemaLinkingStats
from tabulaflow.research.metrics.psjs import PSJS
from tabulaflow.research.metrics.cypherbench_ex import CypherBenchEx
from tabulaflow.research.metrics.spider2_duckdb_match import Spider2DuckdbMatch

__all__ = [
    "NL2QMetric",
    "MetricAggregator",
    "SimpleAverageAggregator",
    "RealScoreAggregator",
    "SimpleInferenceMetricsAggregator",
    "ByDBAggregator",
    "ByAmbigPointNumAggregator",
    "CypherBenchEx",
    "BirdSQLEx",
    "BirdSQLExSoft",
    "Executable",
    "GoldExecutable",
    "GoldResultNotEmpty",
    "Spider2Ex",
    "PredSuccess",
    "AmbigPointStats",
    "GoldAmbigPointStats",
    "SimpleEx",
    "FoundOne",
    "RawPredBirdSQLEx",
    "RawPredSimpleEx",
    "PSJS",
    "SchemaLinkingStats",
    "Spider2DuckdbMatch",
    "metric_registry",
]
