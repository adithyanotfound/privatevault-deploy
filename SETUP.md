# 🚀 Setup Guide — Kubernetes for AI Agents

> **LORK** + **PrivateVault.ai** + **BotBook.dev** — complete setup and testing guide.

---

## 📋 Overview

| Repo | Role | Description |
|------|------|-------------|
| **LORK** | Control Plane | Event-sourced runtime for AI agents — scheduling, replay, time-travel debugging |
| **PrivateVault.ai** | Governance Layer | Runtime policy enforcement, audit ledger, security controls for AI agents |
| **BotBook.dev** | Operating System | Agent lifecycle management — create, run, deploy, and orchestrate AI agents |

### How They Work Together

```
        ┌─────────────────────────────────────┐
        │          BotBook.dev (CLI)           │
        │   botbook init / make / run / deploy │
        └──────────┬──────────────┬───────────┘
                   │              │
          ┌────────▼────────┐    │
          │      LORK       │    │
          │  Control Plane  │    │
          │  (runs, replay, │    │
          │   debug, trace) │    │
          └────────┬────────┘    │
                   │    ┌────────▼────────┐
                   │    │  PrivateVault.ai │
                   │    │   Governance &   │
                   │    │   Security Layer │
                   │    │  (policy, audit, │
                   │    │   identity)      │
                   │    └────────┬─────────┘
                   │             │
          ┌────────▼─────────────▼───────┐
          │     LLM Provider (Gemini     │
          │      or OpenAI)              │
          └──────────────────────────────┘
```

---

## ⚙️ Prerequisites

- **Python 3.10+** (tested with 3.12)
- **pip** (latest)
- **git**

Check your Python version:

```bash
python3 --version    # Should be >= 3.10
pip3 --version
```

---

## 📂 Step 1 — Clone the Repositories

```bash
mkdir -p ~/ai-agents-platform && cd ~/ai-agents-platform

git clone https://github.com/YOUR_ORG/LORK.git
git clone https://github.com/YOUR_ORG/PrivateVault.ai.git
git clone https://github.com/YOUR_ORG/botbook.dev.git
```

> Replace `YOUR_ORG` with the actual GitHub organization/username.

After cloning, your directory should look like:

```
ai-agents-platform/
├── LORK/
├── PrivateVault.ai/
└── botbook.dev/
```

---

## 🐍 Step 2 — Create a Shared Virtual Environment

All three repos share one virtual environment:

```bash
cd ~/ai-agents-platform

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

> ⚠️ **IMPORTANT:** You must run `source .venv/bin/activate` in **every new terminal window** before using any commands (`botbook`, `lork`, `python`, etc). If you see `command not found`, this is why.

---

## 📦 Step 3 — Install All Dependencies

Install each repo in order:

### 3a. Install LORK (editable mode)

```bash
pip install -e ./LORK
```

This installs: `pydantic`, `pydantic-settings`, `python-dotenv`, `google-genai`

### 3b. Install BotBook.dev (editable mode)

```bash
pip install -e ./botbook.dev
```

This installs: `fastapi`, `uvicorn`, and the `botbook` CLI command.

### 3c. Install PrivateVault.ai dependencies

```bash
pip install -r ./PrivateVault.ai/requirements.txt
```

This installs: `fastapi`, `uvicorn`, `pydantic`, `cryptography`, `PyJWT`, `structlog`, `python-dotenv`, `google-genai`, `openai`, and more.

### 3d. Install remaining shared packages

```bash
pip install pyyaml openai google-genai python-dotenv
```

---

## 🖥️ How to Run CLI Commands

> **Every time you open a new terminal**, you must activate the virtual environment first.
> Without this, `botbook`, `lork`, and all Python commands will show `command not found`.

### Activate the virtual environment

```bash
# From the project root (where .venv/ lives)
cd ~/ai-agents-platform
source .venv/bin/activate
```

You'll see `(.venv)` appear at the start of your terminal prompt. Now you can use:

### BotBook CLI

```bash
# Show help
botbook

# Initialize a project
botbook init

# Create an agent
botbook make sales_agent

# Run an agent (needs API key in .env)
botbook run sales_agent "Analyze Q3 pipeline"

# Run a multi-agent workflow
botbook workflow sales_pipeline.yaml "Process enterprise deals"

# View run history
botbook inspect
botbook logs

# Start the API server
cd botbook.dev
python -m uvicorn main:app --reload --port 8001
```

### LORK CLI

```bash
# Show help
lork

# List all recorded runs
cd LORK
lork runs

# Inspect a specific run
lork inspect <run_id>

# Replay a run (deterministic re-execution)
lork replay <run_id>

# Full JSON trace
lork trace <run_id>

# Execution graph (agent flow)
lork graph <run_id>

# Per-agent stats
lork stats <run_id>
```

### PrivateVault.ai Server

```bash
# Start the governance server
cd PrivateVault.ai
python -m uvicorn main:app --reload --port 8000

# Or run directly
python main.py
```

### Alternative: Run Without Activating Venv

If you don't want to activate the venv every time, you can use the full path:

```bash
# Replace ~/ai-agents-platform with your actual project root
~/ai-agents-platform/.venv/bin/botbook init
~/ai-agents-platform/.venv/bin/lork runs
~/ai-agents-platform/.venv/bin/python -m uvicorn main:app --port 8000
```

---

## 🔑 Step 4 — Configure API Keys (.env files)

Each repo uses a `.env` file for configuration. **Never commit API keys to git** — `.env` is already in all three `.gitignore` files.

### Choose Your LLM Provider

You can use either **Google Gemini** (default) or **OpenAI**.

### 4a. BotBook.dev .env

```bash
cp botbook.dev/.env.example botbook.dev/.env
```

Edit `botbook.dev/.env`:

**For Gemini (recommended):**
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash

LORK_PATH=../LORK
PRIVATEVAULT_PATH=../PrivateVault.ai
```

**For OpenAI:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_actual_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

LORK_PATH=../LORK
PRIVATEVAULT_PATH=../PrivateVault.ai
```

### 4b. LORK .env

```bash
cp LORK/.env.example LORK/.env
```

Edit `LORK/.env`:

```env
GEMINI_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
# OPENAI_API_KEY=your_openai_key    # uncomment if using OpenAI
# ANTHROPIC_API_KEY=your_key        # uncomment if using Anthropic
```

### 4c. PrivateVault.ai .env

```bash
cp PrivateVault.ai/.env.example PrivateVault.ai/.env
```

Edit `PrivateVault.ai/.env`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_gemini_api_key
```

### How to Get API Keys

| Provider | URL | Env Variable |
|----------|-----|--------------|
| Google Gemini | https://aistudio.google.com/apikey | `GEMINI_API_KEY` |
| OpenAI | https://platform.openai.com/api-keys | `OPENAI_API_KEY` |

---

## ✅ Step 5 — Verify Installation

> Make sure you have activated the venv: `source .venv/bin/activate`

### 5a. Verify LORK CLI

```bash
lork
```

Expected output:
```
Commands:
  lork runs
  lork inspect <run_id>
  lork replay <run_id>
  lork trace <run_id>
  lork graph <run_id>
  lork stats <run_id>
```

### 5b. Verify BotBook CLI

```bash
botbook
```

Expected output:
```
BotBook CLI

Lifecycle

botbook init
botbook make <agent>
botbook run <agent> "<task>"

Orchestration

botbook workflow <pipeline.yaml> "<task>"

Observability

botbook inspect
botbook logs

Deployment

botbook deploy
```

### 5c. Verify PrivateVault.ai loads

```bash
cd PrivateVault.ai
python3 -c "from main import app; print('PrivateVault OK:', app.title)"
cd ..
```

Expected:
```
PrivateVault OK: Galani Protocol Governance Node
```

---

## 🎮 Step 6 — Run and Test Each Component

### 6a. LORK — Control Plane for AI Agents

**List runs:**
```bash
cd LORK
lork runs
```

**Inspect a run** (after running workflows):
```bash
lork inspect <run_id>
```

Shows execution timeline with latency and token counts.

**Trace a run** (full JSON dump):
```bash
lork trace <run_id>
```

**Graph view:**
```bash
lork graph <run_id>
```

Shows agent-to-agent execution flow like:
```
planner → retriever
retriever → tool:search_docs
retriever → writer
```

**Replay a run** (re-execute historical events):
```bash
lork replay <run_id>
```

**Agent stats:**
```bash
lork stats <run_id>
```

Shows per-agent latency and token usage.

---

### 6b. BotBook.dev — Agent Operating System

**Initialize a new project:**
```bash
mkdir my-project && cd my-project
botbook init
```

Creates the project structure:
```
agents/
tools/
memory/
workflows/
```

**Create an agent:**
```bash
botbook make sales_agent
```

Creates `agents/sales_agent.py` with a template.

Available agent templates:
- `sales_agent` — Sales automation
- `finance_agent` — Financial analysis  
- `executive_assistant` — Scheduling
- `hr_head` — HR management
- `operations_head` — Operations
- `marketing_agent` — Marketing
- `recruiter` — Hiring
- `compliance_agent` — Regulatory
- `risk_monitor` — Risk detection
- `customer_support` — Support

**Run an agent** (requires LLM API key in `.env`):
```bash
botbook run sales_agent "Analyze Q3 pipeline and recommend top 3 leads"
```

**Run a workflow pipeline:**
```bash
botbook workflow sales_pipeline.yaml "Analyze enterprise deals"
```

Example `sales_pipeline.yaml`:
```yaml
steps:
  - research_agent
  - sales_agent
  - outreach_agent
```

**View run history:**
```bash
botbook inspect    # Show last run details
botbook logs       # Show all run logs
```

**Start the BotBook API server:**
```bash
cd botbook.dev
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

Test it:
```bash
curl http://localhost:8001/
# → {"runtime": "BotBook", "status": "running"}
```

**Run the BotBook Demo** (agent registration + trust scoring):
```bash
cd botbook.dev
python demo.py
```

---

### 6c. PrivateVault.ai — Governance & Security

**Start the governance server:**
```bash
cd PrivateVault.ai
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Test the root endpoint:**
```bash
curl http://localhost:8000/
```

Expected:
```json
{
  "system": "Galani Governance Node",
  "status": "ONLINE",
  "mode": "SHADOW_VERIFY",
  "docs_url": "/docs"
}
```

**Health check:**
```bash
curl http://localhost:8000/health
```

Expected: `{"status": "healthy", "service": "galani-node"}`

**Shadow Verify — Transaction ALLOWED:**
```bash
curl -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "transfer",
    "amount": 5000,
    "recipient": "vendor_123",
    "agent_id": "finance_agent"
  }'
```

Expected: `"status": "ALLOW"`

**Shadow Verify — Transaction BLOCKED (exceeds limit):**
```bash
curl -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "transfer",
    "amount": 50000,
    "recipient": "vendor_123",
    "agent_id": "finance_agent"
  }'
```

Expected: `"status": "BLOCK", "reason": "Amount exceeds automated authorization limit"`

**Shadow Verify — Transaction BLOCKED (unknown recipient):**
```bash
curl -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "transfer",
    "amount": 1000,
    "recipient": "anonymous_wallet",
    "agent_id": "finance_agent"
  }'
```

Expected: `"status": "BLOCK", "reason": "Recipient identity cannot be verified"`

**Shadow Verify — Transaction BLOCKED (unauthorized action):**
```bash
curl -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{
    "action": "deploy_contract",
    "amount": 100,
    "recipient": "vendor_123",
    "agent_id": "finance_agent"
  }'
```

Expected: `"status": "BLOCK", "reason": "Action 'deploy_contract' is not in the approved capabilities list"`

**Interactive API docs:**
Open http://localhost:8000/docs in your browser for the Swagger UI.

---

## 🔄 Step 7 — Run All Three Together

Open **3 terminal tabs**:

**Terminal 1 — PrivateVault.ai (Governance on port 8000):**
```bash
cd ~/ai-agents-platform
source .venv/bin/activate
cd PrivateVault.ai
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — BotBook.dev (Agent API on port 8001):**
```bash
cd ~/ai-agents-platform
source .venv/bin/activate
cd botbook.dev
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**Terminal 3 — Run agents and inspect with LORK:**
```bash
cd ~/ai-agents-platform
source .venv/bin/activate

# Initialize a project
mkdir my-project && cd my-project
botbook init
botbook make sales_agent
botbook make finance_agent

# Run an agent (requires API key in .env)
botbook run sales_agent "Analyze Q3 pipeline"

# Check run history
botbook inspect
botbook logs

# Use LORK to inspect runs
cd ../LORK
lork runs
lork inspect <run_id>
lork graph <run_id>
lork stats <run_id>
```

---

## 🔌 LLM Provider Configuration

### Switching Between Providers

The platform supports two LLM providers. Set `LLM_PROVIDER` in your `.env`:

| Value | Provider | Required Env Var |
|-------|----------|-----------------|
| `gemini` (default) | Google Gemini | `GEMINI_API_KEY` |
| `openai` | OpenAI | `OPENAI_API_KEY` |

### Gemini Setup (Default)

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

Supported Gemini models:
- `gemini-2.5-pro` (advanced)
- `gemini-2.5-flash` (balanced)

### OpenAI Setup

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

### LORK LLM Executor

LORK's executor supports three providers: `openai`, `anthropic`, and `gemini`.  
Set the corresponding API key in `LORK/.env`:

```env
GEMINI_API_KEY=your_key
# or
OPENAI_API_KEY=your_key
# or
ANTHROPIC_API_KEY=your_key
```

---

## 🗂️ Project Structure

```
ai-agents-platform/
├── .venv/                    # Shared virtual environment
├── SETUP.md                  # This file
│
├── LORK/                     # Control Plane
│   ├── .env                  # API keys (git-ignored)
│   ├── .env.example          # Template
│   ├── lork/
│   │   ├── cli.py            # CLI entrypoint (lork command)
│   │   ├── config.py         # Settings (loads .env)
│   │   ├── devtools.py       # runs/inspect/replay/trace/graph/stats
│   │   └── runtime/
│   │       └── executors/
│   │           └── llm_executor.py  # OpenAI + Anthropic + Gemini
│   ├── cmd/                  # Standalone CLI tools
│   └── workflows/            # Example workflow YAMLs
│
├── PrivateVault.ai/          # Governance Layer
│   ├── .env                  # API keys (git-ignored)
│   ├── .env.example          # Template
│   ├── main.py               # FastAPI governance server
│   ├── connectors/
│   │   └── ai/
│   │       ├── openai/       # OpenAI connector
│   │       └── gemini/       # Gemini connector (NEW)
│   │           ├── connector.py
│   │           ├── connector.json
│   │           └── config/gemini.defaults.json
│   └── requirements.txt
│
└── botbook.dev/              # Agent OS
    ├── .env                  # API keys (git-ignored)
    ├── .env.example          # Template
    ├── botbook/
    │   ├── __init__.py       # BotBook + MatchIntent classes
    │   ├── cli.py            # CLI entrypoint (botbook command)
    │   ├── core/
    │   │   ├── models.py     # MemberProfile, TrustProfile, Badge
    │   │   └── bridge.py     # LORK + PrivateVault integration
    │   ├── integrations/
    │   │   ├── lork_adapter.py
    │   │   └── privatevault_adapter.py
    │   └── runtime/
    │       ├── llm.py        # Multi-provider LLM (Gemini + OpenAI)
    │       ├── executor.py   # Agent execution engine
    │       └── workflow.py   # Pipeline orchestrator
    ├── demo.py               # Quick demo script
    └── requirements.txt
```

---

## 🧪 Quick Smoke Test Checklist

Run these commands to verify everything works:

```bash
cd ~/ai-agents-platform
source .venv/bin/activate

# ✅ 1. LORK CLI loads
lork
# Expected: shows help with commands

# ✅ 2. BotBook CLI loads
botbook
# Expected: shows help with lifecycle/orchestration/observability

# ✅ 3. BotBook init works
mkdir -p /tmp/test-project && cd /tmp/test-project
botbook init
# Expected: "Project initialized" + folder structure

# ✅ 4. BotBook make works
botbook make sales_agent
# Expected: "Created agent: agents/sales_agent.py"

# ✅ 5. BotBook demo works
cd ~/ai-agents-platform/botbook.dev
python demo.py
# Expected: registered members, trust scores, matching results

# ✅ 6. PrivateVault starts
cd ~/ai-agents-platform/PrivateVault.ai
python -m uvicorn main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/ | python3 -m json.tool
# Expected: {"system": "Galani Governance Node", "status": "ONLINE"}

# ✅ 7. Shadow verify works
curl -s -X POST http://localhost:8000/api/v1/shadow_verify \
  -H "Content-Type: application/json" \
  -d '{"action":"transfer","amount":5000,"recipient":"vendor_123","agent_id":"test"}' \
  | python3 -m json.tool
# Expected: "status": "ALLOW"

# ✅ 8. LORK inspect works  
cd ~/ai-agents-platform/LORK
lork runs
# Expected: lists available runs

# ✅ 9. Gemini connector loads
cd ~/ai-agents-platform/PrivateVault.ai
python3 -c "
from connectors.ai.gemini.connector import GeminiConnector
c = GeminiConnector()
print('OK:', c.id, c.capabilities())
"
# Expected: OK: pv.ai.gemini ['model_invoke']

# Clean up background server
kill %1 2>/dev/null
```

---

## ❓ Troubleshooting

### `botbook: command not found` or `lork: command not found`
→ **You haven't activated the virtual environment.** Run this first:
```bash
cd ~/ai-agents-platform   # or wherever your project root is
source .venv/bin/activate
```
You should see `(.venv)` in your terminal prompt. Now try the command again.

If you still get the error, reinstall:
```bash
pip install -e ./LORK
pip install -e ./botbook.dev
```

### "ModuleNotFoundError: No module named 'lork'"
→ Make sure you installed LORK in editable mode: `pip install -e ./LORK`

### "ModuleNotFoundError: No module named 'botbook'"
→ Make sure you installed BotBook in editable mode: `pip install -e ./botbook.dev`

### "Missing API key" error when running agents
→ Create a `.env` file in the repo root with your API key. See Step 4.

### "openai.OpenAIError: The api_key client option must be set"
→ This means `LLM_PROVIDER` is set to `openai` but `OPENAI_API_KEY` is missing. Either:
  - Switch to Gemini: set `LLM_PROVIDER=gemini` in `.env`
  - Or set `OPENAI_API_KEY` in `.env`

### Port 8000 already in use
→ Use a different port: `python -m uvicorn main:app --port 8002`

### BotBook `botbook run` fails
→ Ensure your `.env` file exists in the `botbook.dev/` directory with a valid API key.

---

## 📝 Notes

- All API keys are loaded from `.env` files via `python-dotenv` — no need to `export` environment variables manually.
- `.env` files are git-ignored in all three repos.
- The default LLM provider is **Gemini** (`gemini-2.0-flash`).
- To switch to OpenAI, change `LLM_PROVIDER=openai` in your `.env` and set `OPENAI_API_KEY`.
- LORK's executor additionally supports **Anthropic** as a third provider.
