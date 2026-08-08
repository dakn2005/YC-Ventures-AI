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
    return _question_to_company_id().get(question)


def sample_starter_questions(n: int = 4) -> list[str]:
    questions = list(_question_to_company_id().keys())
    if not questions:
        return []
    return random.sample(questions, min(n, len(questions)))
