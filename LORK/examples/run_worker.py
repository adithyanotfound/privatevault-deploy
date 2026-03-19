import asyncio
from lork.sdk.client import LorkClient
from lork.runtime.worker import RuntimeWorker


async def main():
    async with LorkClient.embedded() as lork:
        worker = RuntimeWorker(
            scheduler=lork._scheduler,
            registry=lork.agents._registry
        )
        await worker.start()

asyncio.run(main())
