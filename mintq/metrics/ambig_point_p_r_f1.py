from typing import ClassVar, Any
from pydantic import BaseModel
from pydantic_ai import Agent
import jinja2
from mintq.schema import StructuredAmbigNL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.schema import PredAmbiguityPoint, GoldAmbiguityPoint


_SYSTEM_PROMPT = """
You are a helpful AI database expert that can evaluate the predicted ambiguity points for a question about a database.
For each gold ambiguity point, you need to find the matching predicted ambiguity point.
- Your output should be a mapping of ambiguity point id from the gold list to the predicted list.
- An predicted ambiguity point can only be matched to one gold ambiguity point.
- An predicted ambiguity point is considered matched if the phrase is semantically equivalent.
  - Note that the interpretations do not need to match exactly, missing or extra interpretations are allowed as long as the dimension of ambiguity is the same.
- If a gold ambiguity point has no corresponding predicted ambiguity point, set the value to None.

=== START OF EXAMPLE ===
Question: List all students with high GPA from NY.
Gold ambiguity points:
[
  {
    "id": "GOLD-A",
    "phrase": "NY",
    "type": "finite",
    "interpretations": [
      "New York City",
      "New York State"
    ]
  },
  {
    "id": "GOLD-B",
    "phrase": "high GPA",
    "type": "infinite",
    "parameter_name": "gpa_threshold"
  }
]
Predicted ambiguity points:
[
  {
    "id": "PRED-A",
    "phrase": "from NY",
    "type": "finite",
    "interpretations": [
      "from New York City",
      "from New York County"
    ]
  },
]

Output:
{
  "matches": [
    {
      "gold_id": "GOLD-A",
      "pred_id": "PRED-A"
    },
    {
      "gold_id": "GOLD-B",
      "pred_id": null
    }
}
=== END OF EXAMPLE ===
"""

_USER_PROMPT = """
Question: {{question}}
Gold ambiguity points:
{{gold_aps | tojson(indent=2)}}
Predicted ambiguity points:
{{pred_aps | tojson(indent=2)}}
"""


@metric_registry.register
class AmbigPointPRF1:
    name: ClassVar[str] = "ambig_point_p_r_f1"

    def __init__(self, llm: str = "openai:gpt-4.1"):
        self.llm = llm

    def _to_simple_dict(self, ap: PredAmbiguityPoint | GoldAmbiguityPoint, id_prefix: str) -> dict[str, Any]:
        if ap.type == "finite":
            return {
                "id": f"{id_prefix}-{ap.id}",
                "phrase": ap.phrase,
                "type": "finite",
                "interpretations": ap.interpretations,
            }
        elif ap.type == "infinite":
            return {
                "id": f"{id_prefix}-{ap.id}",
                "phrase": ap.phrase,
                "type": "infinite",
                "parameter_name": ap.parameter_name,
            }
        else:
            raise ValueError(f"Unknown ambiguity point type: {ap.type}")

    async def compute_async(self, task: StructuredAmbigNL2QTaskOutput) -> dict[str, float]:
        pred_aps = [self._to_simple_dict(ap, "PRED") for ap in task.pred_ambiguity_points]
        gold_aps = [self._to_simple_dict(ap, "GOLD") for ap in task.gold_ambiguity_points]

        class Match(BaseModel):
            gold_id: str
            pred_id: str | None

        class LLMOutput(BaseModel):
            matches: list[Match]

        agent = Agent[None, LLMOutput](
            model=self.llm,
            output_type=LLMOutput,
            instructions=_SYSTEM_PROMPT,
        )
        prompt = jinja2.Template(_USER_PROMPT).render(question=task.question, gold_aps=gold_aps, pred_aps=pred_aps)
        result = await agent.run(prompt)
        n_overlap = sum(1 for match in result.output.matches if match.pred_id is not None)
        p = n_overlap / len(pred_aps)
        r = n_overlap / len(gold_aps)
        f1 = 2 * p * r / (p + r)
        return {
            "ambig_point_p": p,
            "ambig_point_r": r,
            "ambig_point_f1": f1,
        }
