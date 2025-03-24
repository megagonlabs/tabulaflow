# nl2q-rl

RATTQ (Reinforced Agentic Text-to-Query)



```python
from rattq.db_connector import SQLiteConnector

db = SQLiteConnector(
    "bird-sql_dev_1",
    "data/BIRD-SQL/dev_20240627/dev_databases/california_schools/california_schools.sqlite",
)
tools = get_smolagent_tools(db)
print(
    tools[1](
        [
            'frpm."School Type"',
            'frpm."SchooasdfadlType"',
            'asdf."SchoolType"',
            'frpm."School Name"',
        ],
        ["public", "charter"],
    )
)
exit(9)
```