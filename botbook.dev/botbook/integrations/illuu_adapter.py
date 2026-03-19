import os
import sys

BASE = os.path.expanduser(
    "~/illuu/vault/legacy/enterprise-pilot/privatevault-enterprise-pilot/runtime"
)

if BASE not in sys.path:
    sys.path.append(BASE)

class IlluuAdapter:

    def __init__(self):
        self.runner = None
        try:
            from execute_and_log import execute_and_log
            self.runner = execute_and_log
        except Exception as e:
            print("Illuu import failed:", e)

    def run(self, agent_id, task):

        if not self.runner:
            return {"status": "illuu_not_loaded"}

        intent = {
            "domain": "botbook",
            "intent": task,
            "actor": agent_id,
            "payload": {
                "task": task
            }
        }

        try:
            result = self.runner(intent)

            return {
                "status": "executed",
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
