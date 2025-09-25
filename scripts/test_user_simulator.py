import asyncio
from mintq.agenthub.user_simulator import UserSimulator
from mintq.datahub import get_dataset_loader


async def main() -> None:
    dataset_loader = get_dataset_loader("arcs")
    dataset = await dataset_loader.get_split_async("dev")
    user_simulator = UserSimulator.from_ambig_nl2q_task(dataset.tasks[3])
    print(f"<system_prompt>{user_simulator.system_prompt}</system_prompt>")
    print(
        await user_simulator.ask_async(
            "What is the name of the student with the highest score? What is the name of the student with the lowest score?"
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
