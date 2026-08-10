import os
from dataclasses import dataclass, field

import chainlit as cl
import logfire
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

import dashboard
import eval as ragas_eval
import ground_truths
from rag_pg import RAGPgVector, company_title, get_index, get_pool

logfire.configure()
logfire.instrument_pydantic_ai()

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DASHBOARD_TRIGGER = "__dashboard__"

INSTRUCTIONS = """
You are an assistant answering questions about YC-backed startups using the `search` tool,
which performs hybrid (keyword + vector) search over a database of companies. 
Reformulate the user's question into an effective search query before calling search -> Always call `search` before answering. 
Ground every claim in the search results;
if nothing relevant is found, say so plainly instead of guessing.
"""

PROVIDER_BY_PROFILE = {
    "GPT-5.4-mini (OpenAI)": "openai",
    "Llama 3.2 (Ollama)": "ollama",
}


@dataclass
class SearchDeps:
    index: RAGPgVector
    last_contexts: list = field(default_factory=list)


def build_agent(provider: str) -> Agent:
    if provider == "ollama":
        model = OllamaModel(
            model_name="llama3.2",
            provider=OllamaProvider(base_url=f"{OLLAMA_BASE_URL}/v1"),
        )
    else:
        model = "openai:gpt-5.4-mini"

    agent = Agent(model, deps_type=SearchDeps, instructions=INSTRUCTIONS)

    @agent.tool
    def search(ctx: RunContext[SearchDeps], query: str) -> list[dict]:
        """Hybrid (keyword + vector) search over the YC-OSS company database."""
        results = ctx.deps.index.hybrid_search(query=query, num_recs=20)
        ctx.deps.last_contexts = results
        return results

    return agent


@cl.set_chat_profiles
async def chat_profiles():
    return [
        cl.ChatProfile(
            name="GPT-5.4-mini (OpenAI)",
            markdown_description="Answers generated via OpenAI's **gpt-5.4-mini**.",
        ),
        cl.ChatProfile(
            name="Llama 3.2 (Ollama)",
            markdown_description="Answers generated via **llama3.2**, running locally through Ollama.",
        ),
    ]


@cl.set_starters
async def starters():
    items = []
    for item in ground_truths.sample_starter_items(4):
        name = company_title(item["company_id"]) or "This company"
        text = f"{name}: {item['question']}"
        label = text if len(text) <= 60 else text[:57] + "..."
        items.append(cl.Starter(label=label, message=text))
    items.append(cl.Starter(label="📊 Dashboard", message=DASHBOARD_TRIGGER))
    return items


@cl.on_chat_start
async def on_chat_start():
    profile = cl.user_session.get("chat_profile") or "GPT-5.4-mini (OpenAI)"
    provider = PROVIDER_BY_PROFILE.get(profile, "openai")

    deps = SearchDeps(index=get_index())
    agent = build_agent(provider)

    cl.user_session.set("agent", agent)
    cl.user_session.set("deps", deps)
    cl.user_session.set("provider", provider)


async def send_dashboard():
    figures = dashboard.build_dashboard_figures()
    titles = ["Query volume", "Feedback", "Faithfulness", "Relevance"]
    elements = [
        cl.Plotly(name=title, figure=fig, display="inline")
        for title, fig in zip(titles, figures)
    ]
    await cl.Message(content="Here's the current usage & quality dashboard:", elements=elements).send()


@cl.on_message
async def on_message(message: cl.Message):
    text = message.content.strip()

    if text == DASHBOARD_TRIGGER or text.lower() in ("/dashboard", "dashboard"):
        await send_dashboard()
        return

    agent: Agent = cl.user_session.get("agent")
    deps: SearchDeps = cl.user_session.get("deps")
    provider: str = cl.user_session.get("provider")

    deps.last_contexts = []
    result = await agent.run(text, deps=deps)
    answer = result.output
    input_tokens = result.usage.input_tokens
    output_tokens = result.usage.output_tokens

    reply = cl.Message(content=answer)
    await reply.send()

    contexts = deps.last_contexts
    company_id = ground_truths.company_id_for_question(text)
    reference = deps.index.reference_for_company(company_id) if company_id is not None else None

    eval_row = await ragas_eval.score_and_log(
        question=text,
        answer=answer,
        contexts=contexts,
        provider=provider,
        reference=reference,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    reply.actions = [
        cl.Action(name="feedback_like", payload={"id": eval_row["id"]}, icon="thumbs-up", tooltip="Like"),
        cl.Action(name="feedback_dislike", payload={"id": eval_row["id"]}, icon="thumbs-down", tooltip="Dislike"),
        cl.Action(name="feedback_love", payload={"id": eval_row["id"]}, icon="heart", tooltip="Love"),
    ]
    await reply.update()


async def _record_feedback(action: cl.Action, feedback: str):
    row_id = action.payload.get("id")
    pool = get_pool()
    with pool.connection() as conn:
        conn.execute(
            "UPDATE llm_evaluations SET liked_disliked = %s, feedback_at = now() WHERE id = %s",
            (feedback, row_id),
        )
        conn.commit()
    await cl.Message(content=f"Thanks for the feedback! ({feedback})").send()


@cl.action_callback("feedback_like")
async def on_feedback_like(action: cl.Action):
    await _record_feedback(action, "LIKE")


@cl.action_callback("feedback_dislike")
async def on_feedback_dislike(action: cl.Action):
    await _record_feedback(action, "DISLIKE")


@cl.action_callback("feedback_love")
async def on_feedback_love(action: cl.Action):
    await _record_feedback(action, "LOVE")
