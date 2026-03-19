"""
examples/demo_crewai.py
========================
LORK + CrewAI integration demo.

Shows how to wrap LORK policy enforcement around a CrewAI agent so every
tool call the agent makes is governed by LORK policies before execution.

Requirements:
    pip install lork crewai openai

What this demonstrates:
  - Register a CrewAI agent identity in LORK
  - Wrap CrewAI tool execution with LORK policy checks
  - Full audit trail of every tool call automatically recorded
  - Policy violation halts the agent before any harm is done

Run:
    OPENAI_API_KEY=sk-... python examples/demo_crewai.py
"""

from __future__ import annotations

import asyncio
import os

# ── LORK imports ──────────────────────────────────────────────────────────────
from lork.sdk.client import LorkClient
from lork.models import Policy, PolicyRule, PolicyCondition, PolicyEffect
from lork.policy.engine import PolicyEngine
from lork.exceptions import PolicyDeniedError

# ── CrewAI imports (optional — gracefully skip if not installed) ───────────────
try:
    from crewai import Agent as CrewAgent, Task as CrewTask, Crew
    from crewai.tools import BaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("CrewAI not installed. Running policy demo without CrewAI agent.\n"
          "Install with: pip install crewai openai")


# ---------------------------------------------------------------------------
# LORK-guarded tool wrapper
# ---------------------------------------------------------------------------

class LorkGuardedTool:
    """
    Wraps any callable tool with LORK policy enforcement.
    """

    def __init__(self, name: str, fn, agent, engine: PolicyEngine):
        self.name = name
        self._fn = fn
        self._agent = agent
        self._engine = engine

    def __call__(self, **kwargs):
        try:
            decision = self._engine.enforce(
                agent=self._agent,
                action="api.call",
                context={"tool_name": self.name, **kwargs},
            )
            if decision.requires_approval:
                print(f"  ⚠  [{self.name}] LORK: Human approval required — blocking.")
                return "Action blocked: requires human approval."
        except PolicyDeniedError as exc:
            print(f"  ✗  [{self.name}] LORK BLOCKED: {exc}")
            return f"Action blocked by LORK policy: {exc}"

        print(f"  ✓  [{self.name}] LORK: Allowed. Executing tool...")
        result = self._fn(**kwargs)
        return result


# ---------------------------------------------------------------------------
# Demo tools
# ---------------------------------------------------------------------------

def search_web(query: str) -> str:
    return f"[Mock search results for: {query}]"


def send_email(to: str, subject: str, body: str) -> str:
    return f"[Mock] Email sent to {to}: '{subject}'"


def transfer_funds(amount: float, account: str) -> str:
    return f"[Mock] Transferred ${amount} to {account}"


def delete_database(table: str) -> str:
    return f"[Mock] DELETED table {table}"


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

async def main():
    print("\n" + "═"*65)
    print("  LORK + CrewAI Integration Demo")
    print("═"*65 + "\n")

    async with LorkClient.embedded() as lork:

        print("── 1. Registering CrewAI agent in LORK ──────────────────────")

        agent = await lork.agents.register(
            tenant_id="acme-corp",
            name="research_agent",
            description="CrewAI research agent.",
            allowed_actions=["api.call", "email.send", "data.read"],
            allowed_tools=["search_web", "send_email"],
            require_human_approval_for=["email.send"],
            max_llm_calls_per_run=20,
            tags={"framework": "crewai"},
        )

        await lork.agents.activate(agent.id)

        print(f"  ✓ Agent '{agent.name}' registered and active\n")

        print("── 2. Defining governance policies ─────────────────────────")

        policies = [
            Policy(
                tenant_id="acme-corp",
                name="research_agent_policy",
                rules=[
                    PolicyRule(
                        effect=PolicyEffect.ALLOW,
                        actions=["api.call"],
                        conditions=[
                            PolicyCondition(
                                field="tool_name",
                                operator="in",
                                value=["search_web", "send_email"],
                            )
                        ],
                    ),
                    PolicyRule(
                        effect=PolicyEffect.DENY,
                        actions=["api.call"],
                        conditions=[
                            PolicyCondition(
                                field="tool_name",
                                operator="in",
                                value=["transfer_funds", "delete_database"],
                            )
                        ],
                    ),
                ],
            )
        ]

        engine = PolicyEngine(policies=policies)

        print("  ✓ Policies loaded\n")

        print("── 3. Wrapping tools with LORK guards ───────────────────────")

        guarded_search = LorkGuardedTool("search_web", search_web, agent, engine)
        guarded_email = LorkGuardedTool("send_email", send_email, agent, engine)
        guarded_transfer = LorkGuardedTool("transfer_funds", transfer_funds, agent, engine)
        guarded_delete = LorkGuardedTool("delete_database", delete_database, agent, engine)

        print("  ✓ Tools wrapped\n")

        print("── 4. Simulating agent tool calls ───────────────────────────")

        print("\n  [Tool call 1] search_web")
        print(guarded_search(query="AI safety research"))

        print("\n  [Tool call 2] send_email")
        print(guarded_email(
            to="cto@acme.com",
            subject="Research Summary",
            body="Findings attached",
        ))

        print("\n  [Tool call 3] transfer_funds")
        print(guarded_transfer(amount=50000.0, account="ACC-999"))

        print("\n  [Tool call 4] delete_database")
        print(guarded_delete(table="users"))

        print("\n── 5. Submitting task to LORK scheduler ─────────────────────")

        task = await lork.tasks.submit(
            tenant_id="acme-corp",
            agent_id=agent.id,
            task_type="research_report",
            payload={"topic": "AI agent safety"},
            priority=7,
        )

        print(f"  ✓ Task {task.id[:12]} queued (status={task.status.value})")

    print("\n" + "═"*65)
    print("Demo complete.")
    print("All tool calls were governed by LORK policy.")
    print("═"*65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
