from sqlalchemy import create_engine
from rattq.db_connector.mschema_utils import MSchema, SchemaEngine
from rattq.db_connector.base import BaseDBConnector


class SQLiteConnector(BaseDBConnector):
    def __init__(self, name: str, db_path: str):
        self.name = name
        self.db_path = db_path

        self.mschema = MSchema()
        db_engine = create_engine(f'sqlite:///{db_path}')
        schema_engine = SchemaEngine(engine=db_engine, db_name=self.name)
        mschema = schema_engine.mschema
        mschema_str = mschema.to_mschema()
        self._schema = mschema_str

    def get_schema(self) -> str:
        return self._schema
