"""
context_graph.py — Decision Context Graph Engine

Auto-builds a queryable graph from existing PrivateVault traces:
  - MeshDecisionEngine results (multi-agent decisions)
  - shadow_verify audit entries (single-agent governance)
  - human_approve events

Node types:  decision, agent, human, policy, entity, outcome
Edge types:  reasoned_by, contributed_to, evaluated_by, produced,
             overrode, linked_to, followed_by, initiated, approved_by

All data comes from real pipeline executions — nothing is hardcoded.
"""

import hashlib
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional


class ContextGraph:
    """In-memory Decision Context Graph built from live pipeline data."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self._decision_history: list[str] = []  # ordered list of decision node IDs
        self._entity_index: dict[str, list[str]] = defaultdict(list)  # entity -> [decision_ids]
        self._action_index: dict[str, list[str]] = defaultdict(list)  # action_type -> [decision_ids]
        self._snapshots: dict[str, dict] = {}  # version -> frozen state

    # ─── NODE MANAGEMENT ───

    def _add_node(self, node_id: str, node_type: str, data: dict) -> str:
        """Add or update a node. Returns node_id."""
        if node_id in self.nodes:
            self.nodes[node_id]["data"].update(data)
            return node_id

        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "data": data,
            "created_at": time.time(),
            "merkle_hash": self._hash({"id": node_id, "type": node_type, **data}),
        }
        return node_id

    def _add_edge(self, from_id: str, to_id: str, edge_type: str,
                  weight: float = 1.0, data: dict = None):
        """Add an edge between two nodes."""
        self.edges.append({
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "weight": weight,
            "data": data or {},
            "created_at": time.time(),
        })

    def _hash(self, payload: dict) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str).encode()
        return "sha256:" + hashlib.sha256(serialized).hexdigest()[:24]

    # ─── INGEST FROM MESH DECISION ENGINE ───

    def ingest_mesh_decision(self, result: dict):
        """
        Auto-extract nodes and edges from a MeshDecisionEngine.full_pipeline() result.
        This is the primary ingestion path for multi-agent decisions.
        """
        action_id = result.get("action_id", f"unknown-{uuid.uuid4().hex[:6]}")
        timestamp = result.get("crypto_proof", {}).get("timestamp", datetime.now(timezone.utc).isoformat())
        final_decision = result.get("final_decision", "UNKNOWN")
        final_reason = result.get("final_reason", "")

        # 1. Decision node
        decision_node_id = f"decision:{action_id}"
        self._add_node(decision_node_id, "decision", {
            "action_id": action_id,
            "action": result.get("agent_reasoning", [{}])[0].get("reason", "").split("(")[0].strip() if result.get("agent_reasoning") else "",
            "final_decision": final_decision,
            "final_reason": final_reason,
            "timestamp": timestamp,
            "total_time_ms": result.get("total_time_ms", 0),
            "crypto_hash": result.get("crypto_proof", {}).get("hash", ""),
        })

        # Extract amount and action type from the weights/request context
        amount = 0
        action_type = "unknown"
        consensus = result.get("consensus", {})
        policy_enforcement = result.get("policy_enforcement", {})

        # Try to extract amount from policy checks
        for check in policy_enforcement.get("checks", []):
            detail = check.get("detail", "")
            if "$" in detail:
                import re
                amounts = re.findall(r'\$([\d,]+)', detail)
                if amounts:
                    try:
                        amount = float(amounts[0].replace(",", ""))
                    except ValueError:
                        pass
                    break

        # Try to extract action type from agent reasoning
        for reasoning in result.get("agent_reasoning", []):
            reason_text = reasoning.get("reason", "").lower()
            if "discount" in reason_text:
                action_type = "approve_discount"
                break
            elif "transfer" in reason_text:
                action_type = "transfer"
                break
            elif "loan" in reason_text:
                action_type = "approve_loan"
                break

        self.nodes[decision_node_id]["data"]["amount"] = amount
        self.nodes[decision_node_id]["data"]["action_type"] = action_type

        # Index for queries
        self._decision_history.append(decision_node_id)
        self._action_index[action_type].append(decision_node_id)

        # 2. Agent reasoning nodes + edges
        for reasoning in result.get("agent_reasoning", []):
            agent_id = reasoning.get("agent", "unknown")

            # Agent node (persistent across decisions)
            agent_node_id = f"agent:{agent_id}"
            self._add_node(agent_node_id, "agent", {
                "agent_id": agent_id,
                "static_trust": reasoning.get("static_trust", 0),
                "dynamic_trust": reasoning.get("dynamic_trust", 0),
                "last_seen": timestamp,
            })

            # Agent reasoning node (unique per decision)
            reasoning_node_id = f"reasoning:{action_id}:{agent_id}"
            self._add_node(reasoning_node_id, "agent_reasoning", {
                "agent_id": agent_id,
                "decision": reasoning.get("decision", ""),
                "reason": reasoning.get("reason", ""),
                "static_trust": reasoning.get("static_trust", 0),
                "dynamic_trust": reasoning.get("dynamic_trust", 0),
                "timestamp": timestamp,
            })

            # Edges: agent -> reasoning, reasoning -> decision
            self._add_edge(agent_node_id, reasoning_node_id, "reasoned_by",
                           weight=reasoning.get("dynamic_trust", 0.5))
            self._add_edge(reasoning_node_id, decision_node_id, "contributed_to",
                           weight=reasoning.get("dynamic_trust", 0.5),
                           data={"vote": reasoning.get("decision", "")})

        # 3. Consensus node
        consensus_node_id = f"consensus:{action_id}"
        self._add_node(consensus_node_id, "consensus", {
            "approve_score": consensus.get("approve_score", 0),
            "reject_score": consensus.get("reject_score", 0),
            "threshold": consensus.get("threshold", 1.5),
            "result": consensus.get("result", ""),
            "method": consensus.get("method", "trust_weighted_quorum"),
            "drift_detected": consensus.get("drift_detected", False),
            "timestamp": timestamp,
        })
        self._add_edge(decision_node_id, consensus_node_id, "evaluated_by")

        # 4. Policy enforcement node
        policy_node_id = f"policy:{action_id}"
        self._add_node(policy_node_id, "policy", {
            "pass": policy_enforcement.get("pass", True),
            "reason": policy_enforcement.get("reason", ""),
            "tier": policy_enforcement.get("tier", ""),
            "checks": policy_enforcement.get("checks", []),
            "timestamp": timestamp,
        })
        self._add_edge(consensus_node_id, policy_node_id, "evaluated_by")

        # 5. Check if policy overrode consensus
        consensus_result = consensus.get("result", "")
        if consensus_result == "APPROVE" and not policy_enforcement.get("pass", True):
            self._add_edge(policy_node_id, consensus_node_id, "overrode",
                           data={"reason": policy_enforcement.get("reason", "Policy override")})

        # 6. Outcome node
        outcome_node_id = f"outcome:{action_id}"
        self._add_node(outcome_node_id, "outcome", {
            "decision": final_decision,
            "reason": final_reason,
            "timestamp": timestamp,
        })
        self._add_edge(policy_node_id, outcome_node_id, "produced")
        self._add_edge(decision_node_id, outcome_node_id, "caused_outcome")

        # 7. Trust update edges
        for update in result.get("trust_updates", []):
            agent_node_id = f"agent:{update.get('agent_id', 'unknown')}"
            if agent_node_id in self.nodes:
                self._add_edge(outcome_node_id, agent_node_id, "updated_trust",
                               weight=update.get("new_trust", 0) - update.get("old_trust", 0),
                               data={
                                   "old_trust": update.get("old_trust", 0),
                                   "new_trust": update.get("new_trust", 0),
                                   "reason": update.get("reason", ""),
                               })

        # 8. Temporal edge — link to previous decision
        if len(self._decision_history) > 1:
            prev_decision_id = self._decision_history[-2]
            self._add_edge(prev_decision_id, decision_node_id, "followed_by",
                           data={"temporal": True})

        # 9. Entity linking — find shared entities with past decisions
        for prev_id in self._decision_history[:-1]:
            prev_node = self.nodes.get(prev_id, {})
            prev_action = prev_node.get("data", {}).get("action_type", "")
            if prev_action == action_type and prev_id != decision_node_id:
                self._add_edge(prev_id, decision_node_id, "linked_via_same_action",
                               data={"shared_action": action_type})

        # Create snapshot version
        proof_hash = result.get("crypto_proof", {}).get("hash", "")
        if proof_hash:
            self._snapshots[proof_hash[:16]] = {
                "timestamp": timestamp,
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "decision_id": action_id,
            }

    # ─── INGEST FROM SHADOW VERIFY (Single-Agent Governance) ───

    def ingest_audit_entry(self, entry: dict):
        """
        Auto-extract nodes and edges from a shadow_verify audit entry.
        """
        tx_id = entry.get("transaction_id", f"tx-{uuid.uuid4().hex[:6]}")
        timestamp = entry.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Decision node
        decision_node_id = f"tx:{tx_id}"
        status = entry.get("status", "UNKNOWN")
        self._add_node(decision_node_id, "transaction", {
            "transaction_id": tx_id,
            "action": entry.get("action", ""),
            "amount": entry.get("amount", 0),
            "status": status,
            "reason": entry.get("reason", ""),
            "risk_score": entry.get("risk_score", 0),
            "policy_tier": entry.get("policy_tier", ""),
            "merkle_hash": entry.get("merkle_hash", ""),
            "timestamp": timestamp,
        })

        # Agent node
        agent_id = entry.get("agent_id", "unknown")
        agent_node_id = f"agent:{agent_id}"
        self._add_node(agent_node_id, "agent", {
            "agent_id": agent_id,
            "last_seen": timestamp,
        })
        self._add_edge(agent_node_id, decision_node_id, "initiated")

        # Entity (recipient) node
        recipient = entry.get("recipient", "")
        if recipient:
            entity_node_id = f"entity:{recipient}"
            self._add_node(entity_node_id, "entity", {
                "entity_id": recipient,
                "entity_type": "recipient",
                "last_seen": timestamp,
            })
            self._add_edge(decision_node_id, entity_node_id, "linked_to",
                           data={"relationship": "recipient"})
            self._entity_index[recipient].append(decision_node_id)

        # Policy tier node
        policy_tier = entry.get("policy_tier", "")
        if policy_tier:
            tier_node_id = f"tier:{policy_tier}"
            self._add_node(tier_node_id, "policy_tier", {
                "tier": policy_tier,
                "label": {
                    "auto_approve": "Tier 1 · Auto-Approve",
                    "human_review": "Tier 2 · Human Review",
                    "hard_block": "Tier 3 · Hard Block",
                }.get(policy_tier, policy_tier),
            })
            self._add_edge(decision_node_id, tier_node_id, "evaluated_as")

        # Track in history
        self._decision_history.append(decision_node_id)
        action = entry.get("action", "unknown")
        self._action_index[action].append(decision_node_id)

        # Temporal edge
        if len(self._decision_history) > 1:
            prev_id = self._decision_history[-2]
            self._add_edge(prev_id, decision_node_id, "followed_by",
                           data={"temporal": True})

    # ─── INGEST HUMAN APPROVAL ───

    def ingest_human_approval(self, tx_id: str, approval: dict):
        """Add human approval data to an existing transaction node."""
        decision_node_id = f"tx:{tx_id}"

        # Human node
        approver = approval.get("approver", "Unknown Reviewer")
        human_node_id = f"human:{approver.replace(' ', '_').lower()}"
        self._add_node(human_node_id, "human", {
            "name": approver,
            "role": "financial_approver",
            "last_action": approval.get("approval_timestamp", ""),
        })

        self._add_edge(human_node_id, decision_node_id, "approved_by",
                       data={
                           "decision": approval.get("human_decision", ""),
                           "reason": approval.get("approval_reason", ""),
                           "chain_hash": approval.get("chain_hash", ""),
                       })

    # ─── QUERY METHODS ───

    def get_full_graph(self) -> dict:
        """Return the complete graph for visualization."""
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "total_decisions": len(self._decision_history),
                "node_types": self._count_by_type("nodes"),
                "edge_types": self._count_by_type("edges"),
                "snapshots": len(self._snapshots),
            },
        }

    def _count_by_type(self, kind: str) -> dict:
        counts = defaultdict(int)
        if kind == "nodes":
            for node in self.nodes.values():
                counts[node["type"]] += 1
        else:
            for edge in self.edges:
                counts[edge["type"]] += 1
        return dict(counts)

    def query(self, filters: dict) -> dict:
        """
        Query the graph with filters.

        Supported filters:
          - node_type: str (e.g., "decision", "agent", "entity")
          - action_type: str (e.g., "transfer", "approve_discount")
          - entity: str (e.g., "vendor_acme_corp")
          - status: str (e.g., "ALLOW", "BLOCK")
          - min_amount / max_amount: float
          - time_range: str ("1h", "24h", "7d", "30d")
          - agent_id: str
          - limit: int (default 50)
        """
        matched_nodes = []
        matched_edges = []
        limit = filters.get("limit", 50)

        # Filter nodes
        for node in self.nodes.values():
            if not self._node_matches(node, filters):
                continue
            matched_nodes.append(node)

        # Sort by timestamp (newest first)
        matched_nodes.sort(
            key=lambda n: n.get("data", {}).get("timestamp", ""),
            reverse=True,
        )
        matched_nodes = matched_nodes[:limit]

        # Get edges connected to matched nodes
        matched_ids = {n["id"] for n in matched_nodes}
        for edge in self.edges:
            if edge["from"] in matched_ids or edge["to"] in matched_ids:
                matched_edges.append(edge)
                # Also include connected nodes
                for nid in [edge["from"], edge["to"]]:
                    if nid not in matched_ids and nid in self.nodes:
                        matched_nodes.append(self.nodes[nid])
                        matched_ids.add(nid)

        return {
            "nodes": matched_nodes,
            "edges": matched_edges,
            "query": filters,
            "result_count": len(matched_nodes),
        }

    def _node_matches(self, node: dict, filters: dict) -> bool:
        """Check if a node matches the given filters."""
        data = node.get("data", {})

        # Type filter
        if "node_type" in filters:
            if node.get("type") != filters["node_type"]:
                return False

        # Action type filter
        if "action_type" in filters:
            action = data.get("action_type", data.get("action", ""))
            if action != filters["action_type"]:
                return False

        # Entity filter
        if "entity" in filters:
            entity_val = filters["entity"].lower()
            for field in ["entity_id", "recipient", "agent_id"]:
                if entity_val in str(data.get(field, "")).lower():
                    break
            else:
                return False

        # Status filter
        if "status" in filters:
            status = data.get("status", data.get("final_decision", data.get("decision", "")))
            if status.upper() != filters["status"].upper():
                return False

        # Amount range
        if "min_amount" in filters:
            if data.get("amount", 0) < filters["min_amount"]:
                return False
        if "max_amount" in filters:
            if data.get("amount", 0) > filters["max_amount"]:
                return False

        # Agent filter
        if "agent_id" in filters:
            if data.get("agent_id", "") != filters["agent_id"]:
                return False

        # Time range filter
        if "time_range" in filters:
            node_time = data.get("timestamp", "")
            if node_time and not self._in_time_range(node_time, filters["time_range"]):
                return False

        return True

    def _in_time_range(self, timestamp_str: str, range_str: str) -> bool:
        """Check if a timestamp falls within the given time range."""
        try:
            if isinstance(timestamp_str, (int, float)):
                node_time = timestamp_str
            else:
                node_time = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                ).timestamp()

            now = time.time()
            ranges = {"1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000, "90d": 7776000}
            max_age = ranges.get(range_str, 86400)
            return (now - node_time) <= max_age
        except Exception:
            return True  # Include if we can't parse

    # ─── PRECEDENT ENGINE ───

    def find_precedents(self, action_type: str = None, entity: str = None,
                        min_amount: float = None, max_amount: float = None,
                        limit: int = 10) -> list[dict]:
        """
        Find similar past decisions based on action type, entity, and amount range.
        Returns precedent cards with confidence scores.
        """
        candidates = []

        for node_id in reversed(self._decision_history):
            node = self.nodes.get(node_id)
            if not node:
                continue

            data = node.get("data", {})
            score = 0.0
            match_reasons = []

            # Action type match
            node_action = data.get("action_type", data.get("action", ""))
            if action_type and node_action == action_type:
                score += 0.4
                match_reasons.append(f"Same action: {action_type}")
            elif action_type and node_action:
                score += 0.1  # Different action, but still a decision

            # Amount proximity
            node_amount = data.get("amount", 0)
            if min_amount is not None and max_amount is not None and node_amount > 0:
                target_mid = (min_amount + max_amount) / 2
                if target_mid > 0:
                    ratio = min(node_amount, target_mid) / max(node_amount, target_mid)
                    score += 0.3 * ratio
                    if ratio > 0.7:
                        match_reasons.append(f"Similar amount: ${node_amount:,.0f}")

            # Entity match
            if entity:
                # Check edges for entity connections
                for edge in self.edges:
                    if edge["from"] == node_id or edge["to"] == node_id:
                        other_id = edge["to"] if edge["from"] == node_id else edge["from"]
                        other_node = self.nodes.get(other_id, {})
                        if entity.lower() in str(other_node.get("data", {}).get("entity_id", "")).lower():
                            score += 0.3
                            match_reasons.append(f"Same entity: {entity}")
                            break

            if score > 0.1:
                # Get the outcome for this decision
                outcome = None
                for edge in self.edges:
                    if edge["from"] == node_id and edge["type"] == "caused_outcome":
                        outcome_node = self.nodes.get(edge["to"])
                        if outcome_node:
                            outcome = outcome_node.get("data", {})
                            break

                candidates.append({
                    "node_id": node_id,
                    "confidence": round(min(1.0, score), 3),
                    "match_reasons": match_reasons,
                    "data": data,
                    "outcome": outcome,
                    "node_type": node.get("type", ""),
                })

        # Sort by confidence, then by recency
        candidates.sort(key=lambda c: c["confidence"], reverse=True)
        return candidates[:limit]

    # ─── POLICY DRIFT DETECTION ───

    def detect_policy_drift(self) -> list[dict]:
        """
        Analyze the graph for patterns where consensus was overridden by policy.
        These represent potential policy drift — where agents consistently
        disagree with hard policy rules.
        """
        drift_patterns = []
        override_edges = [e for e in self.edges if e["type"] == "overrode"]

        if not override_edges:
            return drift_patterns

        # Group overrides by the policy reason
        reason_groups = defaultdict(list)
        for edge in override_edges:
            policy_node = self.nodes.get(edge["from"], {})
            reason = policy_node.get("data", {}).get("reason", "Unknown")
            decision_node_id = None
            # Find the decision this policy belongs to
            for e2 in self.edges:
                if e2["to"] == edge["to"] and e2["type"] == "evaluated_by":
                    decision_node_id = e2["from"]
                    break
            if decision_node_id:
                reason_groups[reason].append({
                    "decision_id": decision_node_id,
                    "policy_node": edge["from"],
                    "consensus_node": edge["to"],
                    "timestamp": policy_node.get("data", {}).get("timestamp", ""),
                })

        for reason, occurrences in reason_groups.items():
            if len(occurrences) >= 1:  # Report all overrides for the demo
                drift_patterns.append({
                    "pattern": reason,
                    "occurrence_count": len(occurrences),
                    "severity": "HIGH" if len(occurrences) >= 3 else "MEDIUM" if len(occurrences) >= 2 else "LOW",
                    "recommendation": f"These {len(occurrences)} traces show agents overriding this policy — consider reviewing the threshold.",
                    "occurrences": occurrences[-5:],  # Last 5
                })

        return drift_patterns

    # ─── SUBGRAPH EXTRACTION ───

    def get_decision_subgraph(self, decision_id: str) -> dict:
        """Get the complete subgraph for a single decision."""
        if decision_id not in self.nodes:
            return {"nodes": [], "edges": [], "error": f"Node {decision_id} not found"}

        # BFS to find all connected nodes
        visited = set()
        queue = [decision_id]
        subgraph_nodes = []
        subgraph_edges = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current in self.nodes:
                subgraph_nodes.append(self.nodes[current])

            for edge in self.edges:
                if edge["from"] == current:
                    subgraph_edges.append(edge)
                    if edge["to"] not in visited:
                        queue.append(edge["to"])
                elif edge["to"] == current:
                    subgraph_edges.append(edge)
                    if edge["from"] not in visited:
                        queue.append(edge["from"])

        return {
            "root": decision_id,
            "nodes": subgraph_nodes,
            "edges": subgraph_edges,
        }

    # ─── WHAT-IF ANALYSIS ───

    def what_if_analysis(self, action_type: str, new_threshold: dict) -> dict:
        """
        Replay historical decisions under new policy thresholds.
        Returns projected outcomes vs actual outcomes.
        """
        results = []
        decision_nodes = [
            (nid, self.nodes[nid])
            for nid in self._decision_history
            if nid in self.nodes and self.nodes[nid]["type"] in ("decision", "transaction")
        ]

        for node_id, node in decision_nodes[-20:]:  # Last 20 decisions
            data = node["data"]
            actual_decision = data.get("final_decision", data.get("status", "UNKNOWN"))
            amount = data.get("amount", 0)

            # Simulate with new thresholds
            projected = actual_decision
            reason = "No change"

            new_max = new_threshold.get("max_discount_amount", 250000)
            new_pct = new_threshold.get("max_discount_percent", 25)
            new_hard = new_threshold.get("human_review_limit", 25000)

            if amount > new_max and actual_decision == "ALLOW":
                projected = "BLOCK"
                reason = f"Amount ${amount:,.0f} exceeds new limit ${new_max:,.0f}"
            elif amount <= new_max and actual_decision == "BLOCK":
                # Check if it was blocked by amount limit only
                block_reason = data.get("reason", data.get("final_reason", ""))
                if "exceeds" in block_reason.lower() and "limit" in block_reason.lower():
                    projected = "ALLOW"
                    reason = f"Amount ${amount:,.0f} now within new limit ${new_max:,.0f}"

            changed = projected != actual_decision
            results.append({
                "node_id": node_id,
                "action_type": data.get("action_type", data.get("action", "")),
                "amount": amount,
                "actual_decision": actual_decision,
                "projected_decision": projected,
                "changed": changed,
                "reason": reason,
                "timestamp": data.get("timestamp", ""),
            })

        changed_count = sum(1 for r in results if r["changed"])
        return {
            "total_replayed": len(results),
            "changed_count": changed_count,
            "change_rate": round(changed_count / max(len(results), 1) * 100, 1),
            "new_thresholds": new_threshold,
            "results": results,
        }

    # ─── GRAPH STATS ───

    def get_stats(self) -> dict:
        """Get comprehensive graph statistics."""
        node_types = self._count_by_type("nodes")
        edge_types = self._count_by_type("edges")

        # Decision outcomes
        outcomes = defaultdict(int)
        for node in self.nodes.values():
            if node["type"] in ("decision", "transaction"):
                decision = node["data"].get("final_decision", node["data"].get("status", "UNKNOWN"))
                outcomes[decision] += 1

        # Agent activity
        agent_activity = defaultdict(int)
        for edge in self.edges:
            if edge["type"] in ("reasoned_by", "initiated"):
                agent_node = self.nodes.get(edge["from"], {})
                agent_id = agent_node.get("data", {}).get("agent_id", "")
                if agent_id:
                    agent_activity[agent_id] += 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "total_decisions": len(self._decision_history),
            "node_types": node_types,
            "edge_types": edge_types,
            "outcomes": dict(outcomes),
            "agent_activity": dict(agent_activity),
            "snapshots": len(self._snapshots),
            "override_count": sum(1 for e in self.edges if e["type"] == "overrode"),
        }
