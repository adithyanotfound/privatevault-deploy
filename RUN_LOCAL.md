# 🛠️ Running Services Locally

This guide explains how to start each service for local development. Make sure your virtual environment is activated.

## 🐍 1. Environment Setup

```bash
# In each new terminal window, activate the venv
source .venv/bin/activate
```

---

## 🔒 2. PrivateVault.ai (Governance)
**Role:** Policy enforcement, shadow verification, and audit ledger.
**Port:** 8000

```bash
cd PrivateVault.ai
python -m uvicorn main:app --reload --port 8000
```
- **Verification:** [http://localhost:8000/](http://localhost:8000/)
- **Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🤖 3. BotBook.dev (Agent OS)
**Role:** Agent registration, matching engine, and trust scoring.
**Port:** 8001

```bash
cd botbook.dev
python -m uvicorn main:app --reload --port 8001
```
- **Verification:** [http://localhost:8001/](http://localhost:8001/)
- **Demo:** `python demo.py` (Run this to see agent registration in action)

---

## 🔬 4. LORK (Control Plane)
**Role:** Event-sourcing, run inspection, and deterministic replay.
**Port:** 8002

```bash
cd LORK
python -m uvicorn lork.api_server:app --reload --port 8002
```
- **Verification:** [http://localhost:8002/](http://localhost:8002/)

---

## 💻 5. Demo Frontend
**Role:** Visual dashboard for agents, governance, and tracing.
**Port:** 8003 (or use any static server)

```bash
cd demo-frontend
# Using Python's built-in server
python -m http.server 8003
```
- **Open Dashboard:** [http://localhost:8003/](http://localhost:8003/)

---

## 📂 Configuration
Service URLs are centralized in `services_config.json` at the root and in each service folder:
```json
{
  "privatevault": "http://localhost:8000",
  "botbook": "http://localhost:8001",
  "lork": "http://localhost:8002"
}
```
