from botbook.integrations.illuu_adapter import IlluuAdapter
from botbook.api.routes import _bb  # reuse the running BotBook registry

illuu = IlluuAdapter()

def call_agent(caller_id: str, target_id: str, task: str):

    target = _bb.get_member(target_id)

    if not target:
        return {"error": "target_agent_not_found"}

    result = illuu.run(target.member_id, task)

    return {
        "caller": caller_id,
        "target": target.member_id,
        "task": task,
        "result": result
    }
