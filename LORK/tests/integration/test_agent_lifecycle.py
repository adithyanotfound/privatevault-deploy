"""
tests/integration/test_agent_lifecycle.py
==========================================
Integration tests covering the full agent + task lifecycle.
"""

import asyncio
import pytest

from lork.sdk.client import LorkClient
from lork.models import AgentStatus, TaskStatus
from lork.exceptions import (
    AgentAlreadyExistsError,
    AgentNotFoundError,
    AgentSuspendedError,
)

TENANT = "acme-corp"


@pytest.fixture
async def lork():
    async with LorkClient.embedded() as client:
        yield client


class TestAgentLifecycle:

    async def test_register_and_activate(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="support_agent",
            description="Handles customer support tickets.",
            allowed_actions=["email.send", "crm.read"],
        )

        assert agent.status == AgentStatus.PENDING
        assert agent.name == "support_agent"
        assert agent.tenant_id == TENANT

        active = await lork.agents.activate(agent.id)

        assert active.status == AgentStatus.ACTIVE


    async def test_register_duplicate_name_raises(self, lork):

        await lork.agents.register(
            tenant_id=TENANT,
            name="invoice_agent",
        )

        with pytest.raises(AgentAlreadyExistsError):
            await lork.agents.register(
                tenant_id=TENANT,
                name="invoice_agent",
            )


    async def test_same_name_different_tenant_allowed(self, lork):

        await lork.agents.register(
            tenant_id="tenant-A",
            name="my_agent",
        )

        agent_b = await lork.agents.register(
            tenant_id="tenant-B",
            name="my_agent",
        )

        assert agent_b.tenant_id == "tenant-B"


    async def test_get_nonexistent_agent_raises(self, lork):

        with pytest.raises(AgentNotFoundError):
            await lork.agents.get("does-not-exist")


    async def test_suspend_agent(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="suspended_agent",
        )

        await lork.agents.activate(agent.id)

        suspended = await lork.agents.suspend(
            agent.id,
            reason="Policy violation detected.",
        )

        assert suspended.status == AgentStatus.SUSPENDED


    async def test_list_agents_by_status(self, lork):

        a1 = await lork.agents.register(
            tenant_id=TENANT,
            name="list_agent_1",
        )

        a2 = await lork.agents.register(
            tenant_id=TENANT,
            name="list_agent_2",
        )

        await lork.agents.activate(a1.id)

        active_agents = await lork.agents.list(
            TENANT,
            status=AgentStatus.ACTIVE,
        )

        active_ids = [a.id for a in active_agents]

        assert a1.id in active_ids
        assert a2.id not in active_ids


    async def test_retire_agent(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="retiring_agent",
        )

        await lork.agents.activate(agent.id)

        retired = await lork.agents.retire(agent.id)

        assert retired.status == AgentStatus.RETIRED


class TestTaskSubmission:

    async def test_submit_task_to_active_agent(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="task_agent",
        )

        await lork.agents.activate(agent.id)

        task = await lork.tasks.submit(
            tenant_id=TENANT,
            agent_id=agent.id,
            task_type="process_invoice",
            payload={"invoice_id": "INV-001", "amount": 1500.00},
        )

        assert task.status == TaskStatus.QUEUED
        assert task.input.type == "process_invoice"
        assert task.input.payload["invoice_id"] == "INV-001"


    async def test_submit_task_to_pending_agent_raises(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="pending_agent",
        )

        with pytest.raises(AgentSuspendedError):
            await lork.tasks.submit(
                tenant_id=TENANT,
                agent_id=agent.id,
                task_type="some_task",
                payload={},
            )


    async def test_submit_task_to_suspended_agent_raises(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="susp_task_agent",
        )

        await lork.agents.activate(agent.id)

        await lork.agents.suspend(agent.id)

        with pytest.raises(AgentSuspendedError):
            await lork.tasks.submit(
                tenant_id=TENANT,
                agent_id=agent.id,
                task_type="some_task",
                payload={},
            )


    async def test_task_priority_ordering(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="priority_agent",
        )

        await lork.agents.activate(agent.id)

        await lork.tasks.submit(
            TENANT,
            agent.id,
            "low_task",
            {},
            priority=2,
        )

        await lork.tasks.submit(
            TENANT,
            agent.id,
            "high_task",
            {},
            priority=9,
        )

        await lork.tasks.submit(
            TENANT,
            agent.id,
            "mid_task",
            {},
            priority=5,
        )

        depth = await lork.tasks.queue_depth()

        assert depth == 3


    async def test_cancel_queued_task(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="cancel_agent",
        )

        await lork.agents.activate(agent.id)

        task = await lork.tasks.submit(
            tenant_id=TENANT,
            agent_id=agent.id,
            task_type="cancellable_task",
            payload={},
        )

        cancelled = await lork.tasks.cancel(task.id)

        assert cancelled.status == TaskStatus.CANCELLED


    async def test_list_tasks_for_agent(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="list_tasks_agent",
        )

        await lork.agents.activate(agent.id)

        t1 = await lork.tasks.submit(
            TENANT,
            agent.id,
            "task_type_a",
            {},
        )

        t2 = await lork.tasks.submit(
            TENANT,
            agent.id,
            "task_type_b",
            {},
        )

        tasks = await lork.tasks.list_for_agent(agent.id)

        task_ids = [t.id for t in tasks]

        assert t1.id in task_ids
        assert t2.id in task_ids


class TestConcurrency:

    async def test_concurrent_task_submission(self, lork):

        agent = await lork.agents.register(
            tenant_id=TENANT,
            name="concurrent_agent",
        )

        await lork.agents.activate(agent.id)

        async def submit_task(i):

            return await lork.tasks.submit(
                TENANT,
                agent.id,
                f"task_{i}",
                {"index": i},
            )

        tasks = await asyncio.gather(
            *[submit_task(i) for i in range(20)]
        )

        assert len(tasks) == 20
        assert all(t.status == TaskStatus.QUEUED for t in tasks)

        depth = await lork.tasks.queue_depth()

        assert depth == 20
