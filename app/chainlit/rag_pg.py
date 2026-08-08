import os
from functools import lru_cache

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from psycopg_pool import ConnectionPool
from sentence_transformers import SentenceTransformer

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "relational_db")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "ventures_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")

CONNINFO = (
    f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB} "
    f"user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
)


class RAGPgVector:
    """Ported from notebooks/ventures.ipynb (cell 645a2d15).

    Two differences from the notebook version, since this runs as a live
    multi-user service instead of a single-user notebook:
    - text_search's tsquery input and LIMIT are passed as query parameters
      instead of interpolated into the SQL string.
    - a psycopg_pool.ConnectionPool is used instead of one shared connection,
      since concurrent chat sessions call hybrid_search concurrently.
    """

    def __init__(self, embedder, pool: ConnectionPool):
        self.embedder = embedder
        self.pool = pool

    @staticmethod
    def vec_to_str(vector) -> str:
        return "[" + ",".join(str(x) for x in vector) + "]"

    def text_search(self, query: str, num_results: int = 5, sampling: bool = False) -> list[dict]:
        words = word_tokenize(query)
        stop_words = set(stopwords.words("english"))
        filtered_keywords = [w for w in words if w.isalnum() and w.lower() not in stop_words]
        table = "yc_oss_sample_records" if sampling else "yc_oss_fulltext"
        tsquery_input = " or ".join(filtered_keywords) or query

        sql = f"""
            SELECT
                    company_id,
                    title,
                    content,
                    ts_rank(search_vector, query) AS rank
            FROM
                    {table},
                    websearch_to_tsquery('english', %s) AS query
            WHERE search_vector @@ query
            ORDER BY rank desc
            LIMIT %s
        """

        with self.pool.connection() as conn:
            rows = conn.execute(sql, (tsquery_input, num_results)).fetchall()

        return [
            {"company_id": r[0], "title": r[1], "content": r[2], "match_words_frequency_rank": r[3]}
            for r in rows
        ]

    def vector_search(self, query: str, num_results: int = 5, sampling: bool = False) -> list[dict]:
        query_vector = self.embedder.encode(query)
        query_str = self.vec_to_str(query_vector)
        table = "yc_oss_sample_records" if sampling else "yc_oss_embeddings"

        sql = f"""
            SELECT
                company_id,
                title,
                content,
                1 - (embedding <=> %s::vector) AS cosine_similarity
            FROM {table}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        with self.pool.connection() as conn:
            rows = conn.execute(sql, (query_str, query_str, num_results)).fetchall()

        return [
            {"company_id": r[0], "title": r[1], "content": r[2], "cosine_similarity": r[3]}
            for r in rows
        ]

    def _rrf(self, result_lists: list[list[dict]], k: int = 60, num_results: int = 5) -> list[dict]:
        scores = {}
        docs = {}

        for results in result_lists:
            for rank, doc in enumerate(results):
                key = doc["company_id"]
                scores[key] = scores.get(key, 0) + 1 / (k + rank)
                docs[key] = doc

        ranked = sorted(scores, key=scores.get, reverse=True)
        return [docs[key] for key in ranked[:num_results]]

    def hybrid_search(self, query: str, num_recs: int = 5, sampling: bool = False) -> list[dict]:
        text_results = self.text_search(query, num_results=num_recs, sampling=sampling)
        vector_results = self.vector_search(query, num_results=num_recs, sampling=sampling)

        return self._rrf([text_results, vector_results], num_results=num_recs)

    def reference_for_company(self, company_id: int) -> str | None:
        sql = """
            SELECT title, content FROM yc_oss_sample_records WHERE company_id = %s
            UNION ALL
            SELECT title, content FROM yc_oss_fulltext WHERE company_id = %s
            LIMIT 1
        """
        with self.pool.connection() as conn:
            row = conn.execute(sql, (company_id, company_id)).fetchone()

        if row is None:
            return None
        title, content = row
        return f"{title}: {content}"


def list_rooms() -> list[str]:
    """Distinct room names seen so far, for suggesting existing rooms at chat start."""
    sql = "SELECT DISTINCT room FROM llm_evaluations WHERE room IS NOT NULL ORDER BY room"
    try:
        with get_pool().connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [r[0] for r in rows]
    except Exception:
        # llm_evaluations/room may not exist yet on a fresh DB -- don't block chat start.
        return []


@lru_cache(maxsize=1)
def get_pool() -> ConnectionPool:
    pool = ConnectionPool(conninfo=CONNINFO, min_size=1, max_size=10, open=True)
    return pool


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def get_index() -> RAGPgVector:
    return RAGPgVector(embedder=get_embedder(), pool=get_pool())
