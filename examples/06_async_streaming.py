import asyncio
from swarms import Agent, AgentRearrange

a = Agent(agent_name="a", model_name="gpt-4.1", max_loops=1)
b = Agent(agent_name="b", model_name="gpt-4.1", max_loops=1)
c = Agent(agent_name="c", model_name="gpt-4.1", max_loops=1)

ar = AgentRearrange(agents=[a, b, c], flow="a -> b, c")

async def main():
    # Awaitable result
    result = await ar.run_async("Explain modular arithmetic with examples.")
    print(result)

    # Token-by-token stream; for parallel steps, tokens from b and c interleave.
    async for agent_name, token in ar.arun_stream("Explain it again, briefly."):
        print(f"[{agent_name}] {token}", end="", flush=True)

asyncio.run(main())
