from swarms import Agent, AgentRearrange

writer = Agent(agent_name="writer", model_name="gpt-4.1", max_loops=1)
reviewer = Agent(agent_name="reviewer", model_name="gpt-4.1", max_loops=1)

revise = AgentRearrange(
    agents=[writer, reviewer],
    flow="writer -> reviewer -> writer",  # same agent, two invocations
    max_loops=1,
    team_awareness=True,
)
result = revise.run("Draft, critique, then revise a short essay on Hannah Arendt.")
