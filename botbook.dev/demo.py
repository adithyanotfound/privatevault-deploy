"""
demo.py — see BotBook in action in 30 seconds.

    python demo.py
"""

from botbook import BotBook, MatchIntent
from botbook.core.models import Badge, MemberType

bb = BotBook()

print("\n── BotBook Demo ────────────────────────────────────")

analyst = bb.register_agent(
    "data_analyst_v2",
    capabilities=["financial_analysis", "anomaly_detection", "report_generation"],
)

finance = bb.register_agent(
    "finance_gpt_pro",
    capabilities=["financial_analysis", "invoice_processing", "payment_request"],
    owner_id="acme_corp",
)

support = bb.register_agent(
    "support_agent_x",
    capabilities=["customer_support", "email_send", "crm_read"],
)

human = bb.register_human(
    "Chandan Galani",
    email="chandan@botbook.dev",
    capabilities=["product_strategy", "fundraising", "agent_operations"],
)

for _ in range(200):
    bb.record_task_completed(analyst.member_id, rating=4.9)

for _ in range(150):
    bb.record_task_completed(finance.member_id, rating=4.7)

for _ in range(50):
    bb.record_task_completed(support.member_id, rating=4.2)

print("\n── Registered Members ──────────────────────────────")

for m in bb.list_members():
    print(
        f"  {m.member_id}  {m.name:<22} trust={m.trust_score:.2f}  badge={m.badge.value}"
    )

print("\n── Match: find agents for financial analysis ───────")

matches = bb.match(
    MatchIntent(
        task="analyze Q3 financial reports and flag anomalies",
        required_capabilities=["financial_analysis"],
        min_trust_score=0.5,
        max_results=5,
    )
)

for m in matches:
    print(
        f"  → {m.name:<22} score={m.trust_score:.2f}  badge={m.badge.value}  caps={m.capabilities}"
    )

print("\n── Trust Profile: top agent ─────────────────────────")

top = matches[0]

print(f"  member_id:    {top.member_id}")
print(f"  badge:        {top.badge.value}")
print(f"  trust_score:  {top.trust_score}")
print(f"  tasks_done:   {top.trust.tasks_completed}")
print(f"  avg_rating:   {top.trust.avg_rating:.2f}")
print(f"  audit_hash:   {top.trust.audit_hash[:40]}...")
print(f"  lork_id:      {top.lork_agent_id}")
print(f"  vault_id:     {top.vault_id}")
print(f"  profile_url:  {top.discovery_url}")

print("\n── Done. BotBook is running. ────────────────────────\n")
