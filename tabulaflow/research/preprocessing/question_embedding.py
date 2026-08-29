from pathlib import Path
from typing import ClassVar, Literal, Any
import asyncio
import io
import jinja2
import numpy as np
import numpy.typing as npt
from pydantic import BaseModel
from pydantic_ai import Embedder
from tabulaflow.agents._cache import InvalidCacheEntry, load_or_compute
from tabulaflow.agents.trace import Usage
from tabulaflow.agents.runtime import _get_agent_runtime
from tabulaflow.core._cache import atomic_write_bytes, read_bytes, stable_cache_key
from tabulaflow.research.preprocessing.registry import preprocessor_registry
from tabulaflow.research.types import NL2QDataset, NL2QTask
from tabulaflow.agents.llm import make_agent, embedding_throttle


# Revised based on https://github.com/antgroup/Agentar-Scale-SQL/blob/main/ScaleSQL/prompts/nlu.yaml
PREPROCESSING_SYSTEM_PROMPT = """
You are an AI database expert that is excellent at analyzing text-to-query questions.
You need to:
1. Identifying the database literals appeared in the question.
2. Generating a question skeleton. The question skeleton contains the question structure while ignoring the detailed database information (entity names, column names).

<guidelines>
1. Replace **all the database literals** in the question with its semantic type (e.g. "<COUNTRY>" for "Japan", "<YEAR>" for "1945").
2. Replace **all the database columns** with the placeholder <COLUMN>.
3. Keep SQL keywords such as "average", "total", "difference", "count" in the question skeleton.
4. Your final output should be the question skeleton without additional explanation.
</guidelines>

<examples>
Question: Name movie titles released in year 1945. Sort the listing by the descending order of movie popularity.
Skeleton: Name <COLUMN> released in <YEAR>. Sort the listing by the descending order of <COLUMN>.

Question: In August of 1996, how many orders were placed by the customer with the highest amount of orders?
Skeleton: In <MONTH> of <YEAR>, how many <COLUMN> were placed by the <COLUMN> with the the highest amount of <COLUMN>?

Question: Calculate the total production for each product which were supplied from Japan.
Skeleton: Calculate the total <COLUMN> for each <COLUMN> which were supplied from <COUNTRY>.

Question: Calculate the difference in the average number of low-priority orders shipped by truck in each month of 1995 and 1996.
Skeleton: Calculate the difference in the average number of <COLUMN> in each month of <YEAR> and <YEAR>.
</examples>
""".strip()


PREPROCESSING_USER_PROMPT = """
Generate the question skeleton for the following question:
{{question}}
""".strip()


class QuestionSkeleton(BaseModel):
    qid: str
    question: str
    skeleton: str


class QuestionEmbedderOutput(BaseModel):
    question_skeletons: list[QuestionSkeleton]


@preprocessor_registry.register
class QuestionEmbedder:
    name: ClassVar[str] = "question_embedder"
    input_type: ClassVar[Literal["dataset"]] = "dataset"

    def __init__(
        self,
        embedding_llm: str = "openai:text-embedding-3-small",
        preprocessing_llm: str = "openai-responses:gpt-4.1-mini",
        disable_preprocessing: bool = False,
    ):
        self.embedding_llm = embedding_llm
        self.preprocessing_llm = preprocessing_llm
        self.disable_preprocessing = disable_preprocessing

        self.embedder = Embedder(embedding_llm)
        self._usage = Usage.create(llm=embedding_llm)

    def usage(self) -> Usage:
        return self._usage

    def _cache_path(self, cache_dir: Path, dataset: NL2QDataset) -> Path:
        key = stable_cache_key(
            {
                "version": "v1",
                "dataset": dataset.name,
                "split": dataset.split,
                "databases": dataset.databases,
                "tasks": [{"qid": task.qid, "question": task.question} for task in dataset.tasks],
                "embedding_llm": self.embedding_llm,
                "preprocessing_llm": self.preprocessing_llm,
                "disable_preprocessing": self.disable_preprocessing,
            }
        )
        return cache_dir / "agent" / "question_embeddings" / f"v1@{key}.npz"

    async def _load_cache(self, path: Path) -> tuple[npt.NDArray[Any], QuestionEmbedderOutput]:
        data = await read_bytes(path)

        def decode() -> tuple[npt.NDArray[Any], QuestionEmbedderOutput]:
            try:
                with np.load(io.BytesIO(data), allow_pickle=False) as archive:
                    embeddings = archive["embeddings"]
                    metadata = QuestionEmbedderOutput.model_validate_json(str(archive["metadata"].item()))
                return embeddings, metadata
            except Exception as exc:
                raise InvalidCacheEntry(f"Invalid cache entry: {path}") from exc

        return await asyncio.to_thread(decode)

    async def _store_cache(
        self,
        path: Path,
        value: tuple[npt.NDArray[Any], QuestionEmbedderOutput],
    ) -> None:
        embeddings, metadata = value

        def encode() -> bytes:
            buffer = io.BytesIO()
            np.savez_compressed(buffer, embeddings=embeddings, metadata=metadata.model_dump_json())
            return buffer.getvalue()

        await atomic_write_bytes(path, await asyncio.to_thread(encode))

    async def _get_skeleton_async(self, question: str) -> str:
        system_prompt = jinja2.Template(PREPROCESSING_SYSTEM_PROMPT).render()
        user_prompt = jinja2.Template(PREPROCESSING_USER_PROMPT).render(question=question)
        agent = make_agent(self.preprocessing_llm, output_type=str, instructions=system_prompt)
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage, self.preprocessing_llm)
        return result.output

    async def embed_task_async(self, task: NL2QTask) -> tuple[npt.NDArray[Any], QuestionSkeleton]:
        question = task.question
        if not self.disable_preprocessing:
            skeleton = await self._get_skeleton_async(question)
        else:
            skeleton = question
        async with embedding_throttle():
            result = await self.embedder.embed_query(skeleton)
        self._usage += Usage.from_pydantic_ai_usage(result.usage, self.embedding_llm)
        return np.array(result.embeddings[0]), QuestionSkeleton(qid=task.qid, question=question, skeleton=skeleton)

    async def preprocess_async(self, dataset: NL2QDataset) -> tuple[npt.NDArray[Any], QuestionEmbedderOutput]:
        config = _get_agent_runtime().config
        return await load_or_compute(
            path=self._cache_path(config.cache_dir, dataset),
            mode=config.preprocessing_cache_mode,
            load=self._load_cache,
            compute=lambda: self._embed_dataset(dataset),
            store=self._store_cache,
        )

    async def _embed_dataset(self, dataset: NL2QDataset) -> tuple[npt.NDArray[Any], QuestionEmbedderOutput]:
        all_results = await asyncio.gather(*[self.embed_task_async(task) for task in dataset.tasks])
        return np.stack([result[0] for result in all_results]), QuestionEmbedderOutput(
            question_skeletons=[result[1] for result in all_results]
        )
