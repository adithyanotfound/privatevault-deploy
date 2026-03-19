import asyncio
from botbook.events.bus import bus
from botbook.integrations.illuu_adapter import IlluuAdapter

illuu = IlluuAdapter()

async def handle_job(job):

    agent_id = job["agent_id"]
    task = job["task"]

    print(f"[worker] executing job for {agent_id}: {task}")

    result = await illuu.execute(agent_id, task)

    print("[worker] result:", result)

bus.subscribe("agent.jobs", handle_job)

print("BotBook worker started")

asyncio.run(asyncio.Event().wait())
