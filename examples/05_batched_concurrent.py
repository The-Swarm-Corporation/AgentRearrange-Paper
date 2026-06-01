from swarms import Agent, AgentRearrange

a = Agent(agent_name="extract",   model_name="gpt-5.4-mini", max_loops=1)
b = Agent(agent_name="transform", model_name="gpt-5.4-mini", max_loops=1)
c = Agent(agent_name="load",      model_name="gpt-5.4-mini", max_loops=1)

etl = AgentRearrange(
    agents=[a, b, c],
    flow="extract -> transform -> load",
)

tasks = [f"Process document {i}.pdf" for i in range(50)]

# Batched: deep-copies isolate state per task, batch_size at a time.
batch_results = etl.batch_run(tasks=tasks, batch_size=10)

# Concurrent: ThreadPoolExecutor across all tasks at once.
parallel_results = etl.concurrent_run(tasks=tasks, max_workers=8)
