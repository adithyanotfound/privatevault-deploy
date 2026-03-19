import asyncio
from .service import TrustService

trust = TrustService()

async def recompute_loop():

    while True:

        trust.recompute()

        await asyncio.sleep(300)
