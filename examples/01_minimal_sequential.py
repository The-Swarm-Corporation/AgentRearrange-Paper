from swarms import Agent, AgentRearrange

researcher = Agent(agent_name="researcher", model_name="gpt-4.1", max_loops=1)
writer = Agent(agent_name="writer", model_name="gpt-4.1", max_loops=1)
editor = Agent(agent_name="editor", model_name="gpt-4.1", max_loops=1)

system = AgentRearrange(
    agents=[researcher, writer, editor],
    flow="researcher -> writer -> editor",
    max_loops=1,
)
result = system.run("Write an article on the history of transformer architectures.")
