# Examples

Start with the bundled sample data or adapt these prompts to your own sources.
Each example asks for an outcome rather than prescribing individual tool calls;
the Data Agent inspects the data and chooses the necessary workflow.

## Compare spending by merchant

**Source:** bundled sample data

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

The result opens as an interactive chart. Its data and generated query remain
available in the same result card.

## Evaluate model performance

**Source:** bundled sample data

```text
Using the model evaluation results, calculate accuracy by domain, sort from
highest to lowest, and show the result as a bar chart.
```

This combines a grouped accuracy calculation with a presentation-ready result.

## Extract data from receipts

**Source:** bundled sample data

```text
Extract the merchant, purchase date, subtotal, tax, tip, and total from every
receipt in the sample expense documents. Preserve the result as a workspace
table and show me the completed dataset.
```

The agent reads the receipt images, extracts one structured record per
document, and writes the dataset to the local workspace.

## Combine multiple sources

**Sources:** your file and database

```text
Combine the account records in customers.csv with monthly revenue from the
warehouse and show revenue by customer segment.
```

Connected sources remain read-only. TabulaFlow moves the relevant data into its
local workspace before joining it.

## Build a dataset from the web

**Source:** a public website

```text
Build a table of the speakers on this conference website with their name,
organization, role, and profile URL. Normalize organization names.
```

The agent can browse pages, extract structured records, normalize entity names,
and preserve the result as workspace tables.

## Map geographic boundaries

**Source:** bundled sample data

```text
Using the NYC taxi zones in the sample data, draw the zone boundaries on a map,
color them by borough, and include the zone name in the tooltip.
```

The Data Agent can render points or WGS84 GeoJSON geometry returned by a query.

## Explore relationships

**Source:** your tabular or graph data

```text
Show a graph of customers and the products they purchased. Size customer nodes
by total spend and include order count in the tooltip.
```

TabulaFlow can render explicit entities and relationships from graph databases
or tabular query results.

## Adapt an example

Use `/connect` to add your data, then replace the sample source and field names
with the concepts in your own dataset. You do not need to know the exact schema
before asking: tell the agent to inspect the source first when the relevant
tables or columns are unclear.

Continue to [Connecting data](connecting-data.md) for supported source formats
and connection syntax.
