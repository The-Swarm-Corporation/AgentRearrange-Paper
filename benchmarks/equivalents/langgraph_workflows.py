"""
LangGraph reference implementations of the six canonical workflows
plus their "+ parallel review" variants. Same surface as ar_workflows.

LangGraph is significantly more verbose: each workflow needs a TypedDict
state schema, explicit nodes, explicit edges, and a compile step.
"""

from __future__ import annotations
from typing import Callable, TypedDict, Annotated
import operator

try:
    from langgraph.graph import StateGraph, START, END
    from langchain_openai import ChatOpenAI

    _HAS_LG = True
except Exception:
    _HAS_LG = False


def _llm():
    return ChatOpenAI(model="gpt-4o-mini")


# -------- 1. linear --------
def linear_v1() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str

    g = StateGraph(S)
    g.add_node("a", lambda s: {"msg": _llm().invoke(s["msg"]).content})
    g.add_node("b", lambda s: {"msg": _llm().invoke(s["msg"]).content})
    g.add_node("c", lambda s: {"msg": _llm().invoke(s["msg"]).content})
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x})["msg"]


def linear_v2_with_review() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        review: Annotated[list, operator.add]

    g = StateGraph(S)
    g.add_node("a", lambda s: {"msg": _llm().invoke(s["msg"]).content})
    g.add_node("b", lambda s: {"msg": _llm().invoke(s["msg"]).content, "review": []})
    g.add_node("reviewer", lambda s: {"review": [_llm().invoke(s["msg"]).content]})
    g.add_node(
        "c", lambda s: {"msg": _llm().invoke(s["msg"] + str(s["review"])).content}
    )
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", "reviewer")
    g.add_edge("b", "c")
    g.add_edge("reviewer", "c")
    g.add_edge("c", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "review": []})["msg"]


# -------- 2. fan-out --------
def fanout_v1() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        out: Annotated[list, operator.add]

    g = StateGraph(S)
    g.add_node("root", lambda s: {"msg": _llm().invoke(s["msg"]).content, "out": []})
    g.add_node("b", lambda s: {"out": [_llm().invoke(s["msg"]).content]})
    g.add_node("c", lambda s: {"out": [_llm().invoke(s["msg"]).content]})
    g.add_node("d", lambda s: {"out": [_llm().invoke(s["msg"]).content]})
    g.add_edge(START, "root")
    g.add_edge("root", "b")
    g.add_edge("root", "c")
    g.add_edge("root", "d")
    g.add_edge("b", END)
    g.add_edge("c", END)
    g.add_edge("d", END)
    app = g.compile()
    return lambda x: str(app.invoke({"msg": x, "out": []})["out"])


def fanout_v2_with_review() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        out: Annotated[list, operator.add]

    g = StateGraph(S)
    g.add_node("root", lambda s: {"msg": _llm().invoke(s["msg"]).content, "out": []})
    g.add_node("b", lambda s: {"out": [_llm().invoke(s["msg"]).content]})
    g.add_node("c", lambda s: {"out": [_llm().invoke(s["msg"]).content]})
    g.add_node("d", lambda s: {"out": [_llm().invoke(s["msg"]).content]})
    g.add_node("reviewer", lambda s: {"out": [_llm().invoke(s["msg"]).content]})
    g.add_edge(START, "root")
    g.add_edge("root", "b")
    g.add_edge("root", "c")
    g.add_edge("root", "d")
    g.add_edge("root", "reviewer")
    g.add_edge("b", END)
    g.add_edge("c", END)
    g.add_edge("d", END)
    g.add_edge("reviewer", END)
    app = g.compile()
    return lambda x: str(app.invoke({"msg": x, "out": []})["out"])


# -------- 3. fan-in --------
def fanin_v1() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        results: Annotated[list, operator.add]
        final: str

    g = StateGraph(S)
    g.add_node("a", lambda s: {"results": [_llm().invoke(s["msg"]).content]})
    g.add_node("b", lambda s: {"results": [_llm().invoke(s["msg"]).content]})
    g.add_node("c", lambda s: {"results": [_llm().invoke(s["msg"]).content]})
    g.add_node(
        "aggregator", lambda s: {"final": _llm().invoke(str(s["results"])).content}
    )
    g.add_edge(START, "a")
    g.add_edge(START, "b")
    g.add_edge(START, "c")
    g.add_edge("a", "aggregator")
    g.add_edge("b", "aggregator")
    g.add_edge("c", "aggregator")
    g.add_edge("aggregator", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "results": [], "final": ""})["final"]


def fanin_v2_with_review() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        results: Annotated[list, operator.add]
        final: str

    g = StateGraph(S)
    g.add_node("a", lambda s: {"results": [_llm().invoke(s["msg"]).content]})
    g.add_node("b", lambda s: {"results": [_llm().invoke(s["msg"]).content]})
    g.add_node("c", lambda s: {"results": [_llm().invoke(s["msg"]).content]})
    g.add_node("reviewer", lambda s: {"results": [_llm().invoke(s["msg"]).content]})
    g.add_node(
        "aggregator", lambda s: {"final": _llm().invoke(str(s["results"])).content}
    )
    g.add_edge(START, "a")
    g.add_edge(START, "b")
    g.add_edge(START, "c")
    g.add_edge(START, "reviewer")
    g.add_edge("a", "aggregator")
    g.add_edge("b", "aggregator")
    g.add_edge("c", "aggregator")
    g.add_edge("reviewer", "aggregator")
    g.add_edge("aggregator", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "results": [], "final": ""})["final"]


# -------- 4. diamond --------
def diamond_v1() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        mid: Annotated[list, operator.add]
        final: str

    g = StateGraph(S)
    g.add_node("planner", lambda s: {"msg": _llm().invoke(s["msg"]).content, "mid": []})
    g.add_node("coder", lambda s: {"mid": [_llm().invoke(s["msg"]).content]})
    g.add_node("reviewer", lambda s: {"mid": [_llm().invoke(s["msg"]).content]})
    g.add_node("tester", lambda s: {"final": _llm().invoke(str(s["mid"])).content})
    g.add_edge(START, "planner")
    g.add_edge("planner", "coder")
    g.add_edge("planner", "reviewer")
    g.add_edge("coder", "tester")
    g.add_edge("reviewer", "tester")
    g.add_edge("tester", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "mid": [], "final": ""})["final"]


def diamond_v2_with_review() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        mid: Annotated[list, operator.add]
        final: str

    g = StateGraph(S)
    g.add_node("planner", lambda s: {"msg": _llm().invoke(s["msg"]).content, "mid": []})
    g.add_node("coder", lambda s: {"mid": [_llm().invoke(s["msg"]).content]})
    g.add_node("reviewer", lambda s: {"mid": [_llm().invoke(s["msg"]).content]})
    g.add_node("second_reviewer", lambda s: {"mid": [_llm().invoke(s["msg"]).content]})
    g.add_node("tester", lambda s: {"final": _llm().invoke(str(s["mid"])).content})
    g.add_edge(START, "planner")
    g.add_edge("planner", "coder")
    g.add_edge("planner", "reviewer")
    g.add_edge("planner", "second_reviewer")
    g.add_edge("coder", "tester")
    g.add_edge("reviewer", "tester")
    g.add_edge("second_reviewer", "tester")
    g.add_edge("tester", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "mid": [], "final": ""})["final"]


# -------- 5. revise --------
def revise_v1() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str

    g = StateGraph(S)
    g.add_node("writer1", lambda s: {"msg": _llm().invoke(s["msg"]).content})
    g.add_node("reviewer", lambda s: {"msg": _llm().invoke(s["msg"]).content})
    g.add_node("writer2", lambda s: {"msg": _llm().invoke(s["msg"]).content})
    g.add_edge(START, "writer1")
    g.add_edge("writer1", "reviewer")
    g.add_edge("reviewer", "writer2")
    g.add_edge("writer2", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x})["msg"]


def revise_v2_with_review() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        review: Annotated[list, operator.add]

    g = StateGraph(S)
    g.add_node(
        "writer1", lambda s: {"msg": _llm().invoke(s["msg"]).content, "review": []}
    )
    g.add_node("reviewer", lambda s: {"review": [_llm().invoke(s["msg"]).content]})
    g.add_node(
        "second_reviewer", lambda s: {"review": [_llm().invoke(s["msg"]).content]}
    )
    g.add_node(
        "writer2", lambda s: {"msg": _llm().invoke(s["msg"] + str(s["review"])).content}
    )
    g.add_edge(START, "writer1")
    g.add_edge("writer1", "reviewer")
    g.add_edge("writer1", "second_reviewer")
    g.add_edge("reviewer", "writer2")
    g.add_edge("second_reviewer", "writer2")
    g.add_edge("writer2", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "review": []})["msg"]


# -------- 6. ensemble --------
def ensemble_v1() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        votes: Annotated[list, operator.add]
        final: str

    g = StateGraph(S)
    g.add_node(
        "ingest", lambda s: {"msg": _llm().invoke(s["msg"]).content, "votes": []}
    )
    g.add_node("gpt", lambda s: {"votes": [_llm().invoke(s["msg"]).content]})
    g.add_node("claude", lambda s: {"votes": [_llm().invoke(s["msg"]).content]})
    g.add_node("gemini", lambda s: {"votes": [_llm().invoke(s["msg"]).content]})
    g.add_node(
        "synthesizer", lambda s: {"final": _llm().invoke(str(s["votes"])).content}
    )
    g.add_edge(START, "ingest")
    g.add_edge("ingest", "gpt")
    g.add_edge("ingest", "claude")
    g.add_edge("ingest", "gemini")
    g.add_edge("gpt", "synthesizer")
    g.add_edge("claude", "synthesizer")
    g.add_edge("gemini", "synthesizer")
    g.add_edge("synthesizer", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "votes": [], "final": ""})["final"]


def ensemble_v2_with_review() -> Callable[[str], str]:
    class S(TypedDict):
        msg: str
        votes: Annotated[list, operator.add]
        final: str

    g = StateGraph(S)
    g.add_node(
        "ingest", lambda s: {"msg": _llm().invoke(s["msg"]).content, "votes": []}
    )
    g.add_node("gpt", lambda s: {"votes": [_llm().invoke(s["msg"]).content]})
    g.add_node("claude", lambda s: {"votes": [_llm().invoke(s["msg"]).content]})
    g.add_node("gemini", lambda s: {"votes": [_llm().invoke(s["msg"]).content]})
    g.add_node("reviewer", lambda s: {"votes": [_llm().invoke(s["msg"]).content]})
    g.add_node(
        "synthesizer", lambda s: {"final": _llm().invoke(str(s["votes"])).content}
    )
    g.add_edge(START, "ingest")
    g.add_edge("ingest", "gpt")
    g.add_edge("ingest", "claude")
    g.add_edge("ingest", "gemini")
    g.add_edge("ingest", "reviewer")
    g.add_edge("gpt", "synthesizer")
    g.add_edge("claude", "synthesizer")
    g.add_edge("gemini", "synthesizer")
    g.add_edge("reviewer", "synthesizer")
    g.add_edge("synthesizer", END)
    app = g.compile()
    return lambda x: app.invoke({"msg": x, "votes": [], "final": ""})["final"]


WORKFLOWS_V1 = {
    "linear": linear_v1,
    "fanout": fanout_v1,
    "fanin": fanin_v1,
    "diamond": diamond_v1,
    "revise": revise_v1,
    "ensemble": ensemble_v1,
}
WORKFLOWS_V2 = {
    "linear": linear_v2_with_review,
    "fanout": fanout_v2_with_review,
    "fanin": fanin_v2_with_review,
    "diamond": diamond_v2_with_review,
    "revise": revise_v2_with_review,
    "ensemble": ensemble_v2_with_review,
}
