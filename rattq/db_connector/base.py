class BaseDBConnector:
    def get_schema(self):
        raise NotImplementedError()

    def run_query(self, query: str, timeout: int = 30) -> list:
        raise NotImplementedError()
