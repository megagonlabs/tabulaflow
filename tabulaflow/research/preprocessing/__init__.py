"""Research-only preprocessing workflows."""

from tabulaflow.research.preprocessing.registry import (
    ConnectorPreprocessorProtocol,
    DBSummaryPreprocessor,
    DatasetPreprocessorProtocol,
    preprocessor_registry,
)
from tabulaflow.research.preprocessing.column_profiler import ColumnProfiler
from tabulaflow.research.preprocessing.erd import ERDiagramSynthesizer
from tabulaflow.research.preprocessing.fk_predictor import ForeignKeyPredictor
from tabulaflow.research.preprocessing.question_embedding import QuestionEmbedder
from tabulaflow.research.preprocessing.schema import SchemaPreprocessor

__all__ = [
    "ColumnProfiler",
    "ConnectorPreprocessorProtocol",
    "DBSummaryPreprocessor",
    "DatasetPreprocessorProtocol",
    "ERDiagramSynthesizer",
    "ForeignKeyPredictor",
    "QuestionEmbedder",
    "SchemaPreprocessor",
    "preprocessor_registry",
]
