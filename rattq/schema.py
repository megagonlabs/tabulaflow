from abc import ABC
import pandas as pd
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Union, List, Any


class NL2QTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    qid: str
    language: str
    db: str
    question: str
    evidence: Optional[str] = None
    gold_query: List[str] = []
    gold_exec_result: List[pd.DataFrame] = []
    pred_query: List[str] = []
    metrics: Dict[str, Union[float, int]] = {}


class NL2QDataset(BaseModel):
    name: str
    split_id: str
    tasks: list[NL2QTask]
    db_connectors: dict[str, Any]


class BaseDBSchema(BaseModel, ABC):
    pass


class SQLColumnSchema(BaseModel):
    name: str
    type: str
    cardinality: int
    count: int
    examples: List[Any]


class SQLTableSchema(BaseModel):
    name: str
    columns: List[SQLColumnSchema]
    primary_key: List[str]
    num_rows: int


class ForeignKeySchema(BaseModel):
    table: str
    column: str
    foreign_table: str
    foreign_column: str


class SQLSchema(BaseDBSchema):
    name: str
    tables: List[SQLTableSchema]
    foreign_keys: List[ForeignKeySchema]
