import json
from re import I
from typing import ClassVar, Any
from pydantic import BaseModel
from pydantic_ai import Agent
import jinja2
from mintq.schema import StructuredAmbigNL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.schema import PredAmbiguityPoint, GoldAmbiguityPoint


AMBIG_POINT_MATCHING_SYSTEM_PROMPT = """
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

AMBIG_POINT_MATCHING_USER_PROMPT = """
Question: {{question}}
Gold ambiguity points:
{{gold_aps}}
Predicted ambiguity points:
{{pred_aps}}
"""


INTERPRETATION_MATCHING_SYSTEM_PROMPT = """
You are a helpful AI database expert that can evaluate the predicted interpretations for an ambiguity point in a question about a database.
For each gold interpretation, you need to find the matching predicted interpretation.
- Your output should be a mapping of interpretation id from the gold list to the predicted list.
- An predicted interpretation can only be matched to one gold interpretation.
- An predicted interpretation is considered matched if the interpretation is semantically equivalent.
- If a gold interpretation has no corresponding predicted interpretation, set the value to None.

=== START OF EXAMPLE ===
Question: List all students with high GPA from NY.
Ambiguity phrase: "NY"
Gold interpretations:
[
  {
    "id": "GOLD-0",
    "interpretation": "New York City"
  },
  {
    "id": "GOLD-1",
    "interpretation": "New York State"
  }
]
Predicted ambiguity points:
[
  {
    "id": "PRED-0",
    "interpretation": "from New York City"
  },
  {
    "id": "PRED-1",
    "interpretation": "from New York County"
  }
]

Output:
{
  "matches": [
    {
      "gold_id": "GOLD-0",
      "pred_id": "PRED-0"
    },
    {
      "gold_id": "GOLD-1",
      "pred_id": null
    }
}
=== END OF EXAMPLE ===
"""

INTERPRETATION_MATCHING_USER_PROMPT = """
Question: {{question}}
Ambiguity phrase: "{{phrase}}"
Gold interpretations:
{{gold_interpretations}}
Predicted interpretations:
{{pred_interpretations}}
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

    def _p_r_f1(self, n_overlap: int, n_pred: int, n_gold: int) -> tuple[float, float, float]:
        p = n_overlap / n_pred if n_pred > 0 else 0.0
        r = n_overlap / n_gold if n_gold > 0 else 0.0
        f1 = 2 * p * r / (p + r) if p + r > 0 else 0.0
        return p, r, f1

    async def compute_async(self, task: StructuredAmbigNL2QTaskOutput) -> dict[str, float]:
        pred_aps = [self._to_simple_dict(ap, "PRED") for ap in task.pred_ambiguity_points]
        gold_aps = [self._to_simple_dict(ap, "GOLD") for ap in task.gold_ambiguity_points]

        # If all phrases match exactly, return perfect score
        pred_phrases = sorted([(ap["phrase"], ap["type"]) for ap in pred_aps])
        gold_phrases = sorted([(ap["phrase"], ap["type"]) for ap in gold_aps])
        if pred_phrases == gold_phrases:
            return {
                "ambig_point_p": 1.0,
                "ambig_point_r": 1.0,
                "ambig_point_f1": 1.0,
            }

        class Match(BaseModel):
            gold_id: str
            pred_id: str | None

        class LLMOutput(BaseModel):
            matches: list[Match]

        agent = Agent[None, LLMOutput](
            model=self.llm,
            output_type=LLMOutput,
            instructions=AMBIG_POINT_MATCHING_SYSTEM_PROMPT,
        )
        prompt = jinja2.Template(AMBIG_POINT_MATCHING_USER_PROMPT).render(
            question=task.question, gold_aps=json.dumps(gold_aps, indent=2), pred_aps=json.dumps(pred_aps, indent=2)
        )
        result = await agent.run(prompt)
        matches = [match for match in result.output.matches if match.pred_id is not None]
        ambig_point_p, ambig_point_r, ambig_point_f1 = self._p_r_f1(len(matches), len(pred_aps), len(gold_aps))

        p_list = []
        r_list = []
        f1_list = []
        for match in matches:
            pred_ap = next(ap for ap in pred_aps if ap["id"] == match.pred_id)
            gold_ap = next(ap for ap in gold_aps if ap["id"] == match.gold_id)
            if not (pred_ap["type"] == "finite" and gold_ap["type"] == "finite"):
                continue

            gold_interpretations = [
                {"id": f"GOLD-{i}", "interpretation": interpretation}
                for i, interpretation in enumerate(gold_ap["interpretations"])
            ]
            pred_interpretations = [
                {"id": f"PRED-{i}", "interpretation": interpretation}
                for i, interpretation in enumerate(pred_ap["interpretations"])
            ]

            agent = Agent[None, LLMOutput](
                model=self.llm,
                output_type=LLMOutput,
                instructions=INTERPRETATION_MATCHING_SYSTEM_PROMPT,
            )
            prompt = jinja2.Template(INTERPRETATION_MATCHING_USER_PROMPT).render(
                question=task.question,
                phrase=gold_ap["phrase"],
                gold_interpretations=json.dumps(gold_interpretations, indent=2),
                pred_interpretations=json.dumps(pred_interpretations, indent=2),
            )
            print(prompt)
            result = await agent.run(prompt)
            print(result.output)
            matches = [match for match in result.output.matches if match.pred_id is not None]
            p, r, f1 = self._p_r_f1(len(matches), len(pred_ap["interpretations"]), len(gold_ap["interpretations"]))
            p_list.append(p)
            r_list.append(r)
            f1_list.append(f1)

        interpretation_p = sum(p_list) / len(p_list) if p_list else 0.0
        interpretation_r = sum(r_list) / len(r_list) if r_list else 0.0
        interpretation_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0
        return {
            "ambig_point_p": ambig_point_p,
            "ambig_point_r": ambig_point_r,
            "ambig_point_f1": ambig_point_f1,
            "interpretation_p": interpretation_p,
            "interpretation_r": interpretation_r,
            "interpretation_f1": interpretation_f1,
        }
