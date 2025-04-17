from abc import ABC
from pydantic import BaseModel
from typing import Optional, Dict, Union, List, Any


class NL2QTask(BaseModel):
    qid: str
    language: str
    db: str
    question: str
    evidence: Optional[str] = None
    gold_query: Optional[str] = None
    gold_exec_result: Optional[List[Any]] = None
    pred_query: Optional[str] = None
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
