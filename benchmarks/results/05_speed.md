# Benchmark 5 — Wall-clock speed (diamond workflow)

N tasks: 2.  Concurrent workers: 4.

| Framework | Mean seq (s) | Total seq (s) | Concurrent total (s) | Speedup vs AR (seq mean) |
|---|---:|---:|---:|---:|
| AgentRearrange | 44.28 | 88.56 | 43.86 | 1.00× |
| LangGraph | 21.87 | 43.74 | 31.88 | 2.02× |