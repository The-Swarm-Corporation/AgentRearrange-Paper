# Benchmarks

Reproducible benchmarks supporting the claims in `paper.pdf`. Each file is
self-contained and runnable on its own. Defaults are small (`--limit 5`) so a
smoke run costs cents; pass `--full` to reproduce the paper numbers.

All scripts write a JSON blob (`<name>.json`), a Markdown table
(`<name>.md`), and a matplotlib chart (`<name>.png`) — and benches 2, 3,
and 4 additionally write a CSV (`<name>.csv`) — into `benchmarks/results/`
by default. Pass `--out <prefix>` to redirect them anywhere.

To run everything in one shot:

```bash
python benchmarks/run_all.py --limit 3           # smoke run
python benchmarks/run_all.py --full              # paper run
python benchmarks/run_all.py --only 1,3 --clean  # subset, wipe results/ first
```

`run_all.py` invokes each benchmark as a subprocess with
`--out benchmarks/results/<NN>_<name>_<YYYY-MM-DD_HH-MM-SS>`, so every
artifact (`.png`, `.json`, `.md`, `.csv`) for a given run shares one
timestamp suffix and lives under `benchmarks/results/`. Re-running never
clobbers prior output. Benchmarks whose required API keys are missing
are skipped (not failed).

| # | File | What it measures | Cost defaults |
|---|---|---|---|
| 1 | `01_dx_loc.py` | Lines-of-code and Levenshtein edit-distance for six canonical workflows expressed in AgentRearrange vs LangGraph, CrewAI, AutoGen, then the cost of inserting a parallel review step into each. | $0 (no LLM calls) |
| 2 | `02_topology_sweep.py` | Fix 5 agents, sweep 4 topologies (linear, fan-out, diamond, fan-in) over a HuggingFace task suite, score with an LLM judge. Demonstrates "iterate on topology like you iterate on prompts." | ~$0.10 at `--limit 5` |
| 3 | `03_multi_model_ensemble.py` | Fan-out/fan-in over GPT/Claude/Gemini vs. each model alone on MMLU-Pro / GPQA / HumanEval-style. Accuracy delta and tokens-per-correct. | ~$0.25 at `--limit 5` |
| 4 | `04_context_accumulation.py` | Quality vs. flow length (2 → 10 steps). Tokens-into-final-agent vs. step count. Manual truncation via `Agent.context_length` as the "compression" comparison. | ~$0.30 at `--limit 5` |
| 5 | `05_speed.py` | Wall-clock latency of an equivalent diamond flow in AgentRearrange vs LangGraph vs (optionally) CrewAI / AutoGen. | ~$0.05 at `--limit 5` |

## Running

```bash
pip install -U swarms datasets python-Levenshtein matplotlib
# optional comparison frameworks for benches 1 & 5
pip install langgraph crewai pyautogen

export OPENAI_API_KEY=...
# bench 3 additionally wants:
export ANTHROPIC_API_KEY=... GEMINI_API_KEY=...

python benchmarks/01_dx_loc.py            # no API key required
python benchmarks/02_topology_sweep.py --limit 5
python benchmarks/03_multi_model_ensemble.py --limit 5 --suite mmlu_pro
python benchmarks/04_context_accumulation.py --limit 5
python benchmarks/05_speed.py --limit 3
```

## Cost guardrail

Every script that hits an LLM has `--limit N` (default 5) and `--full` to
expand to the configuration used in the paper. Smoke-test on `--limit 3`
before any `--full` run.

## Output directories

| Location | Contents |
|---|---|
| `benchmarks/results/` | All outputs: scripts run directly write `<NN>_<name>.{json,md,png,csv}`; `run_all.py` appends a `_YYYY-MM-DD_HH-MM-SS` timestamp to keep runs distinct |
| `benchmarks/equivalents/` | Reference workflow implementations in AR, LangGraph, CrewAI, AutoGen — used by benches 1 (DX) and 5 (Speed) |

## Equivalents

The DX and Speed benchmarks compare against minimal equivalent
implementations in other frameworks, kept under `equivalents/`. These are
*reference code*, not test fixtures — the DX benchmark reads them as strings,
the Speed benchmark imports them as modules.
