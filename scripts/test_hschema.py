import os
import argparse
from mintq.datahub import get_dataset_loader
from mintq.formatters.hschema import HSchemaFormatter
from mintq.schema import HSQLSchema
from mintq.metadata_synthesizer.hschema import HSchemaSynthesizer


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default="bird-sql")
    parser.add_argument("--split", type=str, default="dev")
    parser.add_argument("--database", type=str, default="european_football_2")
    parser.add_argument("--llm", type=str, default="gpt-4o")
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()
    print(args)
    print()

    dataset_loader = get_dataset_loader(args.dataset)
    dataset = await dataset_loader.get_split_async(args.split, databases=[args.database])
    db_connector = dataset.db_connectors[args.database]
    synthesizer = HSchemaSynthesizer(
        llm=args.llm,
        batch_size=args.batch_size,
        temperature=args.temperature,
    )
    hschema = await synthesizer.run(db_connector)

    with open("cache/hschema.json", "w") as f:
        f.write(hschema.model_dump_json(indent=2))

    with open("cache/hschema.json", "r") as f:
        hschema = HSQLSchema.model_validate_json(f.read())

    formatter = HSchemaFormatter()
    hschema_str = formatter.format(hschema)
    print(hschema_str)

    output_dir = "output/test_hschema/"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "hschema.txt"), "w") as f:
        f.write(hschema_str)

    with open(os.path.join(output_dir, "root_trajectory.xml"), "w") as f:
        f.write(synthesizer.root_trajectory_.model_dump_json(indent=2))

    for section_name, trajectory in synthesizer.per_section_trajectories_.items():
        with open(os.path.join(output_dir, f"{section_name}_trajectory.xml"), "w") as f:
            f.write(trajectory.model_dump_json(indent=2))
