from swarms import Agent, AgentRearrange

ingest = Agent(agent_name="ingest", model_name="gpt-4.1", max_loops=1)

gpt    = Agent(agent_name="gpt",    model_name="gpt-4.1",          max_loops=1)
claude = Agent(agent_name="claude", model_name="claude-sonnet-4-6", max_loops=1)
gemini = Agent(agent_name="gemini", model_name="gemini/gemini-2.5-pro", max_loops=1)

synth  = Agent(
    agent_name="synthesizer",
    model_name="gpt-4.1",
    system_prompt="Combine the three expert responses into one coherent answer.",
    max_loops=1,
)

ensemble = AgentRearrange(
    agents=[ingest, gpt, claude, gemini, synth],
    flow="ingest -> gpt, claude, gemini -> synthesizer",
    max_loops=1,
)
print(ensemble("What is the most underrated breakthrough in deep learning since 2020?"))
