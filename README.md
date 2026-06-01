# AgentRearrange: A General-Purpose Multi-Agent Orchestrator

> A Technical Report on the `AgentRearrange` primitive in the [Swarms](https://github.com/kyegomez/swarms) framework.

[![Paper (PDF)](https://img.shields.io/badge/Paper-PDF-red.svg)](./paper.pdf)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Swarms](https://img.shields.io/badge/Swarms-v12.0.0-orange.svg)](https://github.com/kyegomez/swarms)
[![PyPI](https://img.shields.io/badge/PyPI-swarms-blue.svg)](https://pypi.org/project/swarms/)
[![Docs](https://img.shields.io/badge/docs-swarms.world-green.svg)](https://docs.swarms.world)

**Read the paper:** [`paper.pdf`](./paper.pdf)

---

## Authors

**Swarms Research Department**
Correspondence: [kye@swarms.world](mailto:kye@swarms.world)
Repository: [github.com/kyegomez/swarms](https://github.com/kyegomez/swarms)

## Publication Details

| Field | Value |
|---|---|
| Title | *AgentRearrange: A General-Purpose Multi-Agent Orchestrator* |
| Date | June 2026 |
| Version | Swarms v12.0.0 |
| Format | Single-column, continuous article |
| License | Apache-2.0 |
| Paper | [`paper.pdf`](./paper.pdf) |

---

## Abstract

This report introduces **AgentRearrange**, a multi-agent orchestration primitive in the Swarms framework that lets engineers express arbitrary mixtures of sequential and concurrent agent execution through a tiny, readable flow grammar. Where dedicated structures such as `SequentialWorkflow` and `ConcurrentWorkflow` fix a single topology at construction time, AgentRearrange separates *topology* from *instantiation*: a workflow is a string like `"researcher -> writer, reviewer -> editor"`, parsed at runtime into an executable schedule. We describe the motivation behind the abstraction, the parsing and scheduling model, the team-awareness mechanism that lets each agent see its upstream and downstream neighbors, and the supporting features for batched, concurrent, asynchronous, and token-streaming execution. We then present architectural diagrams for the canonical patterns AgentRearrange enables (linear pipelines, fan-out/fan-in, diamonds, and human-in-the-loop hops), followed by runnable code examples.

## Key Contributions

1. **Topology as data, not code.** Workflows are expressed as compact strings rather than class hierarchies, enabling iteration on orchestration shape at the same speed as iteration on prompts.
2. **A minimal flow DSL.** Two operators — `->` for sequential dependence and `,` for concurrent fan-out — compose to cover linear, fan-out, fan-in, diamond, repeated-agent, and human-in-the-loop patterns.
3. **Shared-conversation execution model.** A single `Conversation` object propagates context monotonically across sequential and parallel hops, eliminating hidden message routing and providing a complete execution trace.
4. **Production-ready surface.** Synchronous, asynchronous, token-streaming, batched, and concurrent multi-task execution all available without modifying the flow string.
5. **Generalization of existing structures.** `SequentialWorkflow`, `ConcurrentWorkflow`, and related orchestrators reduce to special cases of `AgentRearrange`, simplifying the framework's mental model.

## The Flow DSL at a Glance

The grammar fits on one line:

```
flow      := step ("->" step)*
step      := agent_name ("," agent_name)*
```

| Flow String | Topology |
|---|---|
| `"a -> b -> c"` | Linear pipeline |
| `"a -> b, c, d"` | Fan-out |
| `"a, b, c -> d"` | Fan-in (concurrent leaves into aggregator) |
| `"a -> b, c -> d"` | Diamond |
| `"writer -> reviewer -> writer"` | Revise loop (repeated agent) |
| `"drafter -> H -> finisher"` | Human-in-the-loop hop |

## Repository Layout

```
AgentRearrange-Paper/
├── paper.pdf      # Full technical report
├── examples/      # Runnable Python examples
├── README.md      # This file
└── LICENSE        # Apache-2.0
```

## Minimal Usage Example

```python
from swarms import Agent, AgentRearrange

researcher = Agent(agent_name="researcher", model_name="gpt-4.1", max_loops=1)
writer     = Agent(agent_name="writer",     model_name="gpt-4.1", max_loops=1)
editor     = Agent(agent_name="editor",     model_name="gpt-4.1", max_loops=1)

system = AgentRearrange(
    agents=[researcher, writer, editor],
    flow="researcher -> writer -> editor",
    max_loops=1,
)
result = system.run("Write an article on the history of transformer architectures.")
```

See **Section 6** of the report for diamond, multi-model ensemble, batched, asynchronous, and streaming examples.

## Examples

Runnable Python scripts for each canonical pattern live under [`examples/`](./examples). Each file is self-contained and corresponds to a listing in the report.

| # | File | Pattern | Flow String | Agents | Key Feature | Report § |
|---|---|---|---|---|---|---|
| 1 | [`01_minimal_sequential.py`](./examples/01_minimal_sequential.py) | Linear pipeline | `researcher -> writer -> editor` | 3 | Baseline sequential execution | Listing 1 |
| 2 | [`02_diamond_workflow.py`](./examples/02_diamond_workflow.py) | Diamond | `planner -> coder, reviewer -> tester` | 4 | Parallel middle, joined aggregator; `team_awareness=True` | Listing 2 |
| 3 | [`03_multi_model_ensemble.py`](./examples/03_multi_model_ensemble.py) | Fan-out / fan-in | `ingest -> gpt, claude, gemini -> synthesizer` | 5 | Multi-provider ensemble (GPT, Claude, Gemini) with synthesis | Listing 3 |
| 4 | [`04_revise_loop.py`](./examples/04_revise_loop.py) | Repeated agent (revise) | `writer -> reviewer -> writer` | 2 | Same agent invoked twice; indexed outputs (`Writer_0`, `Writer_2`) | Listing 4 |
| 5 | [`05_batched_concurrent.py`](./examples/05_batched_concurrent.py) | Multi-task execution | `extract -> transform -> load` | 3 | `batch_run` (isolated state) vs. `concurrent_run` (shared instance) | Listing 5 |
| 6 | [`06_async_streaming.py`](./examples/06_async_streaming.py) | Async + token streaming | `a -> b, c` | 3 | `run_async` awaitable; `arun_stream` for token-level interleaved output | Listing 6 |

### Running an example

```bash
pip install -U swarms
export OPENAI_API_KEY=...      # plus ANTHROPIC_API_KEY / GEMINI_API_KEY for ex. 3
python examples/01_minimal_sequential.py
```

## Resources

| Resource | Location |
|---|---|
| Source repository | [github.com/kyegomez/swarms](https://github.com/kyegomez/swarms) |
| AgentRearrange source | [`swarms/structs/agent_rearrange.py`](https://github.com/kyegomez/swarms/blob/master/swarms/structs/agent_rearrange.py) |
| Documentation | [docs.swarms.world](https://docs.swarms.world) |
| PyPI package | [pypi.org/project/swarms](https://pypi.org/project/swarms/) |
| Marketplace | [swarms.world](https://swarms.world) |
| Community (Discord) | [discord.gg/EamjgSaEQf](https://discord.gg/EamjgSaEQf) |
| Twitter / X | [@swarms_corp](https://twitter.com/swarms_corp/) |

## Citation

If you use AgentRearrange or this report in your research, please cite:

```bibtex
@techreport{swarms2026agentrearrange,
  title       = {AgentRearrange: A General-Purpose Multi-Agent Orchestrator},
  author      = {{Swarms Research Department} and Gomez, Kye},
  institution = {Swarms},
  year        = {2026},
  month       = {June},
  type        = {Technical Report},
  note        = {Swarms v12.0.0},
  url         = {https://github.com/kyegomez/swarms}
}

@software{swarms2026framework,
  author  = {Gomez, Kye and {The Swarms Research Department}},
  title   = {Swarms: The Enterprise-Grade Production-Ready Multi-Agent Orchestration Framework},
  year    = {2024--2026},
  version = {12.0.0},
  url     = {https://github.com/kyegomez/swarms}
}
```

## References

The full bibliography appears at the end of [`paper.pdf`](./paper.pdf). Selected references include:

1. Wu, Q., Bansal, G., Zhang, J., Wu, Y., Zhang, S., Zhu, E., Li, B., Jiang, L., Zhang, X., & Wang, C. **AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation.** *arXiv:2308.08155*, 2023.

2. Hong, S., Zheng, X., Chen, J., Cheng, Y., Wang, J., Zhang, C., Wang, Z., Yau, S. K. S., Lin, Z., Zhou, L., Ran, C., Xiao, L., Wu, C., & Schmidhuber, J. **MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework.** *ICLR*, 2024.

3. Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. **Generative Agents: Interactive Simulacra of Human Behavior.** *UIST*, 2023.

4. Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. **ReAct: Synergizing Reasoning and Acting in Language Models.** *ICLR*, 2023.

5. Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. **Reflexion: Language Agents with Verbal Reinforcement Learning.** *NeurIPS*, 2023.

6. Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N., & Scialom, T. **Toolformer: Language Models Can Teach Themselves to Use Tools.** *NeurIPS*, 2023.

7. Wang, J., Wang, J., Athiwaratkun, B., Zhang, C., & Zou, J. **Mixture-of-Agents Enhances Large Language Model Capabilities.** *arXiv:2406.04692*, 2024.

8. Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. **Tree of Thoughts: Deliberate Problem Solving with Large Language Models.** *NeurIPS*, 2023.

9. Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., & Zhou, D. **Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.** *NeurIPS*, 2022.

10. Significant Gravitas. **AutoGPT: An Autonomous GPT-4 Experiment.** GitHub, 2023. <https://github.com/Significant-Gravitas/AutoGPT>

11. LangChain, Inc. **LangGraph: Building Stateful, Multi-Actor Applications with LLMs.** GitHub, 2024. <https://github.com/langchain-ai/langgraph>

12. crewAI Inc. **CrewAI: Framework for Orchestrating Role-Playing, Autonomous AI Agents.** GitHub, 2024. <https://github.com/crewAIInc/crewAI>

13. BerriAI. **LiteLLM: Call All LLM APIs Using the OpenAI Format.** GitHub, 2024. <https://github.com/BerriAI/litellm>

14. Anthropic. **Introducing the Model Context Protocol.** 2024. <https://www.anthropic.com/news/model-context-protocol>

15. OpenAI. **GPT-4 Technical Report.** *arXiv:2303.08774*, 2023.

16. Anthropic. **The Claude 3 Model Family: Opus, Sonnet, Haiku.** Technical Report, 2024.

17. Apache Software Foundation. **Apache Airflow: A Platform to Programmatically Author, Schedule, and Monitor Workflows.** 2014–present. <https://airflow.apache.org>

18. Gomez, K., and the Swarms Research Department. **Swarms: The Enterprise-Grade Production-Ready Multi-Agent Orchestration Framework.** GitHub, v12.0.0, 2024–2026. <https://github.com/kyegomez/swarms>

## License

This report and accompanying code are released under the [Apache License 2.0](./LICENSE).

## Contact

For questions, feedback, or collaboration inquiries, please reach out to **[kye@swarms.world](mailto:kye@swarms.world)** or open an issue on the [Swarms repository](https://github.com/kyegomez/swarms/issues).
