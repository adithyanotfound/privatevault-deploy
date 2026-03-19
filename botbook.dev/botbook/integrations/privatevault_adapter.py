import os
import sys
import hashlib

VAULT_PATH = os.getenv("PRIVATEVAULT_PATH", os.path.expanduser("~/PrivateVault.ai"))
if VAULT_PATH not in sys.path:
    sys.path.append(VAULT_PATH)

class PrivateVaultAdapter:

    def __init__(self):
        self.issue = None
        try:
            from agent_identity import issue_identity
            self.issue = issue_identity
        except Exception:
            self.issue = None

    def issue_identity(self, profile):

        if self.issue:
            try:
                return self.issue(
                    member_id=profile.member_id,
                    name=profile.name,
                    capabilities=profile.capabilities
                )
            except Exception:
                pass

        # fallback deterministic vault identity
        payload = f"{profile.member_id}:{profile.name}"
        return "vault_" + hashlib.sha256(payload.encode()).hexdigest()[:12]
