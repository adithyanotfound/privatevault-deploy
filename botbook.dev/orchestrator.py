"""
LiveOrchestrator — Chains BotBook + PrivateVault + Gemini + LORK in real-time.
Streams Server-Sent Events to the frontend for every step.
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
    "query_database":{"allowed_agents":["finance_agent","data_analyst_v2","compliance_guardian","finance_gpt_pro"]},
    "search_records":{"allowed_agents":["finance_agent","data_analyst_v2","compliance_guardian","support_agent_x","finance_gpt_pro"]},
    "generate_report":{"allowed_agents":["finance_agent","data_analyst_v2","compliance_guardian","finance_gpt_pro"]},
    "send_notification":{"allowed_agents":["support_agent_x","sales_accelerator","onboarding_bot"],"block_external":True},
}

MOCK_TOOL_RESULTS = {
    "query_database":{"status":"success","rows_returned":847,"data":{"q3_revenue":"$5.17M","q2_revenue":"$4.2M","growth_rate":"23.1%","enterprise_deals":12,"top_segments":["Enterprise SaaS ($2.8M)","SMB Subscriptions ($1.4M)","API Revenue ($970K)"],"anomalies":[{"month":"September","category":"Marketing","spike":"+67%","amount":"$340K"}]},"query_time_ms":45},
    "search_records":{"status":"success","results_count":23,"records":[{"id":"TXN-4521","type":"subscription","amount":"$2,400/mo","customer":"Acme Corp"},{"id":"TXN-4522","type":"enterprise_deal","amount":"$180,000/yr","customer":"TechGiant Inc"}]},
    "generate_report":{"status":"success","pages":12,"format":"PDF","sections_generated":["Executive Summary","Revenue Breakdown","Growth Projections","Risk Factors"]},
    "send_notification":{"status":"sent","delivered":True},
}

class LiveOrchestrator:
    def __init__(self, vault_url, lork_url, agents_store, gemini_key):
        self.vault_url = vault_url
        self.lork_url = lork_url
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
        if any(w in t for w in ["transfer","send money","wire","pay "]):
            action = "transfer"
        elif "invoice" in t: action = "pay_invoice"
        elif any(w in t for w in ["balance","query_balance"]): action = "query_balance"
        else: action = "query_balance"
        recipient = "internal_analytics"
        if "anonymous" in t or "anon" in t: recipient = "anonymous_wallet"
        elif "offshore" in t: recipient = "anonymous_offshore"
        elif "vendor" in t or "acme" in t: recipient = "vendor_acme_corp"
        elif "personal" in t or "@gmail" in t or "external" in t: recipient = "external_personal"
        return {"action":action,"amount":amount,"recipient":recipient,"agent_id":"agent"}

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
        async with httpx.AsyncClient(timeout=30.0) as http:
            # STEP 1: Agent Selection (BotBook)
            agent = self.find_agent(agent_name)
            if not agent:
                print(f"   ❌ Agent '{agent_name}' not found!")
                yield sse("error",{"message":f"Agent '{agent_name}' not found"})
                return
            print(f"   ✅ Agent selected: {agent['name']} (trust: {agent['trust_score']})")
            yield sse("agent_selected",{"agent":agent["name"],"trust_score":agent["trust_score"],"badge":agent["badge"],"capabilities":agent.get("capabilities",[]),"member_id":agent.get("member_id",""),"layer":"BotBook"})
            events_log.append({"seq":len(events_log)+1,"type":"agent_selected","agent":agent["name"],"latency_ms":0,"tokens":0,"payload":f"Selected {agent['name']} (trust: {agent['trust_score']})"})
            await asyncio.sleep(0.4)

            # STEP 2: Intent Classification
            intent = self.classify_intent(task)
            intent["agent_id"] = agent["name"]
            yield sse("intent_declared",{"action":intent["action"],"amount":intent["amount"],"recipient":intent["recipient"],"layer":"BotBook"})
            events_log.append({"seq":len(events_log)+1,"type":"intent_declared","agent":agent["name"],"latency_ms":5,"tokens":0,"payload":f"Intent: {intent['action']} ${intent['amount']:,.0f} -> {intent['recipient']}"})
            await asyncio.sleep(0.3)

            # STEP 3: Governance (PrivateVault)
            yield sse("governance_start",{"layer":"PrivateVault"})
            gov_start = time.time()
            try:
                r = await http.post(f"{self.vault_url}/api/v1/shadow_verify",json=intent)
                gov_result = r.json()
            except Exception as e:
                gov_result = {"status":"ERROR","reason":f"PrivateVault unreachable: {e}","risk_score":1.0,"transaction_id":str(uuid.uuid4()),"merkle_hash":"unavailable"}
            gov_ms = round((time.time()-gov_start)*1000)
            print(f"   🔒 Governance: {gov_result.get('status')} — {gov_result.get('reason','')} ({gov_ms}ms)")
            yield sse("governance_result",{"status":gov_result.get("status","ERROR"),"reason":gov_result.get("reason",""),"risk_score":gov_result.get("risk_score",0),"transaction_id":gov_result.get("transaction_id",""),"merkle_hash":gov_result.get("merkle_hash",""),"latency_ms":gov_ms,"layer":"PrivateVault"})
            events_log.append({"seq":len(events_log)+1,"type":"governance_check","agent":"PrivateVault","latency_ms":gov_ms,"tokens":0,"payload":f"{gov_result.get('status')}: {gov_result.get('reason','')}"})
            await asyncio.sleep(0.3)

            if gov_result.get("status") == "BLOCK":
                yield sse("execution_blocked",{"reason":gov_result["reason"],"risk_score":gov_result.get("risk_score",0),"layer":"PrivateVault"})
                await self._record_run(http,run_id,agent["name"],task,events_log,"blocked")
                yield sse("event_recorded",{"run_id":run_id,"events_count":len(events_log),"status":"blocked","layer":"LORK"})
                await asyncio.sleep(0.2)
                yield sse("complete",{"status":"BLOCKED","reason":gov_result["reason"],"total_time_ms":round((time.time()-start_time)*1000),"run_id":run_id,"events_count":len(events_log)})
                return

            # STEP 4: Gemini LLM Call
            yield sse("llm_start",{"provider":"Gemini","model":"gemini-2.5-flash","task_preview":task[:100],"layer":"Gemini"})
            llm_start = time.time()
            llm_result = await self._call_gemini(task,agent)
            llm_ms = round((time.time()-llm_start)*1000)
            print(f"   ✨ Gemini: {llm_result.get('tokens',0)} tokens, {llm_ms}ms, {len(llm_result.get('tool_calls',[]))} tool calls")
            print(f"   📝 Response: {llm_result['text'][:100]}...")
            yield sse("llm_response",{"text":llm_result["text"][:600],"tokens":llm_result.get("tokens",0),"latency_ms":llm_ms,"has_tool_calls":len(llm_result.get("tool_calls",[]))>0,"tool_calls_count":len(llm_result.get("tool_calls",[])),"layer":"Gemini"})
            events_log.append({"seq":len(events_log)+1,"type":"llm_call","agent":agent["name"],"latency_ms":llm_ms,"tokens":llm_result.get("tokens",0),"payload":f"Gemini: {llm_result['text'][:80]}..."})
            await asyncio.sleep(0.3)

            # STEP 5: Tool Calls + Policy Gating
            for tc in llm_result.get("tool_calls",[]):
                tool_name = tc["name"]
                tool_input = tc.get("input",{})
                yield sse("tool_request",{"tool":tool_name,"input":tool_input,"layer":"LORK"})
                events_log.append({"seq":len(events_log)+1,"type":"tool_call","agent":agent["name"],"latency_ms":0,"tokens":0,"tool":tool_name,"input":json.dumps(tool_input)[:100],"payload":f"Tool request: {tool_name}"})
                await asyncio.sleep(0.4)
                policy = await self._policy_gate_tool(http,agent,tool_name,tool_input)
                print(f"   🛡️ Tool policy: {tool_name} → {policy['decision']} ({policy['reason']})")
                yield sse("policy_gate",{"tool":tool_name,"decision":policy["decision"],"reason":policy["reason"],"layer":"PrivateVault"})
                events_log.append({"seq":len(events_log)+1,"type":"policy_gate","agent":"PrivateVault","latency_ms":3,"tokens":0,"payload":f"Tool {tool_name}: {policy['decision']}"})
                await asyncio.sleep(0.3)
                if policy["decision"] == "ALLOW":
                    tr = self._execute_tool(tool_name,tool_input)
                    yield sse("tool_result",{"tool":tool_name,"output":tr,"layer":"LORK"})
                    events_log.append({"seq":len(events_log)+1,"type":"tool_result","agent":agent["name"],"latency_ms":45,"tokens":0,"payload":f"Tool {tool_name} executed"})
                else:
                    yield sse("tool_blocked",{"tool":tool_name,"reason":policy["reason"],"layer":"PrivateVault"})
                    events_log.append({"seq":len(events_log)+1,"type":"tool_blocked","agent":"PrivateVault","latency_ms":0,"tokens":0,"payload":f"BLOCKED: {tool_name}"})
                await asyncio.sleep(0.2)

            # STEP 6: Record in LORK
            await self._record_run(http,run_id,agent["name"],task,events_log,"completed")
            yield sse("event_recorded",{"run_id":run_id,"events_count":len(events_log),"status":"completed","layer":"LORK"})
            await asyncio.sleep(0.3)

            # STEP 7: Update Trust (BotBook)
            old_score = agent["trust_score"]
            new_score = round(min(1.0, old_score + 0.002), 4)
            agent["trust_score"] = new_score
            agent["tasks_completed"] = agent.get("tasks_completed",0)+1
            yield sse("trust_updated",{"agent":agent["name"],"old_score":old_score,"new_score":new_score,"tasks_completed":agent["tasks_completed"],"layer":"BotBook"})
            await asyncio.sleep(0.2)

            # STEP 8: Complete
            total_ms = round((time.time()-start_time)*1000)
            print(f"   ✅ COMPLETE: {total_ms}ms, {len(events_log)} events")
            print(f"{'='*60}\n")
            yield sse("complete",{"status":"SUCCESS","output":llm_result["text"][:400],"total_time_ms":total_ms,"total_tokens":llm_result.get("tokens",0),"run_id":run_id,"events_count":len(events_log)})

    async def _call_gemini(self, task, agent):
        if not GEMINI_AVAILABLE or not self.gemini_key:
            return {"text":"[Gemini unavailable - check google-genai and API key]","tokens":0,"tool_calls":[]}
        try:
            client = genai.Client(api_key=self.gemini_key)
            system_prompt = f"You are '{agent['name']}', an enterprise AI agent on BotBook.\nCapabilities: {', '.join(agent.get('capabilities',[]))}\nTrust: {agent['trust_score']}, Badge: {agent['badge']}\nYou are governed by PrivateVault.ai. Respond concisely (under 150 words). Use tools when helpful."
            func_decls = []
            for td in TOOL_DECLARATIONS:
                props = {}
                for pname, pinfo in td["parameters"]["properties"].items():
                    props[pname] = genai_types.Schema(type=pinfo["type"], description=pinfo.get("description",""))
                func_decls.append(genai_types.FunctionDeclaration(name=td["name"],description=td["description"],parameters=genai_types.Schema(type="OBJECT",properties=props,required=td["parameters"].get("required",[]))))
            tools = [genai_types.Tool(function_declarations=func_decls)]
            response = client.models.generate_content(model="gemini-2.5-flash",contents=task,config=genai_types.GenerateContentConfig(system_instruction=system_prompt,tools=tools,temperature=0.3))
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
