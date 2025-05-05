from abc import ABC
from pydantic import BaseModel
from typing import Optional, Dict, Union, List, Any


class BaseNL2QTask(BaseModel, ABC):
    qid: str
    language: str
    db: str
    question: str
    evidence: Optional[str] = None
    metrics: Dict[str, Union[float, int]] = {}


class SingleOutputNL2QTask(BaseNL2QTask):
    gold_queries: List[str] = []
    gold_exec_results: List[List[dict]] = []
    pred_query: Optional[str] = None
    trajectory: Optional[List[dict]] = None


class MultiOutputNL2QTask(BaseNL2QTask):
    gold_queries: List[str] = []
    gold_exec_results: List[List[dict]] = []
    pred_queries: List[str] = []
    trajectories: List[List[dict]] = []


NL2QTask = Union[SingleOutputNL2QTask, MultiOutputNL2QTask]


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
    examples: List[Any]


class SQLTableSchema(BaseModel):
    name: str
    schema_name: Optional[str]
    columns: List[SQLColumnSchema]
    primary_key: List[str]
    num_rows: int


class ForeignKeySchema(BaseModel):
    schema_name: Optional[str]
    table: str
    columns: List[str]
    foreign_schema_name: Optional[str]
    foreign_table: str
    foreign_columns: List[str]


class SQLSchema(BaseDBSchema):
    name: str
    tables: List[SQLTableSchema]
    foreign_keys: List[ForeignKeySchema]


class ERDiagramRelation(BaseModel):
    from_schema: Optional[str]
    from_table: str
    from_column: str
    to_schema: Optional[str]
    to_table: str
    to_column: str


class ERDiagram(BaseModel):
    db_schema: SQLSchema
    relations: List[ERDiagramRelation]
