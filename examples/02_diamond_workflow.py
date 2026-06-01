from swarms import Agent, AgentRearrange

planner  = Agent(agent_name="planner",  model_name="gpt-4.1", max_loops=1)
coder    = Agent(agent_name="coder",    model_name="gpt-4.1", max_loops=1)
reviewer = Agent(agent_name="reviewer", model_name="gpt-4.1", max_loops=1)
tester   = Agent(agent_name="tester",   model_name="gpt-4.1", max_loops=1)

pipeline = AgentRearrange(
    agents=[planner, coder, reviewer, tester],
    flow="planner -> coder, reviewer -> tester",
    max_loops=1,
    team_awareness=True,  # tell each agent its neighbors
)
result = pipeline.run("Build a Python function that validates email addresses.")
