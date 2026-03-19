# PrivateVault.ai

**Runtime Governance & Security Infrastructure for AI Systems**

PrivateVault provides a robust runtime governance layer that monitors, evaluates, and enforces policies on AI agents *before* any action is executed. It acts as an unbreakable control boundary between AI models and real-world execution environments.

This document breaks down the core architecture, including the **Envoy Proxy**, **Shadow Verifier**, **Policy Engine**, and **Cryptographic Ledger**.

---

## 🏗 System Architecture & How It Works

At a high level, when an AI Agent attempts to perform an action (like executing a trade, sending a payment, or reading a database), it does not directly access the infrastructure. Instead, the request flows through a strict governance pipeline.

### The End-to-End Flow:

1. **Agent Intent Generation**: The AI agent formulates an "intent" (e.g., `execute_payment` for `$15,000`). It signs this intent, generating a unique 32-byte `intent_hash`.
2. **Envoy Proxy Interception**: The request hits the **Envoy API Gateway**. Envoy pauses the request and asks the Governance Control Plane for authorization.
3. **Shadow Verification (Optional/Parallel)**: The **Shadow Verifier** silently tests the intent against stricter, experimental policies to see if it *would* be blocked under new rules.
4. **Policy Engine Evaluation**: The core **Open Policy Agent (OPA)** or Python Governance Engine evaluates the intent against active production rules.
5. **Ledger Recording**: The decision (Allow/Deny) and the intent are cryptographically hashed and appended to a **Decision Ledger**, generating a Merkle Root for audits.
6. **Execution**: If approved, Envoy routes the request to the execution systems. If denied, the agent receives an immediate 422/403 rejection with a strict "fix" reason.

---

## 🔍 Core Components in Detail

### 1. The Envoy Proxy (The Gatekeeper)
**Folder Location:** `/deployments/`, `/cli/` scripts (e.g., `envoy-direct-opa.sh`)

**What is it?**
Envoy is a highly performant, open-source edge and service proxy. In PrivateVault, Envoy acts as the primary "choke point" for all AI agent network traffic.

**How it works:**
*   **External Authorization (`ext_authz`)**: We configure Envoy to never route a request blindly. Using Envoy's `ext_authz` filter, every single incoming AI API call is paused. Envoy forwards the request metadata to our internal Policy Engine (OPA or Python FastAPI).
*   **Synchronous Enforcement**: Envoy waits for a strict `ALLOW` or `DENY` from the Policy Engine. If `DENY` is returned, Envoy drops the connection immediately and returns an error to the Agent.
*   **Why Envoy?** It prevents AI agents from exploiting network backdoors. Even if the AI agent's code is compromised, it has no physical network path to the database except through Envoy, which tightly polices the traffic.

### 2. The Shadow Verifier (The Sandbox)
**Folder Location:** `/src/security/shadow_mode.py`, `/src/core/uaal_shadow_verify.py`

**What is it?**
The Shadow Verifier is a safe simulation environment that runs simultaneously with production infrastructure. It is used to test *new* or *stricter* AI guardrails without breaking ongoing business operations.

**How it works:**
*   **Silent Evaluation**: When an AI agent submits an intent, the Shadow Verifier evaluates it against "Shadow Policies" (e.g., a new rule saying "Block all fintech payments over $10,000").
*   **Divergence Tracking**: If the production engine ALLOWS the transaction, but the Shadow policy DENIES it, the system logs a **Divergence**. 
*   **Metrics**: It records the `divergence_count` and `prevented_total` (how much money/risk would have been prevented if the shadow policy was live).
*   **Why use it?** If a company wants to tighten their AI safety rules, they can deploy the rule in "Shadow Mode" first. They monitor the Shadow Impact Panel (via the React UI) for a week to see if the new rule accidentally blocks legitimate AI tasks before flipping it to active production.

### 3. The Control Plane & Policy Engine
**Folder Location:** `/src/governance/`, `/src/core/`

**What is it?**
The brains of the operation. It houses the specific business logic (e.g., healthcare compliance limits, fintech withdrawal limits). 

**How it works:**
*   Evaluates conditional payloads. If the action is `execute_payment`, it enforces that an `amount` and `recipient` must exist.
*   Resolves multiple parallel rules.
*   If a request violates a policy, it formulates a strict `RejectDetail` payload returning `missing_fields`, `invalid_fields`, and a `fix` instruction so the AI agent can autonomously attempt to correct its mistake.

### 4. Cryptographic Evidence Ledger
**Folder Location:** `/src/ledger/`

**What is it?**
An immutable, append-only record of every decision the governance layer ever makes.

**How it works:**
*   Every intent hash and governance decision is pushed into a **Merkle Tree**.
*   This produces a `merkle_root`—a cryptographic proof of the system's state. 
*   When enterprise auditors analyze the AI's behavior, they don't just look at text logs; they verify the Merkle proof to ensure nobody tampered with the history of the AI's actions.
*   A valid `merkle_root` is structurally required by the system for any production execution.

---

## 📂 Repository Structure Guide

Following the recent major refactor, the repository is cleanly divided into these core areas:

*   **`/src/`**: All backend Python mechanics. Contains the `/governance` engine, `/security` limits (Shadow Verifier), `/ledger` tracking, and the core `/agents` infrastructure.
*   **`/ui/dashboard/src/`**: The frontend React UI (Control Plane) where humans can monitor the AI, view the IntentTable, and analyze Shadow Impact metrics.
*   **`/demos/`**: Reference implementations for Healthcare, Fintech, and generic multi-agent workflows. Start here to see real payloads.
*   **`/tests/`**: Unit tests verifying everything from Merkle hashes to exact rejection reasons.
*   **`/scripts/`**: Operational bash shortcuts to spin up Envoy, mock deployments, or test Direct OPA integration.
*   **`main.py`**: The Python entry point that boots the overarching execution APIs. 

---

## 🚀 Where to start checking the code?
1. Open up **`/src/security/shadow_mode.py`** to see how Shadow Divergencies are counted.
2. Look at **`/src/core/uaal_shadow_verify.py`** to see the FastAPI implementation rejecting bad schemas.
3. Browse **`/demos/`** to see an AI agent payload effectively hitting the Envoy gateway structure!
