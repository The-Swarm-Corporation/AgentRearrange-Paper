"""
Benchmark 5 — Wall-clock speed: AgentRearrange vs equivalents.

Runs the same diamond workflow

    planner -> coder, reviewer -> tester

end-to-end in:
  * AgentRearrange (this paper)
  * LangGraph     (if installed)
  * CrewAI        (if installed)
  * AutoGen       (if installed)

For each framework, runs N tasks sequentially and N tasks concurrently
(where the framework provides a concurrent surface). Reports the mean
wall-clock per task and a relative speedup vs AgentRearrange.

Missing frameworks are skipped with a printed note — the benchmark is
not rendered unrunnable by their absence.

Cost guardrail: `--limit 3` default (3 tasks). `--full` = 30 tasks.

Run:
    python benchmarks/05_speed.py --limit 3

Outputs:
    benchmarks/results/05_speed.json
    benchmarks/results/05_speed.md
    benchmarks/results/05_speed.png
"""

from __future__ import annotations
import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))


def get_workflows():
    """Import each framework's diamond_v1 if available."""
    workflows = {}
    try:
        from equivalents.ar_workflows import diamond_v1 as ar_diamond

        workflows["AgentRearrange"] = ar_diamond
    except Exception as e:
        print(f"[skip] AgentRearrange unavailable: {e}")
    try:
        from equivalents.langgraph_workflows import diamond_v1 as lg_diamond

        workflows["LangGraph"] = lg_diamond
    except Exception as e:
        print(f"[skip] LangGraph unavailable: {e}")
    try:
        from equivalents.crewai_workflows import diamond_v1 as cr_diamond

        workflows["CrewAI"] = cr_diamond
    except Exception as e:
        print(f"[skip] CrewAI unavailable: {e}")
    try:
        from equivalents.autogen_workflows import diamond_v1 as ag_diamond

        workflows["AutoGen"] = ag_diamond
    except Exception as e:
        print(f"[skip] AutoGen unavailable: {e}")
    return workflows


def load_tasks(limit: int) -> list[str]:
    return [
        f"Implement a Python function that {desc}. Keep it under 30 lines."
        for desc in [
            "validates email addresses against RFC 5322",
            "computes the moving average of a stream of numbers",
            "merges two sorted linked lists",
            "rate-limits API calls with a token bucket",
            "deduplicates a list of dicts by a key",
            "converts CamelCase to snake_case",
            "parses a CSV row respecting quoted commas",
            "finds the longest palindromic substring",
            "computes shortest path in an unweighted graph",
            "implements a basic LRU cache with a max size",
        ]
    ][:limit]


def time_sequential(run, tasks: list[str]) -> list[float]:
    times = []
    for t in tasks:
        t0 = time.time()
        try:
            run(t)
        except Exception as e:
            print(f"  task failed: {e}")
        times.append(time.time() - t0)
    return times


def time_concurrent(run, tasks: list[str], max_workers: int = 4) -> float:
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(lambda x: _safe(run, x), tasks))
    return time.time() - t0


def _safe(run, x):
    try:
        return run(x)
    except Exception as e:
        return f"<error: {e}>"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--full", action="store_true", help="set limit=30")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--out", default=str(RESULTS / "05_speed"))
    args = parser.parse_args()
    if args.full:
        args.limit = 30

    workflows = get_workflows()
    if "AgentRearrange" not in workflows:
        raise SystemExit("AgentRearrange must be installed to run this benchmark.")

    tasks = load_tasks(args.limit)
    results = {}

    for name, factory in workflows.items():
        print(f"\n== {name} ==")
        try:
            run = factory()  # builds the pipeline once
        except Exception as e:
            print(f"[skip] {name} could not be built: {e}")
            continue
        seq_times = time_sequential(run, tasks)
        try:
            conc_run = factory()
            conc_wall = time_concurrent(conc_run, tasks, args.max_workers)
        except Exception as e:
            print(f"[warn] {name} concurrent run failed: {e}")
            conc_wall = None
        results[name] = {
            "sequential_per_task_s": seq_times,
            "sequential_mean_s": statistics.mean(seq_times) if seq_times else None,
            "sequential_total_s": sum(seq_times),
            "concurrent_total_s": conc_wall,
        }

    base = results["AgentRearrange"]["sequential_mean_s"] or 1.0
    for name, r in results.items():
        if r["sequential_mean_s"]:
            r["seq_speedup_vs_AR"] = base / r["sequential_mean_s"]

    out = {"config": vars(args), "tasks": tasks, "results": results}
    Path(args.out + ".json").write_text(json.dumps(out, indent=2))

    md = ["# Benchmark 5 — Wall-clock speed (diamond workflow)", ""]
    md += [f"N tasks: {len(tasks)}.  Concurrent workers: {args.max_workers}.", ""]
    md += [
        "| Framework | Mean seq (s) | Total seq (s) | Concurrent total (s) | Speedup vs AR (seq mean) |"
    ]
    md += ["|---|---:|---:|---:|---:|"]
    for name, r in results.items():
        mean_s = f"{r['sequential_mean_s']:.2f}" if r["sequential_mean_s"] else "—"
        tot_s = f"{r['sequential_total_s']:.2f}" if r["sequential_total_s"] else "—"
        cnc_s = f"{r['concurrent_total_s']:.2f}" if r["concurrent_total_s"] else "—"
        spd = (
            f"{r.get('seq_speedup_vs_AR', 0):.2f}×"
            if r.get("seq_speedup_vs_AR")
            else "—"
        )
        md += [f"| {name} | {mean_s} | {tot_s} | {cnc_s} | {spd} |"]
    md_text = "\n".join(md)
    Path(args.out + ".md").write_text(md_text)

    # Plot
    try:
        import matplotlib.pyplot as plt

        names = list(results)
        seq_means = [results[n]["sequential_mean_s"] or 0 for n in names]
        conc_totals = [results[n]["concurrent_total_s"] or 0 for n in names]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
        bars1 = ax1.bar(
            names,
            seq_means,
            color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"][: len(names)],
        )
        ax1.set_ylabel("seconds")
        ax1.set_title("Mean wall-clock per task (sequential)")
        for b, v in zip(bars1, seq_means):
            ax1.text(
                b.get_x() + b.get_width() / 2, v, f"{v:.1f}s", ha="center", va="bottom"
            )

        bars2 = ax2.bar(
            names,
            conc_totals,
            color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"][: len(names)],
        )
        ax2.set_ylabel("seconds")
        ax2.set_title(f"Total wall-clock for {len(tasks)} tasks (concurrent)")
        for b, v in zip(bars2, conc_totals):
            ax2.text(
                b.get_x() + b.get_width() / 2, v, f"{v:.1f}s", ha="center", va="bottom"
            )

        for ax in (ax1, ax2):
            ax.tick_params(axis="x", rotation=15)
            ax.grid(True, axis="y", alpha=0.3)

        fig.tight_layout()
        fig.savefig(args.out + ".png", dpi=150)
        print(f"Wrote {args.out}.png")
    except Exception as e:
        print(f"[warn] plotting skipped: {e}")

    print("\n" + md_text)
    print(f"\nWrote {args.out}.json and {args.out}.md")


if __name__ == "__main__":
    main()
