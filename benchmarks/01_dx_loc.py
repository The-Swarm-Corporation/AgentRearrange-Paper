"""
Benchmark 1 — Developer experience: lines of code & edit distance.

For each of the six canonical workflows (linear, fan-out, fan-in, diamond,
revise, ensemble) we read the source of the v1 implementation and the v2
implementation (the same workflow with one parallel review step inserted)
from `equivalents/{framework}_workflows.py`. Then:

  * LOC      = non-blank, non-comment, non-import lines in the v1 fn body
  * v1 flow  = the orchestration string / graph signature (for AR: the flow
               string itself)
  * Δ-edit   = Levenshtein distance between the v1 and v2 function source
               bodies — i.e. the literal cost of a topology change
  * Δ-LOC    = lines added/removed by the v2 patch

No LLM is invoked. Cost: $0.

Run:
    python benchmarks/01_dx_loc.py
Outputs:
    benchmarks/results/01_dx_loc.json
    benchmarks/results/01_dx_loc.md
"""

from __future__ import annotations
import argparse
import ast
import inspect
import json
import sys
import textwrap
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))

from equivalents import (
    ar_workflows,
    langgraph_workflows,
    crewai_workflows,
    autogen_workflows,
)  # noqa


FRAMEWORKS = {
    "AgentRearrange": ar_workflows,
    "LangGraph": langgraph_workflows,
    "CrewAI": crewai_workflows,
    "AutoGen": autogen_workflows,
}
WORKFLOWS = ["linear", "fanout", "fanin", "diamond", "revise", "ensemble"]


def levenshtein(a: str, b: str) -> int:
    """Pure-python Levenshtein; no external dep required."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(
                min(
                    cur[j - 1] + 1,
                    prev[j] + 1,
                    prev[j - 1] + (0 if ca == cb else 1),
                )
            )
        prev = cur
    return prev[-1]


def count_loc(src: str) -> int:
    """Non-blank, non-pure-comment, non-import lines."""
    n = 0
    for line in src.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s.startswith(("import ", "from ")):
            continue
        n += 1
    return n


def get_body(fn: Callable) -> str:
    """Get the source of fn, dedented, body-only (no signature)."""
    src = textwrap.dedent(inspect.getsource(fn))
    tree = ast.parse(src)
    fn_node = tree.body[0]
    body_src = "\n".join(
        ast.unparse(stmt)
        for stmt in fn_node.body
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)
    )
    return body_src


def line_diff(a: str, b: str) -> tuple[int, int]:
    """(added, removed) lines, via difflib."""
    import difflib

    al, bl = a.splitlines(), b.splitlines()
    added = removed = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, al, bl).get_opcodes():
        if op == "replace":
            added += j2 - j1
            removed += i2 - i1
        elif op == "insert":
            added += j2 - j1
        elif op == "delete":
            removed += i2 - i1
    return added, removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(RESULTS / "01_dx_loc"))
    # Accept-and-ignore so run_all.py can pass these uniformly.
    parser.add_argument("--limit", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--full", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    rows = []
    summary = {
        fw: {
            "v1_loc": 0,
            "v2_loc": 0,
            "delta_edit": 0,
            "delta_added": 0,
            "delta_removed": 0,
        }
        for fw in FRAMEWORKS
    }

    for wf in WORKFLOWS:
        for fw_name, mod in FRAMEWORKS.items():
            v1_fn = (
                getattr(mod.WORKFLOWS_V1, "get", lambda *_: None)(wf)
                or mod.WORKFLOWS_V1[wf]
            )
            v2_fn = (
                getattr(mod.WORKFLOWS_V2, "get", lambda *_: None)(wf)
                or mod.WORKFLOWS_V2[wf]
            )
            v1_src = get_body(v1_fn)
            v2_src = get_body(v2_fn)

            v1_loc = count_loc(v1_src)
            v2_loc = count_loc(v2_src)
            edit = levenshtein(v1_src, v2_src)
            added, removed = line_diff(v1_src, v2_src)

            rows.append(
                {
                    "workflow": wf,
                    "framework": fw_name,
                    "v1_loc": v1_loc,
                    "v2_loc": v2_loc,
                    "delta_loc": v2_loc - v1_loc,
                    "delta_edit_chars": edit,
                    "lines_added": added,
                    "lines_removed": removed,
                }
            )

            s = summary[fw_name]
            s["v1_loc"] += v1_loc
            s["v2_loc"] += v2_loc
            s["delta_edit"] += edit
            s["delta_added"] += added
            s["delta_removed"] += removed

    out_json = {"per_workflow": rows, "totals": summary}
    Path(args.out + ".json").write_text(json.dumps(out_json, indent=2))

    # Markdown table
    md = ["# Benchmark 1 — DX: LOC & Edit Distance", ""]
    md += ["## Per-workflow", ""]
    md += [
        "| Workflow | Framework | v1 LOC | v2 LOC | ΔLOC | Δedit (chars) | +lines | -lines |"
    ]
    md += ["|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        md += [
            f"| {r['workflow']} | {r['framework']} | {r['v1_loc']} | {r['v2_loc']} | "
            f"{r['delta_loc']:+d} | {r['delta_edit_chars']} | {r['lines_added']} | {r['lines_removed']} |"
        ]
    md += ["", "## Totals across all six workflows", ""]
    md += [
        "| Framework | Total v1 LOC | Total v2 LOC | Total Δedit | Total +lines | Total -lines |"
    ]
    md += ["|---|---:|---:|---:|---:|---:|"]
    for fw, s in summary.items():
        md += [
            f"| {fw} | {s['v1_loc']} | {s['v2_loc']} | {s['delta_edit']} | {s['delta_added']} | {s['delta_removed']} |"
        ]
    md_text = "\n".join(md)
    Path(args.out + ".md").write_text(md_text)

    # Plot
    try:
        import matplotlib.pyplot as plt

        fw_names = list(FRAMEWORKS)
        n_wf = len(WORKFLOWS)

        # Per-workflow v1 LOC grouped bar
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
        idx = list(range(n_wf))
        bar_w = 0.18
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

        for i, fw in enumerate(fw_names):
            vals = [
                next(
                    r["v1_loc"]
                    for r in rows
                    if r["workflow"] == wf and r["framework"] == fw
                )
                for wf in WORKFLOWS
            ]
            ax1.bar(
                [x + i * bar_w for x in idx], vals, bar_w, label=fw, color=colors[i]
            )
        ax1.set_xticks([x + 1.5 * bar_w for x in idx])
        ax1.set_xticklabels(WORKFLOWS, rotation=20)
        ax1.set_ylabel("LOC (v1)")
        ax1.set_title("Lines of code per workflow")
        ax1.legend()
        ax1.grid(True, axis="y", alpha=0.3)

        # Per-workflow edit distance grouped bar
        for i, fw in enumerate(fw_names):
            vals = [
                next(
                    r["delta_edit_chars"]
                    for r in rows
                    if r["workflow"] == wf and r["framework"] == fw
                )
                for wf in WORKFLOWS
            ]
            ax2.bar(
                [x + i * bar_w for x in idx], vals, bar_w, label=fw, color=colors[i]
            )
        ax2.set_xticks([x + 1.5 * bar_w for x in idx])
        ax2.set_xticklabels(WORKFLOWS, rotation=20)
        ax2.set_ylabel("Levenshtein chars  (v1 → v2)")
        ax2.set_title("Cost of inserting a parallel review step")
        ax2.legend()
        ax2.grid(True, axis="y", alpha=0.3)

        # Totals
        totals = [summary[fw]["v1_loc"] for fw in fw_names]
        edits = [summary[fw]["delta_edit"] for fw in fw_names]
        x = list(range(len(fw_names)))
        ax3b = ax3.twinx()
        b1 = ax3.bar(
            [xx - 0.18 for xx in x],
            totals,
            0.35,
            label="Total LOC (v1)",
            color="#4c72b0",
        )
        b2 = ax3b.bar(
            [xx + 0.18 for xx in x],
            edits,
            0.35,
            label="Total Δedit chars",
            color="#dd8452",
        )
        ax3.set_xticks(x)
        ax3.set_xticklabels(fw_names)
        ax3.set_ylabel("Total LOC across 6 workflows", color="#4c72b0")
        ax3b.set_ylabel("Total edit-distance across 6 workflows", color="#dd8452")
        ax3.set_title("Aggregate cost across all 6 workflows")
        for b, v in zip(b1, totals):
            ax3.text(
                b.get_x() + b.get_width() / 2,
                v,
                str(v),
                ha="center",
                va="bottom",
                fontsize=8,
                color="#4c72b0",
            )
        for b, v in zip(b2, edits):
            ax3b.text(
                b.get_x() + b.get_width() / 2,
                v,
                str(v),
                ha="center",
                va="bottom",
                fontsize=8,
                color="#dd8452",
            )

        fig.tight_layout()
        fig.savefig(args.out + ".png", dpi=150)
        print(f"Wrote {args.out}.png")
    except Exception as e:
        print(f"[warn] plotting skipped: {e}")

    print(md_text)
    print(f"\nWrote {args.out}.json and {args.out}.md")


if __name__ == "__main__":
    main()
