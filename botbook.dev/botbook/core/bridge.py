from __future__ import annotations

import logging

from botbook.integrations.lork_adapter import LorkAdapter
from botbook.integrations.privatevault_adapter import PrivateVaultAdapter

from .models import MemberProfile, MemberType

logger = logging.getLogger("botbook.bridge")


class BotBookBridge:

    def __init__(self):

        self.lork = LorkAdapter()
        self.vault = PrivateVaultAdapter()

    async def onboard_agent(self, profile: MemberProfile) -> MemberProfile:

        if profile.member_type != MemberType.AGENT:
            return profile

        try:
            profile.lork_agent_id = self.lork.register(profile)
        except Exception:
            profile.lork_agent_id = None

        try:
            profile.vault_id = self.vault.issue_identity(profile)
        except Exception:
            profile.vault_id = None

        profile.trust.update_audit_hash(profile.member_id)

        logger.info(
            f"agent onboarded {profile.member_id} "
            f"lork={profile.lork_agent_id} "
            f"vault={profile.vault_id}"
        )

        return profile

    async def onboard_human(self, profile: MemberProfile) -> MemberProfile:

        try:
            profile.vault_id = self.vault.issue_identity(profile)
        except Exception:
            profile.vault_id = None

        profile.trust.update_audit_hash(profile.member_id)

        logger.info(
            f"human onboarded {profile.member_id} "
            f"vault={profile.vault_id}"
        )

        return profile
