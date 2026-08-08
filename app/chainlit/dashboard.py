import pandas as pd
import plotly.express as px

from rag_pg import get_pool

QUERY_VOLUME_SQL = """
SELECT date_trunc('day', created_at) AS day, count(*) AS queries
FROM llm_evaluations
GROUP BY 1
ORDER BY 1
"""

FEEDBACK_SQL = """
SELECT coalesce(liked_disliked, 'NONE') AS feedback, count(*) AS count
FROM llm_evaluations
GROUP BY 1
"""

FAITHFULNESS_SQL = """
SELECT date_trunc('day', created_at) AS day, avg(faithfulness) AS faithfulness
FROM llm_evaluations
WHERE faithfulness IS NOT NULL
GROUP BY 1
ORDER BY 1
"""

RELEVANCE_SQL = """
SELECT date_trunc('day', created_at) AS day, avg(answer_relevancy) AS answer_relevancy
FROM llm_evaluations
WHERE answer_relevancy IS NOT NULL
GROUP BY 1
ORDER BY 1
"""

ROOMS_SQL = """
SELECT coalesce(room, 'general') AS room, count(*) AS queries
FROM llm_evaluations
GROUP BY 1
ORDER BY 2 DESC
"""


def _fetch_df(sql: str) -> pd.DataFrame:
    pool = get_pool()
    with pool.connection() as conn:
        cur = conn.execute(sql)
        columns = [d.name for d in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def build_dashboard_figures() -> list:
    volume_df = _fetch_df(QUERY_VOLUME_SQL)
    fig_volume = px.bar(volume_df, x="day", y="queries", title="Query volume over time")

    feedback_df = _fetch_df(FEEDBACK_SQL)
    fig_feedback = px.bar(feedback_df, x="feedback", y="count", title="Likes vs dislikes")

    faithfulness_df = _fetch_df(FAITHFULNESS_SQL)
    fig_faithfulness = px.line(
        faithfulness_df, x="day", y="faithfulness", markers=True, title="Faithfulness over time"
    )
    fig_faithfulness.update_yaxes(range=[0, 1])

    relevance_df = _fetch_df(RELEVANCE_SQL)
    fig_relevance = px.line(
        relevance_df, x="day", y="answer_relevancy", markers=True, title="Answer relevance over time"
    )
    fig_relevance.update_yaxes(range=[0, 1])

    rooms_df = _fetch_df(ROOMS_SQL)
    fig_rooms = px.bar(rooms_df, x="room", y="queries", title="Queries by room")

    return [fig_volume, fig_feedback, fig_faithfulness, fig_relevance, fig_rooms]
