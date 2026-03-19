"""
lorkctl CLI

Command line interface for interacting with the LORK control plane.
"""

import asyncio
import typer

from lork.sdk.client import LorkClient

app = typer.Typer()


@app.command()
def version():
    print("LORK CLI v0.1")


@app.command()
def register_agent(tenant: str, name: str):
    async def run():
        async with LorkClient.embedded() as lork:
            agent = await lork.agents.register(
                tenant_id=tenant,
                name=name,
            )
            print("Agent created:", agent.id)

    asyncio.run(run())


if __name__ == "__main__":
    app()
