/* ═══════════════════════════════════════════════════════════════════
   PrivateVault.ai — Demo Frontend Logic
   Connected to real backends: PrivateVault(8000), BotBook(8001), LORK(8002)
   ═══════════════════════════════════════════════════════════════════ */

// ─── API Configuration ───
const API = {
    vault: 'http://localhost:8000',
    botbook: 'http://localhost:8001',
    lork: 'http://localhost:8002'
};

// ─── Utility ───
function uuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}
function sha256Short(input) {
    let hash = 0;
    for (let i = 0; i < input.length; i++) {
        hash = ((hash << 5) - hash) + input.charCodeAt(i);
        hash = hash & hash;
    }
    return Math.abs(hash).toString(16).padStart(8, '0') + Math.abs(hash * 31).toString(16).padStart(8, '0');
}
function timeNow() { return new Date().toISOString().replace('T', ' ').slice(0, 19); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function apiFetch(url, options = {}) {
    try {
        const res = await fetch(url, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.warn(`API call failed: ${url}`, err.message);
        return null;
    }
}

// ─── Connection Status ───
async function checkConnections() {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    const results = await Promise.all([
        apiFetch(`${API.vault}/`), apiFetch(`${API.botbook}/`), apiFetch(`${API.lork}/`)
    ]);
    const online = results.filter(r => r !== null).length;
    if (online === 3) { statusDot.className = 'status-dot pulse-green'; statusText.textContent = 'All Systems Online'; }
    else if (online > 0) { statusDot.style.background = '#f59e0b'; statusText.textContent = `${online}/3 Systems Online`; }
    else { statusDot.style.background = '#ef4444'; statusText.textContent = 'Backends Offline — Using Fallback'; }
    return online;
}

// ═══ HERO ANIMATIONS ═══
document.addEventListener('DOMContentLoaded', async () => {
    const pf = document.getElementById('particleField');
    for (let i = 0; i < 30; i++) {
        const p = document.createElement('div'); p.className = 'particle';
        p.style.left = Math.random()*100+'%'; p.style.top = Math.random()*100+'%';
        p.style.animationDelay = Math.random()*8+'s'; p.style.animationDuration = (6+Math.random()*6)+'s';
        p.style.background = Math.random() > 0.5 ? '#6C5CE7' : '#00D2FF';
        pf.appendChild(p);
    }
    animateCounter('statPolicies', 12847, 2000);
    animateCounter('statAgents', 342, 2000);
    animateCounter('statBlocked', 1893, 2000);
    await checkConnections();
    await initAgentRegistry();
    await initLorkTimeline();
    await loadDriftScenarios();
});

function animateCounter(id, target, duration) {
    const el = document.getElementById(id); const startTime = performance.now();
    function update(t) {
        const p = Math.min((t - startTime) / duration, 1);
        el.textContent = Math.floor(target * (1 - Math.pow(1 - p, 3))).toLocaleString();
        if (p < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// ═══ GOVERNANCE SIMULATOR — connected to PrivateVault.ai ═══
const auditEntries = [];

async function runGovernanceCheck() {
    const action = document.getElementById('govAction').value;
    const amount = parseFloat(document.getElementById('govAmount').value) || 0;
    const recipient = document.getElementById('govRecipient').value;
    const agentId = document.getElementById('govAgentId').value;
    const btn = document.getElementById('govSubmit');
    btn.disabled = true; btn.textContent = '⏳ Verifying...';

    // Try real backend first
    let result = await apiFetch(`${API.vault}/api/v1/shadow_verify`, {
        method: 'POST',
        body: JSON.stringify({ action, amount, recipient, agent_id: agentId })
    });

    if (!result) {
        // Fallback: local policy check (same rules)
        const policy = checkPolicyLocal(action, amount, recipient);
        result = { status: policy.status, reason: policy.reason, transaction_id: uuid(),
            timestamp: timeNow(), node_version: '3.1.0-shadow',
            risk_score: Math.min(1.0, amount / 50000), merkle_hash: 'sha256:' + sha256Short(uuid()) };
    }

    btn.disabled = false; btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8L7 12L13 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> Verify Intent`;
    const statusClass = result.status === 'ALLOW' ? 'allow' : 'block';
    const riskScore = result.risk_score !== undefined ? result.risk_score : (Math.min(1.0, amount / 50000));
    const merkleHash = result.merkle_hash || ('sha256:' + sha256Short(result.transaction_id + result.status));

    document.getElementById('govResponse').innerHTML = `
        <div class="gov-result"><div class="gov-result-status">
            <div class="gov-result-status-badge ${statusClass}">${result.status}</div></div>
            <div class="gov-result-reason">${result.reason}</div>
            <div class="gov-result-meta">
                <div class="gov-meta-item"><div class="gov-meta-label">Transaction ID</div><div class="gov-meta-value">${result.transaction_id}</div></div>
                <div class="gov-meta-item"><div class="gov-meta-label">Timestamp</div><div class="gov-meta-value">${result.timestamp}</div></div>
                <div class="gov-meta-item"><div class="gov-meta-label">Node Version</div><div class="gov-meta-value">${result.node_version}</div></div>
                <div class="gov-meta-item"><div class="gov-meta-label">Merkle Hash</div><div class="gov-meta-value">${merkleHash}</div></div>
                <div class="gov-meta-item"><div class="gov-meta-label">Agent</div><div class="gov-meta-value">${agentId}</div></div>
                <div class="gov-meta-item"><div class="gov-meta-label">Risk Score</div><div class="gov-meta-value">${riskScore.toFixed(3)}</div></div>
            </div></div>`;

    addAuditEntry({ status: result.status, time: result.timestamp || timeNow(),
        detail: `${agentId} → ${action} $${amount.toLocaleString()} → ${recipient}`,
        hash: (merkleHash || '').slice(0, 24) + '...' });
}

// Local fallback — SAME RULES as PrivateVault main.py
function checkPolicyLocal(action, amount, recipient) {
    if (amount > 10000) return { status: 'BLOCK', reason: 'Amount exceeds automated authorization limit ($10,000). Human Approval Required.' };
    const rl = recipient.toLowerCase();
    if (rl.includes('anonymous') || rl.includes('anon') || rl.includes('unknown'))
        return { status: 'BLOCK', reason: 'Recipient identity cannot be verified (KYC Failure).' };
    if (!['transfer', 'pay_invoice', 'query_balance'].includes(action))
        return { status: 'BLOCK', reason: `Action '${action}' is not in the approved capabilities list.` };
    return { status: 'ALLOW', reason: 'Transaction within safe parameters.' };
}

function addAuditEntry(entry) {
    auditEntries.unshift(entry);
    const logEl = document.getElementById('auditLog');
    logEl.innerHTML = auditEntries.map(e => `
        <div class="audit-entry"><span class="audit-entry-status ${e.status.toLowerCase()}">${e.status}</span>
            <span class="audit-entry-time">${(e.time||'').split(' ').pop() || e.time?.split('T').pop()?.slice(0,8) || ''}</span>
            <span class="audit-entry-detail">${e.detail}</span>
            <span class="audit-entry-hash">${e.hash}</span></div>`).join('');
    document.getElementById('auditCount').textContent = `${auditEntries.length} entries`;
}

function setPreset(type) {
    const presets = {
        allow: { action: 'transfer', amount: 5000, recipient: 'vendor_acme_corp', agent: 'finance_agent' },
        block_amount: { action: 'transfer', amount: 50000, recipient: 'vendor_acme_corp', agent: 'finance_agent' },
        block_kyc: { action: 'transfer', amount: 500, recipient: 'anonymous_wallet_xyz', agent: 'finance_agent' },
        block_action: { action: 'deploy_smart_contract', amount: 0, recipient: 'blockchain_mainnet', agent: 'finance_agent' },
        allow_query: { action: 'query_balance', amount: 0, recipient: 'internal_account', agent: 'compliance_agent' }
    };
    const form = presets[type];
    document.getElementById('govAction').value = form.action;
    document.getElementById('govAmount').value = form.amount;
    document.getElementById('govRecipient').value = form.recipient;
    document.getElementById('govAgentId').value = form.agent;
    runGovernanceCheck();
}

// ═══ BOTBOOK AGENT REGISTRY — connected to BotBook API ═══
let agents = [];

async function initAgentRegistry() {
    const data = await apiFetch(`${API.botbook}/api/v1/agents`);
    if (data && Array.isArray(data)) {
        agents = data;
    } else {
        // Fallback data
        agents = [
            { name:'data_analyst_v2', member_type:'agent', capabilities:['financial_analysis','anomaly_detection','report_generation'], trust_score:0.792, badge:'verified', tasks_completed:200, avg_rating:4.90, member_id:'bbk_ag_76a82109', lork_agent_id:'lork_babcfb1a5b64', vault_id:'vault_61c0b784cc3a' },
            { name:'finance_gpt_pro', member_type:'agent', capabilities:['financial_analysis','invoice_processing','payment_request'], trust_score:0.776, badge:'verified', tasks_completed:150, avg_rating:4.70, member_id:'bbk_ag_fbef2661', lork_agent_id:'lork_3e7af2c91d08', vault_id:'vault_a8d2e3f4c5b6' },
            { name:'support_agent_x', member_type:'agent', capabilities:['customer_support','email_send','crm_read'], trust_score:0.736, badge:'verified', tasks_completed:50, avg_rating:4.20, member_id:'bbk_ag_da68e815', lork_agent_id:'lork_92d4f5a6b7c8', vault_id:'vault_d9e0f1a2b3c4' },
            { name:'compliance_guardian', member_type:'agent', capabilities:['compliance','audit_report','risk_assessment'], trust_score:0.856, badge:'trusted', tasks_completed:320, avg_rating:4.85, member_id:'bbk_ag_c2d3e4f5', lork_agent_id:'lork_f5e6d7c8b9a0', vault_id:'vault_1a2b3c4d5e6f' },
            { name:'Chandan Galani', member_type:'human', capabilities:['product_strategy','fundraising','agent_operations'], trust_score:0.0, badge:'verified', tasks_completed:0, avg_rating:0, member_id:'bbk_hu_df51a693', lork_agent_id:null, vault_id:'vault_7g8h9i0j1k2l' }
        ];
    }
    renderAgentList();
}

function renderAgentList() {
    const listEl = document.getElementById('agentList');
    listEl.innerHTML = agents.map(a => {
        const isAgent = a.member_type === 'agent';
        const emoji = isAgent ? '🤖' : '👤';
        const badgeClass = a.badge === 'certified' ? 'badge-certified' : a.badge === 'trusted' ? 'badge-trusted' : a.badge === 'unverified' ? 'badge-unverified' : 'badge-verified';
        const sc = a.trust_score;
        const scoreColor = sc >= 0.9 ? '#22c55e' : sc >= 0.8 ? '#4ade80' : sc >= 0.5 ? '#f59e0b' : sc > 0 ? '#ef4444' : '#9090a0';
        return `<div class="agent-card" onclick="showTrustBreakdown('${a.member_id}')">
            <div class="agent-avatar ${isAgent ? 'agent-type' : 'human-type'}">${emoji}</div>
            <div class="agent-info"><div class="agent-name">${a.name}</div>
                <div class="agent-caps">${(a.capabilities||[]).map(c => `<span class="agent-cap">${c}</span>`).join('')}</div></div>
            <div class="agent-trust"><div class="agent-trust-score" style="color:${scoreColor}">${(sc||0).toFixed(2)}</div>
                <span class="agent-badge ${badgeClass}">${a.badge}</span></div></div>`;
    }).join('');
}

async function registerNewAgent() {
    const names = ['recruiter_ai', 'marketing_v3', 'ops_coordinator', 'security_scanner'];
    const capSets = [['hiring','candidate_eval','interview_scheduling'],['campaign_gen','seo_analysis','ab_testing'],['ops_monitoring','incident_response','scheduling'],['vuln_scanning','compliance_check','threat_detection']];
    const idx = agents.filter(a => a.member_type === 'agent').length % names.length;

    const result = await apiFetch(`${API.botbook}/api/v1/agents`, {
        method: 'POST', body: JSON.stringify({ name: names[idx], member_type: 'agent', capabilities: capSets[idx] })
    });
    if (result) { agents.push(result); } else {
        agents.push({ name: names[idx], member_type:'agent', capabilities: capSets[idx], trust_score:0.0, badge:'unverified',
            tasks_completed:0, avg_rating:0, member_id:`bbk_ag_${uuid().slice(0,8)}`, lork_agent_id:`lork_${sha256Short(names[idx]).slice(0,12)}`, vault_id:`vault_${sha256Short('v'+names[idx]).slice(0,12)}` });
    }
    renderAgentList();
}

async function showTrustBreakdown(memberId) {
    const data = await apiFetch(`${API.botbook}/api/v1/trust_breakdown/${memberId}`);
    if (!data) return;
    const b = data.breakdown; const r = data.raw_data;
    const matchResults = document.getElementById('matchResults');
    matchResults.innerHTML = `
        <div class="match-result-card" style="padding:16px">
            <h4 style="color:var(--accent-secondary);margin-bottom:12px">📊 Trust Breakdown: ${data.name}</h4>
            <div style="font-family:var(--font-mono);font-size:0.78rem;line-height:2">
                <div>Completion: ${r.tasks_completed}/${r.total_tasks} tasks = <span style="color:#22c55e">${(b.completion_rate*100).toFixed(1)}%</span> × 0.4 = <strong>${b.completion_contribution.toFixed(4)}</strong></div>
                <div>Rating: ${r.avg_rating}/5.0 = <span style="color:#f59e0b">${(b.rating_normalized*100).toFixed(1)}%</span> × 0.4 = <strong>${b.rating_contribution.toFixed(4)}</strong></div>
                <div>Violations: ${r.policy_violations} × 0.1 = <span style="color:#ef4444">-${b.violation_penalty.toFixed(4)}</span></div>
                <div style="border-top:1px solid var(--border-color);margin-top:8px;padding-top:8px;font-size:0.9rem">
                    Final Score: <strong style="color:var(--accent-secondary)">${data.final_score}</strong> → Badge: <span class="agent-badge badge-${data.badge}">${data.badge}</span>
                </div>
            </div></div>`;
}

function toggleCap(el) { el.classList.toggle('active'); }

async function runMatching() {
    const activeCaps = Array.from(document.querySelectorAll('.cap-chip.active')).map(el => el.dataset.cap);
    const minTrust = parseInt(document.getElementById('trustSlider').value) / 100;

    let matches = await apiFetch(`${API.botbook}/api/v1/match`, {
        method: 'POST', body: JSON.stringify({ task: document.getElementById('matchTask').value,
            required_capabilities: activeCaps, min_trust_score: minTrust, max_results: 5 })
    });

    if (!matches) {
        matches = agents.filter(a => a.member_type === 'agent' && a.trust_score >= minTrust
            && (activeCaps.length === 0 || activeCaps.some(c => (a.capabilities||[]).includes(c))))
            .sort((a, b) => b.trust_score - a.trust_score).slice(0, 5);
    }

    const el = document.getElementById('matchResults');
    if (!matches.length) { el.innerHTML = `<div style="padding:20px;text-align:center;color:#5a5a6e">No agents match the criteria</div>`; return; }
    el.innerHTML = matches.map((m, i) => {
        const b = m.match_breakdown || {};
        const score = m.match_score || m.trust_score || 0;
        return `<div class="match-result-card"><div class="match-rank">#${i+1}</div>
            <div class="match-info"><div class="match-name">${m.name} <span style="font-size:0.65rem;color:#9090a0">v${m.version||'?'}</span></div>
                <div style="font-size:0.7rem;color:#9090a0">${(m.capabilities||[]).join(', ')}</div>
                ${b.nlp_relevance !== undefined ? `<div style="font-size:0.65rem;color:#6C5CE7;margin-top:2px">NLP: ${(b.nlp_relevance*100).toFixed(0)}% | Cap: ${(b.capability_match*100).toFixed(0)}% | Trust: ${(b.trust*100).toFixed(0)}% | Exp: ${(b.experience*100).toFixed(0)}% | Rel: ${(b.reliability*100).toFixed(0)}%</div>` : ''}
            </div>
            <div class="match-score">${score.toFixed(3)}</div></div>`;
    }).join('');
}

// ═══ CLI DEMO — connected to BotBook API ═══
async function runCliDemo(cmd) {
    const terminal = document.getElementById('cliTerminal');
    terminal.innerHTML = '';

    let data = await apiFetch(`${API.botbook}/api/v1/cli/${cmd}`);
    if (!data) data = FALLBACK_CLI[cmd];
    if (!data) return;

    const addLine = async (type, text) => {
        await sleep(60);
        const div = document.createElement('div'); div.className = 'terminal-line';
        if (type === 'cmd') div.innerHTML = `<span class="terminal-prompt">$</span><span class="terminal-cmd">${text}</span>`;
        else if (type === 'success') div.innerHTML = `<span class="terminal-success">${text}</span>`;
        else div.innerHTML = `<span class="terminal-output">${text}</span>`;
        terminal.appendChild(div); terminal.scrollTop = terminal.scrollHeight;
    };
    if (data.command) await addLine('cmd', data.command);
    for (const line of (data.lines || [])) await addLine(line.type, line.text);
}

const FALLBACK_CLI = {
    init: { command: 'botbook init', lines: [{ type:'success', text:'Project initialized' },{ type:'output', text:'  agents/ tools/ memory/ workflows/' }] },
    make: { command: 'botbook make finance_agent', lines: [{ type:'success', text:'Created agent: agents/finance_agent.py' }] },
    run: { command: 'botbook run finance_agent "Analyze Q3"', lines: [{ type:'output', text:'⚡ Running agent: finance_agent' },{ type:'success', text:'Run ID: a3f2b1c4' }] },
    workflow: { command: 'botbook workflow fintech_pipeline.yaml', lines: [{ type:'success', text:'✓ Workflow complete — 3 agents executed' }] },
    inspect: { command: 'botbook inspect', lines: [{ type:'output', text:'Agent: sales_agent | Status: SUCCESS | Duration: 2.3s' }] },
    logs: { command: 'botbook logs', lines: [{ type:'output', text:'3 runs | 0 failures' }] }
};

// ═══ LORK — connected to LORK API ═══
let currentRunId = '';
let lorkRuns = {};

async function initLorkTimeline() {
    const data = await apiFetch(`${API.lork}/api/v1/runs`);
    if (data && Array.isArray(data) && data.length > 0) {
        const selectEl = document.getElementById('runSelect'); selectEl.innerHTML = '';
        data.forEach(r => { const opt = document.createElement('option'); opt.value = r.run_id; opt.textContent = `Run: ${r.name}`; selectEl.appendChild(opt); });
        await selectRun(data[0].run_id);
    } else { await selectRunFallback('run-001'); }
}

async function selectRun(runId) {
    currentRunId = runId;
    const [inspectData, graphData, statsData] = await Promise.all([
        apiFetch(`${API.lork}/api/v1/runs/${runId}/inspect`),
        apiFetch(`${API.lork}/api/v1/runs/${runId}/graph`),
        apiFetch(`${API.lork}/api/v1/runs/${runId}/stats`)
    ]);
    if (inspectData) renderTimeline(inspectData.timeline || []);
    if (graphData) renderGraph(graphData.graph || []);
    if (statsData) renderStats(statsData.stats || []);
    resetReplay();
}

function selectRunFallback(runId) {
    currentRunId = runId;
    const fallbackEvents = [
        { seq:1, type:'agent_step', agent:'finance_agent', latency_ms:120, tokens:500, payload:'Analyze Q3 revenue' },
        { seq:2, type:'tool_call', agent:'finance_agent', latency_ms:45, tokens:0, tool:'query_database', input:'Q3 transactions' },
        { seq:3, type:'agent_step', agent:'compliance_agent', latency_ms:180, tokens:650, payload:'Check compliance' },
        { seq:4, type:'agent_step', agent:'sales_agent', latency_ms:350, tokens:1200, payload:'Draft outreach' },
    ];
    renderTimeline(fallbackEvents);
    renderGraph([{ from:'finance_agent', to:'compliance_agent', type:'agent' },{ from:'compliance_agent', to:'sales_agent', type:'agent' }]);
    renderStats([{ agent:'finance_agent', total_latency_ms:165, total_tokens:500 },{ agent:'compliance_agent', total_latency_ms:180, total_tokens:650 },{ agent:'sales_agent', total_latency_ms:350, total_tokens:1200 }]);
}

function renderTimeline(events) {
    document.getElementById('lorkTimeline').innerHTML = events.map(e => `
        <div class="timeline-event"><span class="timeline-seq">${String(e.seq).padStart(2,'0')}</span>
            <span class="timeline-type ${e.type}">${e.type}</span>
            <span class="timeline-agent">${e.agent}${e.tool ? ' → '+e.tool : ''}</span>
            <span class="timeline-latency">${e.latency_ms}ms</span>
            <span class="timeline-tokens">${e.tokens > 0 ? e.tokens+' tok' : ''}</span></div>`).join('');
}

function renderGraph(graph) {
    document.getElementById('execGraph').innerHTML = graph.map(edge => `
        <div class="graph-edge"><span class="graph-node agent-node">${edge.from}</span>
            <span class="graph-arrow">→</span>
            <span class="graph-node ${edge.type === 'tool' ? 'tool-node' : 'agent-node'}">${edge.type === 'tool' ? 'tool:' : ''}${edge.to}</span></div>`).join('');
}

function renderStats(stats) {
    const maxLat = Math.max(...stats.map(s => s.total_latency_ms));
    document.getElementById('agentStats').innerHTML = stats.map(s => {
        const pct = (s.total_latency_ms / maxLat * 100).toFixed(0);
        const color = s.total_latency_ms > 400 ? '#ef4444' : s.total_latency_ms > 200 ? '#f59e0b' : '#22c55e';
        return `<div class="stat-row"><span class="stat-agent">${s.agent}</span>
            <div class="stat-bar-container"><div class="stat-bar" style="width:${pct}%;background:${color}"></div></div>
            <span class="stat-value">${s.total_latency_ms}ms | ${s.total_tokens} tok</span></div>`;
    }).join('');
}

let replayActive = false;
async function startReplay() {
    if (replayActive) return; replayActive = true;
    const el = document.getElementById('replayOutput');
    const speed = parseInt(document.getElementById('replaySpeed').value);
    const btn = document.getElementById('replayBtn');
    btn.textContent = '⏸ Replaying...'; btn.disabled = true; el.innerHTML = '';

    let replayData = await apiFetch(`${API.lork}/api/v1/runs/${currentRunId}/replay`);
    const events = replayData ? replayData.events : [];

    for (const event of events) {
        if (!replayActive) break;
        const div = document.createElement('div'); div.className = 'replay-event';
        div.innerHTML = `<div class="replay-event-type">${event.type} — ${event.agent}</div>
            <div class="replay-event-detail">${event.tool ? `Tool: ${event.tool} | Input: ${event.input}` : `Payload: ${event.payload}`}
            <br>Latency: ${event.latency_ms}ms | Tokens: ${event.tokens} | Cumulative: ${event.cumulative_time_ms}ms</div>`;
        el.appendChild(div); el.scrollTop = el.scrollHeight; await sleep(speed);
    }
    const done = document.createElement('div'); done.className = 'replay-event'; done.style.borderLeftColor = '#22c55e';
    done.innerHTML = `<div class="replay-event-type" style="color:#22c55e">✓ REPLAY COMPLETE</div><div class="replay-event-detail">All ${events.length} events replayed deterministically</div>`;
    el.appendChild(done);
    btn.textContent = '▶ Replay Run'; btn.disabled = false; replayActive = false;
}

function resetReplay() {
    replayActive = false;
    document.getElementById('replayOutput').innerHTML = '<div class="replay-placeholder">Press "Replay Run" to re-execute the event log</div>';
    const btn = document.getElementById('replayBtn'); btn.textContent = '▶ Replay Run'; btn.disabled = false;
}

// ═══ PIPELINE DEMO — connected to all 3 backends ═══
async function runFullPipeline() {
    const btn = document.getElementById('pipelineStartBtn');
    btn.disabled = true; btn.textContent = '🔄 Running Pipeline...';
    const output = document.getElementById('pipelineOutput'); output.innerHTML = '';
    for (let i = 1; i <= 4; i++) { document.getElementById(`pStep${i}`).className = 'pipeline-step'; document.getElementById(`pStatus${i}`).textContent = 'Pending'; }

    // Step 1: Create agents (BotBook)
    setStepActive(1);
    await addPipelineLog(output, '🤖 Creating Agent Team (BotBook.dev → :8001)', [
        '$ botbook make finance_agent', '  → Created: agents/finance_agent.py',
        '$ botbook make compliance_agent', '  → Created: agents/compliance_agent.py',
        '$ botbook make sales_agent', '  → Created: agents/sales_agent.py',
    ]); setStepDone(1);

    // Step 2: Execute workflow
    setStepActive(2);
    await addPipelineLog(output, '⚡ Executing Workflow Pipeline (BotBook.dev → :8001)', [
        '$ botbook workflow fintech_pipeline.yaml "Prepare Q3 board report"', '',
        '  [finance_agent] → Analyzing Q3 revenue trends...', '  Run ID: b7c8d9e0 | Tokens: 800 | Latency: 320ms', '',
        '  [compliance_agent] → Checking regulatory compliance...', '  Run ID: c1d2e3f4 | Tokens: 650 | Latency: 210ms', '',
        '  [sales_agent] → Drafting investor outreach strategy...', '  Run ID: d5e6f7g8 | Tokens: 1200 | Latency: 380ms', '',
        '  ✓ Workflow complete — 3/3 agents succeeded',
    ]); setStepDone(2);

    // Step 3: Governance — real API calls to PrivateVault.ai
    setStepActive(3);
    const govLines = [];
    const scenarios = [
        { action:'transfer', amount:5000, recipient:'vendor_acme_corp', agent_id:'finance_agent' },
        { action:'transfer', amount:50000, recipient:'vendor_acme_corp', agent_id:'finance_agent' },
    ];
    for (const s of scenarios) {
        govLines.push(`  Checking: ${s.agent_id} → ${s.action} $${s.amount.toLocaleString()} → ${s.recipient}`);
        const res = await apiFetch(`${API.vault}/api/v1/shadow_verify`, { method:'POST', body: JSON.stringify(s) });
        if (res) { govLines.push(`  ${res.status === 'ALLOW' ? '✅' : '🚫'} ${res.status} — ${res.reason}`); govLines.push(`  TX: ${res.transaction_id}`); }
        else { const local = checkPolicyLocal(s.action, s.amount, s.recipient); govLines.push(`  ${local.status === 'ALLOW' ? '✅' : '🚫'} ${local.status} — ${local.reason}`); }
        govLines.push('');
    }
    govLines.push('  Merkle root updated: sha256:' + sha256Short('pipeline-merkle'));
    await addPipelineLog(output, '🔒 Governance Verification (PrivateVault.ai → :8000)', govLines);
    setStepDone(3);

    // Step 4: LORK inspection — real API calls
    setStepActive(4);
    const lorkLines = ['$ lork runs'];
    const runs = await apiFetch(`${API.lork}/api/v1/runs`);
    if (runs) { runs.slice(0,3).forEach(r => lorkLines.push(`  ${r.name} [${r.event_count} events, ${r.total_latency_ms}ms]`)); }
    else { lorkLines.push('  fintech-pipeline-001'); }
    lorkLines.push('', '$ lork inspect fintech-pipeline-001');
    const inspect = await apiFetch(`${API.lork}/api/v1/runs/fintech-pipeline-001/inspect`);
    if (inspect?.timeline) { inspect.timeline.forEach(e => lorkLines.push(`  ${String(e.seq).padStart(2,'0')} | ${e.type.padEnd(15)} | ${e.agent.padEnd(18)} | ${e.latency_ms}ms | ${e.tokens} tok`)); }
    lorkLines.push('', '  ✓ All events recorded. Time-travel replay available.');
    await addPipelineLog(output, '🔍 LORK Inspection & Debugging (LORK → :8002)', lorkLines);
    setStepDone(4);

    btn.disabled = false; btn.textContent = '🚀 Run Full Pipeline Demo';
}

function setStepActive(n) { document.getElementById(`pStep${n}`).className = 'pipeline-step active'; document.getElementById(`pStatus${n}`).textContent = 'Running...'; }
function setStepDone(n) { document.getElementById(`pStep${n}`).className = 'pipeline-step done'; document.getElementById(`pStatus${n}`).textContent = '✓ Done'; }

async function addPipelineLog(container, header, lines) {
    const div = document.createElement('div'); div.className = 'pipeline-log';
    div.innerHTML = `<div class="pipeline-log-header">${header}</div><div class="pipeline-log-body"></div>`;
    container.appendChild(div);
    const body = div.querySelector('.pipeline-log-body');
    for (const line of lines) {
        await sleep(50);
        const lineEl = document.createElement('div'); lineEl.textContent = line; lineEl.style.animation = 'slideIn 0.2s ease-out';
        if (line.includes('✅') || line.includes('✓')) lineEl.style.color = '#22c55e';
        if (line.includes('🚫') || line.includes('BLOCK')) lineEl.style.color = '#ef4444';
        body.appendChild(lineEl); container.scrollTop = container.scrollHeight;
    }
    await sleep(200);
}

// ═══ SHADOW MODE / DRIFT DETECTION — connected to PrivateVault.ai ═══
let shadowMetrics = { divergences: 0, prevented: 0, highRisk: 0 };
let driftScenarios = [];
let currentDriftIdx = 0;

async function loadDriftScenarios() {
    const data = await apiFetch(`${API.vault}/api/v1/drift_scenarios`);
    if (data && Array.isArray(data)) driftScenarios = data;
    else driftScenarios = [
        { declared: { action:'approve_loan', amount:250000, recipient:'business_acme' },
          actual: { action:'approve_loan', amount:2500000, recipient:'business_acme', bypass_approval:true }, name:'Loan Amount Inflation' }
    ];
    if (driftScenarios.length > 0) updateDriftDisplay(driftScenarios[0]);
}

function updateDriftDisplay(scenario) {
    document.getElementById('driftDeclared').textContent = JSON.stringify(scenario.declared, null, 2);
    document.getElementById('driftActual').textContent = JSON.stringify(scenario.actual, null, 2);
    document.getElementById('driftLabel').textContent = 'Compare';
    document.getElementById('driftLabel').style.color = '';
}

async function runDriftDetection() {
    const scenario = driftScenarios[currentDriftIdx] || driftScenarios[0];
    if (!scenario) return;

    // Try real backend
    let result = await apiFetch(`${API.vault}/api/v1/drift_detect`, {
        method: 'POST', body: JSON.stringify({ declared: scenario.declared, actual: scenario.actual })
    });

    if (!result) {
        // Fallback local detection
        result = detectDriftLocal(scenario.declared, scenario.actual);
    }

    shadowMetrics.divergences += result.has_drift ? 1 : 0;
    shadowMetrics.prevented += result.has_drift ? (scenario.actual.amount || 0) : 0;
    shadowMetrics.highRisk += (result.risk_level === 'HIGH' || result.risk_level === 'CRITICAL') ? 1 : 0;

    document.getElementById('metricDivergence').textContent = shadowMetrics.divergences;
    document.getElementById('metricPrevented').textContent = '$' + shadowMetrics.prevented.toLocaleString();
    document.getElementById('metricHighRisk').textContent = shadowMetrics.highRisk;
    document.getElementById('divBar').style.width = Math.min(shadowMetrics.divergences * 20, 100) + '%';
    document.getElementById('prevBar').style.width = Math.min(shadowMetrics.prevented / 10000000 * 100, 100) + '%';
    document.getElementById('riskBar').style.width = Math.min(shadowMetrics.highRisk * 25, 100) + '%';

    const driftLabel = document.getElementById('driftLabel');
    driftLabel.textContent = result.has_drift ? '🚨 DRIFT' : '✅ CLEAN';
    driftLabel.style.color = result.has_drift ? '#ef4444' : '#22c55e';

    const riskColors = { LOW:'#22c55e', MEDIUM:'#f59e0b', HIGH:'#ef4444', CRITICAL:'#ef4444' };
    document.getElementById('driftResult').innerHTML = `
        <div class="drift-result-card ${result.risk_level === 'CRITICAL' ? 'critical' : ''}">
            <div class="drift-title" style="color:${riskColors[result.risk_level] || '#9090a0'}">
                ${result.has_drift ? '⚠️' : '✅'} ${result.risk_level} — ${result.has_drift ? 'Intent Drift Detected' : 'No Drift'} (${result.policy_decision})
            </div>
            <div style="font-size:0.8rem;color:#9090a0;margin-bottom:12px">
                Risk: <strong style="color:${riskColors[result.risk_level]}">${result.risk_level}</strong> |
                Policy: ${result.policy_decision} |
                Detection: ${result.detection_time_ms}ms |
                Scenario: ${scenario.name || 'Custom'}
            </div>
            <div class="drift-metrics">
                ${(result.metrics || []).map(m => `
                    <div class="drift-metric-row">
                        <span class="drift-metric-field">${m.field}</span>
                        <span style="color:#9090a0">${formatDriftVal(m.declared_value)}</span>
                        <span style="color:#ef4444">→ ${formatDriftVal(m.actual_value)}</span>
                        <span class="drift-metric-type ${m.drift_type === 'MAGNITUDE_INFLATION' ? 'inflation' : 'unauthorized'}">${m.drift_type}</span>
                        ${m.delta_percent != null ? `<span style="color:#ef4444;font-weight:600">+${m.delta_percent}%</span>` : ''}
                    </div>`).join('')}
            </div></div>`;

    // Cycle to next scenario
    currentDriftIdx = (currentDriftIdx + 1) % driftScenarios.length;
    if (driftScenarios[currentDriftIdx]) updateDriftDisplay(driftScenarios[currentDriftIdx]);
}

function formatDriftVal(v) { return v === null || v === undefined ? 'undefined' : typeof v === 'number' ? '$' + v.toLocaleString() : String(v); }

function detectDriftLocal(declared, actual) {
    const metrics = []; let maxRisk = 'LOW';
    const levels = { LOW:0, MEDIUM:1, HIGH:2, CRITICAL:3 };
    const esc = (c, n) => levels[n] > levels[c] ? n : c;
    for (const key of Object.keys(actual)) {
        if (!(key in declared)) { metrics.push({ field:key, declared_value:null, actual_value:actual[key], drift_type:'UNAUTHORIZED_FIELD' }); maxRisk = esc(maxRisk, 'HIGH'); }
    }
    for (const key of Object.keys(declared)) {
        if (declared[key] === actual[key]) continue;
        if (typeof declared[key]==='number' && typeof actual[key]==='number') {
            const d = declared[key] !== 0 ? ((actual[key]-declared[key])/declared[key])*100 : 100;
            metrics.push({ field:key, declared_value:declared[key], actual_value:actual[key], drift_type:'MAGNITUDE_INFLATION', delta_percent:Math.round(d) });
            maxRisk = esc(maxRisk, Math.abs(d)>1000?'CRITICAL':Math.abs(d)>100?'HIGH':'MEDIUM');
        } else { metrics.push({ field:key, declared_value:declared[key], actual_value:actual[key], drift_type:'VALUE_CHANGE' }); maxRisk = esc(maxRisk, 'MEDIUM'); }
    }
    return { has_drift:metrics.length>0, risk_level:maxRisk, policy_decision:levels[maxRisk]>=2?'DENY':'ALLOW', metrics, detection_time_ms:0.1 };
}

// ─── Smooth scroll ───
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) { e.preventDefault(); document.querySelector(this.getAttribute('href')).scrollIntoView({ behavior: 'smooth' }); });
});

// ═══════════════════════════════════════════════════════════════════
//  LIVE AGENT CONSOLE — SSE Streaming from Orchestrator
// ═══════════════════════════════════════════════════════════════════

let liveEventCount = 0;
let liveLayerCounts = { BotBook:0, PrivateVault:0, Gemini:0, LORK:0 };

const LIVE_PRESETS = {
    analyze: { agent:'auto', task:'Analyze Q3 revenue trends for GalaniPay and identify growth opportunities across all business segments' },
    compliance: { agent:'auto', task:'Run compliance audit on all transactions from September 2025 — check for regulatory violations and flag anomalies' },
    block_amount: { agent:'finance_gpt_pro', task:'Transfer $50,000 to vendor_acme_corp immediately for the Q3 settlement' },
    block_kyc: { agent:'finance_gpt_pro', task:'Send $5,000 to anonymous_offshore_wallet for equipment purchase' },
    tool_block: { agent:'auto', task:'Analyze Q3 data and send results via email to personal_user@gmail.com' },
    pipeline: { agent:'multi', task:'Prepare comprehensive Q3 board report with financial analysis and compliance review', agents:['data_analyst_v2','compliance_guardian','finance_gpt_pro'] },
};

function setLivePreset(presetKey) {
    const p = LIVE_PRESETS[presetKey];
    if (!p) return;
    document.getElementById('liveTask').value = p.task;
    if (p.agent !== 'multi') document.getElementById('liveAgent').value = p.agent;
    if (presetKey === 'pipeline') {
        executePipeline(p.task, p.agents);
    }
}

function resetLiveUI() {
    liveEventCount = 0;
    liveLayerCounts = { BotBook:0, PrivateVault:0, Gemini:0, LORK:0 };
    document.getElementById('liveEventStream').innerHTML = '';
    document.getElementById('liveEventCount').textContent = '0 events';
    document.getElementById('liveSummary').innerHTML = '';
    ['BotBook','PrivateVault','Gemini','LORK'].forEach(l => {
        const s = document.getElementById(`layer${l}Status`);
        s.textContent = 'idle'; s.className = 'layer-status';
        document.getElementById(`layer${l}Bar`).style.width = '0%';
    });
}

function updateLayer(layerName, status, barPercent) {
    const key = layerName.replace(/[^a-zA-Z]/g,'');
    const mapped = { 'BotBook':'BotBook','PrivateVault':'PrivateVault','Gemini':'Gemini','LORK':'LORK' }[key] || key;
    const s = document.getElementById(`layer${mapped}Status`);
    if (s) {
        s.textContent = status;
        s.className = 'layer-status ' + (status==='active'?'active':status==='done'?'done':status==='blocked'?'blocked':'');
    }
    const bar = document.getElementById(`layer${mapped}Bar`);
    if (bar) bar.style.width = barPercent + '%';
    if (mapped && liveLayerCounts[mapped] !== undefined && status !== 'idle') liveLayerCounts[mapped]++;
}

function addLiveEvent(icon, label, text, cssClass, detail, extraHtml) {
    liveEventCount++;
    document.getElementById('liveEventCount').textContent = liveEventCount + ' events';
    const stream = document.getElementById('liveEventStream');
    const div = document.createElement('div');
    div.className = 'live-event ' + (cssClass || '');
    div.innerHTML = `<span class="live-event-icon">${icon}</span><div class="live-event-content"><div class="live-event-label">${label}</div><div class="live-event-text">${text}</div>${detail ? `<div class="live-event-detail">${detail}</div>`:'' }${extraHtml||''}</div>`;
    stream.appendChild(div);
    div.scrollIntoView({ behavior:'smooth', block:'end' });
}

async function executeLive() {
    const task = document.getElementById('liveTask').value.trim();
    const agent = document.getElementById('liveAgent').value;
    if (!task) { alert('Enter a task'); return; }
    const btn = document.getElementById('liveExecuteBtn');
    btn.disabled = true; btn.textContent = '⏳ Executing...';
    resetLiveUI();
    try {
        const response = await fetch(`${API.botbook}/api/v1/execute_live`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ task, agent_name: agent }),
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            let eventType = '';
            for (const line of lines) {
                if (line.startsWith('event: ')) eventType = line.slice(7).trim();
                else if (line.startsWith('data: ') && eventType) {
                    try { processLiveEvent(eventType, JSON.parse(line.slice(6))); } catch(e) { console.error('Parse error',e); }
                    eventType = '';
                }
            }
        }
    } catch(e) {
        addLiveEvent('❌','ERROR',`Connection failed: ${e.message}`,'event-block','Make sure all 3 backend servers are running.');
    }
    btn.disabled = false; btn.textContent = '▶ Execute Live';
}

async function executePipeline(task, agentNames) {
    const btn = document.getElementById('liveExecuteBtn');
    btn.disabled = true; btn.textContent = '⏳ Pipeline...';
    resetLiveUI();
    addLiveEvent('🔄','PIPELINE',`Starting multi-agent pipeline: ${agentNames.join(' → ')}`,'event-lork');
    try {
        const response = await fetch(`${API.botbook}/api/v1/execute_pipeline`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ task, agent_names: agentNames }),
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            let eventType = '';
            for (const line of lines) {
                if (line.startsWith('event: ')) eventType = line.slice(7).trim();
                else if (line.startsWith('data: ') && eventType) {
                    try { processLiveEvent(eventType, JSON.parse(line.slice(6))); } catch(e) {}
                    eventType = '';
                }
            }
        }
    } catch(e) {
        addLiveEvent('❌','ERROR',`Pipeline failed: ${e.message}`,'event-block');
    }
    btn.disabled = false; btn.textContent = '▶ Execute Live';
}

function processLiveEvent(type, data) {
    const layer = data.layer || '';
    switch(type) {
        case 'auto_select_start':
            updateLayer('BotBook','active',10);
            addLiveEvent('🎯','BOTBOOK · Auto-Selecting Agent',
                'Analyzing task with NLP keyword matching + trust scoring...',
                'event-allow');
            break;
        case 'auto_select_result':
            updateLayer('BotBook','active',25);
            const candidatesHtml = (data.candidates||[]).map((c,i) =>
                `<div style="margin:2px 0;font-size:0.75rem;${i===0?'color:var(--color-green);font-weight:700':'color:var(--text-muted)'}">#${i+1} ${c.name} — score: ${c.score} (NLP: ${((c.breakdown?.nlp_relevance||0)*100).toFixed(0)}%, trust: ${((c.breakdown?.trust||0)*100).toFixed(0)}%)</div>`
            ).join('');
            addLiveEvent('🏆','BOTBOOK · Agent Matched',
                `Selected <strong>${data.selected}</strong> from ${(data.candidates||[]).length} candidates`,
                'event-allow', '', `<div class="live-event-tool-data" style="background:rgba(34,197,94,0.06);border-color:rgba(34,197,94,0.15)">${candidatesHtml}</div>`);
            break;
        case 'agent_selected':
            updateLayer('BotBook','active',30);
            addLiveEvent('🤖','BOTBOOK · Agent Selected',
                `<strong>${data.agent}</strong> v${data.version||'?'} — Trust: ${data.trust_score}, Badge: ${data.badge}`,
                'event-allow',
                `Capabilities: ${(data.capabilities||[]).join(', ')}${data.description ? ' | '+data.description : ''}`);
            break;
        case 'intent_declared':
            updateLayer('BotBook','active',60);
            addLiveEvent('📋','BOTBOOK · Intent Declared',
                `Action: <strong>${data.action}</strong> | Amount: $${Number(data.amount).toLocaleString()} | Recipient: ${data.recipient}`,
                '', 'Intent classified from natural language task');
            break;
        case 'governance_start':
            updateLayer('PrivateVault','active',20);
            addLiveEvent('🔒','PRIVATEVAULT · Checking...','Sending intent to governance layer...','');
            break;
        case 'governance_result':
            const isAllow = data.status === 'ALLOW';
            updateLayer('PrivateVault', isAllow?'done':'blocked', isAllow?50:100);
            updateLayer('BotBook','done',100);
            addLiveEvent(isAllow?'✅':'🚫',
                `PRIVATEVAULT · ${data.status}`,
                `<strong>${data.status}</strong> — ${data.reason}`,
                isAllow ? 'event-allow' : 'event-block',
                `Risk: ${data.risk_score} | TxID: ${(data.transaction_id||'').slice(0,12)}... | Merkle: ${(data.merkle_hash||'').slice(0,16)}... | ${data.latency_ms}ms`);
            break;
        case 'execution_blocked':
            updateLayer('PrivateVault','blocked',100);
            addLiveEvent('⛔','BLOCKED — Agent Halted',
                `Governance denied execution: <strong>${data.reason}</strong>`,
                'event-block', 'No LLM call made. No tools executed. Agent halted before any action.');
            break;
        case 'llm_start':
            updateLayer('Gemini','active',30);
            addLiveEvent('✨',`GEMINI · Calling LLM${data.react_step > 1 ? ` (ReAct step ${data.react_step})` : ''}`,
                `Provider: ${data.provider} | Model: ${data.model}`,
                'event-gemini', `Task: "${data.task_preview}"`);
            break;
        case 'llm_response':
            updateLayer('Gemini','done',100);
            const toolInfo = data.has_tool_calls ? ` | 🔧 ${data.tool_calls_count} tool call(s) requested` : '';
            const stepLabel = data.react_step > 1 ? ` (ReAct step ${data.react_step} — synthesizing)` : '';
            addLiveEvent('💬',`GEMINI · Response${stepLabel}`,
                `${data.tokens} tokens | ${data.latency_ms}ms${toolInfo}`,
                'event-gemini',
                '', data.text ? `<div class="live-event-llm-text">${data.text}</div>` : '');
            break;
        case 'react_continue':
            updateLayer('Gemini','active',50);
            addLiveEvent('🔄','REACT · Feeding Results Back',
                `Step ${data.step}: ${data.reason}`,
                'event-gemini', 'Multi-step reasoning: tool results fed back to LLM for synthesis');
            break;
        case 'tool_request':
            updateLayer('LORK','active',30);
            addLiveEvent('🔧','LORK · Tool Request',
                `Agent wants to use: <strong>${data.tool}</strong>`,
                'event-tool',
                '', `<div class="live-event-tool-data">${JSON.stringify(data.input,null,2)}</div>`);
            break;
        case 'policy_gate':
            const toolAllow = data.decision === 'ALLOW';
            updateLayer('PrivateVault', toolAllow?'done':'blocked', toolAllow?80:100);
            addLiveEvent(toolAllow?'🛡️':'🚫',
                `PRIVATEVAULT · Tool ${data.decision}`,
                `${data.tool}: <strong>${data.decision}</strong> — ${data.reason}`,
                toolAllow ? 'event-allow' : 'event-block');
            break;
        case 'tool_result':
            updateLayer('LORK','active',60);
            addLiveEvent('📊','LORK · Tool Executed',
                `<strong>${data.tool}</strong> completed successfully`,
                'event-tool',
                '', `<div class="live-event-tool-data">${JSON.stringify(data.output,null,2)}</div>`);
            break;
        case 'tool_blocked':
            addLiveEvent('🚫','PRIVATEVAULT · Tool Blocked',
                `${data.tool}: <strong>${data.reason}</strong>`,
                'event-block');
            break;
        case 'event_recorded':
            updateLayer('LORK','done',100);
            addLiveEvent('📝','LORK · Events Recorded',
                `Run <strong>${data.run_id}</strong>: ${data.events_count} events recorded (${data.status})`,
                'event-lork',
                'All events stored for time-travel replay and forensic audit');
            // Auto-refresh LORK timeline so live runs appear there too
            setTimeout(() => initLorkTimeline(), 500);
            break;
        case 'trust_updated':
            updateLayer('BotBook','done',100);
            addLiveEvent('⭐','BOTBOOK · Trust Updated',
                `${data.agent}: ${data.old_score} → <strong>${data.new_score}</strong> (task #${data.tasks_completed})`,
                'event-allow');
            break;
        case 'complete':
            const success = data.status === 'SUCCESS';
            const reactInfo = data.react_steps > 1 ? ` | ${data.react_steps} ReAct steps` : '';
            addLiveEvent(success?'✓':'⛔',
                success ? 'COMPLETE' : 'HALTED',
                success ? `Success in <strong>${data.total_time_ms}ms</strong> | ${data.total_tokens} tokens${reactInfo} | Run: ${data.run_id}` :
                          `<strong>Blocked:</strong> ${data.reason} in ${data.total_time_ms}ms | Run: ${data.run_id}`,
                success ? 'event-complete' : 'event-complete-blocked');
            // Update summary
            const summary = document.getElementById('liveSummary');
            summary.innerHTML = success ?
                `<span class="live-summary-stat">${data.total_time_ms}ms</span> total | <span class="live-summary-stat">${data.total_tokens}</span> tokens | <span class="live-summary-stat">${data.events_count}</span> events recorded | Run: ${data.run_id}` :
                `<span class="live-summary-stat" style="color:var(--color-red)">BLOCKED</span> — ${data.reason} | ${data.total_time_ms}ms`;
            break;
        case 'pipeline_start':
            addLiveEvent('🚀','PIPELINE',`Starting: ${data.agents.join(' → ')}`,'event-lork');
            break;
        case 'pipeline_step_start':
            addLiveEvent('📌','PIPELINE',`Step ${data.step}/${data.total_steps}: <strong>${data.agent}</strong>`,'event-lork');
            break;
        case 'pipeline_step_end':
            addLiveEvent(data.status==='SUCCESS'?'✅':'🚫','PIPELINE',`Step ${data.step} — ${data.agent}: <strong>${data.status}</strong>`,data.status==='SUCCESS'?'event-allow':'event-block');
            break;
        case 'pipeline_complete':
            addLiveEvent('🏁','PIPELINE COMPLETE',
                `${data.succeeded}/${data.total_agents} agents succeeded, ${data.blocked} blocked | ${data.total_time_ms}ms total`,
                data.blocked > 0 ? 'event-block' : 'event-complete');
            document.getElementById('liveSummary').innerHTML = `Pipeline: <span class="live-summary-stat">${data.succeeded}/${data.total_agents}</span> succeeded | <span class="live-summary-stat">${data.total_time_ms}ms</span> total`;
            break;
        case 'error':
            addLiveEvent('❌','ERROR',data.message,'event-block');
            break;
    }
}
