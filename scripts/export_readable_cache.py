import argparse
import os
from pathlib import Path
import tabulaflow
from tabulaflow.config import tabulaflow_config
from tabulaflow.agents.modules.db_summarizer import DBSummary
from tabulaflow.core import SQLSchema
from tabulaflow.output.formatting import SQLDDLSchemaFormatter
from tabulaflow.research.agenthub._erd import ERDiagram, MermaidERDiagramFormatter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default="readable_cache/")
    parser.add_argument("--skip_exists", action="store_true", help="Skip if output file already exists")
    args = parser.parse_args()

    tabulaflow.configure()

    input_dir = Path(tabulaflow_config.cache_dir) / "schemas"
    output_dir = os.path.join(args.output_dir, "schemas")
    os.makedirs(output_dir, exist_ok=True)
    exported = 0
    for path in input_dir.rglob("*.json"):
        output_path = os.path.join(output_dir, path.name.replace(".json", ".md"))
        if args.skip_exists and os.path.exists(output_path):
            continue
        try:
            schema = SQLSchema.model_validate_json(path.read_text())
        except ValueError:
            continue
        schema_str = SQLDDLSchemaFormatter(compact_table_families=True).format(schema, include_descriptions=True)
        with open(output_path, "w") as f:
            f.write(schema_str)
        exported += 1
    print(f"Exported {exported} schemas to {output_dir}")

    input_dir = os.path.join(tabulaflow_config.cache_dir, "preprocessors", "db_summarizer")
    output_dir = os.path.join(args.output_dir, "preprocessors", "db_summarizer")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        output_path = os.path.join(output_dir, f.replace(".json", ".md"))
        if args.skip_exists and os.path.exists(output_path):
            continue
        summary = DBSummary.model_validate_json(open(os.path.join(input_dir, f)).read())
        with open(output_path, "w") as f:
            f.write(summary.db_summary_markdown)
    print(f"Exported {len(os.listdir(input_dir))} DB summaries to {output_dir}")

    input_dir = os.path.join(tabulaflow_config.cache_dir, "preprocessors", "schema_preprocessor")
    output_dir = os.path.join(args.output_dir, "preprocessors", "schema_preprocessor")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        output_path = os.path.join(output_dir, f.replace(".json", ".md"))
        if args.skip_exists and os.path.exists(output_path):
            continue
        schema = SQLSchema.model_validate_json(open(os.path.join(input_dir, f)).read())
        schema_str = SQLDDLSchemaFormatter(compact_table_families=True).format(schema, include_descriptions=True)
        with open(output_path, "w") as f:
            f.write(schema_str)
    print(f"Exported {len(os.listdir(input_dir))} preprocessed schemas to {output_dir}")

    input_dir = os.path.join(tabulaflow_config.cache_dir, "preprocessors", "er_diagram_synthesizer")
    output_dir = os.path.join(args.output_dir, "preprocessors", "er_diagram_synthesizer")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        output_path = os.path.join(output_dir, f.replace(".json", ".md"))
        if args.skip_exists and os.path.exists(output_path):
            continue
        er_diagram = ERDiagram.model_validate_json(open(os.path.join(input_dir, f)).read())
        er_diagram_str = MermaidERDiagramFormatter().format(er_diagram)
        with open(output_path, "w") as f:
            f.write(er_diagram_str)
    print(f"Exported {len(os.listdir(input_dir))} ER diagrams to {output_dir}")


if __name__ == "__main__":
    main()
