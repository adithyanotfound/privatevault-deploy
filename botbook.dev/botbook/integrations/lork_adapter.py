import os
import sys
import uuid
import hashlib

LORK_PATH = os.getenv("LORK_PATH", os.path.expanduser("~/LORk"))
if LORK_PATH not in sys.path:
    sys.path.append(LORK_PATH)

class LorkAdapter:

    def __init__(self):
        self.fn = None
        try:
            # try common LORK identity helpers
            from lork.identity import register_agent_identity as fn
            self.fn = fn
        except Exception:
            try:
                from lork.agent import register as fn
                self.fn = fn
            except Exception:
                self.fn = None

    def register(self, profile):

        # if LORK exposes a helper use it
        if self.fn:
            try:
                return self.fn(
                    name=profile.name,
                    owner=profile.owner_id,
                    permissions=profile.capabilities,
                    botbook_id=profile.member_id
                )
            except Exception:
                pass

        # deterministic fallback based on LORK logic style
        payload = f"{profile.name}:{profile.member_id}"
        return "lork_" + hashlib.sha256(payload.encode()).hexdigest()[:12]
