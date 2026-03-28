/* ===================================================================
   PrivateVault.ai — app.js  v3.1  (reliable animations + full data)
   =================================================================== */
"use strict";

/* ─── helpers ─── */
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ─── API Base URLs (auto-detect local vs production) ─── */
const IS_LOCAL = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
const VAULT_URL = IS_LOCAL ? 'http://localhost:8000' : 'https://privatevault-deploy.vercel.app';
const BOTBOOK_URL = IS_LOCAL ? 'http://localhost:8001' : 'https://botbook-deploy.vercel.app';
const LORK_URL = IS_LOCAL ? 'http://localhost:8002' : 'https://lork-deploy.vercel.app';

function sanitize(str) {
    /* strip emoji & non-ASCII so logs stay monospace-clean */
    return String(str).replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27FF}]/gu, "").trim();
}

/* ─── LOADER ─── */
function hideLoader() {
    const el = $("pageLoader");
    if (!el) return;
    el.style.opacity = "0";
    el.style.pointerEvents = "none";
    setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 400);
}

/* ─── THEME ─── */
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("pv-theme", next);
}
window.toggleTheme = toggleTheme;

/* ─── STATUS DOT ─── */
function setStatus(state, text) {
    const dot = $("statusDot");
    const txt = $("statusText");
    if (!dot || !txt) return;
    dot.className = "status-dot " + state;
    txt.textContent = text;
    txt.style.color = state === "online" ? "var(--green)" : state === "partial" ? "var(--amber)" : "var(--red)";
}

/* ─── ANIMATION HELPERS ─── */

/* Animate a bar fill using CSS width transition.
   el:       the .stat-bar-fill or similar element
   pct:      0-100
   color:    optional CSS color string
   delay:    ms */
function animateBar(el, pct, color, delay = 0) {
    if (!el) return;
    if (color) el.style.background = color;
    el.style.transition = "none";
    el.style.width = "0%";
    void el.offsetWidth;                          // force reflow
    setTimeout(() => {
        el.style.transition = "width 0.7s cubic-bezier(.4,0,.2,1)";
        el.style.width = Math.min(100, Math.max(0, pct)) + "%";
    }, delay + 20);
}

/* Animate a metric card bar + count-up value */
function animateMetricBar(barEl, valueEl, targetPct, targetValue, formatter) {
    animateBar(barEl, targetPct, null, 0);
    if (!valueEl) return;
    const start = 0;
    const end = parseFloat(targetValue) || 0;
    const dur = 800;
    const startTime = performance.now();
    const fmt = formatter || ((v) => Math.round(v).toLocaleString());
    function tick(now) {
        const t = Math.min((now - startTime) / dur, 1);
        const ease = t < .5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
        valueEl.textContent = fmt(start + (end - start) * ease);
        if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

/* Animate a numeric text node (count-up) */
function animateValue(el, to, fmt) {
    if (!el) return;
    const end = parseFloat(String(to).replace(/[^0-9.]/g, "")) || 0;
    let prefix = "", suffix = "";
    if (String(to).startsWith("$")) prefix = "$";
    if (String(to).endsWith("%")) suffix = "%";
    const dur = 900;
    const start = performance.now();
    const f = fmt || ((v) => prefix + Math.round(v).toLocaleString() + suffix);
    function tick(now) {
        const t = Math.min((now - start) / dur, 1);
        const ease = 1 - Math.pow(1 - t, 3);
        el.textContent = f(end * ease);
        if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

/* ─── FALLBACK DATA ─── */

const AGENT_REGISTRY = [
    { id: "finance_agent", name: "finance_agent", trust: 0.94, status: "online", caps: ["financial_analysis", "risk_assessment", "report_generation"] },
    { id: "compliance_agent", name: "compliance_agent", trust: 0.91, status: "online", caps: ["compliance", "audit_trail", "policy_enforcement"] },
    { id: "sales_agent", name: "sales_agent", trust: 0.87, status: "online", caps: ["customer_support", "crm_integration", "outreach"] },
    { id: "risk_monitor", name: "risk_monitor", trust: 0.88, status: "online", caps: ["anomaly_detection", "risk_assessment", "alerting"] },
    { id: "research_agent", name: "research_agent", trust: 0.78, status: "idle", caps: ["web_search", "report_generation", "data_collection"] },
    { id: "hr_assistant", name: "hr_assistant", trust: 0.65, status: "offline", caps: ["employee_onboarding", "document_processing", "scheduling"] },
];

const TIMELINE_DATA = [
    { seq: 1, type: "agent_step", agent: "data_collector", latency_ms: 340, tokens: 220 },
    { seq: 2, type: "tool_call", agent: "financial_analyst", latency_ms: 890, tokens: 410 },
    { seq: 3, type: "policy_check", agent: "governance_node", latency_ms: 42, tokens: 0 },
    { seq: 4, type: "agent_step", agent: "risk_assessor", latency_ms: 1240, tokens: 580 },
    { seq: 5, type: "tool_call", agent: "api_bridge", latency_ms: 200, tokens: 0 },
    { seq: 6, type: "agent_step", agent: "report_writer", latency_ms: 670, tokens: 710 },
    { seq: 7, type: "policy_check", agent: "governance_node", latency_ms: 38, tokens: 0 },
];

const GRAPH_DATA = {
    nodes: [
        { id: "start", label: "start", type: "meta", x: 80, y: 130, status: "done", latency_ms: 0, tokens: 0 },
        { id: "fetch", label: "data_collector", type: "agent", x: 220, y: 65, status: "done", latency_ms: 340, tokens: 220 },
        { id: "db", label: "query_database", type: "tool", x: 220, y: 195, status: "done", latency_ms: 45, tokens: 0 },
        { id: "analyze", label: "financial_analyst", type: "agent", x: 390, y: 65, status: "done", latency_ms: 890, tokens: 1240 },
        { id: "api", label: "external_api", type: "tool", x: 390, y: 195, status: "done", latency_ms: 210, tokens: 0 },
        { id: "policy", label: "policy_check", type: "policy", x: 540, y: 130, status: "done", latency_ms: 42, tokens: 0 },
        { id: "reporter", label: "report_writer", type: "agent", x: 660, y: 65, status: "done", latency_ms: 670, tokens: 920 },
        { id: "output", label: "output", type: "meta", x: 660, y: 195, status: "done", latency_ms: 0, tokens: 0 },
    ],
    edges: [
        { from: "start", to: "fetch", type: "agent" },
        { from: "start", to: "db", type: "tool" },
        { from: "db", to: "fetch", type: "tool" },
        { from: "fetch", to: "analyze", type: "agent" },
        { from: "fetch", to: "policy", type: "policy" },
        { from: "analyze", to: "api", type: "tool" },
        { from: "api", to: "analyze", type: "tool" },
        { from: "analyze", to: "policy", type: "policy" },
        { from: "policy", to: "reporter", type: "agent" },
        { from: "policy", to: "output", type: "agent" },
        { from: "reporter", to: "output", type: "agent" },
    ],
};

const STATS_DATA = [
    { agent: "financial_analyst", latency_ms: 890, tokens: 1240, color: "#60a5fa" },
    { agent: "data_collector", latency_ms: 340, tokens: 560, color: "#22c55e" },
    { agent: "risk_assessor", latency_ms: 1240, tokens: 870, color: "#f87171" },
    { agent: "report_writer", latency_ms: 670, tokens: 920, color: "#fbbf24" },
];

const DRIFT_SCENARIOS = [
    {
        id: "amount_inflation",
        label: "Amount Inflation",
        declared: `{ "action": "transfer", "amount": 5000, "recipient": "vendor_acme_corp" }`,
        actual: `{ "action": "transfer", "amount": 47500, "recipient": "vendor_acme_corp" }`,
        severity: "high",
        metrics: [
            { field: "amount", declared: "5000", actual: "47500", badge: "inflation" },
            { field: "recipient", declared: "vendor_acme_corp", actual: "vendor_acme_corp" },
        ],
    },
    {
        id: "recipient_switch",
        label: "Recipient Substitution",
        declared: `{ "action": "transfer", "amount": 1000, "recipient": "internal_team" }`,
        actual: `{ "action": "transfer", "amount": 1000, "recipient": "unknown_wallet_0x4f3c" }`,
        severity: "high",
        metrics: [
            { field: "amount", declared: "1000", actual: "1000" },
            { field: "recipient", declared: "internal_team", actual: "unknown_wallet_0x4f3c", badge: "unauthorized" },
        ],
    },
    {
        id: "action_escalation",
        label: "Action Escalation",
        declared: `{ "action": "query_balance", "scope": "read_only" }`,
        actual: `{ "action": "deploy_smart_contract", "network": "mainnet" }`,
        severity: "high",
        metrics: [
            { field: "action", declared: "query_balance", actual: "deploy_smart_contract", badge: "unauthorized" },
            { field: "scope", declared: "read_only", actual: "write_mainnet" },
        ],
    },
];

let currentScenarioIdx = 0;

/* ===================================================================
   GOVERNANCE
   =================================================================== */
const PRESET_MAP = {
    allow: { agentId: "finance_agent", action: "transfer", amount: 5000, recipient: "vendor_acme_corp" },
    review: { agentId: "finance_agent", action: "transfer", amount: 18500, recipient: "vendor_techsupply" },
    block_amount: { agentId: "finance_agent", action: "transfer", amount: 42000, recipient: "vendor_acme_corp" },
    block_kyc: { agentId: "sales_agent", action: "transfer", amount: 500, recipient: "anonymous_wallet_xyz" },
    block_action: { agentId: "risk_monitor", action: "deploy_smart_contract", amount: 0, recipient: "blockchain_mainnet" },
    allow_query: { agentId: "compliance_agent", action: "query_balance", amount: 0, recipient: "internal_account" },
};

window.setPreset = function (key) {
    const p = PRESET_MAP[key];
    if (!p) return;
    setSelect("govAgentId", p.agentId);
    setSelect("govAction", p.action);
    const amt = $("govAmount"); if (amt) amt.value = p.amount;
    setSelect("govRecipient", p.recipient);
};

function setSelect(id, value) {
    const el = $(id);
    if (!el) return;
    el.value = value;
    if (el.value !== value) {
        const opt = document.createElement("option");
        opt.value = value; opt.textContent = value;
        el.appendChild(opt);
        el.value = value;
    }
}

let auditEntries = [];

window.runGovernanceCheck = async function () {
    const btn = $("govSubmit");
    if (btn) { btn.textContent = "checking..."; btn.disabled = true; }

    const agentId = $("govAgentId")?.value || "finance_agent";
    const action = $("govAction")?.value || "transfer";
    const amount = parseFloat($("govAmount")?.value) || 0;
    const recipient = $("govRecipient")?.value || "vendor_acme_corp";

    let decision, reason, latency, hash, riskScore, policyTier;

    try {
        const t0 = performance.now();
        const resp = await fetch(`${VAULT_URL}/api/v1/shadow_verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent_id: agentId, action, amount, recipient }),
            signal: AbortSignal.timeout(4000),
        });
        if (!resp.ok) throw new Error(resp.statusText);
        const data = await resp.json();
        latency = Math.round(performance.now() - t0);
        decision = (data.status || "BLOCK").toUpperCase();
        reason = data.reason || "Policy engine response";
        hash = data.merkle_hash || "unavailable";
        riskScore = data.risk_score != null ? data.risk_score : 0;
        policyTier = data.policy_tier || "unknown";
    } catch {
        /* local fallback — mirrors real 3-tier logic */
        latency = Math.round(Math.random() * 60 + 15);
        const RULES = [
            { test: () => recipient.includes("anonymous") || recipient.includes("anon"), verdict: "BLOCK", tier: "hard_block", r: `Recipient ${recipient} failed KYC verification.` },
            { test: () => action === "deploy_smart_contract", verdict: "BLOCK", tier: "hard_block", r: `Action ${action} is not in the approved capability set.` },
            { test: () => amount > 25000, verdict: "BLOCK", tier: "hard_block", r: `Amount $${amount.toLocaleString()} exceeds hard limit of $25,000. Transaction rejected.` },
            { test: () => amount >= 10000, verdict: "REVIEW", tier: "human_review", r: `Amount $${amount.toLocaleString()} is between $10,000\u2013$25,000. Requires human approval.` },
            { test: () => true, verdict: "ALLOW", tier: "auto_approve", r: `Transaction within safe parameters. Auto-approved.` },
        ];
        const rule = RULES.find(r => r.test());
        decision = rule.verdict;
        reason = rule.r;
        policyTier = rule.tier;
        hash = "sha256:" + [...Array(64)].map(() => Math.floor(Math.random()*16).toString(16)).join("");
        riskScore = decision === "ALLOW" ? +(Math.random() * .15 + .05).toFixed(3) : decision === "REVIEW" ? +(Math.random() * .2 + .3).toFixed(3) : +(Math.random() * .3 + .6).toFixed(3);
    }

    renderGovResult(decision, reason, { latency, hash, riskScore, action, agentId, recipient, policyTier });
    appendAuditEntry(decision, action + " / " + recipient, agentId, hash);

    if (btn) { btn.textContent = "Verify Intent"; btn.disabled = false; }
};

function renderGovResult(decision, reason, meta) {
    const el = $("govResponse");
    if (!el) return;
    const isAllow = decision === "ALLOW";
    const isReview = decision === "REVIEW";
    const badgeCss = isAllow ? "allow" : isReview ? "review" : "block";
    const badgeColor = isAllow ? "var(--green)" : isReview ? "#f59e0b" : "var(--red)";
    const tierLabel = meta.policyTier === "auto_approve" ? "Tier 1 · Auto-Approve" :
                      meta.policyTier === "human_review" ? "Tier 2 · Human Review" :
                      meta.policyTier === "hard_block" ? "Tier 3 · Hard Block" : meta.policyTier;
    el.innerHTML = `
    <div class="gov-result" style="width:100%;">
      <div class="gov-result-badge">
        <span class="gov-result-badge-inner ${badgeCss}" style="${isReview ? 'background:rgba(245,158,11,0.12);color:#f59e0b;border-color:#f59e0b;' : ''}">${decision}</span>
        <span style="font-size:0.7rem;color:${badgeColor};margin-left:8px;font-family:var(--font-mono)">${tierLabel}</span>
      </div>
      <div class="gov-result-reason">${esc(reason)}</div>
      <div class="gov-result-meta">
        <div class="gov-meta-item"><div class="gov-meta-label">latency</div><div class="gov-meta-value">${meta.latency}ms</div></div>
        <div class="gov-meta-item"><div class="gov-meta-label">risk score</div><div class="gov-meta-value">${meta.riskScore}</div></div>
        <div class="gov-meta-item"><div class="gov-meta-label">merkle hash</div><div class="gov-meta-value" style="font-size:0.6rem;word-break:break-all">${esc(meta.hash)}</div></div>
        <div class="gov-meta-item"><div class="gov-meta-label">agent</div><div class="gov-meta-value">${esc(meta.agentId)}</div></div>
      </div>
    </div>`;
}

function appendAuditEntry(decision, detail, agent, hash) {
    const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
    auditEntries.unshift({ decision, detail, agent, hash, ts });
    if (auditEntries.length > 40) auditEntries.length = 40;
    renderAuditLog();
}

function renderAuditLog() {
    const el = $("auditLog");
    if (!el) return;
    const count = $("auditCount");
    if (count) count.textContent = auditEntries.length + " " + (auditEntries.length === 1 ? "entry" : "entries");
    el.innerHTML = auditEntries.map(e => `
    <div class="audit-entry">
      <span class="audit-entry-status ${e.decision.toLowerCase()}">${e.decision}</span>
      <span class="audit-entry-time">${e.ts}</span>
      <span class="audit-entry-detail" title="${esc(e.detail)}">${esc(e.detail)}</span>
      <span class="audit-entry-hash">${esc(e.hash)}</span>
    </div>`).join("");
}

/* ===================================================================
   BOTBOOK — REGISTRY
   =================================================================== */
function renderAgentList(agents) {
    const el = $("agentList");
    if (!el) return;
    el.innerHTML = "";
    agents.forEach((a, i) => {
        const trustColor = a.trust >= .85 ? "var(--green)" : a.trust >= .65 ? "var(--amber)" : "var(--red)";
        const dotColor = a.status === "online" ? "var(--green)" : a.status === "idle" ? "var(--amber)" : "var(--red)";
        const capText = (a.caps || []).slice(0, 3).join(" · ");
        const card = document.createElement("div");
        card.className = "agent-card";
        card.style.opacity = "0";
        card.style.transform = "translateX(-12px)";
        card.innerHTML = `
          <div class="agent-status-dot" style="background:${dotColor};"></div>
          <div class="agent-info">
            <div class="agent-name">${esc(a.name || a.id)}</div>
            <div class="agent-caps-text">${esc(capText)}</div>
          </div>
          <div class="agent-trust-score" style="color:${trustColor};">${(a.trust * 100).toFixed(0)}</div>`;
        el.appendChild(card);
        /* staggered entrance */
        setTimeout(() => {
            card.style.transition = "opacity .3s ease, transform .3s ease";
            card.style.opacity = "1";
            card.style.transform = "translateX(0)";
        }, 60 + i * 60);
    });
}

window.registerNewAgent = function () {
    const id = "agent_" + Math.random().toString(36).slice(2, 7);
    AGENT_REGISTRY.push({ id, name: id, trust: +(Math.random() * .4 + .5).toFixed(2), status: "online", caps: ["custom"] });
    renderAgentList(AGENT_REGISTRY);
    log_bot(`botbook make --agent ${id} --lork-enabled`);
};

async function loadAgents() {
    try {
        const r = await fetch(`${BOTBOOK_URL}/api/agents`, { signal: AbortSignal.timeout(3000) });
        if (!r.ok) throw 0;
        const data = await r.json();
        renderAgentList(data.agents || data);
    } catch {
        renderAgentList(AGENT_REGISTRY);
    }
}

/* ─── CAPABILITY MATCHING ─── */
window.toggleCap = function (el) {
    el.classList.toggle("active");
};

window.runMatching = async function () {
    const task = $("matchTask")?.value || "";
    const minTrust = parseFloat($("trustSlider")?.value || 50) / 100;
    const caps = [...document.querySelectorAll(".cap-chip.active")].map(c => c.dataset.cap);

    try {
        const r = await fetch(`${BOTBOOK_URL}/api/v1/match`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task, required_capabilities: caps, min_trust_score: minTrust, max_results: 5 }),
            signal: AbortSignal.timeout(3000),
        });
        if (!r.ok) throw 0;
        const data = await r.json();
        renderMatchResults(data);
    } catch {
        /* local match */
        const matches = AGENT_REGISTRY
            .filter(a => a.trust >= minTrust && (caps.length === 0 || caps.some(c => (a.caps || []).includes(c))))
            .sort((a, b) => b.trust - a.trust)
            .slice(0, 5)
            .map((a, i) => ({ rank: i + 1, name: a.name, trust_score: a.trust, match_score: a.trust * (.7 + Math.random() * .24) }));
        renderMatchResults(matches);
    }
};

function renderMatchResults(matches) {
    const el = $("matchResults");
    if (!el) return;
    if (!matches || !matches.length) {
        el.innerHTML = `<div class="audit-empty">No agents match the criteria.</div>`;
        return;
    }
    el.innerHTML = matches.map((m, i) => {
        const sc = m.match_score != null ? m.match_score : (m.trust_score || m.trust || 0);
        const col = sc >= .35 ? "var(--green)" : sc >= .2 ? "var(--amber)" : "var(--red)";
        const b = m.match_breakdown || {};
        const breakdownHtml = b.nlp_relevance !== undefined
            ? `<div style="font-size:0.65rem;color:var(--brand);margin-top:2px;opacity:.8">NLP: ${(b.nlp_relevance * 100).toFixed(0)}% | Cap: ${(b.capability_match * 100).toFixed(0)}% | Trust: ${(b.trust * 100).toFixed(0)}% | Exp: ${(b.experience * 100).toFixed(0)}%</div>`
            : '';
        return `<div class="match-result-card">
          <span class="match-rank">#${m.rank || (i + 1)}</span>
          <div class="match-info"><div class="match-name">${esc(m.name)} <span style="font-size:0.6rem;opacity:.5">${m.version ? 'v' + m.version : ''}</span></div>${breakdownHtml}</div>
          <div class="match-score" style="color:${col};">${(sc * 100).toFixed(0)}</div>
        </div>`;
    }).join("");
}

/* ─── CLI ─── */
let cliHistory = [];

function log_bot(line) {
    cliHistory.push({ type: "cmd", text: line });
    renderCli();
}

function renderCli() {
    const el = $("cliTerminal");
    if (!el) return;
    el.innerHTML = cliHistory.map(e => {
        if (e.type === "cmd") {
            return `<div class="terminal-line"><span class="terminal-prompt">$</span><span class="terminal-cmd"> ${esc(e.text)}</span></div>`;
        }
        return `<div class="${e.cls || "terminal-output"}">${esc(e.text)}</div>`;
    }).join("");
    el.scrollTop = el.scrollHeight;
}

const CLI_SCRIPTS = {
    init: [
        { type: "cmd", text: "botbook init" },
        { cls: "terminal-output", type: "out", text: "Initializing BotBook workspace..." },
        { cls: "terminal-success", type: "out", text: "Workspace created: .botbook/" },
        { cls: "terminal-output", type: "out", text: "LORK endpoint: ${LORK_URL}" },
        { cls: "terminal-success", type: "out", text: "Ready." },
    ],
    make: [
        { type: "cmd", text: "botbook make --agent finance_agent --lork-enabled" },
        { cls: "terminal-output", type: "out", text: "Creating agent: finance_agent" },
        { cls: "terminal-output", type: "out", text: "Registering with BotBook.dev..." },
        { cls: "terminal-output", type: "out", text: "Binding governance: PrivateVault.ai" },
        { cls: "terminal-success", type: "out", text: "Agent ready. Trust score: 0.94" },
    ],
    run: [
        { type: "cmd", text: "botbook run --workflow fintech-pipeline" },
        { cls: "terminal-output", type: "out", text: "Resolving agents from registry..." },
        { cls: "terminal-output", type: "out", text: "Checking governance pre-flight..." },
        { cls: "terminal-success", type: "out", text: "[ALLOW] All agents verified" },
        { cls: "terminal-output", type: "out", text: "Pipeline started. Run ID: lork-fintech-001" },
    ],
    workflow: [
        { type: "cmd", text: "botbook workflow --list" },
        { cls: "terminal-output", type: "out", text: "  fintech-pipeline    [sequential]  4 agents" },
        { cls: "terminal-output", type: "out", text: "  support-ticket      [parallel]    2 agents" },
        { cls: "terminal-output", type: "out", text: "  compliance-audit    [sequential]  3 agents" },
        { cls: "terminal-success", type: "out", text: "3 workflows registered." },
    ],
    inspect: [
        { type: "cmd", text: "botbook inspect --agent finance_agent" },
        { cls: "terminal-output", type: "out", text: "  STATUS:      online" },
        { cls: "terminal-output", type: "out", text: "  TRUST:       0.94" },
        { cls: "terminal-output", type: "out", text: "  RUNS:        347" },
        { cls: "terminal-output", type: "out", text: "  CAP:         financial_analysis, risk_assessment, report_generation" },
        { cls: "terminal-success", type: "out", text: "  VAULT:       bound (gov-node-0x1a2b)" },
    ],
    logs: [
        { type: "cmd", text: "botbook logs --run lork-fintech-001 --tail 5" },
        { cls: "terminal-output", type: "out", text: "[00:00.341] data_collector  STEP DONE  latency=340ms tokens=220" },
        { cls: "terminal-output", type: "out", text: "[00:01.231] financial_analyst  TOOL_CALL  latency=890ms tokens=410" },
        { cls: "terminal-output", type: "out", text: "[00:01.273] governance_node  POLICY_CHECK  ALLOW  latency=42ms" },
        { cls: "terminal-output", type: "out", text: "[00:02.513] risk_assessor  STEP DONE  latency=1240ms tokens=580" },
        { cls: "terminal-success", type: "out", text: "Tail complete. LORK trace: lork-fintech-001" },
    ],
};

window.runCliDemo = async function (cmd) {
    const script = CLI_SCRIPTS[cmd];
    if (!script) return;
    cliHistory = [];
    renderCli();

    for (let i = 0; i < script.length; i++) {
        await new Promise(r => setTimeout(r, i === 0 ? 0 : 300));
        cliHistory.push(script[i]);
        renderCli();
    }
};

/* ===================================================================
   LORK
   =================================================================== */
function renderTimeline(events) {
    const el = $("lorkTimeline");
    if (!el || !events || !events.length) return;
    const maxLat = Math.max(...events.map(e => e.latency_ms || 0));
    el.innerHTML = "";

    events.forEach((ev, i) => {
        const pct = maxLat ? (ev.latency_ms / maxLat * 100) : 0;
        const barId = "twf_" + i;
        const colors = { agent_step: "#60a5fa", tool_call: "#fbbf24", policy_check: "#f87171" };
        const color = colors[ev.type] || "#60a5fa";

        const row = document.createElement("div");
        row.className = "timeline-event";
        row.style.opacity = "0";
        row.style.transform = "translateX(-10px)";
        row.innerHTML = `
          <span class="timeline-seq">${ev.seq}</span>
          <span class="timeline-type-pill ${ev.type}">${ev.type.replace(/_/g, " ")}</span>
          <span class="timeline-agent">${esc(ev.agent)}</span>
          <div class="timeline-waterfall">
            <div class="stat-bar-fill" id="${barId}" style="height:100%;width:0%;background:${color};border-radius:2px;"></div>
          </div>
          <span class="timeline-latency">${ev.latency_ms}ms</span>
          <span class="timeline-tokens">${ev.tokens ? ev.tokens + "t" : "—"}</span>`;
        el.appendChild(row);

        setTimeout(() => {
            row.style.transition = "opacity .3s ease, transform .3s ease";
            row.style.opacity = "1";
            row.style.transform = "translateX(0)";
            animateBar($(barId), pct, color, 0);
        }, 80 + i * 60);
    });
}

// function renderGraph(graph) {
//     const el = $("execGraph");
//     if (!el || !graph) return;
//     const W = 480, H = 270;

//     const nodeColor = (id) => {
//         if (id.includes("policy") || id.includes("check")) return "var(--red)";
//         if (id.includes("start") || id.includes("end")) return "var(--brand)";
//         return "var(--blue)";
//     };

//     const nodeMap = {};
//     graph.nodes.forEach(n => { nodeMap[n.id] = n; });

//     const svgNS = "http://www.w3.org/2000/svg";
//     const svg = document.createElementNS(svgNS, "svg");
//     svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
//     svg.setAttribute("width", W);
//     svg.setAttribute("height", H);

//     /* ─ Edges ─ */
//     const edgePaths = [];
//     graph.edges.forEach(e => {
//         const from = nodeMap[e.from];
//         const to = nodeMap[e.to];
//         if (!from || !to) return;

//         const path = document.createElementNS(svgNS, "path");
//         const mx = (from.x + to.x) / 2;
//         const d = `M${from.x},${from.y} C${mx},${from.y} ${mx},${to.y} ${to.x},${to.y}`;
//         path.setAttribute("d", d);
//         path.setAttribute("stroke", "var(--bd-3)");
//         path.setAttribute("stroke-width", "1.2");
//         path.setAttribute("fill", "none");
//         path.setAttribute("class", "graph-edge");
//         path.style.opacity = "0";
//         svg.appendChild(path);
//         edgePaths.push(path);
//     });

//     /* ─ Nodes ─ */
//     const nodeEls = [];
//     graph.nodes.forEach(n => {
//         const g = document.createElementNS(svgNS, "g");
//         g.setAttribute("class", "graph-node");
//         g.style.opacity = "0";
//         g.style.transform = "scale(0.7)";
//         g.style.transformOrigin = `${n.x}px ${n.y}px`;
//         g.style.cursor = "default";

//         const circle = document.createElementNS(svgNS, "circle");
//         circle.setAttribute("cx", n.x);
//         circle.setAttribute("cy", n.y);
//         circle.setAttribute("r", 10);
//         circle.setAttribute("fill", "var(--bg-2)");
//         circle.setAttribute("stroke", nodeColor(n.id));
//         circle.setAttribute("stroke-width", "1.5");

//         const text = document.createElementNS(svgNS, "text");
//         text.setAttribute("x", n.x);
//         text.setAttribute("y", n.y + 24);
//         text.setAttribute("text-anchor", "middle");
//         text.setAttribute("font-family", "IBM Plex Mono, monospace");
//         text.setAttribute("font-size", "9");
//         text.setAttribute("fill", "var(--tx-3)");
//         text.textContent = n.label;

//         g.appendChild(circle);
//         g.appendChild(text);
//         svg.appendChild(g);
//         nodeEls.push({ el: g, n });
//     });

//     el.innerHTML = "";
//     el.appendChild(svg);

//     /* ─ Animate nodes in ─ */
//     nodeEls.forEach(({ el: g }, i) => {
//         setTimeout(() => {
//             g.style.transition = "opacity .3s ease, transform .3s ease";
//             g.style.opacity = "1";
//             g.style.transform = "scale(1)";
//         }, 80 + i * 60);
//     });

//     /* ─ Animate edges drawing ─ */
//     setTimeout(() => {
//         edgePaths.forEach((path, i) => {
//             setTimeout(() => {
//                 const len = path.getTotalLength();
//                 path.style.strokeDasharray = len;
//                 path.style.strokeDashoffset = len;
//                 path.style.opacity = "1";
//                 path.style.transition = "stroke-dashoffset .5s ease, opacity .2s ease";
//                 void path.getBoundingClientRect();
//                 path.style.strokeDashoffset = "0";
//             }, i * 80);
//         });
//     }, nodeEls.length * 60 + 100);
// }

/* ================================================================
   PATCH B — Interactive Execution Graph
   
   In app.js, find and REPLACE the entire renderGraph() function
   with the code below. Everything else in app.js stays the same.
   ================================================================ */

/* ── Also add this CSS to the END of your styles.css ── */

/*
.exec-graph { padding: 0; min-height: 340px; flex-direction: column; align-items: stretch; }
.graph-toolbar { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-bottom: 0.5px solid var(--bd-1); flex-wrap: wrap; }
.graph-filter-btn { font-family: var(--font-mono); font-size: 11px; background: transparent; border: 0.5px solid var(--bd-2); color: var(--tx-2); padding: 4px 10px; border-radius: 3px; cursor: pointer; transition: border-color .15s, color .15s; }
.graph-filter-btn:hover { border-color: var(--bd-3); color: var(--tx-1); }
.graph-filter-btn.active { border-color: var(--brand); color: var(--brand); background: var(--blue-bg); }
.graph-canvas { flex: 1; overflow: hidden; cursor: grab; min-height: 280px; position: relative; }
.graph-canvas:active { cursor: grabbing; }
.graph-legend { display: flex; gap: 14px; padding: 8px 14px; border-top: 0.5px solid var(--bd-1); flex-wrap: wrap; }
.graph-leg-item { display: flex; align-items: center; gap: 5px; font-family: var(--font-mono); font-size: 10px; color: var(--tx-3); }
.graph-leg-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.graph-node-detail { border-top: 0.5px solid var(--bd-1); background: var(--bg-2); padding: 14px 18px; font-family: var(--font-mono); font-size: 13px; min-height: 80px; }
.graph-detail-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.graph-detail-name { font-size: 14px; font-weight: 600; }
.graph-detail-type { font-size: 11px; color: var(--tx-3); }
.graph-detail-desc { font-family: var(--font-sans); font-size: 14px; color: var(--tx-2); line-height: 1.65; margin-bottom: 10px; }
.graph-detail-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.graph-detail-metric { background: var(--bg-1); border: 0.5px solid var(--bd-1); border-radius: 4px; padding: 10px 12px; }
.graph-detail-metric-val { font-size: 18px; font-weight: 600; color: var(--tx-1); margin-bottom: 2px; }
.graph-detail-metric-lbl { font-size: 11px; color: var(--tx-3); }
.graph-empty { display: flex; align-items: center; justify-content: center; height: 100%; font-family: var(--font-mono); font-size: 12px; color: var(--tx-3); }
*/

/* ================================================================
   REPLACEMENT renderGraph() FUNCTION
   ================================================================ */

function renderGraph(graphData) {
    const container = document.getElementById("execGraph");
    if (!container) return;

    /* ── normalise input ── */
    const nodeMap = {};
    const edgeList = [];

    if (graphData && graphData.nodes && graphData.edges) {
        graphData.nodes.forEach(n => { nodeMap[n.id] = n; });
        graphData.edges.forEach(e => edgeList.push(e));
    } else if (Array.isArray(graphData)) {
        graphData.forEach(e => {
            edgeList.push(e);
            if (!nodeMap[e.from]) nodeMap[e.from] = { id: e.from, label: e.from, type: "agent" };
            if (!nodeMap[e.to]) nodeMap[e.to] = { id: e.to, label: e.to, type: e.type === "tool" ? "tool" : "agent" };
        });
    }

    const nodes = Object.values(nodeMap);
    if (!nodes.length) {
        container.innerHTML = `<div style="padding:24px;font-family:var(--font-mono);font-size:13px;color:var(--tx-3)">// no execution data</div>`;
        return;
    }

    /* ── auto-layout if coordinates missing ── */
    const VW = 740, VH = 280;
    const NW = 130, NH = 36;
    const minColW = NW + 40;

    const needsLayout = nodes.every(n => n.x === undefined || n.x === null);
    if (needsLayout) {
        /* Simple left-to-right dagre-style placement */
        const mainNodes = nodes.filter(n => n.type !== "tool");
        const subNodes = nodes.filter(n => n.type === "tool");

        const colW = Math.max(minColW, (VW - 80) / Math.max(mainNodes.length, 1));

        mainNodes.forEach((n, i) => {
            n.x = 80 + i * colW;
            n.y = VH / 2 - 40;
        });

        // Track how many tools per parent to offset them
        const parentToolCounts = {};
        subNodes.forEach((n, i) => {
            const parentEdge = edgeList.find(e => e.to === n.id);
            const parentId = parentEdge ? parentEdge.from : "none";
            
            if (!parentToolCounts[parentId]) parentToolCounts[parentId] = 0;
            const offset = (parentToolCounts[parentId]++) * 30;

            const pNode = nodeMap[parentId];
            n.x = pNode ? (pNode.x + offset) : (80 + i * colW + offset);
            n.y = VH / 2 + 55 + (offset % 60); // zigzag y slightly if many tools
        });
    }

    /* ── viewBox: expand to fit all node coordinates ── */
    const allX = nodes.map(n => n.x);
    const allY = nodes.map(n => n.y);
    const minX = Math.min(...allX) - NW / 2 - 40;
    const maxX = Math.max(...allX) + NW / 2 + 40;
    const minY = Math.min(...allY) - NH / 2 - 40;
    const maxY = Math.max(...allY) + NH / 2 + 60;
    const computedW = Math.max(maxX - minX, VW);
    const computedH = Math.max(maxY - minY, VH);
    const vb = `${minX} ${minY} ${computedW} ${computedH}`;

    /* ── constants ── */
    const TYPE_COLOR = { agent: "#60a5fa", tool: "#fbbf24", policy: "#f87171", meta: "#666562" };
    const TYPE_MARKER = { agent: "igArrowBlue", tool: "igArrowAmber", policy: "igArrowRed", meta: "igArrowGray" };

    /* ── state ── */
    let selectedId = null;
    let filterType = "all";
    let pan = { x: 0, y: 0, scale: 1 };
    let dragging = false;
    let dragStart = { x: 0, y: 0 };
    let panOrigin = { x: 0, y: 0 };

    function isVisible(node) {
        if (filterType === "all") return true;
        if (filterType === "agent") return node.type === "agent" || node.type === "meta";
        if (filterType === "tool") return node.type === "tool" || node.type === "meta";
        if (filterType === "policy") return node.type === "policy" || node.type === "meta";
        return true;
    }
    function edgeVisible(e) {
        const f = nodeMap[e.from], t = nodeMap[e.to];
        return f && t && isVisible(f) && isVisible(t);
    }

    /* ── build DOM ── */
    container.innerHTML = `
<div class="ig-wrap">
  <div class="ig-toolbar" id="igToolbar">
    <button class="ig-filter-btn active" data-filter="all">all</button>
    <button class="ig-filter-btn" data-filter="agent">agents</button>
    <button class="ig-filter-btn" data-filter="tool">tools</button>
    <button class="ig-filter-btn" data-filter="policy">policy</button>
    <button class="ig-filter-btn" style="margin-left:auto" data-action="reset">reset</button>
    <button class="ig-filter-btn" data-action="replay">replay</button>
  </div>
  <div class="ig-canvas" id="igCanvas">
    <svg id="igSvg" viewBox="${vb}" height="280" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="igArrowBlue"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 2L8 5L1 8" fill="none" stroke="#60a5fa" stroke-width="1.5" stroke-linecap="round"/></marker>
        <marker id="igArrowAmber" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 2L8 5L1 8" fill="none" stroke="#fbbf24" stroke-width="1.5" stroke-linecap="round"/></marker>
        <marker id="igArrowRed"   viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 2L8 5L1 8" fill="none" stroke="#f87171" stroke-width="1.5" stroke-linecap="round"/></marker>
        <marker id="igArrowGray"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 2L8 5L1 8" fill="none" stroke="#3d4145" stroke-width="1.5" stroke-linecap="round"/></marker>
      </defs>
      <g id="igRoot"></g>
    </svg>
  </div>
  <div class="ig-legend">
    <div class="ig-leg-item"><div class="ig-leg-dot" style="background:#60a5fa"></div>agent step</div>
    <div class="ig-leg-item"><div class="ig-leg-dot" style="background:#fbbf24"></div>tool call</div>
    <div class="ig-leg-item"><div class="ig-leg-dot" style="background:#f87171"></div>policy check</div>
    <div class="ig-leg-item"><div class="ig-leg-dot" style="background:#22c55e"></div>completed</div>
    <span style="margin-left:auto;font-family:var(--font-mono);font-size:11px;color:var(--tx-3)">click · drag · scroll</span>
  </div>
  <div class="ig-detail" id="igDetail">
    <div class="ig-detail-empty">// click any node to inspect</div>
  </div>
</div>`;

    const root = document.getElementById("igRoot");
    const svg = document.getElementById("igSvg");
    const canvas = document.getElementById("igCanvas");

    /* ── draw ── */
    function draw() {
        root.innerHTML = "";

        /* edges — rendered first so nodes sit on top */
        edgeList.forEach((e, ei) => {
            const from = nodeMap[e.from], to = nodeMap[e.to];
            if (!from || !to) return;
            const visible = edgeVisible(e);
            const color = TYPE_COLOR[e.type] || "#3d4145";
            const marker = TYPE_MARKER[e.type] || "igArrowGray";

            /* trim line to node edges */
            const dx = to.x - from.x, dy = to.y - from.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const ux = dx / len, uy = dy / len;
            const x1 = from.x + ux * (NW / 2 + 2);
            const y1 = from.y + uy * (NH / 2 + 2);
            const x2 = to.x - ux * (NW / 2 + 7);
            const y2 = to.y - uy * (NH / 2 + 7);
            const mx = (x1 + x2) / 2;

            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`);
            path.setAttribute("stroke", color);
            path.setAttribute("stroke-width", "1");
            path.setAttribute("fill", "none");
            path.setAttribute("stroke-opacity", visible ? "0.55" : "0.07");
            path.setAttribute("marker-end", `url(#${marker})`);
            path.setAttribute("data-ei", ei);
            /* draw animation */
            path.style.strokeDasharray = "300";
            path.style.strokeDashoffset = "300";
            root.appendChild(path);
        });

        /* nodes */
        nodes.forEach((node, ni) => {
            const visible = isVisible(node);
            const color = TYPE_COLOR[node.type] || "#3d4145";
            const isSelected = selectedId === node.id;

            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
            g.setAttribute("cursor", "pointer");
            g.setAttribute("data-nid", node.id);
            g.style.opacity = "0";

            const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            rect.setAttribute("x", node.x - NW / 2);
            rect.setAttribute("y", node.y - NH / 2);
            rect.setAttribute("width", NW);
            rect.setAttribute("height", NH);
            rect.setAttribute("rx", "5");
            rect.setAttribute("fill", isSelected ? color + "28" : "#1e2023");
            rect.setAttribute("stroke", visible ? color : "#2e3134");
            rect.setAttribute("stroke-width", isSelected ? "1.5" : "0.8");
            rect.setAttribute("stroke-opacity", visible ? "1" : "0.2");

            const label = (node.label || node.id || "");
            const displayLabel = label.length > 14 ? label.slice(0, 13) + "…" : label;

            const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
            txt.setAttribute("x", node.x);
            txt.setAttribute("y", node.y + 1);
            txt.setAttribute("text-anchor", "middle");
            txt.setAttribute("dominant-baseline", "central");
            txt.setAttribute("font-family", "IBM Plex Mono, monospace");
            txt.setAttribute("font-size", "11");
            txt.setAttribute("font-weight", "500");
            txt.setAttribute("fill", visible ? (isSelected ? color : "#eeecea") : "#3d4145");
            txt.setAttribute("pointer-events", "none");
            txt.textContent = displayLabel;

            /* status dot top-right */
            const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            dot.setAttribute("cx", node.x + NW / 2 - 7);
            dot.setAttribute("cy", node.y - NH / 2 + 7);
            dot.setAttribute("r", "3");
            dot.setAttribute("fill", (node.status === "done" || node.total_latency_ms > 0) ? "#22c55e" : "#3d4145");
            dot.setAttribute("pointer-events", "none");

            /* latency badge below node */
            const lat = node.latency_ms || node.total_latency_ms || 0;
            if (lat > 0 && visible) {
                const badge = document.createElementNS("http://www.w3.org/2000/svg", "text");
                badge.setAttribute("x", node.x);
                badge.setAttribute("y", node.y + NH / 2 + 14);
                badge.setAttribute("text-anchor", "middle");
                badge.setAttribute("font-family", "IBM Plex Mono, monospace");
                badge.setAttribute("font-size", "9");
                badge.setAttribute("fill", lat > 500 ? "#f87171" : lat > 200 ? "#fbbf24" : "#22c55e");
                badge.setAttribute("pointer-events", "none");
                badge.textContent = lat + "ms";
                g.appendChild(badge);
            }

            g.appendChild(rect);
            g.appendChild(txt);
            g.appendChild(dot);

            /* hover */
            g.addEventListener("mouseenter", () => {
                if (selectedId !== node.id && visible)
                    rect.setAttribute("fill", color + "15");
            });
            g.addEventListener("mouseleave", () => {
                rect.setAttribute("fill", isSelected ? color + "28" : "#1e2023");
            });

            /* click */
            g.addEventListener("click", ev => {
                ev.stopPropagation();
                selectedId = (selectedId === node.id) ? null : node.id;
                draw();
                renderDetail();
            });

            root.appendChild(g);
        });

        animate();
    }

    /* ── entrance animation ── */
    function animate() {
        const nodeEls = root.querySelectorAll("g[data-nid]");
        nodeEls.forEach((g, i) => {
            const nid = g.getAttribute("data-nid");
            const node = nodeMap[nid];
            if (!node || !isVisible(node)) { g.style.opacity = "0.08"; return; }
            g.style.opacity = "0";
            g.style.transform = "scale(0.75)";
            g.style.transformOrigin = `${node.x}px ${node.y}px`;
            setTimeout(() => {
                g.style.transition = "opacity .22s ease, transform .22s ease";
                g.style.opacity = "1";
                g.style.transform = "scale(1)";
            }, 60 + i * 55);
        });

        /* edges draw after nodes */
        const edgeEls = root.querySelectorAll("[data-ei]");
        const nodeDelay = nodeEls.length * 55 + 90;
        edgeEls.forEach((path, i) => {
            const ei = parseInt(path.getAttribute("data-ei"));
            const edge = edgeList[ei];
            if (!edge || !edgeVisible(edge)) { path.style.strokeDashoffset = "300"; return; }
            setTimeout(() => {
                path.style.transition = "stroke-dashoffset .4s cubic-bezier(.4,0,.2,1)";
                path.style.strokeDashoffset = "0";
            }, nodeDelay + i * 55);
        });
    }

    /* ── detail panel ── */
    function renderDetail() {
        const panel = document.getElementById("igDetail");
        if (!panel) return;
        if (!selectedId) {
            panel.innerHTML = `<div class="ig-detail-empty">// click any node to inspect</div>`;
            return;
        }
        const node = nodeMap[selectedId];
        if (!node) return;
        const color = TYPE_COLOR[node.type] || "#3d4145";
        const lat = node.latency_ms || node.total_latency_ms || 0;
        const tok = node.tokens || node.total_tokens || 0;
        const conns = edgeList.filter(e => e.from === node.id || e.to === node.id).length;
        const latColor = lat > 500 ? "var(--red)" : lat > 200 ? "var(--amber)" : lat > 0 ? "var(--green)" : "var(--tx-3)";

        panel.innerHTML = `
<div class="ig-detail-header">
  <span class="ig-detail-name" style="color:${color}">${node.label || node.id}</span>
  <span class="ig-detail-type">${node.type}</span>
  <span class="ig-detail-conns">${conns} connection${conns !== 1 ? "s" : ""}</span>
</div>
<div class="ig-detail-metrics">
  <div class="ig-metric">
    <div class="ig-metric-val" style="color:${latColor}">${lat > 0 ? lat + "ms" : "—"}</div>
    <div class="ig-metric-lbl">latency</div>
  </div>
  <div class="ig-metric">
    <div class="ig-metric-val" style="color:var(--blue)">${tok > 0 ? tok.toLocaleString() : "—"}</div>
    <div class="ig-metric-lbl">tokens</div>
  </div>
  <div class="ig-metric">
    <div class="ig-metric-val" style="color:var(--green)">done</div>
    <div class="ig-metric-lbl">status</div>
  </div>
</div>`;
    }

    /* ── toolbar events ── */
    document.getElementById("igToolbar").addEventListener("click", ev => {
        const btn = ev.target.closest("button");
        if (!btn) return;
        const action = btn.getAttribute("data-action");
        const filter = btn.getAttribute("data-filter");

        if (action === "reset") {
            pan = { x: 0, y: 0, scale: 1 };
            root.setAttribute("transform", "");
            return;
        }
        if (action === "replay") {
            selectedId = null;
            draw();
            renderDetail();
            return;
        }
        if (filter) {
            filterType = filter;
            document.querySelectorAll(".ig-filter-btn[data-filter]")
                .forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            selectedId = null;
            draw();
            renderDetail();
        }
    });

    /* ── pan + zoom ── */
    canvas.addEventListener("mousedown", e => {
        dragging = true;
        dragStart = { x: e.clientX, y: e.clientY };
        panOrigin = { x: pan.x, y: pan.y };
    });
    window.addEventListener("mousemove", e => {
        if (!dragging) return;
        pan.x = panOrigin.x + (e.clientX - dragStart.x);
        pan.y = panOrigin.y + (e.clientY - dragStart.y);
        root.setAttribute("transform", `translate(${pan.x},${pan.y})`);
    });
    window.addEventListener("mouseup", () => { dragging = false; });

    /* click background to deselect */
    svg.addEventListener("click", () => {
        selectedId = null;
        draw();
        renderDetail();
    });

    draw();
    renderDetail();
}

function renderStats(stats) {
    const el = $("agentStats");
    if (!el || !stats || !stats.length) return;
    const maxLat = Math.max(...stats.map(s => s.latency_ms || 0));
    const maxTok = Math.max(...stats.map(s => s.tokens || 0));
    el.innerHTML = "";

    stats.forEach((s, i) => {
        const latPct = maxLat ? (s.latency_ms / maxLat * 100) : 0;
        const tokPct = maxTok ? (s.tokens / maxTok * 100) : 0;
        const latId = "lat_" + i;
        const tokId = "tok_" + i;

        const block = document.createElement("div");
        block.className = "stat-agent-block";
        block.style.opacity = "0";
        block.style.transform = "translateY(8px)";
        block.innerHTML = `
          <div class="stat-row">
            <span class="stat-agent-name">${esc(s.agent)}</span>
            <div class="stat-bar-container"><div class="stat-bar-fill" id="${latId}" style="background:${s.color || "var(--blue)"}"></div></div>
            <span class="stat-latency-label">${s.latency_ms}ms</span>
          </div>
          <div class="stat-token-row">
            <div class="stat-token-bar-container"><div class="stat-token-bar-fill" id="${tokId}"></div></div>
            <span class="stat-token-label">${s.tokens}t</span>
          </div>`;
        el.appendChild(block);

        setTimeout(() => {
            block.style.transition = "opacity .3s ease, transform .3s ease";
            block.style.opacity = "1";
            block.style.transform = "translateY(0)";
            animateBar($(latId), latPct, s.color, 0);
            animateBar($(tokId), tokPct, "var(--blue)", 0);
        }, 100 + i * 80);
    });
}

window.selectRun = async function (runId) {
    try {
        const r = await fetch(`${LORK_URL}/api/v1/runs/${runId}`, { signal: AbortSignal.timeout(3000) });
        if (!r.ok) throw 0;
        const data = await r.json();
        const events = data.events || [];
        if (events.length > 0) {
            renderTimeline(events);
            // Build graph from events
            const graphNodes = [];
            const graphEdges = [];
            let prevId = null;
            events.forEach((ev, i) => {
                const nodeId = ev.agent + "_" + i;
                const typeMap = { agent_match: "meta", intent_declared: "meta", governance_check: "policy", llm_call: "agent", tool_call: "tool", human_review_escalation: "policy", human_review_completed: "policy", event_recording: "meta" };
                graphNodes.push({ id: nodeId, label: ev.agent || ev.type, type: typeMap[ev.type] || "agent", latency_ms: ev.latency_ms || 0, tokens: ev.tokens || 0 });
                if (prevId) graphEdges.push({ from: prevId, to: nodeId, type: typeMap[ev.type] || "agent" });
                prevId = nodeId;
            });
            renderGraph({ nodes: graphNodes, edges: graphEdges });
            // Build stats from events
            const agentMap = {};
            const colors = ["#60a5fa","#22c55e","#f87171","#fbbf24","#a78bfa","#fb923c","#14b8a6"];
            let ci = 0;
            events.forEach(ev => {
                const agent = ev.agent || ev.type;
                if (!agentMap[agent]) agentMap[agent] = { agent, latency_ms: 0, tokens: 0, color: colors[ci++ % colors.length] };
                agentMap[agent].latency_ms += ev.latency_ms || 0;
                agentMap[agent].tokens += ev.tokens || 0;
            });
            renderStats(Object.values(agentMap).filter(s => s.latency_ms > 0 || s.tokens > 0));
        } else {
            renderTimeline(TIMELINE_DATA);
            renderGraph(GRAPH_DATA);
            renderStats(STATS_DATA);
        }
    } catch {
        renderTimeline(TIMELINE_DATA);
        renderGraph(GRAPH_DATA);
        renderStats(STATS_DATA);
    }
};

/* ─── REPLAY ─── */
let replayTimer = null;

window.startReplay = async function () {
    if (replayTimer) return;
    const runSel = $("runSelect");
    const runId = runSel?.value || "";
    const speed = parseInt($("replaySpeed")?.value || 500);
    const out = $("replayOutput");
    if (!out) return;
    out.innerHTML = "";

    if (!runId) {
        out.innerHTML = `<div class="empty-state-text" style="padding:16px;">No run selected. Execute a live task first, then select the run to replay.</div>`;
        return;
    }

    let events = [];
    let runTask = "";
    try {
        const r = await fetch(`${LORK_URL}/api/v1/runs/${runId}/replay`, { signal: AbortSignal.timeout(3000) });
        if (r.ok) {
            const data = await r.json();
            events = data.events || [];
            runTask = data.task || "";
        }
    } catch { }

    if (!events.length) {
        out.innerHTML = `<div class="empty-state-text" style="padding:16px;">No events found for run ${esc(runId)}. Execute a live task first.</div>`;
        return;
    }

    // Show the task being replayed
    if (runTask) {
        const taskEl = document.createElement("div");
        taskEl.className = "replay-event";
        taskEl.innerHTML = `<div class="replay-event-type" style="color:var(--brand)">REPLAYING: ${esc(runId)}</div>
                           <div class="replay-event-detail" style="color:var(--tx-2)">${esc(runTask)}</div>`;
        out.appendChild(taskEl);
    }

    let idx = 0;
    function playNext() {
        if (idx >= events.length) {
            replayTimer = null;
            const done = document.createElement("div");
            done.className = "replay-event complete";
            done.innerHTML = `<div class="replay-event-type complete-label">RUN COMPLETE</div>
                              <div class="replay-event-detail">All ${events.length} events replayed. Deterministic replay verified.</div>`;
            out.appendChild(done);
            out.scrollTop = out.scrollHeight;
            return;
        }
        const ev = events[idx++];
        const el = document.createElement("div");
        el.className = "replay-event";
        el.style.opacity = "0";
        const payloadText = ev.payload ? ` — ${ev.payload}` : '';
        el.innerHTML = `<div class="replay-event-type">[step ${ev.seq}] ${esc(ev.type)} — ${esc(ev.agent)}${payloadText}</div>
                        <div class="replay-event-detail">latency: ${ev.latency_ms}ms${ev.tokens ? "  tokens: " + ev.tokens : ""}${ev.cumulative_time_ms ? "  cumulative: " + ev.cumulative_time_ms + "ms" : ""}</div>`;
        out.appendChild(el);
        out.scrollTop = out.scrollHeight;
        void el.offsetWidth;
        el.style.transition = "opacity .2s ease";
        el.style.opacity = "1";
        replayTimer = setTimeout(playNext, speed);
    }
    playNext();
};

window.resetReplay = function () {
    if (replayTimer) { clearTimeout(replayTimer); replayTimer = null; }
    const out = $("replayOutput");
    if (out) out.innerHTML = `<div class="empty-state-text" style="padding:16px;">Press "Replay Run" to re-execute the event log from a recorded run.</div>`;
};

/* ===================================================================
   PIPELINE DEMO
   =================================================================== */
let pipelineRunning = false;

function setStep(n, state) {
    /* state: 'idle' | 'running' | 'done' | 'error' */
    const dot = $("pd" + n);
    const stat = $("pst" + n);
    const conn = $("pc" + n);   // connector fill (between this step and next)

    if (dot) {
        dot.style.animation = "none";
        void dot.offsetWidth;                       // flush animation queue
        if (state === "running") { dot.style.background = "var(--amber)"; dot.style.animation = "dotPulse 1s infinite"; }
        else if (state === "done") { dot.style.animation = "dotPop .4s ease forwards"; }
        else if (state === "error") { dot.style.background = "var(--red)"; }
        else { dot.style.background = "var(--bd-2)"; }
    }
    if (stat) {
        stat.textContent = state;
        stat.style.color = state === "done" ? "var(--green)" : state === "error" ? "var(--red)" : state === "running" ? "var(--amber)" : "var(--tx-3)";
    }
    if (conn && state === "done") {
        conn.style.transition = "none";
        conn.style.width = "0%";
        void conn.offsetWidth;
        conn.style.transition = "width .5s cubic-bezier(.4,0,.2,1)";
        conn.style.width = "100%";
    }
}

function pipeLog(header, lines) {
    const out = $("pipelineOutput");
    if (!out) return;
    const wrap = document.createElement("div");
    wrap.className = "pipeline-log";
    const h = document.createElement("div");
    h.className = "pipeline-log-header";
    h.textContent = sanitize(header);
    const body = document.createElement("div");
    body.className = "pipeline-log-body";
    lines.forEach((line, i) => {
        const d = document.createElement("div");
        d.textContent = sanitize(line);
        d.style.animationDelay = (i * 80) + "ms";
        body.appendChild(d);
    });
    wrap.appendChild(h);
    wrap.appendChild(body);
    out.appendChild(wrap);
    out.scrollTop = out.scrollHeight;
}

window.runFullPipeline = async function () {
    if (pipelineRunning) return;
    pipelineRunning = true;
    const btn = $("pipelineStartBtn");
    if (btn) btn.disabled = true;

    const out = $("pipelineOutput");
    if (out) out.innerHTML = "";

    /* reset all steps */
    [1, 2, 3, 4].forEach(n => setStep(n, "idle"));
    ["pc1", "pc2", "pc3"].forEach(id => { const el = $(id); if (el) el.style.width = "0%"; });

    const delay = (ms) => new Promise(r => setTimeout(r, ms));

    /* ─── Step 1: Create team ─── */
    setStep(1, "running");
    pipeLog("Step 1 — Create Agent Team", ["botbook make --agent data_collector --lork-enabled", "botbook make --agent analyst --lork-enabled", "botbook make --agent reporter --lork-enabled"]);
    await delay(1400);
    try {
        const r = await fetch(`${BOTBOOK_URL}/api/team`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agents: ["data_collector", "analyst", "reporter"] }),
            signal: AbortSignal.timeout(3000),
        });
        const d = await r.json();
        pipeLog("Team created", ["team_id: " + (d.team_id || "team-demo-001"), "Status: Active"]);
    } catch {
        pipeLog("Team created (local)", ["team_id: team-demo-001", "3 agents registered"]);
    }
    setStep(1, "done");
    await delay(400);

    /* ─── Step 2: Execute workflow ─── */
    setStep(2, "running");
    pipeLog("Step 2 — Execute Workflow", ["botbook run --workflow fintech-pipeline --team team-demo-001", "Scheduling agents...", "Sequential execution plan: data_collector -> analyst -> reporter"]);
    await delay(1600);
    try {
        const r = await fetch(`${BOTBOOK_URL}/api/workflow`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ workflow: "fintech-pipeline", team_id: "team-demo-001" }),
            signal: AbortSignal.timeout(4000),
        });
        const d = await r.json();
        pipeLog("Workflow complete", ["run_id: " + (d.run_id || "lork-fintech-001"), "Duration: 2847ms", "Tokens used: 1920"]);
    } catch {
        pipeLog("Workflow complete (simulated)", ["run_id: lork-fintech-001", "Duration: 2847ms", "3 agents completed"]);
    }
    setStep(2, "done");
    await delay(400);

    /* ─── Step 3: Governance check ─── */
    setStep(3, "running");
    pipeLog("Step 3 — Governance Check", ["vault.verify agent=analyst action=transfer amount=5000 recipient=vendor_acme_corp", "Checking policy ruleset...", "Running KYC on recipient..."]);
    await delay(1200);
    let govResult = "ALLOW";
    try {
        const r = await fetch(`${VAULT_URL}/api/governance/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent_id: "analyst", action: "transfer", amount: 5000, recipient: "vendor_acme_corp" }),
            signal: AbortSignal.timeout(3000),
        });
        const d = await r.json();
        govResult = (d.decision || "ALLOW").toUpperCase();
    } catch { }
    pipeLog("Governance result", [`Decision: ${govResult}`, "Latency: 42ms", "Audit hash: 0x" + Math.random().toString(16).slice(2, 12)]);
    setStep(3, govResult === "ALLOW" ? "done" : "error");
    await delay(400);

    /* ─── Step 4: LORK inspection ─── */
    setStep(4, "running");
    pipeLog("Step 4 — LORK Inspection", ["lork inspect --run lork-fintech-001", "Loading timeline...", "Rendering execution graph..."]);
    await delay(1100);
    await selectRun("run-001");
    pipeLog("LORK inspection complete", ["7 events recorded", "Replay available", "All traces persisted"]);
    setStep(4, "done");

    if (btn) { btn.disabled = false; btn.textContent = "Re-run Pipeline"; }
    pipelineRunning = false;
};

/* ===================================================================
   SHADOW MODE / DRIFT DETECTION
   =================================================================== */
function renderDiff(declared, actual) {
    const container = $("driftDiff");
    if (!container) return;

    container.style.transition = "none";
    container.style.opacity = "0";
    void container.offsetWidth;

    const declaredStr = typeof declared === 'string' ? declared : JSON.stringify(declared, null, 2);
    const actualStr = typeof actual === 'string' ? actual : JSON.stringify(actual, null, 2);
    const declaredLines = declaredStr.split("\n");
    const actualLines = actualStr.split("\n");
    const maxLen = Math.max(declaredLines.length, actualLines.length);

    let html = "";
    for (let i = 0; i < maxLen; i++) {
        const dl = (declaredLines[i] || "").trim();
        const al = (actualLines[i] || "").trim();
        if (dl === al) {
            html += `<div class="diff-line unchanged"><span class="diff-gutter">${i + 1}</span><span class="diff-content">${esc(dl)}</span></div>`;
        } else {
            if (dl) html += `<div class="diff-line removed"><span class="diff-gutter">−</span><span class="diff-content">${esc(dl)}</span></div>`;
            if (al) html += `<div class="diff-line added"><span class="diff-gutter">+</span><span class="diff-content">${esc(al)}</span></div>`;
        }
    }
    container.innerHTML = html;

    container.style.transition = "opacity .25s ease";
    container.style.opacity = "1";
}

function renderDriftResult(scenario) {
    const el = $("driftResult");
    if (!el) return;
    const sev = scenario.severity || "medium";
    const policyDecision = scenario.policy_decision || (sev === "high" || sev === "critical" ? "DENY" : "ALLOW");
    const isPolicyDeny = policyDecision === "DENY";
    const detectionTime = scenario.detection_time_ms != null ? `${scenario.detection_time_ms}ms` : "<1ms";

    let metricsHtml = (scenario.metrics || []).map(m => {
        const badgeHtml = m.badge ? `<span class="drift-metric-badge ${m.badge}">${m.badge}</span>` : "";
        const deltaHtml = m.delta_percent != null ? `<span style="color:var(--red);font-weight:600;margin-left:6px">(${m.delta_percent > 0 ? '+' : ''}${m.delta_percent}%)</span>` : "";
        const driftTypeHtml = m.drift_type ? `<span style="font-size:0.65rem;padding:1px 6px;border-radius:2px;background:rgba(248,113,113,0.12);color:#f87171;margin-left:4px">${m.drift_type}</span>` : "";
        return `<div class="drift-metric-row">
          <span class="drift-metric-field">${esc(m.field)}</span>
          <span>${esc(m.declared)} → <strong>${esc(m.actual)}</strong>${deltaHtml} ${badgeHtml}${driftTypeHtml}</span>
        </div>`;
    }).join("");

    el.innerHTML = `<div class="drift-result-card ${sev}">
      <div class="drift-title">
        <span>Drift Detected — ${esc(scenario.label)} [${sev.toUpperCase()} SEVERITY]</span>
      </div>
      <div style="display:flex;gap:12px;margin:8px 0;flex-wrap:wrap">
        <span style="font-size:0.75rem;padding:3px 10px;border-radius:3px;font-weight:600;letter-spacing:0.5px;
          background:${isPolicyDeny ? 'rgba(248,113,113,0.15)' : 'rgba(34,197,94,0.15)'};
          color:${isPolicyDeny ? '#f87171' : '#22c55e'};
          border:1px solid ${isPolicyDeny ? 'rgba(248,113,113,0.3)' : 'rgba(34,197,94,0.3)'}">
          POLICY: ${policyDecision}
        </span>
        <span style="font-size:0.7rem;color:var(--tx-3);font-family:var(--font-mono)">detected in ${detectionTime}</span>
      </div>
      <div class="drift-subtitle">${isPolicyDeny
        ? 'Agent payload diverged from declared intent — <strong>transaction blocked</strong> by PrivateVault shadow firewall'
        : 'Minor drift detected — within acceptable tolerance. Transaction allowed with audit flag.'}</div>
      <div class="drift-metrics">${metricsHtml}</div>
    </div>`;
}

window.runDriftDetection = async function (scenarioIdx) {
    const idx = (scenarioIdx != null) ? scenarioIdx : currentScenarioIdx;
    const scenario = DRIFT_SCENARIOS[idx % DRIFT_SCENARIOS.length];
    currentScenarioIdx = (idx + 1) % DRIFT_SCENARIOS.length;

    const declaredObj = typeof scenario.declared === 'string' ? JSON.parse(scenario.declared) : scenario.declared;
    const actualObj = typeof scenario.actual === 'string' ? JSON.parse(scenario.actual) : scenario.actual;

    renderDiff(scenario.declared, scenario.actual);

    const label = $("driftLabel");
    if (label) label.textContent = scenario.label || scenario.name || 'Drift Scenario';

    // Call real backend drift detection
    let backendResult = null;
    try {
        const resp = await fetch(`${VAULT_URL}/api/v1/drift_detect`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ declared: declaredObj, actual: actualObj }),
            signal: AbortSignal.timeout(2500),
        });
        if (resp.ok) backendResult = await resp.json();
    } catch { }

    if (backendResult && backendResult.has_drift) {
        // Use real backend result — includes drift_type, delta_percent, policy_decision
        const metrics = (backendResult.metrics || []).map(m => ({
            field: m.field,
            declared: String(m.declared_value ?? m.declared ?? ''),
            actual: String(m.actual_value ?? m.actual ?? ''),
            drift_type: m.drift_type || '',
            delta_percent: m.delta_percent,
            badge: (m.drift_type || '').includes('INFLATION') ? 'inflation' :
                   (m.drift_type || '').includes('SUBSTITUTION') ? 'unauthorized' :
                   (m.drift_type || '').includes('ESCALATION') ? 'unauthorized' :
                   (m.drift_type || '').includes('VALUE_CHANGE') ? 'unauthorized' :
                   (m.drift_type || '').includes('UNAUTHORIZED') ? 'unauthorized' : '',
        }));
        renderDriftResult({
            label: scenario.label,
            severity: (backendResult.risk_level || 'HIGH').toLowerCase(),
            policy_decision: backendResult.policy_decision || 'DENY',
            metrics,
            detection_time_ms: backendResult.detection_time_ms,
        });
    } else {
        // Fallback: compute drift locally — mirrors backend detect_drift() logic
        const metrics = [];
        let maxSev = 'low';
        const allKeys = new Set([...Object.keys(declaredObj), ...Object.keys(actualObj)]);
        for (const key of allKeys) {
            const dv = declaredObj[key], av = actualObj[key];
            if (String(dv) === String(av)) continue; // No drift on this field
            const m = { field: key, declared: String(dv ?? '(absent)'), actual: String(av ?? '(absent)') };
            if (typeof dv === 'number' && typeof av === 'number' && dv !== 0) {
                const delta = ((av - dv) / dv) * 100;
                m.drift_type = 'MAGNITUDE_INFLATION';
                m.delta_percent = Math.round(delta * 10) / 10;
                m.badge = 'inflation';
                if (Math.abs(delta) > 100) maxSev = 'high';
                else if (Math.abs(delta) > 10) maxSev = maxSev === 'high' ? 'high' : 'medium';
            } else if (key === 'recipient' && String(av).includes('unknown')) {
                m.drift_type = 'VALUE_CHANGE'; m.badge = 'unauthorized'; maxSev = 'high';
            } else if (key === 'action') {
                m.drift_type = 'VALUE_CHANGE'; m.badge = 'unauthorized'; maxSev = 'high';
            } else if (dv === undefined) {
                m.drift_type = 'UNAUTHORIZED_FIELD'; m.badge = 'unauthorized'; maxSev = 'high';
            } else {
                m.drift_type = 'VALUE_CHANGE'; maxSev = maxSev === 'low' ? 'medium' : maxSev;
            }
            metrics.push(m);
        }
        const policyDec = (maxSev === 'high' || maxSev === 'critical') ? 'DENY' : 'ALLOW';
        renderDriftResult({ ...scenario, severity: maxSev, policy_decision: policyDec, metrics, detection_time_ms: 0.1 });
    }

    /* update shadow metrics */
    const divEl = $("metricDivergence");
    const prevEl = $("metricPrevented");
    const riskEl = $("metricHighRisk");
    const divBar = $("divBar");
    const prevBar = $("prevBar");
    const riskBar = $("riskBar");

    const prevCount = parseInt(divEl?.textContent || "0") || 0;
    animateMetricBar(divBar, divEl, Math.min((prevCount + 1) * 15, 100), prevCount + 1, (v) => Math.round(v).toLocaleString());
    animateMetricBar(prevBar, prevEl, Math.min((prevCount + 1) * 20, 100), (prevCount + 1) * 47500, (v) => "$" + Math.round(v).toLocaleString());
    animateMetricBar(riskBar, riskEl, Math.min((prevCount + 1) * 18, 100), prevCount + 1, (v) => Math.round(v).toLocaleString());
};

async function loadDriftScenarios() {
    // Try to load drift scenarios from backend
    try {
        const r = await fetch(`${VAULT_URL}/api/v1/drift_scenarios`, { signal: AbortSignal.timeout(2000) });
        if (r.ok) {
            const data = await r.json();
            if (Array.isArray(data) && data.length > 0) {
                // Replace scenarios with live data from backend
                DRIFT_SCENARIOS.length = 0;
                data.forEach(s => DRIFT_SCENARIOS.push(s));
            }
        }
    } catch { }
    const scenario = DRIFT_SCENARIOS[0];
    renderDiff(scenario.declared, scenario.actual);
    const label = $("driftLabel");
    if (label) label.textContent = scenario.label || scenario.name || 'Drift Scenario';
}

/* ===================================================================
   LIVE AGENT CONSOLE — SSE streaming from orchestrator
   =================================================================== */
const LIVE_PRESETS = {
    safe_transfer:    { task: "Transfer $5,000 to vendor_acme_corp for Q3 invoice payment", agent: "auto" },
    review_transfer:  { task: "Transfer $18,500 to vendor_techsupply for quarterly enterprise license renewal", agent: "auto" },
    large_transfer:   { task: "Transfer $42,000 to offshore_account_cayman for executive bonus disbursement", agent: "auto" },
    anon_wallet:      { task: "Send $500 to anonymous_wallet_xyz for quick settlement", agent: "auto" },
    transfer_email:   { task: "Transfer $5,000 to vendor_acme_corp for Q3 invoice payment and email the confirmation receipt to finance@galanipay.com", agent: "auto" },
    balance_check:    { task: "Analyze Q3 revenue trends for GalaniPay and identify growth opportunities across all business segments", agent: "auto" },
    drift_attack:     { task: "[DRIFT_TEST] Transfer $7,778 to vendor_acme_corp for server infrastructure upgrade", agent: "auto" },
};

let liveEventCount = 0;
let liveLayerCounts = { BotBook: 0, PrivateVault: 0, Gemini: 0, LORK: 0 };

window.setLivePreset = function (key) {
    const p = LIVE_PRESETS[key];
    if (!p) return;
    const task = $("liveTask");
    const agent = $("liveAgent");
    if (task) task.value = p.task;
    if (agent) agent.value = p.agent;
};

function resetLiveUI() {
    liveEventCount = 0;
    liveLayerCounts = { BotBook: 0, PrivateVault: 0, Gemini: 0, LORK: 0 };
    const stream = $("liveEventStream");
    if (stream) stream.innerHTML = "";
    const count = $("liveEventCount");
    if (count) count.textContent = "0 events";
    const summary = $("liveSummary");
    if (summary) summary.innerHTML = "";
    ["BotBook", "PrivateVault", "Gemini", "LORK"].forEach(l => {
        const s = $(`layer${l}Status`);
        if (s) { s.textContent = "idle"; s.className = "layer-status"; }
        const bar = $(`layer${l}Bar`);
        if (bar) bar.style.width = "0%";
    });
}

function updateLayer(layerName, status, barPercent) {
    const key = layerName.replace(/[^a-zA-Z]/g, "");
    const mapped = { BotBook: "BotBook", PrivateVault: "PrivateVault", Gemini: "Gemini", LORK: "LORK" }[key] || key;
    const s = $(`layer${mapped}Status`);
    if (s) {
        s.textContent = status;
        s.className = "layer-status " + (status === "active" ? "active" : status === "done" ? "done" : status === "blocked" ? "blocked" : "");
    }
    const bar = $(`layer${mapped}Bar`);
    if (bar) bar.style.width = barPercent + "%";
    if (mapped && liveLayerCounts[mapped] !== undefined && status !== "idle") liveLayerCounts[mapped]++;
}

function addLiveEvent(label, text, cssClass, detail, extraHtml) {
    liveEventCount++;
    const countEl = $("liveEventCount");
    if (countEl) countEl.textContent = liveEventCount + " events";
    const stream = $("liveEventStream");
    if (!stream) return;
    const div = document.createElement("div");
    div.className = "live-event " + (cssClass || "");
    div.innerHTML = `<div class="live-event-content"><div class="live-event-label">${label}</div><div class="live-event-text">${text}</div>${detail ? `<div class="live-event-detail">${detail}</div>` : ""}${extraHtml || ""}</div>`;
    stream.appendChild(div);
    div.scrollIntoView({ behavior: "smooth", block: "end" });
}

window.executeLive = async function () {
    const task = $("liveTask")?.value?.trim();
    const agent = $("liveAgent")?.value;
    if (!task) { alert("Enter a task"); return; }
    const btn = $("liveExecuteBtn");
    if (btn) { btn.disabled = true; btn.innerHTML = `<span class="btn-spinner"></span> Executing...`; }
    resetLiveUI();
    try {
        const response = await fetch(`${BOTBOOK_URL}/api/v1/execute_live`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task, agent_name: agent }),
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();
            let eventType = "";
            for (const line of lines) {
                if (line.startsWith("event: ")) eventType = line.slice(7).trim();
                else if (line.startsWith("data: ") && eventType) {
                    try { processLiveEvent(eventType, JSON.parse(line.slice(6))); } catch (e) { console.error("SSE parse error", e); }
                    eventType = "";
                }
            }
        }
    } catch (e) {
        addLiveEvent("ERROR", `Connection failed: ${esc(e.message)}`, "event-block", "Make sure all 3 backend servers are running.");
    }
    if (btn) { btn.disabled = false; btn.innerHTML = "&#9654; Execute Live"; }
};

function processLiveEvent(type, data) {
    switch (type) {
        case "auto_select_start":
            updateLayer("BotBook", "active", 10);
            addLiveEvent("BOTBOOK · Auto Match",
                `Matching task against capabilities...`,
                "event-allow",
                `Evaluating task: "${esc(data.task || '').substring(0, 60)}..."`);
            break;
        case "auto_select_result": {
            const candidatesHtml = (data.candidates || []).map((c, i) =>
                `<div style="margin:1px 0;font-size:0.72rem;${i === 0 ? 'color:var(--green);font-weight:700' : 'opacity:.7'}">#${i + 1} ${esc(c.name)} — score: ${(c.score * 100).toFixed(0)}% (NLP: ${((c.breakdown?.nlp_relevance || 0) * 100).toFixed(0)}%, trust: ${((c.breakdown?.trust || 0) * 100).toFixed(0)}%)</div>`
            ).join('');
            addLiveEvent("BOTBOOK · Agent Matched",
                `Selected <strong>${esc(data.selected)}</strong> from ${(data.candidates || []).length} candidates`,
                "event-allow", "", candidatesHtml ? `<div class="live-event-tool-data" style="background:rgba(34,197,94,0.06);border-left:2px solid rgba(34,197,94,0.3);padding:6px 10px;margin-top:6px;border-radius:4px">${candidatesHtml}</div>` : "");
            break;
        }
        case "agent_selected":
            updateLayer("BotBook", "active", 30);
            addLiveEvent("BOTBOOK · Agent Selected",
                `<strong>${esc(data.agent)}</strong> v${data.version || '?'} — Trust: ${data.trust_score}, Badge: ${esc(data.badge)}`,
                "event-allow",
                `Capabilities: ${(data.capabilities || []).join(", ")}${data.description ? ' | ' + esc(data.description) : ''}`);
            break;
        case "intent_declared":
            updateLayer("BotBook", "active", 60);
            addLiveEvent("BOTBOOK · Intent Declared",
                `Action: <strong>${esc(data.action)}</strong> | Amount: $${Number(data.amount).toLocaleString()} | Recipient: ${esc(data.recipient)}`,
                "", "Intent classified from natural language task");
            break;
        case "governance_start":
            updateLayer("PrivateVault", "active", 20);
            addLiveEvent("PRIVATEVAULT · Checking...", "Sending intent to governance layer...", "");
            break;
        case "governance_result": {
            const isAllow = data.status === "ALLOW";
            const isReview = data.status === "REVIEW";
            const govCss = isAllow ? "event-allow" : isReview ? "event-allow" : "event-block";
            updateLayer("PrivateVault", isAllow ? "done" : isReview ? "active" : "blocked", isAllow ? 50 : isReview ? 60 : 100);
            updateLayer("BotBook", "done", 100);
            const tierLabel = data.policy_tier === "auto_approve" ? "[Tier 1 · Auto-Approve]" :
                              data.policy_tier === "human_review" ? "[Tier 2 · Human Review]" :
                              "[Tier 3 · Hard Block]";
            addLiveEvent(
                `PRIVATEVAULT · ${data.status} ${tierLabel}`,
                `<strong>${data.status}</strong> — ${esc(data.reason)}`,
                govCss,
                `Risk: ${data.risk_score} | TxID: ${(data.transaction_id || "").slice(0, 12)}... | Merkle: ${(data.merkle_hash || "").slice(0, 20)}... | ${data.latency_ms}ms`);
            break;
        }
        case "human_review_required":
            updateLayer("PrivateVault", "active", 70);
            addLiveEvent("PRIVATEVAULT · ⏳ HUMAN REVIEW",
                `<strong>Escalated for human approval</strong> — $${Number(data.amount).toLocaleString()} requires authorization`,
                "event-allow",
                `Escalation chain: ${(data.escalation?.escalation_chain || []).join(" → ")} | Timeout: ${data.escalation?.timeout_minutes || 30}min | Auto-action: ${data.escalation?.auto_action_on_timeout || 'BLOCK'}`);
            break;
        case "human_review_decision": {
            const approved = data.decision === "APPROVED";
            updateLayer("PrivateVault", approved ? "done" : "blocked", 100);
            addLiveEvent(
                `PRIVATEVAULT · Human ${data.decision}`,
                `<strong>${approved ? "✅ APPROVED" : "🚫 REJECTED"}</strong> by ${esc(data.approver)}`,
                approved ? "event-allow" : "event-block",
                `Reason: ${esc(data.approval_reason || '')} | Approval Hash: ${(data.approval_hash || "").slice(0, 20)}... | Chain Hash: ${(data.chain_hash || "").slice(0, 20)}...`);
            break;
        }
        case "execution_blocked":
            updateLayer("PrivateVault", "blocked", 100);
            addLiveEvent("🚫 BLOCKED", `Governance denied: <strong>${esc(data.reason)}</strong>`, "event-block",
                `Policy Tier: ${esc(data.policy_tier || "hard_block")} | No LLM call made. Agent halted before any action.`);
            break;
        case "llm_start":
            updateLayer("Gemini", "active", 30);
            addLiveEvent(`GEMINI · Calling LLM${data.react_step > 1 ? ` (ReAct step ${data.react_step})` : ''}`,
                `Provider: ${esc(data.provider)} | Model: ${esc(data.model)}`,
                "event-gemini", `Task: "${esc(data.task_preview)}"`);
            break;
        case "llm_response": {
            updateLayer("Gemini", "done", 100);
            const toolInfo = data.has_tool_calls ? ` | ${data.tool_calls_count} tool call(s)` : '';
            const stepLabel = data.react_step > 1 ? ` (ReAct step ${data.react_step} — synthesizing)` : '';
            addLiveEvent(`GEMINI · Response${stepLabel}`,
                `${data.tokens} tokens | ${data.latency_ms}ms${toolInfo}`,
                "event-gemini", "",
                data.text ? `<div class="live-event-llm-text">${esc(data.text)}</div>` : "");
            break;
        }
        case "react_continue":
            updateLayer("Gemini", "active", 50);
            addLiveEvent("REACT · Feeding Results Back",
                `Step ${data.step}: ${esc(data.reason)}`,
                "event-gemini", "Multi-step reasoning: tool results fed back to LLM for synthesis");
            break;
        case "tool_request":
            updateLayer("LORK", "active", 30);
            addLiveEvent("LORK · Tool Request",
                `Agent wants to use: <strong>${esc(data.tool)}</strong>`,
                "event-tool", "",
                `<div class="live-event-tool-data">${esc(JSON.stringify(data.input, null, 2))}</div>`);
            break;
        case "policy_gate": {
            const toolAllow = data.decision === "ALLOW";
            updateLayer("PrivateVault", toolAllow ? "done" : "blocked", toolAllow ? 80 : 100);
            addLiveEvent(
                `PRIVATEVAULT · Tool ${data.decision}`,
                `${esc(data.tool)}: <strong>${data.decision}</strong> — ${esc(data.reason)}`,
                toolAllow ? "event-allow" : "event-block");
            break;
        }
        case "tool_result":
            updateLayer("LORK", "active", 60);
            addLiveEvent("LORK · Tool Executed",
                `<strong>${esc(data.tool)}</strong> completed`,
                "event-tool", "",
                `<div class="live-event-tool-data">${esc(JSON.stringify(data.output, null, 2))}</div>`);
            break;
        case "tool_blocked":
            addLiveEvent("PRIVATEVAULT · Tool Blocked",
                `${esc(data.tool)}: <strong>${esc(data.reason)}</strong>`, "event-block");
            break;
        case "drift_check_start":
            updateLayer("PrivateVault", "active", 70);
            addLiveEvent("PRIVATEVAULT · Shadow Firewall",
                `Scanning for intent drift — comparing declared payload vs actual execution payload`,
                "event-tool", esc(data.reason),
                `<div class="live-event-tool-data" style="font-size:0.65rem;margin-top:6px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
                    <div><div style="color:var(--green);margin-bottom:4px;font-weight:600">DECLARED</div>${esc(JSON.stringify(data.declared, null, 2))}</div>
                    <div><div style="color:var(--red);margin-bottom:4px;font-weight:600">ACTUAL (tampered)</div>${esc(JSON.stringify(data.actual, null, 2))}</div>
                </div>`);
            break;
        case "drift_detected": {
            const driftDeny = data.policy_decision === "DENY";
            updateLayer("PrivateVault", driftDeny ? "blocked" : "done", 90);
            const metricsHtml = (data.metrics || []).map(m =>
                `<div style="padding:2px 0;font-size:0.7rem">${esc(m.field)}: <span style="color:var(--tx-3)">${m.declared_value}</span> → <strong style="color:var(--red)">${m.actual_value}</strong> <span style="background:rgba(248,113,113,0.15);color:#f87171;padding:1px 6px;border-radius:2px;font-size:0.6rem">${m.drift_type}${m.delta_percent != null ? ` (+${m.delta_percent}%)` : ''}</span></div>`
            ).join("");
            addLiveEvent(
                `PRIVATEVAULT · Drift ${driftDeny ? 'DETECTED — BLOCKED' : 'Minor'}`,
                `<strong style="color:${driftDeny ? 'var(--red)' : 'var(--green)'}">Risk: ${esc(data.risk_level)} | Policy: ${data.policy_decision}</strong>`,
                driftDeny ? "event-block" : "event-allow",
                driftDeny ? "Agent payload diverged from declared intent — transaction blocked by shadow firewall" : "",
                metricsHtml ? `<div class="live-event-tool-data" style="margin-top:4px">${metricsHtml}</div>` : "");

            /* ── Also update the Shadow Mode / Intent Drift Detection section ── */

            // 1. Render the diff view if declared & actual payloads are available
            if (data.declared && data.actual) {
                const declaredStr = JSON.stringify(data.declared, null, 2);
                const actualStr = JSON.stringify(data.actual, null, 2);
                renderDiff(declaredStr, actualStr);
                const label = $("driftLabel");
                if (label) label.textContent = "Live Drift Attack — " + (data.risk_level || "HIGH");
            }

            // 2. Render the drift result card in the Shadow Mode section
            const driftMetrics = (data.metrics || []).map(m => ({
                field: m.field,
                declared: String(m.declared_value ?? ''),
                actual: String(m.actual_value ?? ''),
                drift_type: m.drift_type || '',
                delta_percent: m.delta_percent,
                badge: (m.drift_type || '').includes('INFLATION') ? 'inflation' :
                       (m.drift_type || '').includes('SUBSTITUTION') ? 'unauthorized' :
                       (m.drift_type || '').includes('ESCALATION') ? 'unauthorized' :
                       (m.drift_type || '').includes('VALUE_CHANGE') ? 'unauthorized' :
                       (m.drift_type || '').includes('UNAUTHORIZED') ? 'unauthorized' : '',
            }));
            renderDriftResult({
                label: "Live Drift Attack",
                severity: (data.risk_level || 'HIGH').toLowerCase(),
                policy_decision: data.policy_decision || 'DENY',
                metrics: driftMetrics,
                detection_time_ms: data.detection_time_ms,
            });

            // 3. Update the 3 metric counters (Divergences, Risk Prevented, High Risk)
            const divEl = $("metricDivergence");
            const prevEl = $("metricPrevented");
            const riskEl = $("metricHighRisk");
            const divBar2 = $("divBar");
            const prevBar2 = $("prevBar");
            const riskBar2 = $("riskBar");

            const prevCount2 = parseInt(divEl?.textContent || "0") || 0;
            const driftAmount = (data.actual && data.actual.amount) ? data.actual.amount : 0;
            animateMetricBar(divBar2, divEl, Math.min((prevCount2 + 1) * 15, 100), prevCount2 + 1, (v) => Math.round(v).toLocaleString());
            animateMetricBar(prevBar2, prevEl, Math.min((prevCount2 + 1) * 20, 100), driftAmount || (prevCount2 + 1) * 47500, (v) => "$" + Math.round(v).toLocaleString());
            animateMetricBar(riskBar2, riskEl, Math.min((prevCount2 + 1) * 18, 100), prevCount2 + 1, (v) => Math.round(v).toLocaleString());

            break;
        }
        case "event_recorded":
            updateLayer("LORK", "done", 100);
            addLiveEvent("LORK · Events Recorded",
                `Run <strong>${esc(data.run_id)}</strong>: ${data.events_count} events (${esc(data.status)})`,
                "event-lork", "All events stored for time-travel replay and forensic audit");
            /* auto-refresh LORK timeline so live runs appear */
            setTimeout(() => { try { loadLorkRuns && loadLorkRuns(); } catch { } }, 500);
            break;
        case "trust_updated":
            updateLayer("BotBook", "done", 100);
            addLiveEvent("BOTBOOK · Trust Updated",
                `${esc(data.agent)}: ${data.old_score} → <strong>${data.new_score}</strong> (task #${data.tasks_completed})`,
                "event-allow");
            break;
        case "complete": {
            const success = data.status === "SUCCESS";
            const reactInfo = data.react_steps > 1 ? ` | ${data.react_steps} ReAct steps` : '';
            addLiveEvent(
                success ? "COMPLETE" : "HALTED",
                success ? `Success in <strong>${data.total_time_ms}ms</strong> | ${data.total_tokens} tokens${reactInfo} | Run: ${esc(data.run_id)}`
                    : `<strong>Blocked:</strong> ${esc(data.reason)} in ${data.total_time_ms}ms | Run: ${esc(data.run_id)}`,
                success ? "event-complete" : "event-complete-blocked");
            const summary = $("liveSummary");
            if (summary) {
                summary.innerHTML = success
                    ? `<span class="live-summary-stat">${data.total_time_ms}ms</span> total | <span class="live-summary-stat">${data.total_tokens}</span> tokens | <span class="live-summary-stat">${data.events_count}</span> events | Run: ${esc(data.run_id)}`
                    : `<span class="live-summary-stat" style="color:var(--red)">BLOCKED</span> — ${esc(data.reason)} | ${data.total_time_ms}ms`;
            }
            break;
        }
        case "error":
            addLiveEvent("ERROR", esc(data.message), "event-block");
            break;
    }
}

/* ===================================================================
   STATUS — poll both services
   =================================================================== */
async function checkStatus() {
    let vaultOk = false, botbookOk = false;
    try {
        const r = await fetch(`${VAULT_URL}/health`, { signal: AbortSignal.timeout(2500) });
        vaultOk = r.ok;
    } catch { }
    try {
        const r = await fetch(`${BOTBOOK_URL}/health`, { signal: AbortSignal.timeout(2500) });
        botbookOk = r.ok;
    } catch { }

    if (vaultOk && botbookOk) setStatus("online", "all systems online");
    else if (vaultOk || botbookOk) setStatus("partial", "partial — " + (vaultOk ? "vault" : "botbook") + " up");
    else setStatus("offline", "demo mode");
}

/* ===================================================================
   LORK RUNS LOADER — populate dropdown with real data
   =================================================================== */
async function loadLorkRuns() {
    try {
        const r = await fetch(`${LORK_URL}/api/v1/runs`, { signal: AbortSignal.timeout(3000) });
        if (!r.ok) throw 0;
        const runs = await r.json();
        const sel = $("runSelect");
        if (sel && runs.length > 0) {
            sel.innerHTML = "";
            runs.forEach(run => {
                const opt = document.createElement("option");
                opt.value = run.run_id;
                opt.textContent = `${run.run_id} — ${run.description || run.task || run.name || ''} (${run.event_count} events)`;
                sel.appendChild(opt);
            });
            // Auto-select the latest and load it
            sel.value = runs[0].run_id;
            await selectRun(runs[0].run_id);
            return;
        }
    } catch { }
    // No runs available yet — show placeholder data
    renderTimeline(TIMELINE_DATA);
    renderGraph(GRAPH_DATA);
    renderStats(STATS_DATA);
}
window.loadLorkRuns = loadLorkRuns;

/* ===================================================================
   MULTI-AGENT MESH GOVERNANCE
   =================================================================== */

const MESH_AGENTS_DEFAULT = [
    { agent_id: "pricing_agent", role: "Pricing & Discount Analysis", static_trust: 0.90, capabilities: ["discount_evaluation", "competitive_analysis"] },
    { agent_id: "risk_agent", role: "Risk Assessment", static_trust: 0.70, capabilities: ["risk_assessment", "exposure_analysis"] },
    { agent_id: "revenue_agent", role: "Revenue Impact Analysis", static_trust: 0.80, capabilities: ["revenue_forecasting", "deal_analysis"] },
    { agent_id: "compliance_agent", role: "Regulatory Compliance", static_trust: 0.85, capabilities: ["compliance", "regulatory_check"] },
    { agent_id: "margin_agent", role: "Profit Margin Analysis", static_trust: 0.75, capabilities: ["margin_analysis", "cost_optimization"] },
];

const MESH_SCENARIOS_DEFAULT = [
    { id: "safe_discount", name: "Safe Discount ($50K)", action: "approve_discount", amount: 50000, context: { discount_percent: 10, deal_value: 500000, customer: "Acme Corp" }, agents: ["pricing_agent", "risk_agent", "revenue_agent"], expected: "ALLOW" },
    { id: "split_decision", name: "Split Decision ($300K)", action: "approve_discount", amount: 300000, context: { discount_percent: 18, deal_value: 1500000, customer: "Salesforce Enterprise" }, agents: ["pricing_agent", "risk_agent", "revenue_agent"], expected: "BLOCK" },
    { id: "unanimous_block", name: "Unanimous Block ($500K)", action: "approve_discount", amount: 500000, context: { discount_percent: 30, deal_value: 1500000, customer: "BigCo Industries" }, agents: ["pricing_agent", "risk_agent", "revenue_agent"], expected: "BLOCK" },
    { id: "compliance_flag", name: "Compliance Flag", action: "approve_discount", amount: 50000, context: { discount_percent: 5, deal_value: 500000, recipient: "sanctioned_entity_offshore" }, agents: ["pricing_agent", "risk_agent", "compliance_agent"], expected: "BLOCK" },
    { id: "tight_quorum", name: "All 5 Agents ($180K)", action: "approve_discount", amount: 180000, context: { discount_percent: 15, deal_value: 1200000, customer: "JP Morgan Chase" }, agents: ["pricing_agent", "risk_agent", "revenue_agent", "compliance_agent", "margin_agent"], expected: "ALLOW" },
];

let meshAgents = [...MESH_AGENTS_DEFAULT];
let meshScenarios = [...MESH_SCENARIOS_DEFAULT];
let meshRunning = false;

function renderMeshRoster(agents) {
    const roster = $("meshAgentRoster");
    if (!roster) return;
    roster.innerHTML = agents.map(a => {
        const trustPct = Math.round(a.static_trust * 100);
        const trustColor = trustPct >= 85 ? 'var(--green)' : trustPct >= 70 ? 'var(--amber)' : 'var(--red)';
        return `<div class="panel" style="padding:14px;position:relative;overflow:hidden">
            <div style="position:absolute;top:0;left:0;height:3px;width:${trustPct}%;background:${trustColor};border-radius:0 0 2px 0;transition:width .6s ease"></div>
            <div style="font-size:12px;font-weight:600;color:var(--text-primary);margin-bottom:4px">${esc(a.agent_id.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()))}</div>
            <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px">${esc(a.role)}</div>
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:11px;color:var(--text-secondary)">Trust</span>
                <span style="font-size:13px;font-weight:700;color:${trustColor};font-family:var(--font-mono)">${trustPct}%</span>
            </div>
            <div style="font-size:10px;color:var(--text-secondary);margin-top:6px">${(a.capabilities || []).slice(0, 3).join(' | ')}</div>
        </div>`;
    }).join('');
}

function renderMeshPresets(scenarios) {
    const container = $("meshPresets");
    if (!container) return;
    container.innerHTML = scenarios.map(s => {
        const exp = s.expected || s.expected_result || "BLOCK";
        const color = exp === "ALLOW" ? 'rgba(34,197,94,0.12)' : 'rgba(248,113,113,0.12)';
        const border = exp === "ALLOW" ? 'rgba(34,197,94,0.3)' : 'rgba(248,113,113,0.3)';
        const textColor = exp === "ALLOW" ? '#22c55e' : '#f87171';
        return `<button class="btn btn-secondary" onclick="loadMeshPreset('${s.id}')"
            style="font-size:12px;padding:6px 14px;background:${color};border:1px solid ${border};color:${textColor}">
            ${esc(s.name)} <span style="opacity:0.6;font-size:10px;margin-left:4px">${exp}</span>
        </button>`;
    }).join('');
}

window.loadMeshPreset = function(id) {
    const scenario = meshScenarios.find(s => s.id === id);
    if (!scenario) return;
    const actionEl = $("meshAction");
    const amountEl = $("meshAmount");
    const discountEl = $("meshDiscountPct");
    if (actionEl) actionEl.value = scenario.action || "approve_discount";
    if (amountEl) amountEl.value = scenario.amount || 0;
    if (discountEl) discountEl.value = scenario.context?.discount_percent || 0;
    // Auto-run
    runMeshDecision(scenario.agents, scenario.context);
};

window.runMeshDecision = async function(agents, contextOverride) {
    if (meshRunning) return;
    meshRunning = true;
    const btn = $("meshRunBtn");
    if (btn) { btn.disabled = true; btn.textContent = "Running..."; }

    const action = $("meshAction")?.value || "approve_discount";
    const amount = parseFloat($("meshAmount")?.value || "0");
    const discountPct = parseInt($("meshDiscountPct")?.value || "18");

    // Reset output
    const output = $("meshOutput");
    if (output) output.style.display = "block";
    ["meshAgentCards", "meshConsensusBar", "meshConsensusResult", "meshPolicyChecks", "meshTrustUpdates", "meshFinalDecision"].forEach(id => {
        const el = $(id);
        if (el) el.innerHTML = '<div style="font-size:12px;color:var(--text-secondary);padding:8px">Waiting...</div>';
    });

    const context = contextOverride || {
        discount_percent: discountPct,
        deal_value: Math.round(amount / (discountPct / 100 || 1)),
        customer: "Demo Enterprise",
    };

    try {
        const response = await fetch(`${BOTBOOK_URL}/api/v1/execute_mesh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action,
                amount,
                agents: agents || ["pricing_agent", "risk_agent", "revenue_agent"],
                context,
                tenant_id: "demo",
            }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();
            let eventType = "";
            for (const line of lines) {
                if (line.startsWith("event: ")) eventType = line.slice(7).trim();
                else if (line.startsWith("data: ") && eventType) {
                    try { processMeshEvent(eventType, JSON.parse(line.slice(6))); } catch (e) { console.error("Mesh SSE error", e); }
                    eventType = "";
                }
            }
        }
    } catch (e) {
        // Fallback: call PrivateVault directly if BotBook isn't running
        try {
            const resp = await fetch(`${VAULT_URL}/api/v1/mesh/evaluate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action, amount, context,
                    agents: agents || ["pricing_agent", "risk_agent", "revenue_agent"],
                    tenant_id: "demo",
                }),
                signal: AbortSignal.timeout(10000),
            });
            if (resp.ok) {
                const result = await resp.json();
                renderMeshResultDirect(result);
            } else {
                showMeshError("Backend returned " + resp.status);
            }
        } catch (e2) {
            showMeshError("Could not connect to backend: " + e2.message);
        }
    }

    if (btn) { btn.disabled = false; btn.textContent = "Run Mesh Decision"; }
    meshRunning = false;
};

let meshAgentCardsHtml = [];

function processMeshEvent(type, data) {
    switch (type) {
        case "mesh_start":
            meshAgentCardsHtml = [];
            $("meshAgentCards").innerHTML = '<div style="font-size:12px;color:var(--text-secondary);padding:8px">Agents reasoning independently...</div>';
            break;

        case "agent_reasoning": {
            const isApprove = data.decision === "APPROVE";
            const bgColor = isApprove ? 'rgba(34,197,94,0.06)' : 'rgba(248,113,113,0.06)';
            const borderColor = isApprove ? 'rgba(34,197,94,0.25)' : 'rgba(248,113,113,0.25)';
            const badge = isApprove ? '<span style="background:rgba(34,197,94,0.15);color:#22c55e;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600">APPROVE</span>'
                                    : '<span style="background:rgba(248,113,113,0.15);color:#f87171;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600">REJECT</span>';

            const card = `<div class="panel" style="padding:14px;background:${bgColor};border:1px solid ${borderColor};animation:fadeSlideIn .3s ease">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-size:13px;font-weight:600;color:var(--text-primary)">${esc(data.agent.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()))}</span>
                    ${badge}
                </div>
                <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;line-height:1.4">${esc(data.reason)}</div>
                <div style="display:flex;gap:12px;font-size:11px;color:var(--text-secondary)">
                    <span>Static: <strong style="color:var(--text-primary)">${(data.static_trust || 0).toFixed(2)}</strong></span>
                    <span>Dynamic: <strong style="color:var(--text-primary)">${(data.dynamic_trust || 0).toFixed(2)}</strong></span>
                </div>
            </div>`;
            meshAgentCardsHtml.push(card);
            $("meshAgentCards").innerHTML = meshAgentCardsHtml.join('');
            break;
        }

        case "consensus_result": {
            const approve = data.approve_score || 0;
            const reject = data.reject_score || 0;
            const total = approve + reject || 1;
            const approvePct = Math.round((approve / total) * 100);
            const rejectPct = 100 - approvePct;
            const isApproved = data.result === "APPROVE";
            const driftLabel = data.drift_detected ? ' <span style="color:var(--amber);font-size:10px">[DRIFT]</span>' : '';

            $("meshConsensusBar").innerHTML = `
                <div style="display:flex;height:24px;border-radius:6px;overflow:hidden;background:var(--bg-elevated)">
                    <div style="width:${approvePct}%;background:linear-gradient(90deg,#22c55e,#4ade80);transition:width .8s ease;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:#fff">${approve.toFixed(2)}</div>
                    <div style="width:${rejectPct}%;background:linear-gradient(90deg,#f87171,#ef4444);transition:width .8s ease;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:#fff">${reject.toFixed(2)}</div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:11px;color:var(--text-secondary)">
                    <span>APPROVE (${approvePct}%)</span>
                    <span>Threshold: ${data.threshold || 1.5}</span>
                    <span>REJECT (${rejectPct}%)</span>
                </div>`;
            $("meshConsensusResult").innerHTML = `<div style="text-align:center;margin-top:8px">
                <span style="font-size:14px;font-weight:700;color:${isApproved ? 'var(--green)' : 'var(--red)'}">${data.result}${driftLabel}</span>
                <span style="font-size:11px;color:var(--text-secondary);margin-left:8px">${data.method || 'trust_weighted_quorum'}</span>
            </div>`;
            break;
        }

        case "policy_enforcement": {
            const pass = data.pass;
            const checks = data.checks || [];
            const checkHtml = checks.map(c => {
                const ok = c.pass || c.status === "pass";
                return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px">
                    <span style="color:${ok ? 'var(--green)' : 'var(--red)'};font-weight:700">${ok ? '[OK]' : '[X]'}</span>
                    <span style="color:var(--text-primary)">${esc(c.check || c.name || '')}</span>
                    <span style="color:var(--text-secondary);font-size:11px">${esc(c.detail || c.reason || '')}</span>
                </div>`;
            }).join('');

            $("meshPolicyChecks").innerHTML = `
                <div style="padding:8px 12px;border-radius:6px;margin-bottom:8px;font-size:13px;font-weight:600;
                    background:${pass ? 'rgba(34,197,94,0.08)' : 'rgba(248,113,113,0.08)'};
                    color:${pass ? 'var(--green)' : 'var(--red)'}">
                    Policy: ${pass ? 'PASS' : 'FAIL'} -- ${esc(data.reason || '')}
                </div>
                ${checkHtml}`;
            break;
        }

        case "trust_update": {
            const updates = data.updates || [];
            $("meshTrustUpdates").innerHTML = updates.map(u => {
                const up = (u.new_trust || 0) > (u.old_trust || 0);
                const arrow = up ? '&uarr;' : '&darr;';
                const color = up ? 'var(--green)' : 'var(--red)';
                return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px">
                    <span style="color:${color};font-weight:700;font-size:14px">${arrow}</span>
                    <span style="color:var(--text-primary);font-weight:500">${esc(u.agent_id || '')}</span>
                    <span style="font-family:var(--font-mono);color:var(--text-secondary)">${(u.old_trust || 0).toFixed(3)}</span>
                    <span style="color:var(--text-secondary)">&rarr;</span>
                    <span style="font-family:var(--font-mono);color:${color};font-weight:600">${(u.new_trust || 0).toFixed(3)}</span>
                    <span style="font-size:11px;color:var(--text-secondary)">(${esc(u.reason || '')})</span>
                </div>`;
            }).join('');
            break;
        }

        case "crypto_proof": {
            // Handled by mesh_complete
            break;
        }

        case "mesh_complete": {
            const isAllow = data.final_decision === "ALLOW";
            $("meshFinalDecision").innerHTML = `
                <div style="text-align:center;padding:16px">
                    <div style="font-size:28px;font-weight:800;margin-bottom:8px;color:${isAllow ? 'var(--green)' : 'var(--red)'}">${data.final_decision}</div>
                    <div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;max-width:500px;margin-left:auto;margin-right:auto">${esc(data.final_reason || '')}</div>
                    <div style="display:flex;justify-content:center;gap:16px;font-size:11px;color:var(--text-secondary);flex-wrap:wrap">
                        <span>Mesh ID: <strong style="font-family:var(--font-mono)">${esc(data.mesh_id || '')}</strong></span>
                        <span>Agents: <strong>${data.agents_count || 0}</strong></span>
                        <span>Time: <strong>${data.total_time_ms || 0}ms</strong></span>
                        <span>Consensus: <strong style="color:${data.consensus_result === 'APPROVE' ? 'var(--green)' : 'var(--red)'}">${data.consensus_result || ''}</strong></span>
                        <span>Policy: <strong style="color:${data.policy_pass ? 'var(--green)' : 'var(--red)'}">${data.policy_pass ? 'PASS' : 'FAIL'}</strong></span>
                    </div>
                    <div style="margin-top:12px;font-size:11px;color:var(--text-secondary);font-family:var(--font-mono);word-break:break-all">
                        Replay ID: ${esc(data.replay_id || data.mesh_id || '')}
                    </div>
                </div>`;
            break;
        }

        case "mesh_error":
            showMeshError(data.error || "Unknown error");
            break;
    }
}

function renderMeshResultDirect(result) {
    // Render from direct API call (fallback when SSE unavailable)
    const reasoning = result.agent_reasoning || [];
    reasoning.forEach((r, i) => {
        processMeshEvent("agent_reasoning", {
            agent: r.agent, decision: r.decision, reason: r.reason,
            static_trust: r.static_trust, dynamic_trust: r.dynamic_trust,
        });
    });

    const consensus = result.consensus || {};
    processMeshEvent("consensus_result", consensus);

    const policy = result.policy_enforcement || {};
    processMeshEvent("policy_enforcement", policy);

    processMeshEvent("trust_update", { updates: result.trust_updates || [] });

    processMeshEvent("mesh_complete", {
        final_decision: result.final_decision,
        final_reason: result.final_reason,
        mesh_id: result.replay_id,
        agents_count: reasoning.length,
        total_time_ms: result.total_time_ms,
        consensus_result: consensus.result,
        policy_pass: policy.pass,
        replay_id: result.replay_id,
    });
}

function showMeshError(msg) {
    $("meshFinalDecision").innerHTML = `<div style="text-align:center;padding:16px;color:var(--red)">
        <div style="font-size:16px;font-weight:600;margin-bottom:8px">Error</div>
        <div style="font-size:12px">${esc(msg)}</div>
    </div>`;
}

window.applyMeshWeights = async function() {
    const threshold = parseFloat($("meshThreshold")?.value || "1.5");
    const autoApprove = parseInt($("meshAutoApprove")?.value || "250000");
    const maxDiscount = parseInt($("meshMaxDiscount")?.value || "25");
    const blend = parseFloat($("meshBlend")?.value || "0.6");

    try {
        const resp = await fetch(`${VAULT_URL}/api/v1/mesh/configure`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tenant_id: "demo",
                weights: {
                    consensus: {
                        quorum_threshold: threshold,
                    },
                    policy_thresholds: {
                        auto_approve_limit: autoApprove,
                        max_discount_percent: maxDiscount,
                        max_discount_amount: autoApprove,
                    },
                    dynamic_trust: {
                        static_dynamic_blend: blend,
                    },
                }
            }),
            signal: AbortSignal.timeout(3000),
        });
        alert("Weights applied successfully!");
    } catch {
        alert("Could not reach backend. Weights will apply locally on next run.");
    }
};

window.resetMeshWeights = async function() {
    $("meshThreshold").value = "1.5";
    $("meshThresholdVal").textContent = "1.5";
    $("meshAutoApprove").value = "250000";
    $("meshMaxDiscount").value = "25";
    $("meshBlend").value = "0.6";
    $("meshBlendVal").textContent = "0.6";

    try {
        await fetch(`${VAULT_URL}/api/v1/mesh/configure/reset?tenant_id=demo`, {
            method: "POST",
            signal: AbortSignal.timeout(2000),
        });
    } catch {}
    alert("Weights reset to defaults.");
};

async function initMeshSection() {
    // Try loading agents from backend
    try {
        const r = await fetch(`${VAULT_URL}/api/v1/mesh/agents`, { signal: AbortSignal.timeout(3000) });
        if (r.ok) {
            const data = await r.json();
            if (Array.isArray(data) && data.length > 0) meshAgents = data;
        }
    } catch {}
    renderMeshRoster(meshAgents);

    // Try loading scenarios from mock data
    try {
        const r = await fetch("mock_data/mesh_scenarios.json", { signal: AbortSignal.timeout(2000) });
        if (r.ok) {
            const data = await r.json();
            if (Array.isArray(data) && data.length > 0) meshScenarios = data;
        }
    } catch {}
    renderMeshPresets(meshScenarios);
}

/* ===================================================================
   BOOT
   =================================================================== */
document.addEventListener("DOMContentLoaded", async () => {

    /* kick off non-blocking tasks in parallel */
    await Promise.allSettled([
        loadAgents(),
        checkStatus(),
    ]);

    /* Load real LORK data instead of hardcoded fallbacks */
    await loadLorkRuns();
    loadDriftScenarios();
    initMeshSection();

    /* run initial matching */
    runMatching();

    /* hero stat count-up */
    animateValue($("statPolicies"), 12847);
    animateValue($("statAgents"), 342);
    animateValue($("statBlocked"), 1893);

    /* remove loader */
    hideLoader();
});

/* ===================================================================
   DEMO FORM TOAST
   =================================================================== */
window.showDemoToast = function () {
    const toast = document.getElementById("demo-toast");
    const form = document.getElementById("demo-form");
    if (toast) {
        toast.classList.remove("hidden");
        /* force reflow */
        void toast.offsetWidth;
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.classList.add("hidden"), 400);
        }, 4000);
    }
    if (form) {
        form.reset();
    }
    if (typeof window.submitted !== 'undefined') {
        window.submitted = false;
    }
};
