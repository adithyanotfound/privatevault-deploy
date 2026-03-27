"""
agent_policy_engine.py — Role-Specific Agent Policy Evaluation

Each mesh agent evaluates a proposed action independently based on
its role-specific rules. These are DETERMINISTIC rules (no LLM) —
this is governance, not inference.

Thresholds come from weight_config.py → agent_policies so enterprises
can tune them.
"""

from coordination.trust.weight_config import get_weights


class PolicyEngine:
    """Role-specific deterministic policy evaluation for mesh agents."""

    def evaluate(self, agent_id: str, request: dict,
                 tenant_id: str = None) -> tuple:
        """
        Evaluate a request from the perspective of a specific agent role.

        Args:
            agent_id: e.g. "pricing_agent", "risk_agent"
            request: {"action": "approve_discount", "amount": 300000, ...}
            tenant_id: optional enterprise tenant for weight config

        Returns:
            (decision: str, reason: str) — "APPROVE"/"REJECT" + explanation
        """
        w = get_weights(tenant_id)
        policies = w.get("agent_policies", {})
        thresholds = w.get("policy_thresholds", {})

        action = request.get("action", "")
        amount = float(request.get("amount", 0))
        context = request.get("context", {})

        # Route to the correct evaluator
        role = agent_id.lower().replace(" ", "_")

        if "pricing" in role:
            return self._eval_pricing(amount, context, policies.get("pricing_agent", {}), thresholds)
        elif "risk" in role:
            return self._eval_risk(amount, context, policies.get("risk_agent", {}), thresholds)
        elif "revenue" in role:
            return self._eval_revenue(amount, context, policies.get("revenue_agent", {}), thresholds)
        elif "compliance" in role or "legal" in role:
            return self._eval_compliance(action, amount, context, policies.get("compliance_agent", {}))
        elif "margin" in role:
            return self._eval_margin(amount, context, policies.get("margin_agent", {}))
        else:
            # Generic agent — evaluate based on amount thresholds
            return self._eval_generic(amount, thresholds)

    def _eval_pricing(self, amount, context, policy, thresholds):
        """Pricing agent: evaluates discount % and competitive positioning."""
        discount_pct = context.get("discount_percent", 0)
        if discount_pct == 0 and amount > 0:
            deal_value = context.get("deal_value", amount * 5)
            if deal_value > 0:
                discount_pct = (amount / deal_value) * 100

        approve_below = policy.get("approve_below_percent", 20)
        reject_above = policy.get("reject_above_percent", 30)

        if discount_pct <= approve_below:
            return ("APPROVE", f"Discount {discount_pct:.1f}% within competitive range (≤{approve_below}%)")
        elif discount_pct >= reject_above:
            return ("REJECT", f"Discount {discount_pct:.1f}% exceeds maximum threshold (≥{reject_above}%)")
        else:
            # Gray zone — approve with caution
            return ("APPROVE", f"Discount {discount_pct:.1f}% in review range ({approve_below}%-{reject_above}%), borderline acceptable")

    def _eval_risk(self, amount, context, policy, thresholds):
        """Risk agent: evaluates financial exposure and risk factors."""
        approve_below = policy.get("approve_below_amount", 200_000)
        reject_above = policy.get("reject_above_amount", 300_000)

        if amount <= approve_below:
            return ("APPROVE", f"Amount ${amount:,.0f} within safe threshold (≤${approve_below:,.0f})")
        elif amount >= reject_above:
            return ("REJECT", f"Amount ${amount:,.0f} exceeds risk threshold (≥${reject_above:,.0f})")
        else:
            # Gray zone
            risk_factors = []
            if context.get("new_customer", False):
                risk_factors.append("new customer")
            if context.get("cross_border", False):
                risk_factors.append("cross-border")

            if risk_factors:
                return ("REJECT", f"Amount ${amount:,.0f} in gray zone with risk factors: {', '.join(risk_factors)}")
            return ("APPROVE", f"Amount ${amount:,.0f} in review range, no additional risk factors")

    def _eval_revenue(self, amount, context, policy, thresholds):
        """Revenue agent: evaluates impact on revenue and profitability."""
        deal_value = context.get("deal_value", amount * 5)
        net_revenue = deal_value - amount

        reject_loss_pct = policy.get("reject_loss_threshold_percent", 5)

        if net_revenue > 0:
            margin = (net_revenue / deal_value * 100) if deal_value > 0 else 0
            if margin >= reject_loss_pct:
                return ("APPROVE", f"Net revenue positive: ${net_revenue:,.0f} ({margin:.1f}% margin)")
            else:
                return ("REJECT", f"Net margin {margin:.1f}% below threshold ({reject_loss_pct}%)")
        else:
            return ("REJECT", f"Net revenue negative: -${abs(net_revenue):,.0f}")

    def _eval_compliance(self, action, amount, context, policy):
        """Compliance agent: checks regulatory constraints."""
        # Sanctions check
        recipient = context.get("recipient", "")
        sanctioned_patterns = ["sanction", "embargo", "blocked", "iran", "nk", "syria"]
        if any(s in recipient.lower() for s in sanctioned_patterns):
            return ("REJECT", f"Recipient '{recipient}' flagged by sanctions screening")

        # KYC check
        if policy.get("require_kyc", True):
            kyc_status = context.get("kyc_status", "verified")
            if kyc_status in ("unknown", "failed", "pending"):
                return ("REJECT", f"KYC status '{kyc_status}' — identity verification required")

        # AML check
        if context.get("aml_flag", False):
            return ("REJECT", "AML flag detected — anti-money-laundering review required")

        return ("APPROVE", "Compliance checks passed — no regulatory flags")

    def _eval_margin(self, amount, context, policy):
        """Margin agent: evaluates profit margin impact."""
        deal_value = context.get("deal_value", amount * 5)
        cost = context.get("cost", deal_value * 0.6)  # 60% cost default
        revenue_after = deal_value - amount
        margin = ((revenue_after - cost) / deal_value * 100) if deal_value > 0 else 0

        approve_above = policy.get("approve_above_margin_percent", 15)
        reject_below = policy.get("reject_below_margin_percent", 10)

        if margin >= approve_above:
            return ("APPROVE", f"Post-discount margin {margin:.1f}% exceeds target (≥{approve_above}%)")
        elif margin < reject_below:
            return ("REJECT", f"Post-discount margin {margin:.1f}% below minimum (< {reject_below}%)")
        else:
            return ("APPROVE", f"Post-discount margin {margin:.1f}% in acceptable range ({reject_below}%-{approve_above}%)")

    def _eval_generic(self, amount, thresholds):
        """Generic evaluation for unknown agent roles."""
        limit = thresholds.get("auto_approve_limit", 10_000)
        if amount <= limit:
            return ("APPROVE", f"Amount ${amount:,.0f} within auto-approve limit (≤${limit:,.0f})")
        else:
            return ("REJECT", f"Amount ${amount:,.0f} exceeds auto-approve limit (>${limit:,.0f})")
