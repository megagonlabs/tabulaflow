# mypy: ignore-errors
import tabulaflow
from tabulaflow.research.types import AmbigNL2QTask
import os


def main():
    tabulaflow.configure()
    latency_1 = []
    for qid in os.listdir("data/ARCS/tasks_1"):
        if qid.endswith(".json"):
            continue
        task = AmbigNL2QTask.from_directory(os.path.join("data/ARCS/tasks_1", qid))
        latency_1.append(task.gold_queries[0].exec_result.latency_seconds)
    latency_2 = []
    for qid in os.listdir("data/ARCS/tasks_2"):
        if qid.endswith(".json"):
            continue
        task = AmbigNL2QTask.from_directory(os.path.join("data/ARCS/tasks_2", qid))
        latency_2.append(task.gold_queries[0].exec_result.latency_seconds)
    print(f"Average latency for ARCS 1: {sum(latency_1) / len(latency_1)}")
    print(f"Average latency for ARCS 2: {sum(latency_2) / len(latency_2)}")


if __name__ == "__main__":
    main()
