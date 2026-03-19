"""
examples/demo_langgraph.py
==========================
LORK + LangGraph integration demo.

Shows how to inject LORK's policy engine as a node in a LangGraph
state machine, so every state transition that involves tool execution
is checked against LORK policies first.

Requirements:
    pip install lork langgraph langchain-openai

Pattern:
  ┌──────────┐     ┌──────────────┐     ┌──────────┐
  │  LLM     │────▶│  LORK Policy │────▶│  Tool    │
  │  Node    │     │  Guard Node  │     │  Node    │
  └──────────┘     └──────────────┘     └──────────┘
                         │
                         ▼ (if denied)
                   ┌──────────────┐
                   │  Blocked     │
                   │  Response    │
                   └──────────────┘

The LORK guard node sits between the LLM decision and tool execution.
It's a pure function: takes state, returns state with policy decision.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from lork.sdk.client import LorkClient
from lork.models import Policy, PolicyRule, PolicyCondition, PolicyEffect
from lork.policy.engine import PolicyEngine
from lork.exceptions import PolicyDeniedError

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("LangGraph not installed. Running policy node demo only.")
    print("Install with: pip install langgraph langchain-openai\n")


# ---------------------------------------------------------------------------
# Shared state schema
# ---------------------------------------------------------------------------

class AgentState(dict):
    """Shared LangGraph state object."""
    pass


# ---------------------------------------------------------------------------
# LORK Policy Guard Node
# ---------------------------------------------------------------------------

class LorkPolicyGuardNode:
    """
    LangGraph node enforcing LORK policies before tool execution.
    """

    def __init__(self, engine: PolicyEngine, agent):
        self._engine = engine
        self._agent = agent

    def __call__(self, state: AgentState) -> AgentState:
        pending_tool = state.get("pending_tool_call")

        if not pending_tool:
            return {**state, "lork_allowed": True}

        tool_name = pending_tool.get("name", "")
        arguments = pending_tool.get("arguments", {})

        try:
            decision = self._engine.enforce(
                agent=self._agent,
                action="api.call",
                context={"tool_name": tool_name, **arguments},
            )
            return {
                **state,
                "lork_allowed": True,
                "lork_reason": decision.reason,
                "lork_requires_approval": decision.requires_approval,
            }
        except PolicyDeniedError as exc:
            return {
                **state,
                "lork_allowed": False,
                "lork_reason": str(exc),
            }


# ---------------------------------------------------------------------------
# Mock LLM node
# ---------------------------------------------------------------------------

def mock_llm_node(state: AgentState) -> AgentState:
    task = state.get("task", "")
    print(f"  [LLM] Task: {task}")

    if "invoice" in task.lower():
        tool_call = {"name": "read_invoice", "arguments": {"invoice_id": "INV-001"}}
    elif "transfer" in task.lower():
        tool_call = {"name": "transfer_funds", "arguments": {"amount": 75000}}
    elif "delete" in task.lower():
        tool_call = {"name": "delete_records", "arguments": {"table": "customers"}}
    else:
        tool_call = {"name": "search_knowledge_base", "arguments": {"query": task}}

    print(f"  [LLM] Requesting tool: {tool_call['name']}")
    return {**state, "pending_tool_call": tool_call}


def mock_tool_node(state: AgentState) -> AgentState:
    tool = state.get("pending_tool_call", {})
    print(f"  [Tool] Executing: {tool.get('name')} ✓")
    return {
        **state,
        "tool_result": f"[Mock result from {tool.get('name')}]",
        "pending_tool_call": None,
    }


def blocked_response_node(state: AgentState) -> AgentState:
    reason = state.get("lork_reason", "Policy denied")
    print(f"  [Blocked] {reason}")
    return {
        **state,
        "tool_result": f"Blocked: {reason}",
        "pending_tool_call": None,
    }


def route_after_guard(state: AgentState) -> Literal["execute_tool", "blocked"]:
    return "execute_tool" if state.get("lork_allowed") else "blocked"


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

async def main():
    print("\n" + "═"*65)
    print("  LORK + LangGraph Integration Demo")
    print("═"*65 + "\n")

    async with LorkClient.embedded() as lork:

        agent = await lork.agents.register(
            tenant_id="acme-corp",
            name="langgraph_finance_agent",
            description="LangGraph-powered finance automation agent.",
            allowed_actions=["api.call", "data.read"],
            allowed_tools=["read_invoice", "search_knowledge_base"],
        )

        await lork.agents.activate(agent.id)

        policies = [
            Policy(
                tenant_id="acme-corp",
                name="finance_graph_policy",
                rules=[
                    PolicyRule(
                        effect=PolicyEffect.ALLOW,
                        actions=["api.call"],
                        conditions=[
                            PolicyCondition(
                                field="tool_name",
                                operator="in",
                                value=["read_invoice", "search_knowledge_base"],
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
                                value=["transfer_funds", "delete_records", "drop_table"],
                            )
                        ],
                    ),
                ],
            )
        ]

        engine = PolicyEngine(policies=policies)
        guard_node = LorkPolicyGuardNode(engine, agent)

        if LANGGRAPH_AVAILABLE:
            graph_builder = StateGraph(AgentState)

            graph_builder.add_node("llm", mock_llm_node)
            graph_builder.add_node("lork_guard", guard_node)
            graph_builder.add_node("execute_tool", mock_tool_node)
            graph_builder.add_node("blocked", blocked_response_node)

            graph_builder.set_entry_point("llm")

            graph_builder.add_edge("llm", "lork_guard")
            graph_builder.add_conditional_edges("lork_guard", route_after_guard)

            graph_builder.add_edge("execute_tool", END)
            graph_builder.add_edge("blocked", END)

            graph = graph_builder.compile()

            tasks_to_run = [
                "Read invoice INV-001",
                "Transfer $75,000 to external account",
                "Delete all customer records",
                "Search knowledge base for refund policy",
            ]

            for task_desc in tasks_to_run:
                print(f"\n── Task: {task_desc}")
                result = graph.invoke({"task": task_desc})
                print(f"  Outcome: {result.get('tool_result')}")
        else:
            tasks = [
                "Read invoice INV-001",
                "Transfer $75,000",
                "Search knowledge base",
            ]

            for task_desc in tasks:
                print(f"\n── Task: {task_desc}")
                state: AgentState = {"task": task_desc}

                state = mock_llm_node(state)
                state = guard_node(state)

                if state.get("lork_allowed"):
                    state = mock_tool_node(state)
                else:
                    state = blocked_response_node(state)

                print(f"  Outcome: {state.get('tool_result')}")

    print("\n" + "═"*65)
    print("LangGraph demo complete.")
    print("LORK intercepted every tool call before execution.")
    print("═"*65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
