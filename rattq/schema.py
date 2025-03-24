from pydantic import BaseModel
from typing import Optional, Dict, Union


class NL2QSample(BaseModel):
    qid: str
    language: str
    db: str
    question: str
    evidence: Optional[str] = None
    gold_query: str
    pred_query: Optional[str] = None
    metrics: Dict[str, Union[float, int]] = {}
