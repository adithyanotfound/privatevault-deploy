"""
Agent Manifest Loader
=====================

Allows defining agents via YAML files.
Similar to Kubernetes resource manifests.

Example:

apiVersion: lork.dev/v1
kind: Agent
metadata:
  name: finance_agent
spec:
  tenant_id: acme
  description: Handles finance automation
"""

from __future__ import annotations

import yaml
from pathlib import Path

from lork.sdk.client import LorkClient


async def apply_manifest(path: str):
    data = yaml.safe_load(Path(path).read_text())

    if data["kind"] != "Agent":
        raise ValueError("Unsupported resource kind")

    spec = data["spec"]

    async with LorkClient.embedded() as lork:
        agent = await lork.agents.register(
            tenant_id=spec["tenant_id"],
            name=data["metadata"]["name"],
            description=spec.get("description", ""),
        )

        await lork.agents.activate(agent.id)

        return agent
