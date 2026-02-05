from typing import ClassVar, Literal, Any
import asyncio
import jinja2
import numpy as np
import numpy.typing as npt
from pydantic import BaseModel
from pydantic_ai import Agent, Embedder
from mintq.preprocessors.base import CachedPreprocessorMixin, preprocessor_registry, CacheableResult
from mintq.schema import NL2QDataset, Usage, NL2QTask


# Revised based on https://github.com/antgroup/Agentar-Scale-SQL/blob/main/ScaleSQL/prompts/nlu.yaml
PREPROCESSING_SYSTEM_PROMPT = """
You are a AI database expert that is excellent in analysing text-to-query questions.
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
class QuestionEmbedder(CachedPreprocessorMixin[tuple[npt.NDArray[Any], QuestionEmbedderOutput]]):
    name: ClassVar[str] = "question_embedder"
    input_type: ClassVar[Literal["dataset"]] = "dataset"
    output_type: ClassVar[type[CacheableResult]] = tuple[npt.NDArray[Any], QuestionEmbedderOutput]

    def __init__(
        self,
        embedding_llm: str = "openai:text-embedding-3-small",
        preprocessing_llm: str = "openai-responses:gpt-4.1-mini",
        disable_preprocessing: bool = False,
    ):
        self.embedding_llm = embedding_llm
        self.preprocessing_llm = preprocessing_llm
        self.disable_preprocessing = disable_preprocessing

        self.embedding_embedder = Embedder(embedding_llm)
        self._usage = Usage.create(llm=embedding_llm)

    def usage(self) -> Usage:
        return self._usage

    async def _preprocess(self, question: str) -> str:
        system_prompt = jinja2.Template(PREPROCESSING_SYSTEM_PROMPT).render()
        user_prompt = jinja2.Template(PREPROCESSING_USER_PROMPT).render(question=question)
        agent = Agent[None, str](
            self.preprocessing_llm,
            output_type=str,
            instructions=system_prompt,
        )
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.preprocessing_llm)
        return result.output

    async def _embed(self, task: NL2QTask) -> tuple[npt.NDArray[Any], QuestionSkeleton]:
        question = task.question
        if not self.disable_preprocessing:
            skeleton = await self._preprocess(question)
        else:
            skeleton = question
        result = await self.embedding_embedder.embed_query(skeleton)
        self._usage += Usage.from_pydantic_ai_usage(result.usage, self.embedding_llm)
        return np.array(result.embeddings), QuestionSkeleton(qid=task.qid, question=question, skeleton=skeleton)

    async def _preprocess_impl_async(self, dataset: NL2QDataset) -> tuple[npt.NDArray[Any], QuestionEmbedderOutput]:
        all_results = await asyncio.gather(*[self._embed(task) for task in dataset.tasks])
        return np.stack([result[0] for result in all_results]), QuestionEmbedderOutput(
            question_skeletons=[result[1] for result in all_results]
        )
