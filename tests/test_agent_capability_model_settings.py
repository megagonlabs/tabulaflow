from __future__ import annotations

from pydantic_ai.settings import ModelSettings

from tabulaflow.research.preprocessing.column_profiler import ColumnProfiler
from tabulaflow.agents.summarization import DBSummarizer
from tabulaflow.research.preprocessing.erd import ERDiagramSynthesizer
from tabulaflow.research.preprocessing.fk_predictor import ForeignKeyPredictor
from tabulaflow.research.preprocessing.schema import SchemaPreprocessor
from tabulaflow.agents.summarization import TextSummarizer
from tabulaflow.research.preprocessing import (
    ConnectorPreprocessorProtocol,
    DatasetPreprocessorProtocol,
    preprocessor_registry,
)
from tabulaflow.research.preprocessing.question_embedding import QuestionEmbedder


def test_agent_capabilities_accept_model_settings() -> None:
    settings = ModelSettings(temperature=0)

    column_profiler = ColumnProfiler(model_settings=settings)
    fk_predictor = ForeignKeyPredictor(model_settings=settings)
    er_synthesizer = ERDiagramSynthesizer(model_settings=settings)
    db_summarizer = DBSummarizer(model_settings=settings)
    text_summarizer = TextSummarizer(model_settings=settings)

    assert column_profiler.model_settings is settings
    assert fk_predictor.model_settings is settings
    assert er_synthesizer.model_settings is settings
    assert db_summarizer.model_settings is settings
    assert text_summarizer.model_settings is settings


def test_schema_preprocessor_passes_model_settings_to_llm_submodules() -> None:
    column_settings = ModelSettings(temperature=0)
    fk_settings = ModelSettings(temperature=1)

    preprocessor = SchemaPreprocessor(
        column_profiler_llm="test:column",
        foreign_key_predictor_llm="test:fk",
        column_profiler_model_settings=column_settings,
        foreign_key_predictor_model_settings=fk_settings,
    )

    assert preprocessor.column_profiler is not None
    assert preprocessor.foreign_key_predictor is not None
    assert preprocessor.column_profiler.model_settings is column_settings
    assert preprocessor.foreign_key_predictor.model_settings is fk_settings


def test_research_preprocessor_registry_owns_default_preprocessors() -> None:
    assert QuestionEmbedder.name == "question_embedder"
    assert set(preprocessor_registry.list_names()) == {
        "db_summarizer",
        "er_diagram_synthesizer",
        "question_embedder",
        "schema_preprocessor",
    }


def test_preprocessors_satisfy_their_extension_protocols() -> None:
    connector_preprocessor: ConnectorPreprocessorProtocol = SchemaPreprocessor()
    dataset_preprocessor: DatasetPreprocessorProtocol = QuestionEmbedder(disable_preprocessing=True)

    assert connector_preprocessor.input_type == "db_connector"
    assert dataset_preprocessor.input_type == "dataset"
