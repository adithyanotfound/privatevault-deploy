"""
LORK Python SDK.

Usage:
    from lork.sdk.client import LORKClient

    client = LORKClient(api_key="lork_...", base_url="https://api.lork.ai")

    agent = client.agents.create(
        name="finance_agent",
        permissions=["invoice.read", "payment.request"],
        capabilities=["process_invoice", "summarize_report"],
    )

    task = client.tasks.submit(
        task_type="process_invoice",
        input_data={"invoice_id": "INV-001"},
        agent_id=agent["id"],
    )

    result = client.tasks.wait(task["id"], timeout=60)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx


class LORKError(Exception):
    def __init__(self, message: str, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class AuthenticationError(LORKError):
    pass


class NotFoundError(LORKError):
    pass


class PolicyViolationError(LORKError):
    pass


@dataclass
class AgentConfig:
    name: str
    permissions: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    description: str = ""
    llm_provider: str = "anthropic"
    llm_model: str = "claude-3-5-sonnet-20241022"
    system_prompt: str = ""
    max_concurrent_tasks: int = 1
    task_timeout_seconds: int = 300
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


class _BaseResource:
    def __init__(self, client: "LORKClient") -> None:
        self._client = client

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        return self._client._request(method, path, **kwargs)


class AgentsResource(_BaseResource):

    def create(self, **kwargs: Any) -> dict[str, Any]:
        return self._request("POST", "/agents", json=kwargs)

    def get(self, agent_id: str) -> dict[str, Any]:
        return self._request("GET", f"/agents/{agent_id}")

    def list(self, status: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        return self._request("GET", "/agents", params=params)

    def update(self, agent_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("PATCH", f"/agents/{agent_id}", json=kwargs)

    def activate(self, agent_id: str) -> dict[str, Any]:
        return self._request("POST", f"/agents/{agent_id}/activate")

    def suspend(self, agent_id: str) -> dict[str, Any]:
        return self._request("POST", f"/agents/{agent_id}/suspend")

    def terminate(self, agent_id: str) -> dict[str, Any]:
        return self._request("POST", f"/agents/{agent_id}/terminate")

    def heartbeat(self, agent_id: str) -> None:
        self._request("POST", f"/agents/{agent_id}/heartbeat")

    def delete(self, agent_id: str) -> None:
        self._request("DELETE", f"/agents/{agent_id}")


class TasksResource(_BaseResource):

    def submit(
        self,
        task_type: str,
        input_data: dict[str, Any] | None = None,
        agent_id: str | None = None,
        priority: int = 5,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:

        body: dict[str, Any] = {
            "task_type": task_type,
            "input_data": input_data or {},
            "priority": priority,
            "timeout_seconds": timeout_seconds,
        }

        if agent_id:
            body["agent_id"] = agent_id

        return self._request("POST", "/tasks", json=body)

    def get(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tasks/{task_id}")

    def list(
        self,
        status: str | None = None,
        agent_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:

        params: dict[str, Any] = {"page": page, "page_size": page_size}

        if status:
            params["status"] = status

        if agent_id:
            params["agent_id"] = agent_id

        return self._request("GET", "/tasks", params=params)

    def cancel(self, task_id: str) -> dict[str, Any]:
        return self._request("POST", f"/tasks/{task_id}/cancel")

    def wait(
        self,
        task_id: str,
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:

        terminal = {"completed", "failed", "cancelled", "timed_out"}
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:

            task = self.get(task_id)

            if task.get("status") in terminal:

                if task.get("status") == "failed":
                    raise LORKError(
                        f"Task failed: {task.get('error', 'unknown error')}",
                        detail=task,
                    )

                return task

            time.sleep(poll_interval)

        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


class PoliciesResource(_BaseResource):

    def create(self, **kwargs: Any) -> dict[str, Any]:
        return self._request("POST", "/policies", json=kwargs)

    def list(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self._request("GET", "/policies", params={"page": page, "page_size": page_size})

    def get(self, policy_id: str) -> dict[str, Any]:
        return self._request("GET", f"/policies/{policy_id}")

    def delete(self, policy_id: str) -> None:
        self._request("DELETE", f"/policies/{policy_id}")

    def check(self, agent_id: str, action: str, resource: str, context: dict | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            "/policies/check",
            json={
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": context or {},
            },
        )


class AuditResource(_BaseResource):

    def list(
        self,
        agent_id: str | None = None,
        event_type: str | None = None,
        severity: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:

        params: dict[str, Any] = {"page": page, "page_size": page_size}

        if agent_id:
            params["agent_id"] = agent_id

        if event_type:
            params["event_type"] = event_type

        if severity:
            params["severity"] = severity

        return self._request("GET", "/audit-logs", params=params)


class LORKClient:

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.lork.ai",
        timeout: float = 30.0,
    ) -> None:

        self._api_key = api_key
        self._base_url = base_url.rstrip("/") + "/api/v1"

        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

        self.agents = AgentsResource(self)
        self.tasks = TasksResource(self)
        self.policies = PoliciesResource(self)
        self.audit = AuditResource(self)

    def health(self) -> dict[str, Any]:
        response = self._http.get("/health")
        return response.json()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:

        response = self._http.request(method, path, **kwargs)

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)

        if response.status_code == 403:
            raise PolicyViolationError("Access denied", status_code=403, detail=response.json())

        if response.status_code == 404:
            raise NotFoundError(f"Resource not found: {path}", status_code=404)

        if response.status_code == 204:
            return None

        if not response.is_success:
            raise LORKError(
                f"API error {response.status_code}",
                status_code=response.status_code,
                detail=response.text,
            )

        return response.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "LORKClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
