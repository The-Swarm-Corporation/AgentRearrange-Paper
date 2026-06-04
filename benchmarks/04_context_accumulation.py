"""
Benchmark 4 — Context accumulation / long-flow degradation.

The paper observes that the shared Conversation grows monotonically across
sequential hops. This benchmark quantifies:

  1. tokens-into-the-final-agent as a function of flow length (2 -> 10)
  2. quality of the final answer as a function of flow length
  3. the same with a manual context cap (`Agent.context_length`) imposed —
     the closest thing AgentRearrange offers to "compression" (no
     `context_compression=True` flag exists in the current API).

For each step count K in {2,3,...,10}, build a linear flow
`a1 -> a2 -> ... -> aK`, run it on a task suite, and record both the
prompt size handed to the final agent and an LLM-judge quality score
(1–10) for that final answer.

Cost guardrail: `--limit 3` default. `--full` = 20 tasks per K.

Run:
    python benchmarks/04_context_accumulation.py --limit 3

Outputs:
    benchmarks/results/04_context_accumulation.json
    benchmarks/results/04_context_accumulation.md
    benchmarks/results/04_context_accumulation.png
    benchmarks/results/04_context_accumulation.csv
"""

from __future__ import annotations
import argparse
import csv
import json
import re
import time
from pathlib import Path

from swarms import Agent, AgentRearrange

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

STEP_RANGE = list(range(2, 11))


def count_tokens(s: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(s))
    except Exception:
        return max(1, len(s) // 4)


def build_flow(
    k: int, model: str, context_cap: int | None
) -> tuple[AgentRearrange, list[Agent]]:
    """Linear flow of length k: a1 -> a2 -> ... -> ak."""
    names = [f"a{i}" for i in range(1, k + 1)]
    agents = []
    for i, n in enumerate(names):
        kwargs = dict(
            agent_name=n,
            model_name=model,
            system_prompt=(
                f"You are agent {n}, step {i+1} of a {k}-step pipeline. "
                "Build on prior context, contribute one improvement, and pass forward."
            ),
            max_loops=1,
            autosave=False,
            verbose=False,
        )
        if context_cap is not None:
            kwargs["context_length"] = context_cap
        agents.append(Agent(**kwargs))
    flow = " -> ".join(names)
    ar = AgentRearrange(
        agents=agents,
        flow=flow,
        max_loops=1,
        output_type="all",
        autosave=False,
        verbose=False,
    )
    return ar, agents


def judge_quality(judge: Agent, task: str, answer: str) -> int:
    prompt = (
        f"Rate the QUALITY of the answer to the task on a scale 1–10.\n\n"
        f"TASK:\n{task}\n\n"
        f"ANSWER:\n{answer[:6000]}\n\n"
        f"Consider correctness, depth, clarity, and on-topic-ness. "
        f"Respond with ONLY the integer score."
    )
    raw = judge.run(prompt).strip()
    m = re.search(r"\b(10|[1-9])\b", raw)
    return int(m.group(1)) if m else 5


def load_tasks(limit: int) -> list[str]:
    return [
        "Write a 200-word analysis of how attention mechanisms enabled the transformer revolution.",
        "Compare and contrast the policy responses to the 1970s stagflation and the 2008 financial crisis.",
        "Explain the CAP theorem with one real-world example for each tradeoff (CP, AP, CA).",
        "Outline the major historiographical interpretations of the fall of the Western Roman Empire.",
        "Describe the differences between supervised, self-supervised, and reinforcement learning with examples.",
        "Summarize the philosophical positions on the mind-body problem from Descartes to Chalmers.",
        "Explain how mRNA vaccines work, including the role of lipid nanoparticles and pseudouridine.",
        "Analyze the literary techniques Cormac McCarthy uses to create tone in *Blood Meridian*.",
        "Discuss the design tradeoffs between monolithic and microservice architectures at scale.",
        "Outline the causal chain that led to the start of World War I, beyond just the Sarajevo assassination.",
        "Explain how diffusion models generate images, including the forward and reverse processes.",
        "Discuss the major arguments for and against universal basic income from economic theory.",
        "Describe the structure of the eukaryotic cell cycle and its major regulatory checkpoints.",
        "Compare the foreign policy doctrines of Theodore Roosevelt, Wilson, and FDR.",
        "Explain the role of compiler optimization passes and give three concrete examples.",
        "Analyze the major themes in Hannah Arendt's *The Human Condition*.",
        "Explain the differences between PostgreSQL, MongoDB, and DynamoDB for OLTP workloads.",
        "Discuss the development of quantum field theory from Dirac through to the Standard Model.",
        "Explain consensus algorithms: Paxos vs Raft vs PBFT — what changes and why.",
        "Describe the major schools of macroeconomic thought from Keynes onwards.",
    ][:limit]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3, help="tasks per K")
    parser.add_argument("--full", action="store_true", help="set limit=20")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument(
        "--context-cap",
        type=int,
        default=2000,
        help="tokens cap for the 'compressed' variant (Agent.context_length)",
    )
    parser.add_argument("--out", default=str(RESULTS / "04_context_accumulation"))
    args = parser.parse_args()

    if args.full:
        args.limit = 20

    tasks = load_tasks(args.limit)
    judge = Agent(
        agent_name="judge",
        model_name=args.judge_model,
        system_prompt="You are a strict reviewer of essay-style answers.",
        max_loops=1,
        autosave=False,
        verbose=False,
    )

    # variant -> step_count -> list of per-task records
    data = {"uncapped": {}, "capped": {}}

    for variant, cap in [("uncapped", None), ("capped", args.context_cap)]:
        for K in STEP_RANGE:
            print(f"== variant={variant}  K={K} ==")
            recs = []
            for ti, task in enumerate(tasks):
                ar, agents = build_flow(K, args.model, cap)
                t0 = time.time()
                try:
                    out = ar.run(task)
                except Exception as e:
                    print(f"  task {ti+1} FAILED: {e}")
                    continue
                wall = time.time() - t0

                # Reconstruct the conversation text fed to the final agent.
                # AgentRearrange shares a Conversation; the text passed to the
                # last agent is everything that came before its turn.
                conv = ar.conversation.return_history_as_string()
                # Strip the final agent's own output to estimate "into-final-agent".
                final_marker = f"{agents[-1].agent_name}:"
                pre_final = (
                    conv.split(final_marker)[0] if final_marker in conv else conv
                )

                tokens_into_final = count_tokens(pre_final)
                # Get the final agent's text output.
                if isinstance(out, list):
                    final_answer = next(
                        (
                            m.get("content", "")
                            for m in reversed(out)
                            if isinstance(m, dict)
                            and m.get("role", "").startswith(agents[-1].agent_name)
                        ),
                        str(out[-1]) if out else "",
                    )
                elif isinstance(out, dict):
                    final_answer = str(out)
                else:
                    final_answer = str(out)

                score = judge_quality(judge, task, final_answer)
                recs.append(
                    {
                        "task_idx": ti,
                        "tokens_into_final": tokens_into_final,
                        "quality": score,
                        "wall_s": wall,
                        "final_answer_tokens": count_tokens(final_answer),
                    }
                )
                print(
                    f"  task {ti+1}: tokens_into_final={tokens_into_final}, quality={score}, wall={wall:.1f}s"
                )
            data[variant][K] = recs

    # Aggregate
    summary = {"uncapped": {}, "capped": {}}
    for variant in data:
        for K, recs in data[variant].items():
            if not recs:
                summary[variant][K] = None
                continue
            n = len(recs)
            summary[variant][K] = {
                "n": n,
                "avg_tokens_into_final": sum(r["tokens_into_final"] for r in recs) / n,
                "avg_quality": sum(r["quality"] for r in recs) / n,
                "avg_wall_s": sum(r["wall_s"] for r in recs) / n,
            }

    out = {"config": vars(args), "summary": summary, "raw": data}
    Path(args.out + ".json").write_text(json.dumps(out, indent=2))

    # CSV (long format, plot-ready)
    with open(args.out + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["variant", "k", "avg_tokens_into_final", "avg_quality", "avg_wall_s", "n"]
        )
        for variant in summary:
            for K in STEP_RANGE:
                s = summary[variant][K]
                if s is None:
                    continue
                w.writerow(
                    [
                        variant,
                        K,
                        f"{s['avg_tokens_into_final']:.1f}",
                        f"{s['avg_quality']:.2f}",
                        f"{s['avg_wall_s']:.2f}",
                        s["n"],
                    ]
                )

    # Markdown table
    md = ["# Benchmark 4 — Context accumulation vs flow length", ""]
    md += [
        f"Tasks per K: {len(tasks)}.  Worker={args.model}  Judge={args.judge_model}  Cap={args.context_cap} tokens",
        "",
    ]
    md += ["## Uncapped (default AgentRearrange)", ""]
    md += ["| K | tokens into final | quality (1-10) | wall (s) |"]
    md += ["|---:|---:|---:|---:|"]
    for K in STEP_RANGE:
        s = summary["uncapped"][K]
        if s is None:
            continue
        md += [
            f"| {K} | {s['avg_tokens_into_final']:.0f} | {s['avg_quality']:.2f} | {s['avg_wall_s']:.1f} |"
        ]
    md += ["", "## Capped (Agent.context_length = {})".format(args.context_cap), ""]
    md += ["| K | tokens into final | quality (1-10) | wall (s) |"]
    md += ["|---:|---:|---:|---:|"]
    for K in STEP_RANGE:
        s = summary["capped"][K]
        if s is None:
            continue
        md += [
            f"| {K} | {s['avg_tokens_into_final']:.0f} | {s['avg_quality']:.2f} | {s['avg_wall_s']:.1f} |"
        ]
    md_text = "\n".join(md)
    Path(args.out + ".md").write_text(md_text)

    # Plot
    try:
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

        for variant, marker in [("uncapped", "o"), ("capped", "s")]:
            ks, toks, qual = [], [], []
            for K in STEP_RANGE:
                s = summary[variant][K]
                if s is None:
                    continue
                ks.append(K)
                toks.append(s["avg_tokens_into_final"])
                qual.append(s["avg_quality"])
            ax1.plot(ks, toks, marker=marker, label=variant)
            ax2.plot(ks, qual, marker=marker, label=variant)

        ax1.set_xlabel("flow length K")
        ax1.set_ylabel("tokens into final agent")
        ax1.set_title("Context growth vs flow length")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        ax2.set_xlabel("flow length K")
        ax2.set_ylabel("quality (LLM judge, 1–10)")
        ax2.set_title("Quality vs flow length")
        ax2.set_ylim(0, 10)
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        fig.tight_layout()
        fig.savefig(args.out + ".png", dpi=150)
        print(f"Wrote {args.out}.png")
    except Exception as e:
        print(f"[warn] plotting skipped: {e}")

    print("\n" + md_text)
    print(f"\nWrote {args.out}.json, .md, .csv")


if __name__ == "__main__":
    main()
