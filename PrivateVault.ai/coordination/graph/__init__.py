# coordination.graph — Decision Context Graph Engine
#
# Auto-builds a queryable graph from governance pipeline data:
# - MeshDecisionEngine results (multi-agent decisions)
# - shadow_verify audit entries (single-agent governance)
# - human_approve events
#
# Provides: querying, precedent finding, policy drift detection,
# and what-if analysis over the decision history.

from coordination.graph.context_graph import ContextGraph  # type: ignore

__all__ = ["ContextGraph"]

