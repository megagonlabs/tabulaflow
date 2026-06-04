# mypy: ignore-errors
import asyncio
import tabulaflow
from tabulaflow.agenthub.user_simulator import UserSimulator, UserFreeTextQuestion
from tabulaflow.datahub import dataset_registry


async def main() -> None:
    tabulaflow.configure()
    dataset_loader = dataset_registry.get_class("arcs")()
    dataset = await dataset_loader.get_split_async("dev")
    user_simulator = UserSimulator.from_ambig_nl2q_task(dataset.tasks[3])  # type: ignore
    print(f"<system_prompt>{user_simulator.system_prompt}</system_prompt>")
    print(
        await user_simulator.ask_async(
            UserFreeTextQuestion(
                question="What is the name of the student with the highest score? What is the name of the student with the lowest score?"
            )
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
