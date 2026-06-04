# Benchmark 1 — DX: LOC & Edit Distance

## Per-workflow

| Workflow | Framework | v1 LOC | v2 LOC | ΔLOC | Δedit (chars) | +lines | -lines |
|---|---|---:|---:|---:|---:|---:|---:|
| linear | AgentRearrange | 3 | 3 | +0 | 33 | 2 | 2 |
| linear | LangGraph | 12 | 16 | +4 | 225 | 7 | 3 |
| linear | CrewAI | 8 | 9 | +1 | 117 | 4 | 3 |
| linear | AutoGen | 7 | 8 | +1 | 120 | 3 | 2 |
| fanout | AgentRearrange | 3 | 3 | +0 | 33 | 2 | 2 |
| fanout | LangGraph | 17 | 20 | +3 | 136 | 3 | 0 |
| fanout | CrewAI | 9 | 10 | +1 | 135 | 3 | 2 |
| fanout | AutoGen | 8 | 9 | +1 | 118 | 3 | 2 |
| fanin | AgentRearrange | 3 | 3 | +0 | 33 | 2 | 2 |
| fanin | LangGraph | 18 | 21 | +3 | 148 | 3 | 0 |
| fanin | CrewAI | 9 | 10 | +1 | 118 | 4 | 3 |
| fanin | AutoGen | 8 | 9 | +1 | 117 | 3 | 2 |
| diamond | AgentRearrange | 3 | 3 | +0 | 49 | 2 | 2 |
| diamond | LangGraph | 17 | 20 | +3 | 165 | 3 | 0 |
| diamond | CrewAI | 9 | 10 | +1 | 159 | 4 | 3 |
| diamond | AutoGen | 8 | 9 | +1 | 125 | 3 | 2 |
| revise | AgentRearrange | 3 | 3 | +0 | 49 | 2 | 2 |
| revise | LangGraph | 12 | 16 | +4 | 263 | 8 | 4 |
| revise | CrewAI | 8 | 9 | +1 | 181 | 5 | 4 |
| revise | AutoGen | 7 | 8 | +1 | 125 | 3 | 2 |
| ensemble | AgentRearrange | 7 | 5 | -2 | 87 | 3 | 5 |
| ensemble | LangGraph | 20 | 23 | +3 | 150 | 3 | 0 |
| ensemble | CrewAI | 10 | 11 | +1 | 139 | 4 | 3 |
| ensemble | AutoGen | 9 | 10 | +1 | 114 | 3 | 2 |

## Totals across all six workflows

| Framework | Total v1 LOC | Total v2 LOC | Total Δedit | Total +lines | Total -lines |
|---|---:|---:|---:|---:|---:|
| AgentRearrange | 22 | 20 | 284 | 13 | 15 |
| LangGraph | 96 | 116 | 1087 | 27 | 7 |
| CrewAI | 53 | 59 | 849 | 24 | 18 |
| AutoGen | 47 | 53 | 719 | 18 | 12 |