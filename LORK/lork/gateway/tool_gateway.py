from typing import Callable, Dict


class ToolGateway:

    def __init__(self, policy_engine):
        self.policy_engine = policy_engine
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    async def invoke(self, agent_id: str, tool_name: str, args: dict, run_id: str):

        allowed = await self.policy_engine.check(
            agent_id=agent_id,
            action=f"tool:{tool_name}",
            context={"run_id": run_id, "args": args}
        )

        if not allowed:
            raise PermissionError(
                f"Agent {agent_id} denied tool {tool_name}"
            )

        tool = self.tools.get(tool_name)

        if not tool:
            raise ValueError(f"Tool {tool_name} not registered")

        return await tool(**args)
