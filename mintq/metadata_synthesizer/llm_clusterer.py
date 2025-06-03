import litellm
import jinja2
from typing import Protocol, Callable, Any
from pydantic import BaseModel
from dataclasses import dataclass
import json


class ItemWithUniqueName(Protocol):
    name: str


class Cluster(BaseModel):
    name: str
    description: str
    item_indexes: list[int]


class UpdateCluster(BaseModel):
    old_name: str
    new_name: str
    new_description: str


class CreateCluster(BaseModel):
    name: str
    description: str


class Assignment(BaseModel):
    item_name: str
    cluster_name: str


class LLMOutput(BaseModel):
    updated_clusters: list[UpdateCluster]
    new_clusters: list[CreateCluster]
    assignments: list[Assignment]


USER_PROMPT = """
Current clusters:
{{current_clusters}}

New items:
{{new_items}}

Output:
""".strip()


@dataclass
class LLMClusterer:
    llm: str
    instruction: str
    format_fn: Callable[[str, Any], str]
    batch_size: int = 20
    temperature: float = 0.0

    async def cluster_async(self, item_names: list[str], items: list[Any]) -> list[Cluster]:
        if len(item_names) != len(set(item_names)):
            raise ValueError("Items must have unique names")

        cluster_descriptions: dict[str, str] = {}
        cluster_items: dict[str, list[int]] = {}

        name2idx = {name: i for i, name in enumerate(item_names)}

        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]

            new_items = "\n\n".join(f"###{i}\n{self.format_fn(item_names[i], item)}" for i, item in enumerate(batch))
            user_prompt = jinja2.Template(USER_PROMPT).render(
                current_clusters=json.dumps(cluster_descriptions, indent=2),
                new_items=new_items,
            )
            response = await litellm.acompletion(
                model=self.llm,
                messages=[{"role": "system", "content": self.instruction}, {"role": "user", "content": user_prompt}],
                response_format=LLMOutput,
                temperature=self.temperature,
            )
            output = LLMOutput.model_validate_json(response.choices[0].message.content)

            for update in output.updated_clusters:
                cluster_descriptions.pop(update.old_name)
                cluster_descriptions[update.new_name] = update.new_description
                cluster_items[update.new_name] = cluster_items.pop(update.old_name)

            for new_cluster in output.new_clusters:
                cluster_descriptions[new_cluster.name] = new_cluster.description
                cluster_items[new_cluster.name] = []

            for assignment in output.assignments:
                cluster_items[assignment.cluster_name].append(name2idx[assignment.item_name])

        return [
            Cluster(name=name, description=description, item_indexes=cluster_items[name])
            for name, description in cluster_descriptions.items()
        ]
