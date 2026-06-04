"""
Run every benchmark sequentially and consolidate every produced artifact
into `benchmarks/results/`, with a shared timestamp suffix per run so
multiple runs do not clobber each other.

Each child benchmark is invoked as a subprocess with
`--out results/<NN>_<name>_<YYYY-MM-DD_HH-MM-SS>`,
so its `.png`, `.json`, `.md`, and `.csv` all land in `results/` under
the same timestamp.

Cost guardrail: forwards `--limit` / `--full` flags to every child.

Run:
    python benchmarks/run_all.py --limit 3        # smoke run, small
    python benchmarks/run_all.py --full           # full paper run
    python benchmarks/run_all.py --only 1,3       # subset (by ID)

The DX/LOC benchmark needs no API key. All others need OPENAI_API_KEY;
benchmark 3 additionally wants ANTHROPIC_API_KEY and GEMINI_API_KEY.
"""

from __future__ import annotations
import argparse
import datetime as _dt
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
RUN_TS = _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


BENCHES = [
    {
        "id": 1,
        "name": "dx_loc",
        "script": "01_dx_loc.py",
        "needs_keys": [],
        "extra_args": [],
    },
    {
        "id": 2,
        "name": "topology_sweep",
        "script": "02_topology_sweep.py",
        "needs_keys": ["OPENAI_API_KEY"],
        "extra_args": [],
    },
    {
        "id": 3,
        "name": "ensemble_mmlu_pro",
        "script": "03_multi_model_ensemble.py",
        "needs_keys": ["OPENAI_API_KEY"],
        "extra_args": ["--suite", "mmlu_pro"],
    },
    {
        "id": 4,
        "name": "context_accumulation",
        "script": "04_context_accumulation.py",
        "needs_keys": ["OPENAI_API_KEY"],
        "extra_args": [],
    },
    {
        "id": 5,
        "name": "speed",
        "script": "05_speed.py",
        "needs_keys": ["OPENAI_API_KEY"],
        "extra_args": [],
    },
]


def run_bench(
    b: dict, limit: int, full: bool, extra_global: list[str], ts: str
) -> dict:
    import os

    script = HERE / b["script"]
    out_base = RESULTS / f"{b['id']:02d}_{b['name']}_{ts}"
    cmd = [sys.executable, str(script), "--out", str(out_base)]
    if full:
        cmd.append("--full")
    else:
        cmd.extend(["--limit", str(limit)])
    cmd.extend(b["extra_args"])
    cmd.extend(extra_global)

    missing = [k for k in b["needs_keys"] if not os.environ.get(k)]
    if missing:
        return {
            "id": b["id"],
            "name": b["name"],
            "status": "skipped",
            "reason": f"missing env: {','.join(missing)}",
            "cmd": " ".join(cmd),
        }

    t0 = time.time()
    print(f"\n{'='*72}\n>>> [{b['id']}] {b['name']}\n{'='*72}\n$ {' '.join(cmd)}\n")
    proc = subprocess.run(cmd, cwd=str(HERE.parent))
    dt = time.time() - t0
    status = "ok" if proc.returncode == 0 else "failed"
    return {
        "id": b["id"],
        "name": b["name"],
        "status": status,
        "exit_code": proc.returncode,
        "wall_s": dt,
        "cmd": " ".join(cmd),
    }


def parse_only(s: str | None) -> set[int] | None:
    if not s:
        return None
    return {int(x) for x in s.split(",") if x.strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--full", action="store_true")
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="comma list of benchmark IDs to run (e.g. '1,3')",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="delete results/ before running",
    )
    parser.add_argument(
        "--timestamp",
        default=RUN_TS,
        help="suffix appended to every output file (default: now, YYYY-MM-DD_HH-MM-SS)",
    )
    args, extra = parser.parse_known_args()

    if args.clean and RESULTS.exists():
        shutil.rmtree(RESULTS)
        RESULTS.mkdir()

    only = parse_only(args.only)
    statuses = []
    for b in BENCHES:
        if only is not None and b["id"] not in only:
            continue
        statuses.append(run_bench(b, args.limit, args.full, extra, args.timestamp))

    # Summary
    print("\n" + "=" * 72 + "\nSUMMARY\n" + "=" * 72)
    print(f"{'ID':<4}{'NAME':<26}{'STATUS':<10}{'TIME':>8}")
    for s in statuses:
        tm = f"{s.get('wall_s', 0):.1f}s" if s.get("wall_s") else "—"
        extra = ""
        if s["status"] == "skipped":
            extra = "  (" + s.get("reason", "") + ")"
        print(f"{s['id']:<4}{s['name']:<26}{s['status']:<10}{tm:>8}{extra}")

    # Collect chart manifest for this run only (matches timestamp suffix).
    pngs = sorted(RESULTS.glob(f"*_{args.timestamp}.png"))
    print(f"\nThis run's charts in {RESULTS}/  ({len(pngs)} files):")
    for p in pngs:
        print(f"  {p.name}")

    if any(s["status"] == "failed" for s in statuses):
        sys.exit(1)


if __name__ == "__main__":
    main()
