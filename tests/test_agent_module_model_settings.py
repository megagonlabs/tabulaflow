from __future__ import annotations

from pydantic_ai.settings import ModelSettings

from tabulaflow.agents.modules.column_profiler import ColumnProfiler
from tabulaflow.agents.modules.db_summarizer import DBSummarizer
from tabulaflow.research.agenthub._erd import ERDiagramSynthesizer
from tabulaflow.agents.modules.fk_predictor import ForeignKeyPredictor
from tabulaflow.agents.modules.schema_preprocessor import SchemaPreprocessor
from tabulaflow.agents.modules.text_summarizer import TextSummarizer


def test_modulehub_llm_components_accept_model_settings() -> None:
    settings = ModelSettings(temperature=0)

    column_profiler = ColumnProfiler(model_settings=settings)
    fk_predictor = ForeignKeyPredictor(model_settings=settings)
    er_synthesizer = ERDiagramSynthesizer(model_settings=settings)
    db_summarizer = DBSummarizer(model_settings=settings)
    text_summarizer = TextSummarizer(model_settings=settings)

    assert column_profiler.model_settings is settings
    assert fk_predictor.model_settings is settings
    assert er_synthesizer.model_settings is settings
    assert db_summarizer.extra_model_settings is settings
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
