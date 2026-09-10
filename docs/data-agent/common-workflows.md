# Common workflows

## Explore before querying

Ask the agent to inspect available tables, columns, and representative values
before composing an analysis:

```text
Inspect this source and explain which tables are relevant to customer churn.
```

## Combine sources

TabulaFlow can materialize relevant data from separate sources into its local
workspace and join the derived tables there.

```text
Combine the account records in customers.csv with monthly revenue from the
warehouse and show revenue by customer segment.
```

## Build a structured dataset

The agent can gather documents or web pages, extract entities, normalize names,
and preserve the result as workspace tables.

## Present results

Ask for the representation that fits the question:

- Tables for detailed records
- Charts for comparisons and trends
- Maps for geographic data
- Graphs for explicit relationships
