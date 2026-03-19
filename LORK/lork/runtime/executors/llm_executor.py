"""
LLM Executor — runs the agentic ReAct loop.
Supports Anthropic and OpenAI with tool use, step recording, and policy gating.
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from lork.config import get_settings
from lork.models import TaskStep
from lork.observability.logging import get_logger
from lork.policy.policy_engine import PolicyContext, PolicyEngine, record_policy_decision
from lork.runtime.executors.tool_registry import ToolCall, ToolRegistry

log = get_logger(__name__)


class ExecutionError(Exception):
    pass


class PolicyViolationError(Exception):
    pass


class LLMExecutor:
    """
    Runs an agent task using a ReAct-style loop:
    1. Send context + tools to LLM
    2. LLM responds with text or a tool call
    3. Gate tool calls through the policy engine
    4. Execute approved tool calls
    5. Feed results back to LLM
    6. Repeat until task complete or max steps reached
    """

    def __init__(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        max_steps: int,
        tool_registry: ToolRegistry,
    ) -> None:
        self._provider = provider
        self._model = model
        self._system_prompt = system_prompt
        self._max_steps = max_steps
        self._tool_registry = tool_registry
        self._settings = get_settings()

    async def run(
        self,
        task_type: str,
        input_data: dict[str, Any],
        agent_id: str | None,
        organization_id: str,
        db: AsyncSession,
        task_id: str,
    ) -> dict[str, Any]:

        messages: list[dict[str, Any]] = []
        step_number = 0
        total_tokens = 0

        user_message = self._build_user_message(task_type, input_data)
        messages.append({"role": "user", "content": user_message})

        for step in range(self._max_steps):

            step_number = step + 1
            step_start = time.perf_counter()

            log.debug(
                "executor.step",
                task_id=task_id,
                step=step_number,
                provider=self._provider,
            )

            response = await self._call_llm(messages)
            total_tokens += response.get("usage", {}).get("total_tokens", 0)

            step_duration_ms = int((time.perf_counter() - step_start) * 1000)

            db.add(TaskStep(
                task_id=task_id,
                step_number=step_number,
                step_type="llm_call",
                input_data={"messages_count": len(messages), "step": step_number},
                output_data={"content_type": response.get("stop_reason", "unknown")},
                llm_tokens_used=response.get("usage", {}).get("total_tokens", 0),
                duration_ms=step_duration_ms,
            ))

            await db.flush()

            stop_reason = response.get("stop_reason", "end_turn")
            content = response.get("content", [])

            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []

            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_calls.append(block)

            messages.append({"role": "assistant", "content": content})

            if stop_reason == "end_turn" and not tool_calls:

                final_text = " ".join(text_parts).strip()

                log.info(
                    "executor.complete",
                    task_id=task_id,
                    steps=step_number,
                    total_tokens=total_tokens,
                )

                return {
                    "output": final_text,
                    "steps": step_number,
                    "total_tokens": total_tokens,
                    "task_type": task_type,
                }

            tool_results: list[dict[str, Any]] = []

            for tool_call in tool_calls:

                tool_name = tool_call.get("name", "")
                tool_input = tool_call.get("input", {})
                tool_use_id = tool_call.get("id", "")

                if agent_id:

                    policy_engine = PolicyEngine(db)

                    ctx = PolicyContext(
                        agent_id=agent_id,
                        organization_id=organization_id,
                        action=f"tool.{tool_name}",
                        resource=tool_input.get("resource", "*"),
                        extra={"tool_input": tool_input, "task_id": task_id},
                    )

                    decision = await policy_engine.check(ctx)

                    await record_policy_decision(db, ctx, decision, task_id=task_id)

                    if not decision.allowed:

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"[BLOCKED by policy: {decision.reason}]",
                            "is_error": True,
                        })

                        log.warning(
                            "executor.tool.blocked",
                            tool=tool_name,
                            reason=decision.reason,
                            task_id=task_id,
                        )

                        continue

                tool_step_start = time.perf_counter()

                try:

                    tool_result = await self._tool_registry.execute(
                        ToolCall(name=tool_name, input=tool_input)
                    )

                    result_content = str(tool_result)
                    is_error = False

                except Exception as exc:

                    result_content = f"[Tool error: {exc}]"
                    is_error = True

                    log.warning("executor.tool.error", tool=tool_name, error=str(exc))

                tool_duration_ms = int((time.perf_counter() - tool_step_start) * 1000)

                db.add(TaskStep(
                    task_id=task_id,
                    step_number=step_number,
                    step_type="tool_call",
                    input_data={"tool": tool_name, "input": tool_input},
                    output_data={"result": result_content[:500], "is_error": is_error},
                    duration_ms=tool_duration_ms,
                ))

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_content,
                    "is_error": is_error,
                })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            await db.flush()

        raise ExecutionError(f"Task exceeded max steps ({self._max_steps})")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_llm(self, messages: list[dict[str, Any]]) -> dict[str, Any]:

        if self._provider == "anthropic":
            return await self._call_anthropic(messages)

        if self._provider == "openai":
            return await self._call_openai(messages)

        raise ExecutionError(f"Unknown LLM provider: {self._provider}")

    async def _call_anthropic(self, messages: list[dict[str, Any]]) -> dict[str, Any]:

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._settings.ANTHROPIC_API_KEY)
        tools = self._tool_registry.get_anthropic_tool_schemas()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": messages,
        }

        if self._system_prompt:
            kwargs["system"] = self._system_prompt

        if tools:
            kwargs["tools"] = tools

        response = await client.messages.create(**kwargs)

        return {
            "content": [block.model_dump() for block in response.content],
            "stop_reason": response.stop_reason,
            "usage": {
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
        }

    async def _call_openai(self, messages: list[dict[str, Any]]) -> dict[str, Any]:

        import openai

        client = openai.AsyncOpenAI(api_key=self._settings.OPENAI_API_KEY)
        tools = self._tool_registry.get_openai_tool_schemas()

        response = await client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": self._system_prompt}, *messages]
            if self._system_prompt else messages,
            tools=tools if tools else openai.NOT_GIVEN,
            max_tokens=4096,
        )

        choice = response.choices[0]

        content: list[dict[str, Any]] = []

        if choice.message.content:
            content.append({"type": "text", "text": choice.message.content})

        if choice.message.tool_calls:

            import json

            for tc in choice.message.tool_calls:

                content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                })

        return {
            "content": content,
            "stop_reason": "tool_use" if choice.message.tool_calls else "end_turn",
            "usage": {"total_tokens": response.usage.total_tokens if response.usage else 0},
        }

    @staticmethod
    def _build_user_message(task_type: str, input_data: dict[str, Any]) -> str:

        lines = [f"Task type: {task_type}", ""]

        for key, value in input_data.items():
            lines.append(f"{key}: {value}")

        return "\n".join(lines)
