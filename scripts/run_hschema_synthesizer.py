import os
import shutil
import argparse
import asyncio
from mintq.datahub import get_dataset_loader
from mintq.formatters.hschema import HSchemaFormatter
from mintq.schema import HSQLSchema
from mintq.metadata_synthesizer.hschema import HSchemaSynthesizer
from mintq.utils import format_trajectory


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default="bird-sql")
    parser.add_argument("--split", type=str, default="dev")
    parser.add_argument("--database", type=str, default="european_football_2")
    parser.add_argument("--llm", type=str, default="gpt-4o")
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--output_dir", default="output/run_hschema_synthesizer")
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
    hschema = await synthesizer.run_async(db_connector)

    with open("cache/hschema.json", "w") as f:
        f.write(hschema.model_dump_json(indent=2))

    with open("cache/hschema.json", "r") as f:
        hschema = HSQLSchema.model_validate_json(f.read())

    formatter = HSchemaFormatter()
    hschema_str = formatter.format(hschema)
    print(hschema_str)

    if os.path.exists(args.output_dir):
        shutil.rmtree(args.output_dir)
    os.makedirs(args.output_dir, exist_ok=True)

    with open(os.path.join(args.output_dir, "hschema.txt"), "w") as f:
        f.write(hschema_str)

    for tg in hschema.table_groups:
        table = tg.tables[0]

        table_synthesizer = synthesizer.table_synthesizers_[table.name]

        with open(os.path.join(args.output_dir, f"{table.name}_section.xml"), "w") as f:
            f.write(format_trajectory(table_synthesizer.section_clusterer_.trajectory_))

        for section_name, clusterer in table_synthesizer.column_group_clusterers_.items():
            with open(os.path.join(args.output_dir, f"{table.name}_{section_name}_column_group.xml"), "w") as f:
                f.write(format_trajectory(clusterer.trajectory_))


if __name__ == "__main__":
    asyncio.run(main())
