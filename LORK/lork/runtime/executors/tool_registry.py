"""
Tool Registry — pluggable tool system for agent actions.
Tools are registered with JSON Schema definitions and async handlers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from lork.observability.logging import get_logger

log = get_logger(__name__)


@dataclass
class ToolCall:
    name: str
    input: dict[str, Any]


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[Any]]


class ToolNotFoundError(Exception):
    pass


class ToolRegistry:
    """
    Central registry of all tools available to agents.
    Tools can be added dynamically via register().
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._register_builtin_tools()

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool
        log.debug("tool.registered", name=tool.name)

    async def execute(self, call: ToolCall) -> Any:
        tool = self._tools.get(call.name)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{call.name}' is not registered")

        log.info("tool.executing", tool=call.name, input_keys=list(call.input.keys()))
        result = await tool.handler(call.input)
        log.info("tool.executed", tool=call.name)

        return result

    def get_anthropic_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def get_openai_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in self._tools.values()
        ]

    def _register_builtin_tools(self) -> None:

        self.register(ToolDefinition(
            name="web_search",
            description="Search the web for information.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
            handler=self._web_search,
        ))

        self.register(ToolDefinition(
            name="http_request",
            description="Make an HTTP request to an external API.",
            input_schema={
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                },
                "required": ["method", "url"],
            },
            handler=self._http_request,
        ))

        self.register(ToolDefinition(
            name="data_transform",
            description="Transform, filter, or aggregate structured data.",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["filter", "map", "aggregate", "sort"]},
                    "data": {"type": "array"},
                    "expression": {"type": "string"},
                },
                "required": ["operation", "data"],
            },
            handler=self._data_transform,
        ))

        self.register(ToolDefinition(
            name="send_notification",
            description="Send a notification to a channel (email, slack, webhook).",
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "enum": ["email", "slack", "webhook"]},
                    "destination": {"type": "string"},
                    "subject": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["channel", "destination", "message"],
            },
            handler=self._send_notification,
        ))

    # ── Built-in tool handlers ─────────────────────────────────────────────────

    async def _web_search(self, input: dict[str, Any]) -> str:
        query = input.get("query", "")
        log.info("tool.web_search", query=query)
        return f"[Search results for: {query}] — integrate with your preferred search provider."

    async def _http_request(self, input: dict[str, Any]) -> dict[str, Any]:

        import httpx

        method = input.get("method", "GET")
        url = input.get("url", "")
        headers = input.get("headers", {})
        body = input.get("body")

        async with httpx.AsyncClient(timeout=30.0) as client:

            response = await client.request(method, url, headers=headers, json=body)

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text[:4000],
            }

    async def _data_transform(self, input: dict[str, Any]) -> Any:

        operation = input.get("operation")
        data = input.get("data", [])

        if operation == "filter":

            expr = input.get("expression", "")

            if "=" in expr:
                key, _, value = expr.partition("=")
                return [item for item in data if str(item.get(key.strip())) == value.strip()]

        elif operation == "sort":

            expr = input.get("expression", "")
            return sorted(data, key=lambda x: x.get(expr, ""))

        elif operation == "aggregate":

            return {"count": len(data), "items": data}

        return data

    async def _send_notification(self, input: dict[str, Any]) -> str:

        channel = input.get("channel")
        destination = input.get("destination")
        message = input.get("message")

        log.info("tool.notification.sent", channel=channel, destination=destination)

        return f"Notification sent via {channel} to {destination}"
