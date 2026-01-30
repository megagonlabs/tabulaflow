import argparse
import os
from mintq.config import config
from mintq.schema import SQLSchema
from mintq.preprocessors.er_diagram import ERDiagram
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
from mintq.formatters.er_diagram import ERDiagramCompactFormatter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", default="readable/")
    args = parser.parse_args()

    input_dir = os.path.join(config.cache_dir, "preprocessors", "schema_preprocessor")
    output_dir = os.path.join(args.output_dir, "preprocessors", "schema_preprocessor")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        schema = SQLSchema.model_validate_json(open(os.path.join(input_dir, f)).read())
        schema_str = SQLDDLSchemaFormatter().format(schema)
        with open(os.path.join(output_dir, f.replace(".json", ".txt")), "w") as f:
            f.write(schema_str)
    print(f"Exported {len(os.listdir(input_dir))} schemas to {output_dir}")

    input_dir = os.path.join(config.cache_dir, "preprocessors", "er_diagram_synthesizer")
    output_dir = os.path.join(args.output_dir, "preprocessors", "er_diagram_synthesizer")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        er_diagram = ERDiagram.model_validate_json(open(os.path.join(input_dir, f)).read())
        er_diagram_str = ERDiagramCompactFormatter().format(er_diagram)
        with open(os.path.join(output_dir, f.replace(".json", ".txt")), "w") as f:
            f.write(er_diagram_str)
    print(f"Exported {len(os.listdir(input_dir))} ER diagrams to {output_dir}")

    input_dir = os.path.join(config.cache_dir, "schemas")
    output_dir = os.path.join(args.output_dir, "schemas")
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        schema = SQLSchema.model_validate_json(open(os.path.join(input_dir, f)).read())
        schema_str = SQLDDLSchemaFormatter().format(schema)
        with open(os.path.join(output_dir, f.replace(".json", ".txt")), "w") as f:
            f.write(schema_str)
    print(f"Exported {len(os.listdir(input_dir))} schemas to {output_dir}")


if __name__ == "__main__":
    main()
