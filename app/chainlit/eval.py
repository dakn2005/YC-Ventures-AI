import asyncio
import os
import uuid

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from psycopg.types.json import Json
from ragas import SingleTurnSample
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

from rag_pg import get_pool

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

# Ported from notebooks/ventures.ipynb's ragas setup cell (3f9b0b7b) -- OpenAI-generated
# answers are judged/embedded by OpenAI, Ollama-generated answers by Ollama's
# OpenAI-compatible endpoint (requires `ollama pull llama3.2` and `ollama pull all-minilm`).
_openai_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
_openai_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())

_ollama_llm = LangchainLLMWrapper(
    ChatOpenAI(model="llama3.2", base_url=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")
)
_ollama_embeddings = LangchainEmbeddingsWrapper(
    OpenAIEmbeddings(model="all-minilm", base_url=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")
)

PROVIDER_LLM = {"openai": _openai_llm, "ollama": _ollama_llm}
PROVIDER_EMBEDDINGS = {"openai": _openai_embeddings, "ollama": _ollama_embeddings}

INSERT_SQL = """
INSERT INTO llm_evaluations
    (run_id, question, answer, contexts, ground_truth, llm_provider,
     faithfulness, answer_relevancy, context_precision, context_recall)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id, run_id
"""


def build_metrics(provider: str, has_reference: bool) -> list:
    llm = PROVIDER_LLM[provider]
    embeddings = PROVIDER_EMBEDDINGS[provider]

    # fresh instances per call -- ragas metric objects hold their bound llm/embeddings,
    # and provider switches turn to turn (openai vs ollama chat profile), so these can't
    # be shared singletons the way the notebook's build_metrics() was for a single run.
    metrics = [Faithfulness(llm=llm), AnswerRelevancy(llm=llm, embeddings=embeddings)]
    if has_reference:
        metrics.append(ContextPrecision(llm=llm))
        metrics.append(ContextRecall(llm=llm))
    return metrics


async def score_and_log(
    question: str,
    answer: str,
    contexts: list[dict],
    provider: str,
    reference: str | None = None,
) -> dict:
    context_strs = [f"{c['title']}: {c['content']}" for c in contexts]

    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=context_strs,
        reference=reference,
    )

    metrics = build_metrics(provider, has_reference=reference is not None)
    scores = await asyncio.gather(*(m.single_turn_ascore(sample) for m in metrics))
    scores_by_name = dict(zip((type(m).__name__ for m in metrics), scores))

    faithfulness = scores_by_name.get("Faithfulness")
    answer_relevancy = scores_by_name.get("AnswerRelevancy")
    context_precision = scores_by_name.get("ContextPrecision")
    context_recall = scores_by_name.get("ContextRecall")

    run_id = uuid.uuid4()
    pool = get_pool()
    with pool.connection() as conn:
        row = conn.execute(
            INSERT_SQL,
            (
                str(run_id),
                question,
                answer,
                Json(context_strs),
                reference,
                provider,
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ),
        ).fetchone()
        conn.commit()

    return {
        "id": row[0],
        "run_id": row[1],
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }
