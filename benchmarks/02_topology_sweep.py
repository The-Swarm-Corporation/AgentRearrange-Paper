"""
Benchmark 2 — Topology sweep.

Fix five agents (a, b, c, d, e). Sweep four canonical topologies:

  linear     : a -> b -> c -> d -> e
  fanout     : a -> b, c -> d, e            (root branches twice then joins)
  diamond    : a -> b, c, d -> e            (broad parallel middle)
  fanin      : a, b, c, d -> e              (concurrent leaves into aggregator)

Run each topology over a task suite drawn from a HuggingFace dataset
(default: `cais/mmlu` -> 'high_school_world_history' open-ended subset,
treated as short essay prompts). Score outputs pairwise with an LLM judge.

Demonstrates "iterate on topology like you iterate on prompts": same
agents, same task, only the flow string changes.

Cost guardrail: `--limit N` (default 5). Use `--full` for 100 tasks.

Run:
    python benchmarks/02_topology_sweep.py --limit 5
Outputs:
    benchmarks/results/02_topology_sweep.json
    benchmarks/results/02_topology_sweep.md
"""

from __future__ import annotations
import argparse
import json
import random
import re
import time
from collections import defaultdict
from pathlib import Path

from swarms import Agent, AgentRearrange

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

TOPOLOGIES = {
    "linear": "a -> b -> c -> d -> e",
    "fanout": "a -> b, c -> d, e",
    "diamond": "a -> b, c, d -> e",
    "fanin": "a, b, c, d -> e",
}


def build_agents(model: str) -> list[Agent]:
    roles = {
        "a": "You are a research analyst. Identify the key questions to answer and pull together relevant context.",
        "b": "You are a domain expert. Provide deep technical analysis and cite reasoning.",
        "c": "You are a critic. Identify weaknesses in any draft you see and suggest improvements.",
        "d": "You are an editor. Tighten prose, fix structure, ensure clarity.",
        "e": "You are the finalizer. Produce a single concise final answer that addresses the original task.",
    }
    return [
        Agent(agent_name=n, model_name=model, system_prompt=p, max_loops=1)
        for n, p in roles.items()
    ]


def load_tasks(limit: int, hf_dataset: str, hf_config: str, hf_split: str) -> list[str]:
    """Load `limit` short-essay-style prompts from a HuggingFace dataset.

    Default: MMLU 'high_school_world_history' converted to open-ended.
    Falls back to a hardcoded mini-suite if `datasets` is unavailable
    or the user is offline.
    """
    try:
        from datasets import load_dataset

        ds = load_dataset(hf_dataset, hf_config, split=hf_split)
        prompts = []
        for ex in ds:
            q = ex.get("question") or ex.get("prompt") or ex.get("text")
            if not q:
                continue
            prompts.append(f"Answer thoroughly and concisely: {q}")
            if len(prompts) >= limit:
                break
        if prompts:
            return prompts
    except Exception as e:
        print(f"[warn] dataset load failed ({e}); using fallback prompts")
    return [
        "Explain the main causes of the 2008 financial crisis.",
        "Summarize the key ideas in Hannah Arendt's *The Origins of Totalitarianism*.",
        "Describe how transformer architectures differ from RNNs.",
        "Outline the major tradeoffs between SQL and NoSQL databases.",
        "Explain the role of mitochondria in eukaryotic cells.",
        "Compare Keynesian and Austrian schools of economics.",
        "What were the long-term consequences of the Bretton Woods agreement?",
        "Summarize the plot and themes of Dostoevsky's *Crime and Punishment*.",
        "Explain the CAP theorem and give a real-world example.",
        "Describe the photoelectric effect and Einstein's contribution.",
    ][:limit]


def judge_pairwise(judge: Agent, task: str, a: str, b: str) -> str:
    """Return 'A', 'B', or 'tie'."""
    prompt = (
        f"You are an impartial judge. Compare two answers to the same task.\n\n"
        f"TASK:\n{task}\n\n"
        f"--- ANSWER A ---\n{a[:4000]}\n\n"
        f"--- ANSWER B ---\n{b[:4000]}\n\n"
        f"Which is better in correctness, depth, and clarity? "
        f"Respond with EXACTLY one token: A, B, or tie."
    )
    raw = judge.run(prompt).strip().upper()
    m = re.search(r"\b(A|B|TIE)\b", raw)
    if not m:
        return "tie"
    return {"A": "A", "B": "B", "TIE": "tie"}[m.group(1)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="tasks per topology")
    parser.add_argument("--full", action="store_true", help="set limit=100")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--hf-dataset", default="cais/mmlu")
    parser.add_argument("--hf-config", default="high_school_world_history")
    parser.add_argument("--hf-split", default="test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=str(RESULTS / "02_topology_sweep"))
    args = parser.parse_args()

    if args.full:
        args.limit = 100

    random.seed(args.seed)
    tasks = load_tasks(args.limit, args.hf_dataset, args.hf_config, args.hf_split)
    print(f"Loaded {len(tasks)} tasks")

    agents = build_agents(args.model)
    judge = Agent(
        agent_name="judge",
        model_name=args.judge_model,
        system_prompt="You are a strict impartial judge of written answers.",
        max_loops=1,
    )

    # Run each topology over all tasks; store outputs.
    outputs: dict[str, list[str]] = {}
    timings: dict[str, float] = {}
    for name, flow in TOPOLOGIES.items():
        ar = AgentRearrange(
            agents=agents,
            flow=flow,
            max_loops=1,
            output_type="final",
            autosave=False,
            verbose=False,
        )
        outs = []
        t0 = time.time()
        for i, task in enumerate(tasks):
            print(f"[{name}] task {i+1}/{len(tasks)}")
            try:
                outs.append(str(ar.run(task)))
            except Exception as e:
                print(f"[{name}] task {i+1} FAILED: {e}")
                outs.append(f"<error: {e}>")
        timings[name] = time.time() - t0
        outputs[name] = outs

    # Pairwise judge: round-robin over all topology pairs, random A/B order.
    pair_wins = defaultdict(lambda: defaultdict(int))  # winner -> loser -> count
    pair_ties = defaultdict(int)
    names = list(TOPOLOGIES)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            tA, tB = names[i], names[j]
            for k, task in enumerate(tasks):
                # randomize A/B presentation order to mitigate position bias
                if random.random() < 0.5:
                    verdict = judge_pairwise(
                        judge, task, outputs[tA][k], outputs[tB][k]
                    )
                    win = tA if verdict == "A" else (tB if verdict == "B" else None)
                else:
                    verdict = judge_pairwise(
                        judge, task, outputs[tB][k], outputs[tA][k]
                    )
                    win = tB if verdict == "A" else (tA if verdict == "B" else None)
                if win is None:
                    pair_ties[(tA, tB)] += 1
                else:
                    loser = tB if win == tA else tA
                    pair_wins[win][loser] += 1

    # Per-topology aggregate score: wins - losses.
    score = {n: 0 for n in names}
    for w, losers in pair_wins.items():
        for l, n in losers.items():
            score[w] += n
            score[l] -= n

    result = {
        "config": vars(args),
        "tasks": tasks,
        "timings_sec": timings,
        "score_net_wins": score,
        "pair_wins": {w: dict(losers) for w, losers in pair_wins.items()},
        "pair_ties": {f"{a}-{b}": v for (a, b), v in pair_ties.items()},
        "outputs": outputs,
    }
    Path(args.out + ".json").write_text(json.dumps(result, indent=2))

    md = ["# Benchmark 2 — Topology sweep (5 agents, 4 topologies)", ""]
    md += [
        f"Tasks: {len(tasks)} (dataset: `{args.hf_dataset}/{args.hf_config}`)  ",
        f"Worker model: `{args.model}`  Judge model: `{args.judge_model}`",
        "",
    ]
    md += ["## Net wins (pairwise judge, randomized A/B order)", ""]
    md += ["| Topology | Flow | Net wins | Wall time (s) |"]
    md += ["|---|---|---:|---:|"]
    for n in sorted(names, key=lambda x: -score[x]):
        md += [f"| {n} | `{TOPOLOGIES[n]}` | {score[n]:+d} | {timings[n]:.1f} |"]
    md += ["", "## Pair matrix (winner -> loser counts)", ""]
    md += ["| Winner \\ Loser | " + " | ".join(names) + " |"]
    md += ["|---|" + "|".join(["---:"] * len(names)) + "|"]
    for w in names:
        row = [w]
        for l in names:
            row.append("—" if w == l else str(pair_wins[w].get(l, 0)))
        md += ["| " + " | ".join(row) + " |"]
    md_text = "\n".join(md)
    Path(args.out + ".md").write_text(md_text)

    # Plot
    try:
        import matplotlib.pyplot as plt

        sorted_names = sorted(names, key=lambda x: -score[x])
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))

        bars = ax1.bar(
            sorted_names,
            [score[n] for n in sorted_names],
            color=["#2ca02c" if score[n] >= 0 else "#d62728" for n in sorted_names],
        )
        for b, n in zip(bars, sorted_names):
            ax1.text(
                b.get_x() + b.get_width() / 2,
                b.get_height(),
                f"{score[n]:+d}",
                ha="center",
                va="bottom" if score[n] >= 0 else "top",
            )
        ax1.set_ylabel("Net wins (pairwise judge)")
        ax1.set_title("Topology quality ranking")
        ax1.axhline(0, color="k", lw=0.5)
        ax1.grid(True, axis="y", alpha=0.3)

        # Time bars
        time_bars = ax2.bar(
            sorted_names, [timings[n] for n in sorted_names], color="#1f77b4"
        )
        for b, n in zip(time_bars, sorted_names):
            ax2.text(
                b.get_x() + b.get_width() / 2,
                b.get_height(),
                f"{timings[n]:.1f}s",
                ha="center",
                va="bottom",
            )
        ax2.set_ylabel("Wall time (s)")
        ax2.set_title(f"Wall time across {len(tasks)} tasks")
        ax2.grid(True, axis="y", alpha=0.3)

        fig.tight_layout()
        fig.savefig(args.out + ".png", dpi=150)
        print(f"Wrote {args.out}.png")
    except Exception as e:
        print(f"[warn] plotting skipped: {e}")

    print("\n" + md_text)
    print(f"\nWrote {args.out}.json and {args.out}.md")


if __name__ == "__main__":
    main()
