from botbook.tools.registry import get_tool
from botbook.integrations.privatevault_adapter import PrivateVaultAdapter

vault = PrivateVaultAdapter()

def run_tool(agent_id, tool_name, args):

    tool = get_tool(tool_name)

    if not tool:
        return {"error": "tool_not_found"}

    # governance check
    allowed = True
    try:
        if hasattr(vault, "authorize"):
            allowed = vault.authorize(agent_id, tool_name)
    except Exception:
        pass

    if not allowed:
        return {"error": "tool_blocked_by_policy"}

    try:
        result = tool(**args)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
