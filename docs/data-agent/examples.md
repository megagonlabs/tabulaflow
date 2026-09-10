# Examples

These examples show the kinds of end-to-end tasks you can give the Data Agent.
[Connect your data](connecting-data.md), then adapt a prompt to your sources.

## Analyze and visualize data

```text
Using orders.parquet, compare monthly revenue by product category and show the
result as a line chart.
```

TabulaFlow inspects the file, runs the analysis, and presents the underlying
rows with an interactive chart.

## Combine multiple sources

```text
Combine the account records in customers.csv with monthly revenue from the
warehouse and show revenue by customer segment.
```

Connected sources remain read-only. TabulaFlow moves the relevant data into its
local workspace before joining it.

## Build a dataset from the web

```text
Build a table of the speakers on this conference website with their name,
organization, role, and profile URL. Normalize organization names.
```

The agent can browse pages, extract structured records, normalize entity names,
and preserve the result as workspace tables.

## Map geographic data

```text
Show store locations on a map, sized by annual revenue and colored by region.
Include store name and revenue in the tooltip.
```

Maps work with coordinates or geographic geometry returned by a connected
source.

## Explore relationships

```text
Show a graph of customers and the products they purchased. Size customer nodes
by total spend and include order count in the tooltip.
```

TabulaFlow can render explicit entities and relationships from graph databases
or tabular query results.
