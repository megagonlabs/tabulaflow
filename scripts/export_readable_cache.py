import argparse
import os
from mintq.config import mintq_config
from mintq.preprocessors.db_summarizer import DBSummary
from mintq.schema import SQLSchema
from mintq.preprocessors.components.schema_compressor import SchemaCompressor
from mintq.preprocessors.er_diagram import ERDiagram
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
from mintq.formatters.er_diagram import ERDiagramMermaidFormatter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default="readable_cache/")
    args = parser.parse_args()

    mintq_config.setup_logging()

    input_dir = os.path.join(mintq_config.cache_dir, "schemas")
    output_dir = os.path.join(args.output_dir, "schemas")
    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(input_dir):
        schema = SQLSchema.model_validate_json(open(os.path.join(input_dir, file)).read())
        compressed_schema = SchemaCompressor().compress(schema)
        compressed_schema_str = SQLDDLSchemaFormatter().format(compressed_schema, add_description=True)
        with open(os.path.join(output_dir, file.replace(".json", ".md")), "w") as f:
            f.write(compressed_schema_str)
    print(f"Exported {len(os.listdir(input_dir))} schemas to {output_dir}")

    input_dir = os.path.join(mintq_config.cache_dir, "preprocessors", "db_summarizer")
    output_dir = os.path.join(args.output_dir, "preprocessors", "db_summarizer")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        summary = DBSummary.model_validate_json(open(os.path.join(input_dir, f)).read())
        with open(os.path.join(output_dir, f.replace(".json", ".md")), "w") as f:
            f.write(summary.db_summary_markdown)
    print(f"Exported {len(os.listdir(input_dir))} DB summaries to {output_dir}")

    input_dir = os.path.join(mintq_config.cache_dir, "preprocessors", "schema_preprocessor")
    output_dir = os.path.join(args.output_dir, "preprocessors", "schema_preprocessor")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        schema = SQLSchema.model_validate_json(open(os.path.join(input_dir, f)).read())
        schema_str = SQLDDLSchemaFormatter().format(schema, add_description=True)
        with open(os.path.join(output_dir, f.replace(".json", ".md")), "w") as f:
            f.write(schema_str)
    print(f"Exported {len(os.listdir(input_dir))} preprocessed schemas to {output_dir}")

    input_dir = os.path.join(mintq_config.cache_dir, "preprocessors", "er_diagram_synthesizer")
    output_dir = os.path.join(args.output_dir, "preprocessors", "er_diagram_synthesizer")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        er_diagram = ERDiagram.model_validate_json(open(os.path.join(input_dir, f)).read())
        er_diagram_str = ERDiagramMermaidFormatter().format(er_diagram)
        with open(os.path.join(output_dir, f.replace(".json", ".md")), "w") as f:
            f.write(er_diagram_str)
    print(f"Exported {len(os.listdir(input_dir))} ER diagrams to {output_dir}")


if __name__ == "__main__":
    main()
