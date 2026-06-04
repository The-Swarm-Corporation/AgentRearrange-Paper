"""
AutoGen (pyautogen) reference implementations of the six canonical workflows
plus their "+ parallel review" variants.

AutoGen models everything as a chat between agents. Parallel patterns
require either GroupChat with a custom speaker selector, or hand-rolled
asyncio fan-out — neither is one-liner ergonomic.
"""

from __future__ import annotations
from typing import Callable

try:
    from autogen import AssistantAgent, UserProxyAgent

    _HAS_AG = True
except Exception:
    _HAS_AG = False

_CFG = {"config_list": [{"model": "gpt-4o-mini"}], "cache_seed": None}


def _assistant(name: str) -> "AssistantAgent":
    return AssistantAgent(name=name, llm_config=_CFG)


def _user() -> "UserProxyAgent":
    return UserProxyAgent(
        name="user", human_input_mode="NEVER", code_execution_config=False
    )


# -------- 1. linear --------
def linear_v1() -> Callable[[str], str]:
    a, b, c, u = _assistant("a"), _assistant("b"), _assistant("c"), _user()

    def run(x: str) -> str:
        r1 = u.initiate_chat(a, message=x, max_turns=1).chat_history[-1]["content"]
        r2 = u.initiate_chat(b, message=r1, max_turns=1).chat_history[-1]["content"]
        r3 = u.initiate_chat(c, message=r2, max_turns=1).chat_history[-1]["content"]
        return r3

    return run


def linear_v2_with_review() -> Callable[[str], str]:
    a, b, c, r, u = (
        _assistant("a"),
        _assistant("b"),
        _assistant("c"),
        _assistant("reviewer"),
        _user(),
    )

    def run(x: str) -> str:
        r1 = u.initiate_chat(a, message=x, max_turns=1).chat_history[-1]["content"]
        r2 = u.initiate_chat(b, message=r1, max_turns=1).chat_history[-1]["content"]
        rv = u.initiate_chat(r, message=r2, max_turns=1).chat_history[-1]["content"]
        r3 = u.initiate_chat(c, message=r2 + "\n" + rv, max_turns=1).chat_history[-1][
            "content"
        ]
        return r3

    return run


# -------- 2. fan-out --------
def fanout_v1() -> Callable[[str], str]:
    root, b, c, d, u = (
        _assistant("root"),
        _assistant("b"),
        _assistant("c"),
        _assistant("d"),
        _user(),
    )

    def run(x: str) -> str:
        r0 = u.initiate_chat(root, message=x, max_turns=1).chat_history[-1]["content"]
        rb = u.initiate_chat(b, message=r0, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(c, message=r0, max_turns=1).chat_history[-1]["content"]
        rd = u.initiate_chat(d, message=r0, max_turns=1).chat_history[-1]["content"]
        return f"{rb}\n{rc}\n{rd}"

    return run


def fanout_v2_with_review() -> Callable[[str], str]:
    root, b, c, d, rev, u = (
        _assistant("root"),
        _assistant("b"),
        _assistant("c"),
        _assistant("d"),
        _assistant("reviewer"),
        _user(),
    )

    def run(x: str) -> str:
        r0 = u.initiate_chat(root, message=x, max_turns=1).chat_history[-1]["content"]
        rb = u.initiate_chat(b, message=r0, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(c, message=r0, max_turns=1).chat_history[-1]["content"]
        rd = u.initiate_chat(d, message=r0, max_turns=1).chat_history[-1]["content"]
        rr = u.initiate_chat(rev, message=r0, max_turns=1).chat_history[-1]["content"]
        return f"{rb}\n{rc}\n{rd}\n{rr}"

    return run


# -------- 3. fan-in --------
def fanin_v1() -> Callable[[str], str]:
    a, b, c, agg, u = (
        _assistant("a"),
        _assistant("b"),
        _assistant("c"),
        _assistant("aggregator"),
        _user(),
    )

    def run(x: str) -> str:
        ra = u.initiate_chat(a, message=x, max_turns=1).chat_history[-1]["content"]
        rb = u.initiate_chat(b, message=x, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(c, message=x, max_turns=1).chat_history[-1]["content"]
        rg = u.initiate_chat(
            agg, message=f"{ra}\n{rb}\n{rc}", max_turns=1
        ).chat_history[-1]["content"]
        return rg

    return run


def fanin_v2_with_review() -> Callable[[str], str]:
    a, b, c, rev, agg, u = (
        _assistant("a"),
        _assistant("b"),
        _assistant("c"),
        _assistant("reviewer"),
        _assistant("aggregator"),
        _user(),
    )

    def run(x: str) -> str:
        ra = u.initiate_chat(a, message=x, max_turns=1).chat_history[-1]["content"]
        rb = u.initiate_chat(b, message=x, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(c, message=x, max_turns=1).chat_history[-1]["content"]
        rr = u.initiate_chat(rev, message=x, max_turns=1).chat_history[-1]["content"]
        rg = u.initiate_chat(
            agg, message=f"{ra}\n{rb}\n{rc}\n{rr}", max_turns=1
        ).chat_history[-1]["content"]
        return rg

    return run


# -------- 4. diamond --------
def diamond_v1() -> Callable[[str], str]:
    p, c, r, t, u = (
        _assistant("planner"),
        _assistant("coder"),
        _assistant("reviewer"),
        _assistant("tester"),
        _user(),
    )

    def run(x: str) -> str:
        rp = u.initiate_chat(p, message=x, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(c, message=rp, max_turns=1).chat_history[-1]["content"]
        rr = u.initiate_chat(r, message=rp, max_turns=1).chat_history[-1]["content"]
        rt = u.initiate_chat(t, message=f"{rc}\n{rr}", max_turns=1).chat_history[-1][
            "content"
        ]
        return rt

    return run


def diamond_v2_with_review() -> Callable[[str], str]:
    p, c, r, sr, t, u = (
        _assistant("planner"),
        _assistant("coder"),
        _assistant("reviewer"),
        _assistant("second_reviewer"),
        _assistant("tester"),
        _user(),
    )

    def run(x: str) -> str:
        rp = u.initiate_chat(p, message=x, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(c, message=rp, max_turns=1).chat_history[-1]["content"]
        rr = u.initiate_chat(r, message=rp, max_turns=1).chat_history[-1]["content"]
        rsr = u.initiate_chat(sr, message=rp, max_turns=1).chat_history[-1]["content"]
        rt = u.initiate_chat(t, message=f"{rc}\n{rr}\n{rsr}", max_turns=1).chat_history[
            -1
        ]["content"]
        return rt

    return run


# -------- 5. revise --------
def revise_v1() -> Callable[[str], str]:
    w, r, u = _assistant("writer"), _assistant("reviewer"), _user()

    def run(x: str) -> str:
        r1 = u.initiate_chat(w, message=x, max_turns=1).chat_history[-1]["content"]
        r2 = u.initiate_chat(r, message=r1, max_turns=1).chat_history[-1]["content"]
        r3 = u.initiate_chat(w, message=f"{r1}\n{r2}", max_turns=1).chat_history[-1][
            "content"
        ]
        return r3

    return run


def revise_v2_with_review() -> Callable[[str], str]:
    w, r, sr, u = (
        _assistant("writer"),
        _assistant("reviewer"),
        _assistant("second_reviewer"),
        _user(),
    )

    def run(x: str) -> str:
        r1 = u.initiate_chat(w, message=x, max_turns=1).chat_history[-1]["content"]
        r2 = u.initiate_chat(r, message=r1, max_turns=1).chat_history[-1]["content"]
        r2b = u.initiate_chat(sr, message=r1, max_turns=1).chat_history[-1]["content"]
        r3 = u.initiate_chat(w, message=f"{r1}\n{r2}\n{r2b}", max_turns=1).chat_history[
            -1
        ]["content"]
        return r3

    return run


# -------- 6. ensemble --------
def ensemble_v1() -> Callable[[str], str]:
    ing, g, cl, gm, s, u = (
        _assistant("ingest"),
        _assistant("gpt"),
        _assistant("claude"),
        _assistant("gemini"),
        _assistant("synthesizer"),
        _user(),
    )

    def run(x: str) -> str:
        r0 = u.initiate_chat(ing, message=x, max_turns=1).chat_history[-1]["content"]
        rg = u.initiate_chat(g, message=r0, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(cl, message=r0, max_turns=1).chat_history[-1]["content"]
        rm = u.initiate_chat(gm, message=r0, max_turns=1).chat_history[-1]["content"]
        rs = u.initiate_chat(s, message=f"{rg}\n{rc}\n{rm}", max_turns=1).chat_history[
            -1
        ]["content"]
        return rs

    return run


def ensemble_v2_with_review() -> Callable[[str], str]:
    ing, g, cl, gm, s, r, u = (
        _assistant("ingest"),
        _assistant("gpt"),
        _assistant("claude"),
        _assistant("gemini"),
        _assistant("synthesizer"),
        _assistant("reviewer"),
        _user(),
    )

    def run(x: str) -> str:
        r0 = u.initiate_chat(ing, message=x, max_turns=1).chat_history[-1]["content"]
        rg = u.initiate_chat(g, message=r0, max_turns=1).chat_history[-1]["content"]
        rc = u.initiate_chat(cl, message=r0, max_turns=1).chat_history[-1]["content"]
        rm = u.initiate_chat(gm, message=r0, max_turns=1).chat_history[-1]["content"]
        rr = u.initiate_chat(r, message=r0, max_turns=1).chat_history[-1]["content"]
        rs = u.initiate_chat(
            s, message=f"{rg}\n{rc}\n{rm}\n{rr}", max_turns=1
        ).chat_history[-1]["content"]
        return rs

    return run


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
