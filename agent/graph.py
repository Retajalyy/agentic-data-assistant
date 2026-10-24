"""LangGraph agent: LLM node <-> tool node loop with conversation memory."""
import time
import uuid
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from agent import config
from agent.logging_utils import JsonlCallback, _emit, setup_logging
from agent.tools.api_tool import get_exchange_rate
from agent.tools.db_tool import describe_database, query_database

TOOLS = [describe_database, query_database, get_exchange_rate]

SYSTEM_PROMPT = """You are a data analyst assistant for a sales database (all amounts in USD).
Rules:
- Inspect the schema with describe_database before writing SQL.
- Use query_database for any number about the data; never guess figures.
- Use get_exchange_rate for currency conversion or exchange-rate questions.
- Break multi-part questions into steps: query first, then convert/compute.
- You cannot modify data. If asked to, refuse and explain the database is read-only.
- Give a concise final answer and state key numbers and the assumptions you used."""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_llm():
    """Pick the LLM provider from LLM_PROVIDER ('anthropic' or 'google')."""
    if config.PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=config.MODEL, temperature=0, max_retries=5)
    if config.PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=config.MODEL, temperature=0, max_retries=5)
    raise ValueError(f"Unknown LLM_PROVIDER: {config.PROVIDER}")


def build_agent():
    llm = build_llm().bind_tools(TOOLS)

    def call_model(state: AgentState):
        return {"messages": [llm.invoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # tool calls -> "tools", else END
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=MemorySaver())


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))


def ask(agent, question: str, thread_id: str | None = None) -> dict:
    """Run one question. Returns answer, tools used (in order), step count and latency."""
    setup_logging()
    thread_id = thread_id or str(uuid.uuid4())
    start = time.perf_counter()
    result = agent.invoke(
        {"messages": [HumanMessage(question)]},
        config={
            "configurable": {"thread_id": thread_id},
            "callbacks": [JsonlCallback()],
            "recursion_limit": config.MAX_STEPS * 2,
        },
    )
    msgs = result["messages"]
    tools_used = [tc["name"] for m in msgs if isinstance(m, AIMessage) for tc in m.tool_calls]
    out = {
        "question": question,
        "answer": _text(msgs[-1].content),
        "tools_used": tools_used,
        "latency_s": round(time.perf_counter() - start, 2),
    }
    _emit("question_done", **{k: v for k, v in out.items() if k != "answer"})
    return out
