import argparse
import os
import tabulaflow
from tabulaflow.core.config import tabulaflow_config
from tabulaflow.preprocessors.db_summarizer import DBSummary
from tabulaflow.core.types import SQLSchema
from tabulaflow.preprocessors.components.schema_compressor import SchemaCompressor
from tabulaflow.preprocessors.er_diagram import ERDiagram
from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.core.formatters.er_diagram import ERDiagramMermaidFormatter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default="readable_cache/")
    parser.add_argument("--skip_exists", action="store_true", help="Skip if output file already exists")
    args = parser.parse_args()

    tabulaflow.configure()

    input_dir = os.path.join(tabulaflow_config.cache_dir, "schemas")
    output_dir = os.path.join(args.output_dir, "schemas")
    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(input_dir):
        output_path = os.path.join(output_dir, file.replace(".json", ".md"))
        if args.skip_exists and os.path.exists(output_path):
            continue
        schema = SQLSchema.model_validate_json(open(os.path.join(input_dir, file)).read())
        compressed_schema = SchemaCompressor().compress(schema)
        compressed_schema_str = SQLDDLSchemaFormatter().format(compressed_schema, add_description=True)
        with open(output_path, "w") as f:
            f.write(compressed_schema_str)
    print(f"Exported {len(os.listdir(input_dir))} schemas to {output_dir}")

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
        schema_str = SQLDDLSchemaFormatter().format(schema, add_description=True)
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
        er_diagram_str = ERDiagramMermaidFormatter().format(er_diagram)
        with open(output_path, "w") as f:
            f.write(er_diagram_str)
    print(f"Exported {len(os.listdir(input_dir))} ER diagrams to {output_dir}")


if __name__ == "__main__":
    main()
