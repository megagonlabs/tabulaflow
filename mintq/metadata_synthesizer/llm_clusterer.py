import litellm
import jinja2
from typing import Protocol, Callable, Any
from pydantic import BaseModel
from dataclasses import dataclass
import json
import logging
import random
from mintq.schema import Trajectory, UserMessage, AssistantMessage

logger = logging.getLogger(__name__)


class ItemWithUniqueName(Protocol):
    name: str


class Cluster(BaseModel):
    name: str
    description: str | None
    item_names: list[str]


class MergeCluster(BaseModel):
    clusters_to_merge: list[str]
    new_name: str
    new_description: str | None


class UpdateCluster(BaseModel):
    old_name: str
    new_name: str
    new_description: str | None


class CreateCluster(BaseModel):
    name: str
    description: str | None


class Assignment(BaseModel):
    item_name: str
    cluster_name: str


class LLMOutput(BaseModel):
    merge_cluster_actions: list[MergeCluster]
    update_cluster_actions: list[UpdateCluster]
    create_cluster_actions: list[CreateCluster]
    assignments: list[Assignment]


LLM_CLUSTERER_PROMPT = """
You are an intelligent AI cluster manager.
- You will receive a current list of clusters along with a list of new items to be integrated.
- Your task is to maintain and update the clusters appropriately by creating new clusters, merging
  existing ones, or modifying the name or description of existing clusters as needed to maintain consistency.
- Ensure that a cluster exists before assigning any item to it.


Clustering instructions:
{{instruction}}

Current clusters:
{{current_clusters}}

New items:
{{new_items}}

Result:
""".strip()


class ClusterStore:
    def __init__(self):
        self._descriptions: dict[str, str | None] = {}
        self._items: dict[str, list[int]] = {}

    def create_cluster(self, action: CreateCluster) -> None:
        if action.name in self._descriptions:
            self._descriptions[action.name] = action.description
        else:
            self._descriptions[action.name] = action.description
            self._items[action.name] = []

    def update_cluster(self, action: UpdateCluster) -> None:
        self._descriptions.pop(action.old_name)
        self._descriptions[action.new_name] = action.new_description
        self._items[action.new_name] = self._items.pop(action.old_name)

    def merge_clusters(self, action: MergeCluster) -> None:
        merged_items = []
        for name in action.clusters_to_merge:
            merged_items += self._items.pop(name)
            self._descriptions.pop(name)
        self._descriptions[action.new_name] = action.new_description
        self._items[action.new_name] = merged_items

    def assign_item(self, item_name: str, cluster_name: str) -> None:
        self._items[cluster_name].append(item_name)

    @property
    def clusters(self) -> list[Cluster]:
        return [
            Cluster(name=name, description=description, item_names=self._items[name])
            for name, description in self._descriptions.items()
        ]


@dataclass
class LLMClusterer:
    llm: str
    instruction: str
    format_fn: Callable[[str, Any], str]
    batch_size: int = 10
    temperature: float = 0.0
    trajectory_: Trajectory | None = None

    async def cluster_async(self, item_names: list[str], items: list[Any]) -> list[Cluster]:
        if len(item_names) != len(set(item_names)):
            raise ValueError("Items must have unique names")

        store = ClusterStore()

        self.trajectory_ = Trajectory(messages=[])

        local_random = random.Random(42)

        for i in range(0, len(items), self.batch_size):
            names = item_names[i : i + self.batch_size]
            batch = items[i : i + self.batch_size]

            current_clusters = json.dumps(
                [
                    {
                        "name": c.name,
                        "description": c.description,
                        "sample_items": local_random.sample(c.item_names, min(len(c.item_names), 3)),
                    }
                    for c in store.clusters
                ],
                indent=2,
            )

            new_items = "\n\n".join(
                f"#{k}\n{self.format_fn(name, item)}" for k, (name, item) in enumerate(zip(names, batch))
            )
            prompt = jinja2.Template(LLM_CLUSTERER_PROMPT).render(
                instruction=self.instruction,
                current_clusters=current_clusters,
                new_items=new_items,
            )
            self.trajectory_.messages.append(UserMessage(content=prompt))

            response = await litellm.acompletion(
                model=self.llm,
                messages=[{"role": "system", "content": prompt}],
                response_format=LLMOutput,
                temperature=self.temperature,
            )
            self.trajectory_.messages.append(AssistantMessage(content=response.choices[0].message.content))
            output = LLMOutput.model_validate_json(response.choices[0].message.content)
            try:
                assert len(output.assignments) == len(batch)
                for merge in output.merge_cluster_actions:
                    store.merge_clusters(merge)
                for update in output.update_cluster_actions:
                    store.update_cluster(update)
                for new_cluster in output.create_cluster_actions:
                    store.create_cluster(new_cluster)
                for assignment in output.assignments:
                    store.assign_item(assignment.item_name, assignment.cluster_name)
            except Exception:
                logger.error(f"<prompt>{prompt}</prompt>")
                logger.error(f"<output>{output.model_dump_json(indent=2)}</output>")
                raise

        return store.clusters
