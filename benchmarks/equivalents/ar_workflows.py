"""
AgentRearrange reference implementations of the six canonical workflows
plus their "+ parallel review" variants. Each workflow is a function that
returns a runnable callable (str -> str). Used by:
  * 01_dx_loc.py — reads the source of each function as a string
  * 05_speed.py — imports and invokes the v1 variants
"""

from __future__ import annotations
from typing import Callable
from swarms import Agent, AgentRearrange


def _mk(name: str, model: str = "gpt-4o-mini") -> Agent:
    return Agent(agent_name=name, model_name=model, max_loops=1)


# -------- 1. linear pipeline --------
def linear_v1() -> Callable[[str], str]:
    a, b, c = _mk("a"), _mk("b"), _mk("c")
    flow = AgentRearrange(agents=[a, b, c], flow="a -> b -> c", max_loops=1)
    return flow.run


def linear_v2_with_review() -> Callable[[str], str]:
    a, b, c, r = _mk("a"), _mk("b"), _mk("c"), _mk("reviewer")
    flow = AgentRearrange(
        agents=[a, b, c, r], flow="a -> b, reviewer -> c", max_loops=1
    )
    return flow.run


# -------- 2. fan-out --------
def fanout_v1() -> Callable[[str], str]:
    root, b, c, d = _mk("root"), _mk("b"), _mk("c"), _mk("d")
    flow = AgentRearrange(agents=[root, b, c, d], flow="root -> b, c, d", max_loops=1)
    return flow.run


def fanout_v2_with_review() -> Callable[[str], str]:
    root, b, c, d, r = _mk("root"), _mk("b"), _mk("c"), _mk("d"), _mk("reviewer")
    flow = AgentRearrange(
        agents=[root, b, c, d, r],
        flow="root -> b, c, d, reviewer",
        max_loops=1,
    )
    return flow.run


# -------- 3. fan-in --------
def fanin_v1() -> Callable[[str], str]:
    a, b, c, agg = _mk("a"), _mk("b"), _mk("c"), _mk("aggregator")
    flow = AgentRearrange(
        agents=[a, b, c, agg], flow="a, b, c -> aggregator", max_loops=1
    )
    return flow.run


def fanin_v2_with_review() -> Callable[[str], str]:
    a, b, c, agg, r = _mk("a"), _mk("b"), _mk("c"), _mk("aggregator"), _mk("reviewer")
    flow = AgentRearrange(
        agents=[a, b, c, agg, r], flow="a, b, c, reviewer -> aggregator", max_loops=1
    )
    return flow.run


# -------- 4. diamond --------
def diamond_v1() -> Callable[[str], str]:
    p, c, r, t = _mk("planner"), _mk("coder"), _mk("reviewer"), _mk("tester")
    flow = AgentRearrange(
        agents=[p, c, r, t], flow="planner -> coder, reviewer -> tester", max_loops=1
    )
    return flow.run


def diamond_v2_with_review() -> Callable[[str], str]:
    p, c, r, t, sr = (
        _mk("planner"),
        _mk("coder"),
        _mk("reviewer"),
        _mk("tester"),
        _mk("second_reviewer"),
    )
    flow = AgentRearrange(
        agents=[p, c, r, t, sr],
        flow="planner -> coder, reviewer, second_reviewer -> tester",
        max_loops=1,
    )
    return flow.run


# -------- 5. revise loop --------
def revise_v1() -> Callable[[str], str]:
    w, r = _mk("writer"), _mk("reviewer")
    flow = AgentRearrange(
        agents=[w, r],
        flow="writer -> reviewer -> writer",
        max_loops=1,
        team_awareness=True,
    )
    return flow.run


def revise_v2_with_review() -> Callable[[str], str]:
    w, r, sr = _mk("writer"), _mk("reviewer"), _mk("second_reviewer")
    flow = AgentRearrange(
        agents=[w, r, sr],
        flow="writer -> reviewer, second_reviewer -> writer",
        max_loops=1,
        team_awareness=True,
    )
    return flow.run


# -------- 6. multi-model ensemble (fan-out/fan-in) --------
def ensemble_v1() -> Callable[[str], str]:
    ing = _mk("ingest")
    g = _mk("gpt", "gpt-4o-mini")
    cl = _mk("claude", "gpt-4o-mini")  # model identity irrelevant for DX/LOC
    gm = _mk("gemini", "gpt-4o-mini")
    s = _mk("synthesizer")
    flow = AgentRearrange(
        agents=[ing, g, cl, gm, s],
        flow="ingest -> gpt, claude, gemini -> synthesizer",
        max_loops=1,
    )
    return flow.run


def ensemble_v2_with_review() -> Callable[[str], str]:
    ing = _mk("ingest")
    g, cl, gm = _mk("gpt"), _mk("claude"), _mk("gemini")
    s, r = _mk("synthesizer"), _mk("reviewer")
    flow = AgentRearrange(
        agents=[ing, g, cl, gm, s, r],
        flow="ingest -> gpt, claude, gemini, reviewer -> synthesizer",
        max_loops=1,
    )
    return flow.run


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
