# 🎬 Demo — FinTech AI Agent Pipeline

> A real-world scenario: deploying AI agents for a FinTech company to automate financial analysis, compliance checks, and customer outreach — all governed by PrivateVault.ai and orchestrated through BotBook + LORK.

---

## 📖 Scenario

**GalaniPay** is a fintech startup. They want to deploy AI agents to:

1. **Research** market trends and competitor pricing
2. **Analyze** their Q3 financial data for anomalies
3. **Check compliance** — ensure no transaction violates policy limits
4. **Generate** a customer outreach strategy

They need **governance** (no agent can move money without policy checks) and **observability** (every agent action is logged and replayable).

---

## ⚙️ Before You Start

**Activate the virtual environment** (required in every terminal):

```bash
cd ~/ai-agents-platform     # or wherever your repos live
source .venv/bin/activate    # you should see (.venv) in your prompt
```

> 🛑 If you skip this step, all `botbook` and `lork` commands will say `command not found`.

Make sure you have a `.env` file in `botbook.dev/` with your API key:

```bash
# Check if .env exists
cat botbook.dev/.env

# If not, create it:
cp botbook.dev/.env.example botbook.dev/.env
# Then edit it and add your GEMINI_API_KEY or OPENAI_API_KEY
```

---

## 🚀 Part 1 — Start the Governance Server (PrivateVault.ai)

Open **Terminal 1**:

```bash
cd ~/ai-agents-platform
source .venv/bin/activate

cd PrivateVault.ai
python -m uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Verify governance is online** (from another terminal):

```bash
curl -s http://localhost:8000/ | python3 -m json.tool
```

```json
{
    "system": "Galani Governance Node",
    "status": "ONLINE",
    "mode": "SHADOW_VERIFY"
}
```

---

## 🤖 Part 2 — Create the Agent Team (BotBook)

Open **Terminal 2**:

```bash
cd ~/ai-agents-platform
source .venv/bin/activate
```

### 2a. Initialize a new project

```bash
mkdir -p galanipay-agents && cd galanipay-agents
botbook init
```

Output:
```
Project initialized

Structure created:

agents/
tools/
memory/
workflows/

Next steps:

botbook make sales_agent
botbook run sales_agent "task"
```

### 2b. Create the agent team

```bash
botbook make finance_agent
botbook make compliance_agent
botbook make sales_agent
botbook make risk_monitor
```

Output:
```
Created agent: agents/finance_agent.py
Created agent: agents/compliance_agent.py
Created agent: agents/sales_agent.py
Created agent: agents/risk_monitor.py
```

### 2c. Create a workflow pipeline

```bash
cat > workflows/fintech_pipeline.yaml << 'EOF'
steps:
  - finance_agent
  - compliance_agent
  - sales_agent
EOF
```

---

## 🔒 Part 3 — Test Governance Policies (PrivateVault.ai)

Before agents execute financial actions, they go through PrivateVault's shadow verification. Let's simulate what happens when agents try to perform transactions.

### ✅ Scenario A: Normal invoice payment ($5,000) — ALLOWED

```bash
curl -s -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "transfer",
    "amount": 5000,
    "recipient": "vendor_acme_corp",
    "agent_id": "finance_agent"
  }' | python3 -m json.tool
```

```json
{
    "status": "ALLOW",
    "reason": "Transaction within safe parameters.",
    "transaction_id": "a1b2c3d4-...",
    "timestamp": "2026-03-18T12:00:00",
    "node_version": "3.1.0-shadow"
}
```

### 🚫 Scenario B: Large transfer ($50,000) — BLOCKED

```bash
curl -s -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "transfer",
    "amount": 50000,
    "recipient": "vendor_acme_corp",
    "agent_id": "finance_agent"
  }' | python3 -m json.tool
```

```json
{
    "status": "BLOCK",
    "reason": "Amount exceeds automated authorization limit (k). Human Approval Required.",
    "transaction_id": "e5f6g7h8-...",
    "timestamp": "2026-03-18T12:00:01",
    "node_version": "3.1.0-shadow"
}
```

> 💡 The agent wanted to pay $50k, but governance blocked it — requires a human.

### 🚫 Scenario C: Anonymous recipient — BLOCKED (KYC)

```bash
curl -s -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "transfer",
    "amount": 500,
    "recipient": "anonymous_wallet_xyz",
    "agent_id": "finance_agent"
  }' | python3 -m json.tool
```

```json
{
    "status": "BLOCK",
    "reason": "Recipient identity cannot be verified (KYC Failure)."
}
```

### 🚫 Scenario D: Unauthorized action — BLOCKED

```bash
curl -s -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "deploy_smart_contract",
    "amount": 0,
    "recipient": "blockchain_mainnet",
    "agent_id": "finance_agent"
  }' | python3 -m json.tool
```

```json
{
    "status": "BLOCK",
    "reason": "Action 'deploy_smart_contract' is not in the approved capabilities list."
}
```

### ✅ Scenario E: Balance query — ALLOWED

```bash
curl -s -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "query_balance",
    "amount": 0,
    "recipient": "internal_account",
    "agent_id": "compliance_agent"
  }' | python3 -m json.tool
```

```json
{
    "status": "ALLOW",
    "reason": "Transaction within safe parameters."
}
```

---

## 🧠 Part 4 — Run AI Agents (BotBook)

### 4a. Run a single agent

> ⚠️ This requires a valid API key (Gemini or OpenAI) in `botbook.dev/.env`

```bash
cd ~/ai-agents-platform/galanipay-agents
source ../.venv/bin/activate

botbook run finance_agent "Analyze Q3 revenue trends for GalaniPay. Identify top 3 growth areas and any anomalies."
```

Expected output:
```
⚡ Running agent: finance_agent
Run ID: a3f2b1c4

[Agent response with financial analysis...]
```

### 4b. Run the full workflow pipeline

```bash
botbook workflow workflows/fintech_pipeline.yaml "Prepare Q3 board report: analyze finances, check compliance, and draft investor outreach"
```

This runs the agents **sequentially** — each agent gets the output from the previous one:

```
====================
Running agent: finance_agent
====================
⚡ Running agent: finance_agent
Run ID: b7c8d9e0
Output summary: Q3 revenue analysis shows 23% growth...

====================
Running agent: compliance_agent
====================
⚡ Running agent: compliance_agent
Run ID: c1d2e3f4
Output summary: Compliance checks passed. No regulatory...

====================
Running agent: sales_agent
====================
⚡ Running agent: sales_agent
Run ID: d5e6f7g8
Output summary: Recommended outreach strategy targeting...

Workflow complete
```

### 4c. Check run history

```bash
botbook inspect
```

Shows the last run:
```
Last Run
--------
Agent: sales_agent
Task: Prepare Q3 board report...
Result:
[Full agent output]
```

```bash
botbook logs
```

Shows all runs:
```
Agent: finance_agent
Task: Prepare Q3 board report...
Time: 2026-03-18T12:15:00

Agent: compliance_agent
Task: Prepare Q3 board report...
Time: 2026-03-18T12:15:03

Agent: sales_agent
Task: Prepare Q3 board report...
Time: 2026-03-18T12:15:06
```

---

## 🔍 Part 5 — Debug and Replay with LORK

```bash
cd ~/ai-agents-platform/LORK
source ../.venv/bin/activate
```

### 5a. List all recorded runs

```bash
lork runs
```

```
LORk Runs

test-run-001
```

### 5b. Inspect a run timeline

```bash
lork inspect test-run-001
```

```
Run Timeline

01 | agent_step      | planner   | 120ms | tokens:500
02 | tool_call       | retriever | 45ms  | tokens:0
     tool: search_docs
     input: kubernetes docs
03 | agent_step      | retriever | 200ms | tokens:800
04 | agent_step      | writer    | 350ms | tokens:1200
```

### 5c. View the execution graph

```bash
lork graph test-run-001
```

```
Execution Graph

planner → retriever
retriever → tool:search_docs
retriever → writer
```

Shows you exactly which agent called which, and what tools were invoked.

### 5d. Get per-agent performance stats

```bash
lork stats test-run-001
```

```
Agent Stats

planner      latency:120ms tokens:500
retriever    latency:245ms tokens:800
writer       latency:350ms tokens:1200
```

### 5e. Replay a run (deterministic re-execution)

```bash
lork replay test-run-001
```

Replays each event from the run's event log — lets you debug exactly what happened.

### 5f. Full JSON trace

```bash
lork trace test-run-001
```

Dumps the complete event log as JSON for programmatic analysis.

---

## 👥 Part 6 — Agent Registry and Trust (BotBook Demo)

```bash
cd ~/ai-agents-platform/botbook.dev
source ../.venv/bin/activate

python demo.py
```

Output — full agent registration with trust scores and matching:

```
── BotBook Demo ────────────────────────────────────

── Registered Members ──────────────────────────────
  bbk_ag_76a82109  data_analyst_v2        trust=0.79  badge=verified
  bbk_ag_fbef2661  finance_gpt_pro        trust=0.78  badge=verified
  bbk_ag_da68e815  support_agent_x        trust=0.74  badge=verified
  bbk_hu_df51a693  Chandan Galani         trust=0.00  badge=verified

── Match: find agents for financial analysis ───────
  → data_analyst_v2        score=0.79  badge=verified
  → finance_gpt_pro        score=0.78  badge=verified

── Trust Profile: top agent ─────────────────────────
  member_id:    bbk_ag_76a82109
  badge:        verified
  trust_score:  0.792
  tasks_done:   200
  avg_rating:   4.90
  audit_hash:   sha256:197079d81cf312acc7150de29667e2825...
  lork_id:      lork_babcfb1a5b64
  vault_id:     vault_61c0b784cc3a
  profile_url:  https://botbook.dev/members/bbk_ag_76a82109

── Done. BotBook is running. ────────────────────────
```

**What happened:**
- 3 AI agents and 1 human were registered
- Each got a **trust score** based on completed tasks and ratings
- Each got a **LORK ID** (execution tracking) and **Vault ID** (governance identity)
- The matching engine found the best agents for "financial analysis"

---

## 🌐 Part 7 — BotBook API Server

Start the server:

```bash
cd ~/ai-agents-platform/botbook.dev
source ../.venv/bin/activate

python -m uvicorn main:app --reload --port 8001
```

Test from another terminal:

```bash
curl -s http://localhost:8001/ | python3 -m json.tool
```

```json
{
    "runtime": "BotBook",
    "status": "running"
}
```

---

## 📊 Summary — What Each Tool Does in This Demo

| Step | Tool | What Happened |
|------|------|---------------|
| Governance server | **PrivateVault.ai** | Policy enforcement: blocks risky transfers, KYC failures, unauthorized actions |
| Create agents | **BotBook** `make` | Scaffolded 4 agents with role templates |
| Run agents | **BotBook** `run` | Executed agent with LLM (Gemini/OpenAI) and logged the run |
| Workflow | **BotBook** `workflow` | Chained 3 agents in sequence, each feeding into the next |
| Inspect runs | **BotBook** `inspect/logs` | Viewed run history and last output |
| Debug timeline | **LORK** `inspect` | Saw step-by-step execution with latency and tokens |
| Execution graph | **LORK** `graph` | Visualized agent-to-agent call flow |
| Performance | **LORK** `stats` | Measured per-agent latency and token usage |
| Replay | **LORK** `replay` | Deterministically re-executed a historical run |
| Trust scoring | **BotBook** `demo.py` | Registered agents with trust profiles, matched by capability |

---

## 🔄 Full Command Reference

### Always Start With

```bash
cd ~/ai-agents-platform
source .venv/bin/activate
```

### BotBook Commands

| Command | Description |
|---------|-------------|
| `botbook` | Show help |
| `botbook init` | Initialize project structure |
| `botbook make <agent>` | Create agent from template |
| `botbook run <agent> "<task>"` | Run agent with LLM |
| `botbook workflow <file> "<task>"` | Run multi-agent pipeline |
| `botbook inspect` | Show last run details |
| `botbook logs` | Show all run history |
| `botbook deploy` | Deploy agents (coming soon) |

### LORK Commands

| Command | Description |
|---------|-------------|
| `lork` | Show help |
| `lork runs` | List all recorded runs |
| `lork inspect <run_id>` | Timeline with latency + tokens |
| `lork replay <run_id>` | Deterministic re-execution |
| `lork trace <run_id>` | Full JSON event dump |
| `lork graph <run_id>` | Agent execution flow graph |
| `lork stats <run_id>` | Per-agent performance stats |

### PrivateVault.ai Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server status |
| `/health` | GET | Health check |
| `/api/v1/shadow_verify` | POST | Policy enforcement (ALLOW/BLOCK) |
| `/docs` | GET | Swagger UI (interactive) |
