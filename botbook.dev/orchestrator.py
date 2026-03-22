"""
LiveOrchestrator — Chains BotBook + PrivateVault + Gemini + LORK in real-time.
Streams SSE to frontend. Now with auto-selection + multi-step ReAct.
"""
import json, time, uuid, re, os, asyncio
from typing import AsyncGenerator
import httpx
from dotenv import load_dotenv
load_dotenv()

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

def sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

TOOL_DECLARATIONS = [
    {"name":"query_database","description":"Query the financial database to retrieve revenue, transactions, or analytics data.","parameters":{"type":"OBJECT","properties":{"query":{"type":"STRING","description":"What data to look up"},"database":{"type":"STRING","description":"Which database: finance, sales, compliance"}},"required":["query"]}},
    {"name":"generate_report","description":"Generate a formatted business report from analysis.","parameters":{"type":"OBJECT","properties":{"title":{"type":"STRING","description":"Report title"},"sections":{"type":"STRING","description":"Comma-separated sections"}},"required":["title"]}},
    {"name":"send_notification","description":"Send a notification via email or Slack.","parameters":{"type":"OBJECT","properties":{"channel":{"type":"STRING","description":"email or slack"},"recipient":{"type":"STRING","description":"Recipient address"},"message":{"type":"STRING","description":"Content"}},"required":["channel","recipient","message"]}},
    {"name":"search_records","description":"Search customer or transaction records.","parameters":{"type":"OBJECT","properties":{"search_term":{"type":"STRING","description":"What to search for"},"record_type":{"type":"STRING","description":"customer, transaction, or compliance"}},"required":["search_term"]}},
]

TOOL_POLICIES = {
    "query_database":{"allowed_agents":["finance_agent","data_analyst_v2","compliance_guardian","finance_gpt_pro","risk_sentinel_v3","legal_reviewer_v2","finops_assistant"]},
    "search_records":{"allowed_agents":["finance_agent","data_analyst_v2","compliance_guardian","support_agent_x","finance_gpt_pro","risk_sentinel_v3","sales_accelerator","finops_assistant"]},
    "generate_report":{"allowed_agents":["finance_agent","data_analyst_v2","compliance_guardian","finance_gpt_pro","legal_reviewer_v2","finops_assistant"]},
    "send_notification":{"allowed_agents":["support_agent_x","sales_accelerator","onboarding_bot","finops_assistant"],"block_external":True},
}

MOCK_TOOL_RESULTS = {
    "query_database":{"status":"success","rows_returned":847,"data":{"q3_revenue":"$5.17M","q2_revenue":"$4.2M","growth_rate":"23.1%","enterprise_deals":12,"top_segments":["Enterprise SaaS ($2.8M)","SMB Subscriptions ($1.4M)","API Revenue ($970K)"],"anomalies":[{"month":"September","category":"Marketing","spike":"+67%","amount":"$340K"}]},"query_time_ms":45},
    "search_records":{"status":"success","results_count":23,"records":[{"id":"TXN-4521","type":"subscription","amount":"$2,400/mo","customer":"Acme Corp"},{"id":"TXN-4522","type":"enterprise_deal","amount":"$180,000/yr","customer":"TechGiant Inc"},{"id":"TXN-4523","type":"api_usage","amount":"$3,200/mo","customer":"DataFlow Labs"}]},
    "generate_report":{"status":"success","pages":12,"format":"PDF","sections_generated":["Executive Summary","Revenue Breakdown","Growth Projections","Risk Factors"]},
    "send_notification":{"status":"sent","delivered":True},
}

class LiveOrchestrator:
    def __init__(self, vault_url, lork_url, botbook_url, agents_store, gemini_key):
        self.vault_url = vault_url
        self.lork_url = lork_url
        self.botbook_url = botbook_url
        self.agents = agents_store
        self.gemini_key = gemini_key

    def find_agent(self, name):
        for a in self.agents:
            if a["name"] == name: return a
        return None

    def classify_intent(self, task):
        t = task.lower()
        amounts = re.findall(r'\$?([\d,]+(?:\.\d+)?)', task)
        amount = float(amounts[0].replace(',','')) if amounts else 0
        if any(w in t for w in ["transfer","send money","wire","disburse"]):
            action = "transfer"
        elif re.search(r'\bsend\b.*\$', t) or re.search(r'\$.*\bto\b', t):
            action = "transfer"  # "send $5415 to X" pattern
        elif "pay " in t and "galanipay" not in t:
            action = "transfer"
        elif "invoice" in t: action = "pay_invoice"
        else: action = "query_balance"
        # Recipient detection
        recipient = "internal_analytics"
        if "anonymous" in t or "anon" in t: recipient = "anonymous_wallet"
        elif "offshore" in t: recipient = "anonymous_offshore"
        elif "vendor" in t or "acme" in t: recipient = "vendor_acme_corp"
        elif "techsupply" in t: recipient = "vendor_techsupply"
        elif "personal" in t or "@gmail" in t or "external" in t: recipient = "external_personal"
        else:
            # Try to extract recipient name from "to <name>" pattern
            to_match = re.search(r'\bto\s+([a-zA-Z_]+)', task)
            if to_match and amount > 0:
                recipient = to_match.group(1).lower()
        return {"action":action,"amount":amount,"recipient":recipient,"agent_id":"agent"}

    async def auto_select_agent(self, http, task):
        """Call BotBook's /match endpoint to intelligently select the best agent."""
        try:
            resp = await http.post(f"{self.botbook_url}/api/v1/match", json={"task": task, "max_results": 5})
            matches = resp.json()
            if matches and len(matches) > 0:
                return matches  # Return all ranked matches
        except Exception as e:
            print(f"   ⚠️ Auto-select failed: {e}")
        return []

    async def execute_stream(self, task, agent_name):
        run_id = f"live-{uuid.uuid4().hex[:8]}"
        events_log = []
        start_time = time.time()
        print(f"\n{'='*60}")
        print(f"🤖 [BotBook] Live Execution Started")
        print(f"   Run: {run_id} | Agent: {agent_name}")
        print(f"   Task: {task[:80]}...")
        print(f"   Gemini Key: {'✅ set' if self.gemini_key else '❌ MISSING'}")
        print(f"{'='*60}")
        async with httpx.AsyncClient(timeout=60.0) as http:

            # STEP 0: Auto-select if requested
            if agent_name == "auto":
                yield sse("auto_select_start", {"task": task[:100], "layer": "BotBook"})
                matches = await self.auto_select_agent(http, task)
                if not matches:
                    yield sse("error", {"message": "No suitable agents found"})
                    return
                # Emit all candidates
                yield sse("auto_select_result", {
                    "candidates": [{"name": m["name"], "score": m.get("match_score",0), "trust": m.get("trust_score",0), "breakdown": m.get("match_breakdown",{})} for m in matches[:5]],
                    "selected": matches[0]["name"],
                    "layer": "BotBook",
                })
                events_log.append({"seq":len(events_log)+1,"type":"auto_select","agent":"BotBook","latency_ms":0,"tokens":0,"payload":f"Auto-selected {matches[0]['name']} (score: {matches[0].get('match_score',0)})"})
                agent_name = matches[0]["name"]
                # Update local store reference
                for a in self.agents:
                    if a["name"] == agent_name:
                        break
                await asyncio.sleep(0.4)

            # STEP 1: Agent Selection
            agent = self.find_agent(agent_name)
            if not agent:
                print(f"   ❌ Agent '{agent_name}' not found!")
                yield sse("error",{"message":f"Agent '{agent_name}' not found in registry"})
                return
            print(f"   ✅ Agent selected: {agent['name']} (trust: {agent['trust_score']}, v{agent.get('version','?')})")
            yield sse("agent_selected",{"agent":agent["name"],"trust_score":agent["trust_score"],"badge":agent["badge"],"capabilities":agent.get("capabilities",[]),"member_id":agent.get("member_id",""),"version":agent.get("version","1.0.0"),"description":agent.get("description",""),"layer":"BotBook"})
            events_log.append({"seq":len(events_log)+1,"type":"agent_selected","agent":agent["name"],"latency_ms":0,"tokens":0,"payload":f"Selected {agent['name']} v{agent.get('version','?')} (trust: {agent['trust_score']})"})
            await asyncio.sleep(0.4)

            # STEP 2: Intent Classification
            intent = self.classify_intent(task)
            intent["agent_id"] = agent["name"]
            yield sse("intent_declared",{"action":intent["action"],"amount":intent["amount"],"recipient":intent["recipient"],"layer":"BotBook"})
            events_log.append({"seq":len(events_log)+1,"type":"intent_declared","agent":agent["name"],"latency_ms":5,"tokens":0,"payload":f"Intent: {intent['action']} ${intent['amount']:,.0f} -> {intent['recipient']}"})
            await asyncio.sleep(0.3)

            # STEP 3: Governance (PrivateVault) — 3-Tier Policy
            yield sse("governance_start",{"layer":"PrivateVault"})
            gov_start = time.time()
            try:
                r = await http.post(f"{self.vault_url}/api/v1/shadow_verify",json=intent)
                gov_result = r.json()
            except Exception as e:
                gov_result = {"status":"ERROR","reason":f"PrivateVault unreachable: {e}","risk_score":1.0,"transaction_id":str(uuid.uuid4()),"merkle_hash":"unavailable","policy_tier":"error"}
            gov_ms = round((time.time()-gov_start)*1000)
            print(f"   🔒 Governance: {gov_result.get('status')} [{gov_result.get('policy_tier','')}] — {gov_result.get('reason','')} ({gov_ms}ms)")
            yield sse("governance_result",{
                "status":gov_result.get("status","ERROR"),
                "reason":gov_result.get("reason",""),
                "risk_score":gov_result.get("risk_score",0),
                "transaction_id":gov_result.get("transaction_id",""),
                "merkle_hash":gov_result.get("merkle_hash",""),
                "latency_ms":gov_ms,
                "policy_tier":gov_result.get("policy_tier",""),
                "escalation":gov_result.get("escalation"),
                "layer":"PrivateVault"
            })
            events_log.append({"seq":len(events_log)+1,"type":"governance_check","agent":"PrivateVault","latency_ms":gov_ms,"tokens":0,"payload":f"{gov_result.get('status')} [{gov_result.get('policy_tier','')}]: {gov_result.get('reason','')}"})
            await asyncio.sleep(0.3)

            # Handle BLOCK — hard stop
            if gov_result.get("status") == "BLOCK":
                yield sse("execution_blocked",{"reason":gov_result["reason"],"risk_score":gov_result.get("risk_score",0),"policy_tier":gov_result.get("policy_tier","hard_block"),"layer":"PrivateVault"})
                await self._record_run(http,run_id,agent["name"],task,events_log,"blocked")
                yield sse("event_recorded",{"run_id":run_id,"events_count":len(events_log),"status":"blocked","layer":"LORK"})
                await asyncio.sleep(0.2)
                yield sse("complete",{"status":"BLOCKED","reason":gov_result["reason"],"total_time_ms":round((time.time()-start_time)*1000),"run_id":run_id,"events_count":len(events_log)})
                return

            # Handle REVIEW — human-in-the-loop
            if gov_result.get("status") == "REVIEW":
                escalation = gov_result.get("escalation", {})
                tx_id = gov_result.get("transaction_id", "")
                yield sse("human_review_required",{
                    "transaction_id": tx_id,
                    "amount": intent.get("amount", 0),
                    "reason": gov_result["reason"],
                    "risk_score": gov_result.get("risk_score", 0),
                    "escalation": escalation,
                    "policy_tier": "human_review",
                    "layer": "PrivateVault"
                })
                events_log.append({"seq":len(events_log)+1,"type":"human_review_escalation","agent":"PrivateVault","latency_ms":0,"tokens":0,"payload":f"Escalated for human review: ${intent.get('amount',0):,.0f}"})
                await asyncio.sleep(1.5)  # Simulate human review time

                # Auto-approve for demo (in production this would wait for actual human input)
                try:
                    approve_resp = await http.post(f"{self.vault_url}/api/v1/human_approve", json={
                        "transaction_id": tx_id,
                        "approved": True,
                        "approver_name": "Dr. Priya Sharma (Finance Director)",
                        "reason": "Transaction reviewed and approved. Amount within acceptable range for vendor payment."
                    })
                    approval = approve_resp.json()
                except Exception:
                    approval = {"human_decision":"APPROVED","final_status":"ALLOW","approver":"Dr. Priya Sharma","approval_hash":"simulated","chain_hash":"simulated"}

                yield sse("human_review_decision",{
                    "transaction_id": tx_id,
                    "decision": approval.get("human_decision","APPROVED"),
                    "final_status": approval.get("final_status","ALLOW"),
                    "approver": approval.get("approver",""),
                    "approval_reason": approval.get("approval_reason",""),
                    "approval_hash": approval.get("approval_hash",""),
                    "chain_hash": approval.get("chain_hash",""),
                    "layer": "PrivateVault"
                })
                events_log.append({"seq":len(events_log)+1,"type":"human_review_completed","agent":"PrivateVault","latency_ms":1500,"tokens":0,"payload":f"Human {approval.get('human_decision','APPROVED')} by {approval.get('approver','')}"})
                await asyncio.sleep(0.4)

                if approval.get("final_status") == "BLOCK":
                    yield sse("execution_blocked",{"reason":"Human reviewer rejected the transaction.","risk_score":gov_result.get("risk_score",0),"policy_tier":"human_review","layer":"PrivateVault"})
                    await self._record_run(http,run_id,agent["name"],task,events_log,"blocked")
                    yield sse("event_recorded",{"run_id":run_id,"events_count":len(events_log),"status":"blocked","layer":"LORK"})
                    yield sse("complete",{"status":"BLOCKED","reason":"Human reviewer rejected.","total_time_ms":round((time.time()-start_time)*1000),"run_id":run_id,"events_count":len(events_log)})
                    return

            # STEP 3.5: Shadow Drift Detection — compare declared intent vs actual execution payload
            # For [DRIFT_TEST] tasks, simulate a compromised agent tampering the payload
            is_drift_test = "[DRIFT_TEST]" in task
            if is_drift_test:
                # Simulate: agent tampered the payload (inflated amount, swapped recipient)
                tampered_intent = {
                    "action": intent["action"],
                    "amount": intent["amount"] * 10,  # 10x inflation attack
                    "recipient": "offshore_shell_corp",  # substituted recipient
                }
                declared_payload = {"action": intent["action"], "amount": intent["amount"], "recipient": intent["recipient"]}
                yield sse("drift_check_start", {
                    "declared": declared_payload,
                    "actual": tampered_intent,
                    "reason": "Shadow firewall comparing declared intent vs agent execution payload",
                    "layer": "PrivateVault"
                })
                events_log.append({"seq":len(events_log)+1,"type":"drift_check","agent":"PrivateVault","latency_ms":0,"tokens":0,"payload":"Checking declared vs actual payload..."})
                await asyncio.sleep(0.6)

                # Call real drift detection
                try:
                    dr = await http.post(f"{self.vault_url}/api/v1/drift_detect", json={
                        "declared": declared_payload,
                        "actual": tampered_intent,
                    })
                    drift_result = dr.json()
                except:
                    drift_result = {"has_drift": True, "risk_level": "HIGH", "policy_decision": "DENY", "metrics": [], "detection_time_ms": 0}

                drift_ms = drift_result.get("detection_time_ms", 0)
                yield sse("drift_detected", {
                    "has_drift": drift_result.get("has_drift", False),
                    "risk_level": drift_result.get("risk_level", "LOW"),
                    "policy_decision": drift_result.get("policy_decision", "ALLOW"),
                    "metrics": drift_result.get("metrics", []),
                    "detection_time_ms": drift_ms,
                    "declared": declared_payload,
                    "actual": tampered_intent,
                    "layer": "PrivateVault"
                })
                events_log.append({"seq":len(events_log)+1,"type":"drift_detected","agent":"PrivateVault","latency_ms":round(drift_ms),"tokens":0,
                    "payload":f"DRIFT: {drift_result.get('risk_level','?')} — {drift_result.get('policy_decision','?')} — {len(drift_result.get('metrics',[]))} fields drifted"})
                await asyncio.sleep(0.4)

                if drift_result.get("policy_decision") == "DENY":
                    yield sse("execution_blocked", {
                        "reason": f"Intent drift detected — agent payload diverged from declared intent. Risk: {drift_result.get('risk_level','HIGH')}. Transaction blocked by shadow firewall.",
                        "risk_score": gov_result.get("risk_score", 0),
                        "policy_tier": "drift_block",
                        "drift_metrics": drift_result.get("metrics", []),
                        "layer": "PrivateVault"
                    })
                    await self._record_run(http, run_id, agent["name"], task, events_log, "drift_blocked")
                    yield sse("event_recorded", {"run_id": run_id, "events_count": len(events_log), "status": "drift_blocked", "layer": "LORK"})
                    await asyncio.sleep(0.2)
                    yield sse("complete", {
                        "status": "BLOCKED",
                        "reason": f"Drift attack detected and blocked. Agent tried to inflate ${intent['amount']:,.0f} → ${tampered_intent['amount']:,.0f} and redirect to {tampered_intent['recipient']}.",
                        "total_time_ms": round((time.time()-start_time)*1000),
                        "run_id": run_id,
                        "events_count": len(events_log)
                    })
                    return

            # STEP 4: ReAct Loop — Gemini → tools → feed back → final answer
            total_tokens = 0
            react_step = 0
            max_react_steps = 3
            conversation = [task]  # Start with the original task

            while react_step < max_react_steps:
                react_step += 1
                current_prompt = conversation[-1] if len(conversation) == 1 else f"Original task: {task}\n\nPrevious tool results:\n{conversation[-1]}\n\nBased on these results, provide your final analysis. Do NOT call any more tools."

                yield sse("llm_start",{"provider":"Gemini","model":"gemini-2.5-flash","task_preview":current_prompt[:100],"react_step":react_step,"layer":"Gemini"})
                llm_start = time.time()
                llm_result = await self._call_gemini(current_prompt, agent, force_text=(react_step > 1))
                llm_ms = round((time.time()-llm_start)*1000)
                total_tokens += llm_result.get("tokens",0)
                print(f"   ✨ Gemini step {react_step}: {llm_result.get('tokens',0)} tokens, {llm_ms}ms, {len(llm_result.get('tool_calls',[]))} tool calls")
                print(f"   📝 Response: {llm_result['text'][:100]}...")

                yield sse("llm_response",{"text":llm_result["text"][:600],"tokens":llm_result.get("tokens",0),"latency_ms":llm_ms,"has_tool_calls":len(llm_result.get("tool_calls",[]))>0,"tool_calls_count":len(llm_result.get("tool_calls",[])),"react_step":react_step,"layer":"Gemini"})
                events_log.append({"seq":len(events_log)+1,"type":"llm_call","agent":agent["name"],"latency_ms":llm_ms,"tokens":llm_result.get("tokens",0),"payload":f"ReAct step {react_step}: {llm_result['text'][:60]}..."})
                await asyncio.sleep(0.3)

                # If no tool calls or we have text, we're done
                if not llm_result.get("tool_calls") or react_step >= max_react_steps:
                    break

                # Process tool calls
                tool_results_text = []
                for tc in llm_result.get("tool_calls",[]):
                    tool_name = tc["name"]
                    tool_input = tc.get("input",{})
                    yield sse("tool_request",{"tool":tool_name,"input":tool_input,"react_step":react_step,"layer":"LORK"})
                    events_log.append({"seq":len(events_log)+1,"type":"tool_call","agent":agent["name"],"latency_ms":0,"tokens":0,"tool":tool_name,"payload":f"Tool: {tool_name}"})
                    await asyncio.sleep(0.4)

                    # Policy gate
                    policy = await self._policy_gate_tool(http,agent,tool_name,tool_input)
                    print(f"   🛡️ Tool policy: {tool_name} → {policy['decision']}")
                    yield sse("policy_gate",{"tool":tool_name,"decision":policy["decision"],"reason":policy["reason"],"layer":"PrivateVault"})
                    events_log.append({"seq":len(events_log)+1,"type":"policy_gate","agent":"PrivateVault","latency_ms":3,"tokens":0,"payload":f"Tool {tool_name}: {policy['decision']}"})
                    await asyncio.sleep(0.3)

                    if policy["decision"] == "ALLOW":
                        tr = self._execute_tool(tool_name,tool_input)
                        yield sse("tool_result",{"tool":tool_name,"output":tr,"layer":"LORK"})
                        events_log.append({"seq":len(events_log)+1,"type":"tool_result","agent":agent["name"],"latency_ms":45,"tokens":0,"payload":f"Tool {tool_name} executed"})
                        tool_results_text.append(f"Tool '{tool_name}' returned: {json.dumps(tr)[:300]}")
                    else:
                        yield sse("tool_blocked",{"tool":tool_name,"reason":policy["reason"],"layer":"PrivateVault"})
                        events_log.append({"seq":len(events_log)+1,"type":"tool_blocked","agent":"PrivateVault","latency_ms":0,"tokens":0,"payload":f"BLOCKED: {tool_name}"})
                        tool_results_text.append(f"Tool '{tool_name}' was BLOCKED by governance: {policy['reason']}")
                    await asyncio.sleep(0.2)

                # Feed tool results back to Gemini for next iteration
                if tool_results_text:
                    conversation.append("\n".join(tool_results_text))
                    yield sse("react_continue",{"step":react_step+1,"reason":"Feeding tool results back to LLM for synthesis","layer":"Gemini"})
                    await asyncio.sleep(0.3)
                else:
                    break

            # STEP 5: Record in LORK
            await self._record_run(http,run_id,agent["name"],task,events_log,"completed")
            yield sse("event_recorded",{"run_id":run_id,"events_count":len(events_log),"status":"completed","layer":"LORK"})
            await asyncio.sleep(0.3)

            # STEP 6: Update Trust
            old_score = agent["trust_score"]
            new_score = round(min(1.0, old_score + 0.002), 4)
            agent["trust_score"] = new_score
            agent["tasks_completed"] = agent.get("tasks_completed",0)+1
            yield sse("trust_updated",{"agent":agent["name"],"old_score":old_score,"new_score":new_score,"tasks_completed":agent["tasks_completed"],"layer":"BotBook"})
            await asyncio.sleep(0.2)

            # STEP 7: Complete
            total_ms = round((time.time()-start_time)*1000)
            print(f"   ✅ COMPLETE: {total_ms}ms, {len(events_log)} events, {total_tokens} tokens")
            print(f"{'='*60}\n")
            yield sse("complete",{"status":"SUCCESS","output":llm_result["text"][:400],"total_time_ms":total_ms,"total_tokens":total_tokens,"run_id":run_id,"events_count":len(events_log),"react_steps":react_step})

    async def _call_gemini(self, task, agent, force_text=False):
        if not GEMINI_AVAILABLE or not self.gemini_key:
            return {"text":"[Gemini unavailable - check google-genai and API key]","tokens":0,"tool_calls":[]}
        try:
            client = genai.Client(api_key=self.gemini_key)
            agent_caps = ', '.join(agent.get('capabilities',[]))
            system_prompt = (
                f"You are '{agent['name']}' v{agent.get('version','?')}, an enterprise AI agent deployed on the BotBook Agent OS.\n"
                f"Capabilities: {agent_caps}\n"
                f"Trust Score: {agent['trust_score']}, Badge: {agent['badge']}\n"
                f"You are governed by PrivateVault.ai which has ALREADY verified and approved this action.\n\n"
                f"CRITICAL INSTRUCTION: You ARE this agent executing live in production. When asked to perform any task "
                f"within your capabilities (transfer funds, send emails, generate reports, analyze data, etc.), "
                f"you MUST simulate executing it and confirm completion with realistic operational details.\n"
                f"Include: confirmation/transaction IDs, timestamps, status updates, next steps.\n"
                f"You are an OPERATIONAL agent, NOT an advisory chatbot. Never say 'I cannot' for tasks in your capabilities.\n\n"
                f"Example for transfer: 'Transfer executed. $5,000 sent to vendor_acme_corp. TXN-ID: TXN-A7B3F2. "
                f"Settlement: T+1 business day. Audit trail recorded.'\n"
                f"Example for email: 'Email sent to finance@company.com. Subject: Transfer Confirmation. MSG-ID: MSG-8F3A21.'\n\n"
                f"Respond concisely (under 200 words). Use tools when helpful."
            )
            if force_text:
                system_prompt += "\nIMPORTANT: Provide your final text analysis now. Do NOT request any tools."

            func_decls = []
            if not force_text:
                for td in TOOL_DECLARATIONS:
                    props = {}
                    for pname, pinfo in td["parameters"]["properties"].items():
                        props[pname] = genai_types.Schema(type=pinfo["type"], description=pinfo.get("description",""))
                    func_decls.append(genai_types.FunctionDeclaration(name=td["name"],description=td["description"],parameters=genai_types.Schema(type="OBJECT",properties=props,required=td["parameters"].get("required",[]))))

            tools = [genai_types.Tool(function_declarations=func_decls)] if func_decls else None
            config = genai_types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3)
            if tools:
                config = genai_types.GenerateContentConfig(system_instruction=system_prompt, tools=tools, temperature=0.3)

            response = client.models.generate_content(model="gemini-2.5-flash", contents=task, config=config)
            text, tool_calls = "", []
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if hasattr(part,'text') and part.text: text += part.text
                    if hasattr(part,'function_call') and part.function_call:
                        fc = part.function_call
                        tool_calls.append({"name":fc.name,"input":dict(fc.args) if fc.args else {}})
            tokens = getattr(getattr(response,'usage_metadata',None),'total_token_count',0) or 0
            return {"text":text or "[Agent processing complete]","tokens":tokens,"tool_calls":tool_calls}
        except Exception as e:
            return {"text":f"[Gemini error: {str(e)}]","tokens":0,"tool_calls":[]}

    async def _policy_gate_tool(self, http, agent, tool_name, tool_input):
        policy = TOOL_POLICIES.get(tool_name,{})
        allowed = policy.get("allowed_agents",[])
        if allowed and agent["name"] not in allowed:
            return {"decision":"DENY","reason":f"Agent '{agent['name']}' not authorized for '{tool_name}'"}
        if policy.get("block_external"):
            recip = tool_input.get("recipient","")
            if any(ext in recip.lower() for ext in ["@gmail","@yahoo","@hotmail","external","personal"]):
                return {"decision":"DENY","reason":f"External recipient '{recip}' blocked. Internal only."}
        try:
            v = {"action":f"tool.{tool_name}","amount":0,"recipient":tool_input.get("recipient","internal"),"agent_id":agent["name"]}
            resp = await http.post(f"{self.vault_url}/api/v1/shadow_verify",json=v)
            vr = resp.json()
            if vr.get("status")=="BLOCK": return {"decision":"DENY","reason":vr.get("reason","")}
        except: pass
        return {"decision":"ALLOW","reason":f"Tool '{tool_name}' approved for '{agent['name']}'"}

    def _execute_tool(self, tool_name, tool_input):
        base = json.loads(json.dumps(MOCK_TOOL_RESULTS.get(tool_name,{"status":"success"})))
        if tool_name=="generate_report":
            base["report_id"]="RPT-"+uuid.uuid4().hex[:6].upper()
            base["title"]=tool_input.get("title","Report")
        elif tool_name=="send_notification":
            base["message_id"]="MSG-"+uuid.uuid4().hex[:8]
            base["channel"]=tool_input.get("channel","email")
            base["recipient"]=tool_input.get("recipient","")
        return base

    async def _record_run(self, http, run_id, agent_name, task, events, status):
        try:
            await http.post(f"{self.lork_url}/api/v1/runs/record",json={"run_id":run_id,"name":f"live-{agent_name}","description":task[:80],"task":task,"status":status,"events":events,"graph":[]})
        except: pass

class PipelineOrchestrator:
    def __init__(self, orch): self.orch = orch
    async def execute_pipeline(self, task, agent_names):
        pid = f"pipeline-{uuid.uuid4().hex[:8]}"
        yield sse("pipeline_start",{"pipeline_id":pid,"agents":agent_names,"task":task})
        results = []
        for i, name in enumerate(agent_names):
            yield sse("pipeline_step_start",{"step":i+1,"total_steps":len(agent_names),"agent":name})
            await asyncio.sleep(0.3)
            blocked = False
            async for ev in self.orch.execute_stream(task, name):
                yield ev
                if '"BLOCKED"' in ev: blocked = True
            results.append({"agent":name,"status":"BLOCKED" if blocked else "SUCCESS"})
            yield sse("pipeline_step_end",{"step":i+1,"agent":name,"status":"BLOCKED" if blocked else "SUCCESS"})
            await asyncio.sleep(0.3)
        succeeded = sum(1 for r in results if r["status"]=="SUCCESS")
        yield sse("pipeline_complete",{"pipeline_id":pid,"total_agents":len(agent_names),"succeeded":succeeded,"blocked":len(agent_names)-succeeded,"results":results})
