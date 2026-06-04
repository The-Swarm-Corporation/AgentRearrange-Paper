"""
Benchmark 3 — Multi-model ensemble (Listing 3) vs. each model alone.

Compares the canonical fan-out/fan-in pattern

    ingest -> gpt, claude, gemini -> synthesizer

against each of the three component models running solo, on one of:

    --suite mmlu_pro     TIGER-Lab/MMLU-Pro     (multiple choice)
    --suite gpqa         Idavidrein/gpqa        (multiple choice, hard sci)
    --suite humaneval    openai_humaneval       (code generation)

Reports accuracy and tokens-per-correct-answer for each condition.

Cost guardrail: `--limit 5` default. `--full` = 200 problems.

Run:
    python benchmarks/03_multi_model_ensemble.py --limit 5 --suite mmlu_pro

Outputs:
    benchmarks/results/03_ensemble_<suite>.json
    benchmarks/results/03_ensemble_<suite>.md
"""

from __future__ import annotations
import argparse
import io
import json
import re
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable

from swarms import Agent, AgentRearrange

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


# ---------- Suite loaders ----------


def load_mmlu_pro(limit: int) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
    out = []
    for ex in ds:
        opts = ex["options"]
        letters = [chr(ord("A") + i) for i in range(len(opts))]
        prompt = (
            f"Question: {ex['question']}\n"
            + "\n".join(f"{l}. {o}" for l, o in zip(letters, opts))
            + "\n\nAnswer with ONLY the single letter."
        )
        out.append({"prompt": prompt, "answer": ex["answer"], "type": "mc"})
        if len(out) >= limit:
            break
    return out


def load_gpqa(limit: int) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset("Idavidrein/gpqa", "gpqa_main", split="train")
    out = []
    for ex in ds:
        opts = [
            ex["Correct Answer"],
            ex["Incorrect Answer 1"],
            ex["Incorrect Answer 2"],
            ex["Incorrect Answer 3"],
        ]
        # deterministic shuffle so A is not always correct
        idx = [0, 1, 2, 3]
        seed = (len(out) * 17) % 24
        from itertools import permutations

        perm = list(permutations(idx))[seed]
        opts = [opts[i] for i in perm]
        ans = "ABCD"[perm.index(0)]
        prompt = (
            f"Question: {ex['Question']}\n"
            + "\n".join(f"{l}. {o}" for l, o in zip("ABCD", opts))
            + "\n\nAnswer with ONLY the single letter."
        )
        out.append({"prompt": prompt, "answer": ans, "type": "mc"})
        if len(out) >= limit:
            break
    return out


def load_humaneval(limit: int) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset("openai_humaneval", split="test")
    out = []
    for ex in ds:
        out.append(
            {
                "prompt": (
                    "Complete the following Python function. Return ONLY the function body "
                    "(or full function), no markdown fencing, no extra prose:\n\n"
                    + ex["prompt"]
                ),
                "answer": ex["canonical_solution"],
                "test": ex["test"],
                "entry_point": ex["entry_point"],
                "function_prompt": ex["prompt"],
                "type": "code",
            }
        )
        if len(out) >= limit:
            break
    return out


SUITES: dict[str, Callable[[int], list[dict]]] = {
    "mmlu_pro": load_mmlu_pro,
    "gpqa": load_gpqa,
    "humaneval": load_humaneval,
}


# ---------- Grading ----------


def extract_letter(text: str) -> str | None:
    m = re.search(r"\b([A-J])\b", text.strip())
    return m.group(1) if m else None


def grade_mc(ex: dict, response: str) -> bool:
    g = extract_letter(response)
    return g is not None and g == ex["answer"]


def grade_code(ex: dict, response: str) -> bool:
    """Run the response against the HumanEval test harness in-process."""
    code = response
    if "```" in code:
        m = re.search(r"```(?:python)?\n(.*?)```", code, re.DOTALL)
        if m:
            code = m.group(1)
    # If the response is body-only, prepend the prompt's function signature.
    if "def " not in code:
        code = ex["function_prompt"] + code
    ns: dict = {}
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(code, ns)
            exec(ex["test"], ns)
            ns["check"](ns[ex["entry_point"]])
        return True
    except Exception:
        return False


def grade(ex: dict, response: str) -> bool:
    return grade_code(ex, response) if ex["type"] == "code" else grade_mc(ex, response)


# ---------- Token counting ----------


def count_tokens(s: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(s))
    except Exception:
        return max(1, len(s) // 4)


# ---------- Conditions ----------


def build_solo(name: str, model: str) -> Callable[[str], str]:
    a = Agent(
        agent_name=name, model_name=model, max_loops=1, autosave=False, verbose=False
    )
    return a.run


def build_ensemble(models: dict[str, str]) -> Callable[[str], str]:
    ingest = Agent(
        agent_name="ingest",
        model_name=models["gpt"],
        max_loops=1,
        autosave=False,
        verbose=False,
    )
    gpt = Agent(
        agent_name="gpt",
        model_name=models["gpt"],
        max_loops=1,
        autosave=False,
        verbose=False,
    )
    claude = Agent(
        agent_name="claude",
        model_name=models["claude"],
        max_loops=1,
        autosave=False,
        verbose=False,
    )
    gemini = Agent(
        agent_name="gemini",
        model_name=models["gemini"],
        max_loops=1,
        autosave=False,
        verbose=False,
    )
    synth = Agent(
        agent_name="synthesizer",
        model_name=models["gpt"],
        max_loops=1,
        autosave=False,
        verbose=False,
        system_prompt=(
            "You receive three candidate answers from three models. "
            "Pick the best answer or synthesize a stronger one. "
            "If the task is multiple choice, output ONLY the single letter."
        ),
    )
    ar = AgentRearrange(
        agents=[ingest, gpt, claude, gemini, synth],
        flow="ingest -> gpt, claude, gemini -> synthesizer",
        max_loops=1,
        output_type="final",
        autosave=False,
        verbose=False,
    )
    return lambda x: str(ar.run(x))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=list(SUITES), default="mmlu_pro")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--full", action="store_true", help="set limit=200")
    parser.add_argument("--gpt-model", default="gpt-4o-mini")
    parser.add_argument("--claude-model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--gemini-model", default="gemini/gemini-2.5-flash")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if args.full:
        args.limit = 200
    out_base = args.out or str(RESULTS / f"03_ensemble_{args.suite}")

    examples = SUITES[args.suite](args.limit)
    print(f"Loaded {len(examples)} {args.suite} examples")

    conditions = {
        "gpt_solo": build_solo("gpt_solo", args.gpt_model),
        "claude_solo": build_solo("claude_solo", args.claude_model),
        "gemini_solo": build_solo("gemini_solo", args.gemini_model),
        "ensemble": build_ensemble(
            {
                "gpt": args.gpt_model,
                "claude": args.claude_model,
                "gemini": args.gemini_model,
            }
        ),
    }

    results: dict[str, dict] = {}
    per_example: list[dict] = []

    for cond, fn in conditions.items():
        correct = 0
        tokens_in = tokens_out = 0
        wall = 0.0
        details = []
        for i, ex in enumerate(examples):
            t0 = time.time()
            try:
                resp = fn(ex["prompt"])
            except Exception as e:
                resp = f"<error: {e}>"
            dt = time.time() - t0
            wall += dt
            ok = grade(ex, resp)
            correct += int(ok)
            ti = count_tokens(ex["prompt"])
            to = count_tokens(resp)
            tokens_in += ti
            tokens_out += to
            details.append(
                {
                    "idx": i,
                    "correct": ok,
                    "tokens_in": ti,
                    "tokens_out": to,
                    "wall_s": dt,
                }
            )
            print(f"  [{cond}] {i+1}/{len(examples)}  ok={ok}  ({dt:.1f}s)")

        n = len(examples)
        acc = correct / n if n else 0.0
        per_correct_tokens = (tokens_in + tokens_out) / correct if correct else None
        results[cond] = {
            "n": n,
            "correct": correct,
            "accuracy": acc,
            "tokens_in_total": tokens_in,
            "tokens_out_total": tokens_out,
            "tokens_per_correct": per_correct_tokens,
            "wall_s_total": wall,
            "per_example": details,
        }

    out = {"config": vars(args), "results": results}
    Path(out_base + ".json").write_text(json.dumps(out, indent=2))

    md = [f"# Benchmark 3 — Multi-model ensemble vs solo  (`{args.suite}`)", ""]
    md += [
        f"N = {len(examples)}.  GPT={args.gpt_model}, Claude={args.claude_model}, Gemini={args.gemini_model}",
        "",
    ]
    md += [
        "| Condition | Accuracy | Correct/N | Tokens in | Tokens out | Tokens / correct | Wall (s) |"
    ]
    md += ["|---|---:|---:|---:|---:|---:|---:|"]
    for cond, r in results.items():
        tpc = f"{r['tokens_per_correct']:.0f}" if r["tokens_per_correct"] else "—"
        md += [
            f"| {cond} | {r['accuracy']:.3f} | {r['correct']}/{r['n']} | "
            f"{r['tokens_in_total']} | {r['tokens_out_total']} | {tpc} | {r['wall_s_total']:.1f} |"
        ]
    # Delta vs best solo.
    solos = {k: v["accuracy"] for k, v in results.items() if k.endswith("_solo")}
    best_solo = max(solos, key=solos.get) if solos else None
    if best_solo:
        delta = results["ensemble"]["accuracy"] - solos[best_solo]
        md += [
            "",
            f"**Δ vs best solo** ({best_solo}, {solos[best_solo]:.3f}): {delta:+.3f}",
        ]
    md_text = "\n".join(md)
    Path(out_base + ".md").write_text(md_text)

    # Plot
    try:
        import matplotlib.pyplot as plt

        conds = list(results)
        accs = [results[c]["accuracy"] for c in conds]
        tpc = [results[c]["tokens_per_correct"] or 0 for c in conds]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))
        colors = ["#1f77b4", "#9467bd", "#8c564b", "#2ca02c"]
        bars = ax1.bar(conds, accs, color=colors[: len(conds)])
        for b, a in zip(bars, accs):
            ax1.text(
                b.get_x() + b.get_width() / 2, a, f"{a:.2f}", ha="center", va="bottom"
            )
        ax1.set_ylim(0, 1)
        ax1.set_ylabel("Accuracy")
        ax1.set_title(f"Accuracy — {args.suite}")
        ax1.grid(True, axis="y", alpha=0.3)
        ax1.tick_params(axis="x", rotation=10)

        bars2 = ax2.bar(conds, tpc, color=colors[: len(conds)])
        for b, v in zip(bars2, tpc):
            ax2.text(
                b.get_x() + b.get_width() / 2, v, f"{v:.0f}", ha="center", va="bottom"
            )
        ax2.set_ylabel("Tokens per correct answer")
        ax2.set_title("Cost-efficiency (lower is better)")
        ax2.grid(True, axis="y", alpha=0.3)
        ax2.tick_params(axis="x", rotation=10)

        fig.tight_layout()
        fig.savefig(out_base + ".png", dpi=150)
        print(f"Wrote {out_base}.png")
    except Exception as e:
        print(f"[warn] plotting skipped: {e}")

    print("\n" + md_text)
    print(f"\nWrote {out_base}.json and {out_base}.md")


if __name__ == "__main__":
    main()
