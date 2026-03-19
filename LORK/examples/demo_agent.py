"""
examples/demo_agent.py
=======================
LORK end-to-end demo.
"""

import asyncio
import logging

from lork.sdk.client import LorkClient
from lork.models import (
    Policy,
    PolicyCondition,
    PolicyEffect,
    PolicyRule,
)
from lork.policy.engine import PolicyEngine
from lork.exceptions import AgentSuspendedError

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("lork.demo")


async def main():

    print("\n============================================================")
    print("  LORK — Control Plane for AI Agents (Demo)")
    print("============================================================\n")

    async with LorkClient.embedded() as lork:

        print("Step 1 — Registering agents")

        finance_agent = await lork.agents.register(
            tenant_id="acme-corp",
            name="finance_agent",
            description="Processes invoices and payment requests.",
            allowed_actions=[
                "finance.read",
                "finance.transfer",
                "data.read",
                "email.send",
            ],
            require_human_approval_for=["finance.transfer"],
            max_llm_calls_per_run=20,
            tags={"team": "finance", "env": "production"},
        )

        support_agent = await lork.agents.register(
            tenant_id="acme-corp",
            name="support_agent",
            description="Answers customer support tickets.",
            allowed_actions=["email.send", "crm.read", "data.read"],
            max_llm_calls_per_run=30,
            tags={"team": "support"},
        )

        print("Agents registered")

        print("\nStep 2 — Activating agents")

        finance_agent = await lork.agents.activate(finance_agent.id)
        support_agent = await lork.agents.activate(support_agent.id)

        print("Agents activated")

        print("\nStep 3 — Policy engine demo")

        policies = [
            Policy(
                id="policy-001",
                tenant_id="acme-corp",
                name="finance_policy",
                rules=[
                    PolicyRule(
                        effect=PolicyEffect.ALLOW,
                        actions=["finance.read", "data.read", "email.send"],
                    ),
                    PolicyRule(
                        effect=PolicyEffect.ALLOW,
                        actions=["finance.transfer"],
                        conditions=[
                            PolicyCondition(field="amount", operator="lte", value=10000),
                        ],
                    ),
                    PolicyRule(
                        effect=PolicyEffect.DENY,
                        actions=["finance.transfer"],
                        conditions=[
                            PolicyCondition(field="amount", operator="gt", value=10000),
                        ],
                    ),
                ],
            )
        ]

        engine = PolicyEngine(policies)

        d1 = engine.evaluate(finance_agent, "finance.read")
        print("finance.read allowed:", d1.allowed)

        d2 = engine.evaluate(finance_agent, "finance.transfer", {"amount": 5000})
        print("transfer 5000 allowed:", d2.allowed)

        d3 = engine.evaluate(finance_agent, "finance.transfer", {"amount": 50000})
        print("transfer 50000 allowed:", d3.allowed)

        print("\nStep 4 — Submitting tasks")

        t1 = await lork.tasks.submit(
            tenant_id="acme-corp",
            agent_id=finance_agent.id,
            task_type="process_invoice",
            payload={"invoice_id": "INV-001"},
            priority=8,
        )

        t2 = await lork.tasks.submit(
            tenant_id="acme-corp",
            agent_id=support_agent.id,
            task_type="answer_ticket",
            payload={"ticket": "Customer cannot login"},
            priority=5,
        )

        print("Tasks submitted:", t1.id, t2.id)

        depth = await lork.tasks.queue_depth()
        print("Queue depth:", depth)

        print("\nStep 5 — Cancelling a task")

        cancelled = await lork.tasks.cancel(t2.id)

        print("Cancelled task status:", cancelled.status.value)

        print("\nStep 6 — Suspending agent")

        await lork.agents.suspend(finance_agent.id)

        try:
            await lork.tasks.submit(
                tenant_id="acme-corp",
                agent_id=finance_agent.id,
                task_type="should_fail",
                payload={},
            )
        except AgentSuspendedError as exc:
            print("Task blocked as expected:", exc)

        print("\nStep 7 — Listing agents")

        agents = await lork.agents.list("acme-corp")

        for a in agents:
            print(a.name, a.status.value)

    print("\nDemo complete. LORK core system working.\n")


if __name__ == "__main__":
    asyncio.run(main())
