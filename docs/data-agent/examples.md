# Examples

Try these prompts with the bundled sample data, or adapt them to your own
sources. Describe the result you want; the Data Agent will choose the workflow.

## Compare spending by merchant

**Source:** bundled sample data

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

The result card includes the chart, its data, and the generated query.

## Evaluate model performance

**Source:** bundled sample data

```text
Using the model evaluation results, calculate accuracy by domain, sort from
highest to lowest, and show the result as a bar chart.
```

This prompt calculates grouped accuracy and presents the result in one step.

## Extract data from receipts

**Source:** bundled sample data

```text
Extract the merchant, purchase date, subtotal, tax, tip, and total from every
receipt in the sample expense documents. Preserve the result as a workspace
table and show me the completed dataset.
```

The agent extracts one record per receipt and saves the dataset in your local
workspace.

## Combine multiple sources

**Sources:** your file and database

```text
Combine the account records in customers.csv with monthly revenue from the
warehouse and show revenue by customer segment.
```

TabulaFlow keeps both sources read-only and joins the relevant data in your
local workspace.

## Build a dataset from the web

**Source:** a public website

```text
Build a table of the speakers on this conference website with their name,
organization, role, and profile URL. Normalize organization names.
```

The agent browses the pages, extracts the records, normalizes organization
names, and saves the result in your workspace.

## Map geographic boundaries

**Source:** bundled sample data

```text
Using the NYC taxi zones in the sample data, draw the zone boundaries on a map,
color them by borough, and include the zone name in the tooltip.
```

Maps can display points or WGS84 GeoJSON geometry.

## Explore relationships

**Source:** your tabular or graph data

```text
Show a graph of customers and the products they purchased. Size customer nodes
by total spend and include order count in the tooltip.
```

Graphs can use relationships from a graph database or tabular query.

## Adapt an example

Use `/connect` to add your data, then replace the sample concepts with your
own. If you do not know the schema, ask the agent to inspect the source first.

See [Connecting data](connecting-data.md) for supported sources and syntax.
