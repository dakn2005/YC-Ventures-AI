import os
import random
from functools import lru_cache

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

CSV_FILES = [
    os.path.join(DATA_DIR, "ground_truths_by_openai.csv"),
    os.path.join(DATA_DIR, "ground_truths_by_ollama.csv"),
]


@lru_cache(maxsize=1)
def _question_to_company_id() -> dict[str, int]:
    lookup: dict[str, int] = {}
    for path in CSV_FILES:
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        for row in df.to_dict(orient="records"):
            lookup[row["question"]] = row["company_id"]
    return lookup


def company_id_for_question(question: str) -> int | None:
    lookup = _question_to_company_id()
    if question in lookup:
        return lookup[question]
    # starters prefix the raw question with "<company name>: ", so a suffix
    # match recovers the company_id for those (see app.py's starters()).
    for raw_question, company_id in lookup.items():
        if question.endswith(raw_question):
            return company_id
    return None


def sample_starter_items(n: int = 4) -> list[dict]:
    items = [{"question": q, "company_id": cid} for q, cid in _question_to_company_id().items()]
    if not items:
        return []
    return random.sample(items, min(n, len(items)))
