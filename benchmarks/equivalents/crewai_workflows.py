"""
CrewAI reference implementations of the six canonical workflows
plus their "+ parallel review" variants.

CrewAI requires Agent + Task + Crew triples. Sequential flow is natural;
parallel fan-out/fan-in is awkward — CrewAI tends to express it via
multiple tasks all assigned to one Crew with `process=Process.sequential`
or via hierarchical mode.
"""

from __future__ import annotations
from typing import Callable

try:
    from crewai import Agent, Task, Crew, Process

    _HAS_CREW = True
except Exception:
    _HAS_CREW = False


def _agent(role: str) -> "Agent":
    return Agent(
        role=role,
        goal=f"act as {role}",
        backstory=f"You are {role}.",
        allow_delegation=False,
    )


# -------- 1. linear --------
def linear_v1() -> Callable[[str], str]:
    a, b, c = _agent("a"), _agent("b"), _agent("c")

    def run(x: str) -> str:
        t1 = Task(description=x, expected_output="text", agent=a)
        t2 = Task(description="continue", expected_output="text", agent=b, context=[t1])
        t3 = Task(description="finalize", expected_output="text", agent=c, context=[t2])
        crew = Crew(agents=[a, b, c], tasks=[t1, t2, t3], process=Process.sequential)
        return str(crew.kickoff())

    return run


def linear_v2_with_review() -> Callable[[str], str]:
    a, b, c, r = _agent("a"), _agent("b"), _agent("c"), _agent("reviewer")

    def run(x: str) -> str:
        t1 = Task(description=x, expected_output="text", agent=a)
        t2 = Task(description="continue", expected_output="text", agent=b, context=[t1])
        tr = Task(description="review", expected_output="text", agent=r, context=[t2])
        t3 = Task(
            description="finalize", expected_output="text", agent=c, context=[t2, tr]
        )
        crew = Crew(
            agents=[a, b, r, c], tasks=[t1, t2, tr, t3], process=Process.sequential
        )
        return str(crew.kickoff())

    return run


# -------- 2. fan-out --------
def fanout_v1() -> Callable[[str], str]:
    root, b, c, d = _agent("root"), _agent("b"), _agent("c"), _agent("d")

    def run(x: str) -> str:
        t0 = Task(description=x, expected_output="text", agent=root)
        tb = Task(
            description="branch b",
            expected_output="text",
            agent=b,
            context=[t0],
            async_execution=True,
        )
        tc = Task(
            description="branch c",
            expected_output="text",
            agent=c,
            context=[t0],
            async_execution=True,
        )
        td = Task(
            description="branch d",
            expected_output="text",
            agent=d,
            context=[t0],
            async_execution=True,
        )
        crew = Crew(
            agents=[root, b, c, d], tasks=[t0, tb, tc, td], process=Process.sequential
        )
        return str(crew.kickoff())

    return run


def fanout_v2_with_review() -> Callable[[str], str]:
    root, b, c, d, r = (
        _agent("root"),
        _agent("b"),
        _agent("c"),
        _agent("d"),
        _agent("reviewer"),
    )

    def run(x: str) -> str:
        t0 = Task(description=x, expected_output="text", agent=root)
        tb = Task(
            description="branch b",
            expected_output="text",
            agent=b,
            context=[t0],
            async_execution=True,
        )
        tc = Task(
            description="branch c",
            expected_output="text",
            agent=c,
            context=[t0],
            async_execution=True,
        )
        td = Task(
            description="branch d",
            expected_output="text",
            agent=d,
            context=[t0],
            async_execution=True,
        )
        tr = Task(
            description="review",
            expected_output="text",
            agent=r,
            context=[t0],
            async_execution=True,
        )
        crew = Crew(
            agents=[root, b, c, d, r],
            tasks=[t0, tb, tc, td, tr],
            process=Process.sequential,
        )
        return str(crew.kickoff())

    return run


# -------- 3. fan-in --------
def fanin_v1() -> Callable[[str], str]:
    a, b, c, agg = _agent("a"), _agent("b"), _agent("c"), _agent("aggregator")

    def run(x: str) -> str:
        ta = Task(description=x, expected_output="text", agent=a, async_execution=True)
        tb = Task(description=x, expected_output="text", agent=b, async_execution=True)
        tc = Task(description=x, expected_output="text", agent=c, async_execution=True)
        tagg = Task(
            description="aggregate",
            expected_output="text",
            agent=agg,
            context=[ta, tb, tc],
        )
        crew = Crew(
            agents=[a, b, c, agg], tasks=[ta, tb, tc, tagg], process=Process.sequential
        )
        return str(crew.kickoff())

    return run


def fanin_v2_with_review() -> Callable[[str], str]:
    a, b, c, agg, r = (
        _agent("a"),
        _agent("b"),
        _agent("c"),
        _agent("aggregator"),
        _agent("reviewer"),
    )

    def run(x: str) -> str:
        ta = Task(description=x, expected_output="text", agent=a, async_execution=True)
        tb = Task(description=x, expected_output="text", agent=b, async_execution=True)
        tc = Task(description=x, expected_output="text", agent=c, async_execution=True)
        tr = Task(description=x, expected_output="text", agent=r, async_execution=True)
        tagg = Task(
            description="aggregate",
            expected_output="text",
            agent=agg,
            context=[ta, tb, tc, tr],
        )
        crew = Crew(
            agents=[a, b, c, r, agg],
            tasks=[ta, tb, tc, tr, tagg],
            process=Process.sequential,
        )
        return str(crew.kickoff())

    return run


# -------- 4. diamond --------
def diamond_v1() -> Callable[[str], str]:
    p, c, r, t = (
        _agent("planner"),
        _agent("coder"),
        _agent("reviewer"),
        _agent("tester"),
    )

    def run(x: str) -> str:
        tp = Task(description=x, expected_output="text", agent=p)
        tc = Task(
            description="code",
            expected_output="text",
            agent=c,
            context=[tp],
            async_execution=True,
        )
        tr = Task(
            description="review",
            expected_output="text",
            agent=r,
            context=[tp],
            async_execution=True,
        )
        tt = Task(description="test", expected_output="text", agent=t, context=[tc, tr])
        crew = Crew(
            agents=[p, c, r, t], tasks=[tp, tc, tr, tt], process=Process.sequential
        )
        return str(crew.kickoff())

    return run


def diamond_v2_with_review() -> Callable[[str], str]:
    p, c, r, t, sr = (
        _agent("planner"),
        _agent("coder"),
        _agent("reviewer"),
        _agent("tester"),
        _agent("second_reviewer"),
    )

    def run(x: str) -> str:
        tp = Task(description=x, expected_output="text", agent=p)
        tc = Task(
            description="code",
            expected_output="text",
            agent=c,
            context=[tp],
            async_execution=True,
        )
        tr = Task(
            description="review",
            expected_output="text",
            agent=r,
            context=[tp],
            async_execution=True,
        )
        tsr = Task(
            description="second review",
            expected_output="text",
            agent=sr,
            context=[tp],
            async_execution=True,
        )
        tt = Task(
            description="test", expected_output="text", agent=t, context=[tc, tr, tsr]
        )
        crew = Crew(
            agents=[p, c, r, sr, t],
            tasks=[tp, tc, tr, tsr, tt],
            process=Process.sequential,
        )
        return str(crew.kickoff())

    return run


# -------- 5. revise --------
def revise_v1() -> Callable[[str], str]:
    w, r = _agent("writer"), _agent("reviewer")

    def run(x: str) -> str:
        t1 = Task(description=x, expected_output="text", agent=w)
        t2 = Task(description="review", expected_output="text", agent=r, context=[t1])
        t3 = Task(
            description="revise", expected_output="text", agent=w, context=[t1, t2]
        )
        crew = Crew(agents=[w, r], tasks=[t1, t2, t3], process=Process.sequential)
        return str(crew.kickoff())

    return run


def revise_v2_with_review() -> Callable[[str], str]:
    w, r, sr = _agent("writer"), _agent("reviewer"), _agent("second_reviewer")

    def run(x: str) -> str:
        t1 = Task(description=x, expected_output="text", agent=w)
        t2 = Task(
            description="review",
            expected_output="text",
            agent=r,
            context=[t1],
            async_execution=True,
        )
        t2b = Task(
            description="second review",
            expected_output="text",
            agent=sr,
            context=[t1],
            async_execution=True,
        )
        t3 = Task(
            description="revise", expected_output="text", agent=w, context=[t1, t2, t2b]
        )
        crew = Crew(
            agents=[w, r, sr], tasks=[t1, t2, t2b, t3], process=Process.sequential
        )
        return str(crew.kickoff())

    return run


# -------- 6. ensemble --------
def ensemble_v1() -> Callable[[str], str]:
    ing, g, cl, gm, s = (
        _agent("ingest"),
        _agent("gpt"),
        _agent("claude"),
        _agent("gemini"),
        _agent("synthesizer"),
    )

    def run(x: str) -> str:
        t0 = Task(description=x, expected_output="text", agent=ing)
        tg = Task(
            description="gpt take",
            expected_output="text",
            agent=g,
            context=[t0],
            async_execution=True,
        )
        tc = Task(
            description="claude take",
            expected_output="text",
            agent=cl,
            context=[t0],
            async_execution=True,
        )
        tm = Task(
            description="gemini take",
            expected_output="text",
            agent=gm,
            context=[t0],
            async_execution=True,
        )
        ts = Task(
            description="synthesize",
            expected_output="text",
            agent=s,
            context=[tg, tc, tm],
        )
        crew = Crew(
            agents=[ing, g, cl, gm, s],
            tasks=[t0, tg, tc, tm, ts],
            process=Process.sequential,
        )
        return str(crew.kickoff())

    return run


def ensemble_v2_with_review() -> Callable[[str], str]:
    ing, g, cl, gm, s, r = (
        _agent("ingest"),
        _agent("gpt"),
        _agent("claude"),
        _agent("gemini"),
        _agent("synthesizer"),
        _agent("reviewer"),
    )

    def run(x: str) -> str:
        t0 = Task(description=x, expected_output="text", agent=ing)
        tg = Task(
            description="gpt take",
            expected_output="text",
            agent=g,
            context=[t0],
            async_execution=True,
        )
        tc = Task(
            description="claude take",
            expected_output="text",
            agent=cl,
            context=[t0],
            async_execution=True,
        )
        tm = Task(
            description="gemini take",
            expected_output="text",
            agent=gm,
            context=[t0],
            async_execution=True,
        )
        tr = Task(
            description="review",
            expected_output="text",
            agent=r,
            context=[t0],
            async_execution=True,
        )
        ts = Task(
            description="synthesize",
            expected_output="text",
            agent=s,
            context=[tg, tc, tm, tr],
        )
        crew = Crew(
            agents=[ing, g, cl, gm, r, s],
            tasks=[t0, tg, tc, tm, tr, ts],
            process=Process.sequential,
        )
        return str(crew.kickoff())

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
