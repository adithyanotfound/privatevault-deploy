"""Unit tests for AgentRegistryService."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lork.models import Agent, AgentStatus
from lork.schemas import AgentCreate, AgentUpdate
from lork.control_plane.services.agent_service import (
    AgentConflictError,
    AgentNotFoundError,
    AgentRegistryService,
)


def make_agent_orm(name: str = "test_agent", org_id: str = "org-1") -> Agent:
    a = Agent()
    a.id = "agent-uuid-1"
    a.organization_id = org_id
    a.name = name
    a.description = ""
    a.status = AgentStatus.PENDING
    a.permissions = []
    a.capabilities = []
    a.llm_provider = "anthropic"
    a.llm_model = "claude-3-5-sonnet-20241022"
    a.system_prompt = ""
    a.max_concurrent_tasks = 1
    a.task_timeout_seconds = 300
    a.metadata_ = {}
    a.tags = []
    a.last_heartbeat_at = None
    return a


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_db: AsyncMock) -> AgentRegistryService:
    return AgentRegistryService(mock_db)


class TestAgentRegistryService:

    @pytest.mark.asyncio
    async def test_create_agent_success(self, service: AgentRegistryService, mock_db: AsyncMock) -> None:

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        data = AgentCreate(
            name="finance_agent",
            permissions=["invoice.read"],
            capabilities=["process_invoice"],
        )

        agent_orm = make_agent_orm("finance_agent")

        with patch(
            "lork.control_plane.services.agent_service.Agent",
            return_value=agent_orm,
        ):
            with patch(
                "lork.control_plane.services.agent_service.AgentResponse.model_validate"
            ) as mock_validate:

                mock_validate.return_value = MagicMock(
                    id="agent-uuid-1", name="finance_agent"
                )

                result = await service.create_agent("org-1", data)

                assert result is not None


    @pytest.mark.asyncio
    async def test_create_agent_conflict(self, service: AgentRegistryService, mock_db: AsyncMock) -> None:

        existing = make_agent_orm("finance_agent")

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
        )

        data = AgentCreate(name="finance_agent")

        with pytest.raises(AgentConflictError):
            await service.create_agent("org-1", data)


    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, service: AgentRegistryService, mock_db: AsyncMock) -> None:

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with pytest.raises(AgentNotFoundError):
            await service.get_agent("nonexistent", "org-1")


    @pytest.mark.asyncio
    async def test_update_agent_status(self, service: AgentRegistryService, mock_db: AsyncMock) -> None:

        agent = make_agent_orm()

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=agent))
        )

        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        with patch(
            "lork.control_plane.services.agent_service.AgentResponse.model_validate"
        ) as mock_v:

            mock_v.return_value = MagicMock(status=AgentStatus.ACTIVE)

            await service.update_agent(
                "agent-uuid-1",
                "org-1",
                AgentUpdate(status=AgentStatus.ACTIVE),
            )

            assert agent.status == AgentStatus.ACTIVE


    @pytest.mark.asyncio
    async def test_record_heartbeat(self, service: AgentRegistryService, mock_db: AsyncMock) -> None:

        agent = make_agent_orm()
        agent.last_heartbeat_at = None

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=agent))
        )

        mock_db.flush = AsyncMock()

        await service.record_heartbeat("agent-uuid-1", "org-1")

        assert agent.last_heartbeat_at is not None


    @pytest.mark.asyncio
    async def test_delete_agent(self, service: AgentRegistryService, mock_db: AsyncMock) -> None:

        agent = make_agent_orm()

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=agent))
        )

        mock_db.delete = AsyncMock()

        await service.delete_agent("agent-uuid-1", "org-1")

        mock_db.delete.assert_called_once_with(agent)

