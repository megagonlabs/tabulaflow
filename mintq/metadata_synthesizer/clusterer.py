import litellm
import jinja2
from typing import Protocol, Callable, Any
import re
import collections
from pydantic import BaseModel
from dataclasses import dataclass, field
import json
import logging
import random
import datetime
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
    step1_merge_cluster_actions: list[MergeCluster]
    step2_update_cluster_actions: list[UpdateCluster]
    step3_create_cluster_actions: list[CreateCluster]
    step4_assignments: list[Assignment]


class BaseClusterer(Protocol):
    trajectory_: Trajectory | None

    async def cluster_async(self, item_names: list[str], items: list[Any]) -> list[Cluster]: ...


LLM_CLUSTERER_PROMPT = """
You are a smart AI responsible for managing and organizing clusters.
- You will be provided with a current list of clusters and a list of new items that need to be integrated.
- For each new item, first evaluate the existing clusters to determine the best placement:
  - If the item fits:
    - Consider whether merging multiple existing clusters would improve consistency and reduce overly fine-grained clustering. If so, merge them.
    - Otherwise, incorporate the item into the most suitable existing cluster, updating the cluster's name and/or description as needed.
  - If the item does not fit into any existing cluster, create a new cluster for it.
- After the clusters are updated, assign each item to the appropriate cluster.
- Your goal is to maintain consistency and ensure a well-structured cluster organization.

=== Instructions ===
{{instruction}}
=== End ===

=== Current clusters ===
{{current_clusters}}
=== End ===

=== New items to be integrated ===
{{new_items}}
=== End ===

Result:
""".strip()


class ClusterStore:
    def __init__(self, ignore_cluster_not_exists: bool = True):
        self.ignore_cluster_not_exists = ignore_cluster_not_exists

        self._descriptions: dict[str, str | None] = {}
        self._items: dict[str, list[str]] = {}

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
            if name not in self._descriptions:
                if self.ignore_cluster_not_exists:
                    continue
                else:
                    raise ValueError(f"Cluster {name} does not exist")
            merged_items += self._items.pop(name)
            self._descriptions.pop(name)
        self._descriptions[action.new_name] = action.new_description
        self._items[action.new_name] = merged_items

    def assign_item(self, item_name: str, cluster_name: str) -> None:
        if cluster_name not in self._descriptions:
            if self.ignore_cluster_not_exists:
                self.create_cluster(CreateCluster(name=cluster_name, description=None))
            else:
                raise ValueError(f"Cluster {cluster_name} does not exist")
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
                f"#{k + 1}\n{self.format_fn(name, item)}" for k, (name, item) in enumerate(zip(names, batch))
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
                assert len(output.step4_assignments) == len(batch)
                for merge in output.step1_merge_cluster_actions:
                    store.merge_clusters(merge)
                for update in output.step2_update_cluster_actions:
                    store.update_cluster(update)
                for new_cluster in output.step3_create_cluster_actions:
                    store.create_cluster(new_cluster)
                for assignment in output.step4_assignments:
                    store.assign_item(assignment.item_name, assignment.cluster_name)
            except Exception:
                logger.error(f"<prompt>{prompt}</prompt>")
                logger.error(f"<output>{output.model_dump_json(indent=2)}</output>")
                raise

        return store.clusters


class BaseClusterFunc(Protocol):
    def extract(self, name: str) -> tuple[str, str | None]: ...

    def summarize(self, variations: list[str]) -> str | None: ...


class IndexAffixClusterFunc:
    def extract(self, name: str) -> tuple[str, int | None]:
        match = re.search(r"\d+", name)
        if not match:
            return name, None
        pattern = re.sub(r"\d+", "{#}", name, count=1)
        return pattern, int(match.group())

    def summarize(self, indexes: list[int]) -> str | None:
        indexes = sorted(indexes)
        a = indexes[0]
        b = indexes[-1]
        if indexes != list(range(a, b + 1)):
            return None
        return f"# from {a} to {b}"


class YearAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, int | None]:
        match = re.search(r"(?<!\d)\d{4}(?!\d)", name)
        if not match:
            return name, None
        year = int(match.group())
        if year < 1000 or year > datetime.datetime.now().year:
            return name, None
        pattern = re.sub(r"\d{4}", "{YEAR}", name, count=1)
        return pattern, year

    def summarize(self, years: list[int]) -> str | None:
        years = sorted(years)
        a = years[0]
        b = years[-1]
        years_set = set(years)
        missing_years = [y for y in range(a, b + 1) if y not in years_set]
        if len(missing_years) / (b - a + 1) > self.max_missing_ratio:
            return None
        return f"YEAR from {a} to {b} except {', '.join([str(y) for y in missing_years])}"


@dataclass
class YearMonthAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, datetime.datetime | None]:
        match = re.search(r"(?<!\d)\d{4}\d{2}(?!\d)", name)
        if not match:
            return name, None
        year = int(match.group()[:4])
        month = int(match.group()[4:])
        day = 1
        if year < 1000 or datetime.date(year, month, day) > datetime.date.today():
            return name, None
        pattern = re.sub(r"\d{4}\d{2}", "{YYYYMM}", name, count=1)
        return pattern, datetime.date(year, month, day)

    def summarize(self, dates: list[datetime.date]) -> str | None:
        dates = sorted(dates)
        a = dates[0]
        b = dates[-1]
        dates_set = set(dates)
        missing_dates = []
        current = a
        while current <= b:
            if current not in dates_set:
                missing_dates.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        if len(missing_dates) / ((b - a).days + 1) > self.max_missing_ratio:
            return None
        return f"YYYYMM from {a.strftime('%Y%m')} to {b.strftime('%Y%m')} except {', '.join([d.strftime('%Y%m') for d in missing_dates])}"


@dataclass
class AffixClusterer:
    cluster_funcs: list[BaseClusterFunc] = field(
        default_factory=lambda: [YearAffixClusterFunc(), IndexAffixClusterFunc()]
    )
    minimum_cluster_size: int = 5
    trajectory_: None = None

    async def cluster_async(self, item_names: list[str], items: list[Any]) -> list[Cluster]:
        if len(item_names) != len(set(item_names)):
            raise ValueError("Items must have unique names")

        remaining = set(item_names)
        res = []
        for func in self.cluster_funcs:
            groups = collections.defaultdict(list)
            for name in remaining:
                pattern, variation = func.extract(name)
                groups[pattern].append((name, variation))

            for pattern in groups:
                if len(groups[pattern]) >= self.minimum_cluster_size:
                    summary = func.summarize([v for _, v in groups[pattern]])
                    if summary is not None:
                        names = [n for n, _ in groups[pattern]]
                        res.append(Cluster(name=pattern, description=summary, item_names=names))
                        remaining -= set(names)

        for name in remaining:
            res.append(Cluster(name=name, description=None, item_names=[name]))

        return res
