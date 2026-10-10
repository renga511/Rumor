/* ══════════════════════════════════════════════════════════
   AI RUMOR PROPAGATION SIMULATOR - MAIN JS
══════════════════════════════════════════════════════════ */

// ─── State ─────────────────────────────────────────────────────────────────
let lastFactCheckResult = null;
let networkData = null;       // {nodes, edges, adjacency}
let simStates = null;         // current node states array
let simRunning = false;
let simTimer = null;
let simStep = 0;
let propChart = null;
let propHistory = { S: [], I: [], R: [], M: [], T: [] };
let currentNewsTab = 'india';
let newsCache = { india: null, world: null };
let simIsTrue = false;  // is current sim for true/fake news?

// ─── Navigation ────────────────────────────────────────────────────────────
function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b => {
    if (b.textContent.toLowerCase().includes(id.replace('-', ' ').split(' ')[0]))
      b.classList.add('active');
  });
}

// ─── Fact Checker ──────────────────────────────────────────────────────────
function setExample(text) {
  document.getElementById('claim-input').value = text;
}

function loadExample() {
  const examples = [
    "Israel and Hezbollah traded fire across the border",
    "The 1969 moon landing was faked by NASA",
    "Albert Einstein won the Nobel Prize in Physics",
    "5G cell phone towers spread coronavirus",
    "Scientists have discovered water on Mars"
  ];
  setExample(examples[Math.floor(Math.random() * examples.length)]);
}

async function runFactCheck() {
  const claim = document.getElementById('claim-input').value.trim();
  if (!claim) { showToast('Please enter a claim to analyze', 'error'); return; }

  // Show loading
  document.getElementById('fc-loading').style.display = 'flex';
  document.getElementById('results-panel').style.display = 'none';
  document.getElementById('sources-section').style.display = 'none';
  document.getElementById('check-btn').disabled = true;

  // Animate loading steps
  const steps = ['Connecting to global RSS feeds…', 'Scanning Wikipedia databases…', 'Cross-referencing 6 regional feeds…', 'Computing confidence score…'];
  let si = 0;
  const stepEl = document.getElementById('loading-steps');
  const stepTimer = setInterval(() => {
    if (si < steps.length) stepEl.textContent = steps[si++];
    else clearInterval(stepTimer);
  }, 800);

  try {
    const res = await fetch('/api/fact-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: claim })
    });
    const data = await res.json();
    clearInterval(stepTimer);
    lastFactCheckResult = data;
    lastFactCheckResult.claim = claim;
    renderFactCheckResult(data);
    showToast('Analysis complete', 'success');
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
  } finally {
    document.getElementById('fc-loading').style.display = 'none';
    document.getElementById('check-btn').disabled = false;
  }
}

function renderFactCheckResult(data) {
  const panel = document.getElementById('results-panel');
  panel.style.display = 'block';

  // Verdict box
  const vbox = document.getElementById('verdict-box');
  vbox.className = 'verdict-box ' + (data.verdict_cls || 'inconclusive');

  const icons = { real: '✅', fake: '🚨', inconclusive: '⚠️' };
  document.getElementById('verdict-icon').textContent = icons[data.verdict_cls] || '❓';
  document.getElementById('verdict-label').textContent = data.prediction;

  const conf = data.confidence || 50;
  document.getElementById('conf-fill').style.width = conf + '%';
  document.getElementById('conf-pct').textContent = conf + '%';

  // Score breakdown
  const sb = data.score_breakdown || {};
  const scoreGrid = document.getElementById('score-grid');
  scoreGrid.innerHTML = `
    <div class="score-item"><div class="s-val">${sb.wikipedia_score||0}</div><div class="s-lbl">WIKIPEDIA</div></div>
    <div class="score-item"><div class="s-val">${sb.rss_score||0}</div><div class="s-lbl">LIVE RSS</div></div>
    <div class="score-item"><div class="s-val">+${sb.rep_bonus||0}</div><div class="s-lbl">REPUTABLE</div></div>
    <div class="score-item"><div class="s-val">-${sb.keyword_penalty||0}</div><div class="s-lbl">PENALTY</div></div>
  `;

  // Evidence
  document.getElementById('evidence-text').textContent = (data.evidence || '').replace(/\*\*/g, '').replace(/📚|📡|⚠️/g, '').trim();

  // AI Summary
  const aiBox = document.getElementById('ai-summary-box');
  const aiText = document.getElementById('ai-summary-text');
  const transInfo = document.getElementById('translation-info');
  
  if (data.ai_summary) {
    aiBox.style.display = 'block';
    aiText.textContent = data.ai_summary;
    if (data.original_language && data.original_language !== 'en') {
      transInfo.style.display = 'block';
      transInfo.textContent = `(Original Language: ${data.original_language.toUpperCase()} | Analysis performed on English translation: "${data.translated_text}")`;
    } else {
      transInfo.style.display = 'none';
    }
  } else {
    aiBox.style.display = 'none';
  }

  // Sources
  const sources = data.top_sources || [];
  document.getElementById('src-count').textContent = sources.length;
  const sourcesList = document.getElementById('sources-list');
  sourcesList.innerHTML = '';
  sources.forEach(src => {
    const a = document.createElement('a');
    a.className = 'source-item';
    a.href = src.link || '#';
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.innerHTML = `
      <div class="source-badge">${src.reputable ? '✓' : '📰'}</div>
      <div class="source-content">
        <div class="source-title">${escHtml(src.title || '')}</div>
        <div class="source-meta">
          <span class="source-src">${escHtml(src.source || 'Source')}</span>
          ${src.reputable ? '<span class="source-rep">● VERIFIED</span>' : ''}
          <span class="news-ext">↗ open</span>
        </div>
      </div>`;
    sourcesList.appendChild(a);
  });

  // Regional map
  renderRegionalMap(data.hits_by_region || {});

  document.getElementById('sources-section').style.display = 'block';
}

function renderRegionalMap(hitsMap) {
  const regions = ['North America', 'Europe', 'Asia', 'Middle East', 'Africa', 'Australia'];
  const mapEl = document.getElementById('regional-map');
  const maxVal = Math.max(1, ...Object.values(hitsMap));

  mapEl.innerHTML = regions.map(r => {
    const count = hitsMap[r] || 0;
    return `<div class="region-cell ${count > 0 ? 'has-data' : ''}">
      <div class="region-name">${r}</div>
      <div class="region-count ${count === 0 ? 'zero' : ''}">${count}</div>
    </div>`;
  }).join('');

  const barsEl = document.getElementById('region-bars');
  const sorted = Object.entries(hitsMap).sort((a, b) => b[1] - a[1]);
  barsEl.innerHTML = sorted.map(([r, c]) => `
    <div class="rbar-row">
      <div class="rbar-label">${r}</div>
      <div class="rbar-track"><div class="rbar-fill" style="width:${(c/maxVal)*100}%"></div></div>
      <div class="rbar-count">${c}</div>
    </div>`).join('');
}

// ─── Simulator Bridge ───────────────────────────────────────────────────────
function sendToSimulator() {
  if (!lastFactCheckResult) return;
  simIsTrue = lastFactCheckResult.is_true_news === true;
  document.getElementById('sim-topic-label').textContent =
    `Simulating: "${lastFactCheckResult.claim?.substring(0, 80)}..." [${simIsTrue ? 'TRUE NEWS' : 'FAKE NEWS'}]`;
  showSection('simulator');
}

// ─── Export PDF ─────────────────────────────────────────────────────────────
async function exportPDF() {
  if (!lastFactCheckResult) { showToast('Run a fact-check first', 'error'); return; }
  showToast('Generating PDF report…');
  try {
    const res = await fetch('/api/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lastFactCheckResult)
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'rumor_analysis.pdf'; a.click();
    URL.revokeObjectURL(url);
    showToast('PDF downloaded!', 'success');
  } catch (e) {
    showToast('Export failed: ' + e.message, 'error');
  }
}

// ─── Network Simulator ──────────────────────────────────────────────────────
async function generateNetwork() {
  const n = parseInt(document.getElementById('n-nodes').value);
  const netType = document.getElementById('net-type').value;
  const btn = document.getElementById('gen-btn');
  btn.textContent = '⟳ GENERATING…'; btn.disabled = true;

  stopSimulation();
  resetPropChart();

  try {
    const res = await fetch('/api/network/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ n_nodes: n, net_type: netType })
    });
    networkData = await res.json();
    simStates = networkData.nodes.map(n => n.state);
    simStep = 0;

    document.getElementById('canvas-placeholder').style.display = 'none';
    renderNetwork();
    updateMetrics();
    document.getElementById('start-btn').disabled = false;
    showToast(`Network generated: ${n} nodes`, 'success');
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.textContent = '⟳ GENERATE NETWORK'; btn.disabled = false;
  }
}

function toggleSimulation() {
  if (simRunning) stopSimulation();
  else startSimulation();
}

function startSimulation() {
  if (!networkData) { showToast('Generate a network first', 'error'); return; }
  simRunning = true;
  document.getElementById('start-btn').textContent = '⏹ STOP SIMULATION';
  document.getElementById('start-btn').style.background = 'linear-gradient(135deg,#dc2626,#ef4444)';
  runSimStep();
}

function stopSimulation() {
  simRunning = false;
  clearTimeout(simTimer);
  document.getElementById('start-btn').textContent = '▶ START SIMULATION';
  document.getElementById('start-btn').style.background = '';
}

async function runSimStep() {
  if (!simRunning || !networkData) return;

  const beta = parseFloat(document.getElementById('beta').value);
  const gamma = parseFloat(document.getElementById('gamma').value);
  const betaTruth = parseFloat(document.getElementById('beta-truth').value);
  const strategy = document.getElementById('strategy').value;
  const interveneStep = parseInt(document.getElementById('intervene-step').value);
  const speed = parseInt(document.getElementById('sim-speed').value);

  try {
    const res = await fetch('/api/network/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        states: simStates,
        edges: networkData.edges,
        beta, gamma, beta_truth: betaTruth,
        step: simStep, strategy, intervene_step: interveneStep,
        is_true_news: simIsTrue
      })
    });
    const data = await res.json();
    simStates = data.states;
    simStep++;

    if (data.strategy_applied && strategy !== 'None') {
      showToast(`Strategy applied: ${strategy}`, 'success');
    }

    renderNetwork();
    updateMetrics(data.counts);
    updatePropChart(data.counts);

    // Stop if no infected left
    if (data.counts.infected === 0 && simStep > 3) {
      stopSimulation();
      showToast('Simulation complete – spread contained!', 'success');
      return;
    }

    const delay = Math.max(50, 1000 / speed);
    simTimer = setTimeout(runSimStep, delay);
  } catch (e) {
    stopSimulation();
    showToast('Simulation error: ' + e.message, 'error');
  }
}

// ─── Canvas Rendering ────────────────────────────────────────────────────────
const STATE_COLORS_FAKE = {
  0: '#475569',  // susceptible - slate
  1: '#ef4444',  // infected - red (rumor/fake)
  2: '#94a3b8',  // recovered - slate/gray
  3: '#3b82f6'   // immunized - blue
};

const STATE_COLORS_REAL = {
  0: '#475569',  // susceptible
  1: '#10b981',  // infected - green (real news spread)
  2: '#64748b',  // recovered
  3: '#3b82f6'   // immunized
};

function renderNetwork() {
  if (!networkData || !simStates) return;
  const canvas = document.getElementById('network-canvas');
  const parent = canvas.parentElement;
  canvas.width = parent.clientWidth;
  canvas.height = Math.max(450, parent.clientHeight);
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;

  ctx.clearRect(0, 0, W, H);

  // Scale positions from [-1,1] to canvas
  const pad = 40;
  const scaleX = x => (x + 1) / 2 * (W - pad*2) + pad;
  const scaleY = y => (y + 1) / 2 * (H - pad*2) + pad;

  const nodes = networkData.nodes;
  const edges = networkData.edges;

  // Draw edges
  ctx.strokeStyle = 'rgba(56,189,248,0.08)';
  ctx.lineWidth = 0.6;
  edges.forEach(e => {
    const n0 = nodes[e.source], n1 = nodes[e.target];
    if (!n0 || !n1) return;
    const s0 = simStates[e.source], s1 = simStates[e.target];
    if (s0 === 1 || s1 === 1) {
      ctx.strokeStyle = 'rgba(239,68,68,0.2)';
    } else {
      ctx.strokeStyle = 'rgba(56,189,248,0.06)';
    }
    ctx.beginPath();
    ctx.moveTo(scaleX(n0.x), scaleY(n0.y));
    ctx.lineTo(scaleX(n1.x), scaleY(n1.y));
    ctx.stroke();
  });

  // Draw nodes
  nodes.forEach((node, i) => {
    const state = simStates[i] ?? 0;
    const colors = simIsTrue ? STATE_COLORS_REAL : STATE_COLORS_FAKE;
    const color = colors[state];
    const cx = scaleX(node.x), cy = scaleY(node.y);
    const r = Math.min(5, 2 + (node.degree || 1) * 0.4);

    if (state === 1) {
      // Glow for infected
      ctx.beginPath();
      ctx.arc(cx, cy, r + 3, 0, Math.PI * 2);
      ctx.fillStyle = simIsTrue ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  });

  // Legend
  const legend = simIsTrue ? [
    { color: '#475569', label: 'Susceptible' },
    { color: '#10b981', label: 'Spreading Real News' },
    { color: '#64748b', label: 'Heard & Dismissed' },
    { color: '#3b82f6', label: 'Verified Sharing' }
  ] : [
    { color: '#475569', label: 'Susceptible' },
    { color: '#ef4444', label: 'Spreading Rumor' },
    { color: '#94a3b8', label: 'Heard & Ignored' },
    { color: '#3b82f6', label: 'Fact-Checked (Protected)' }
  ];
  ctx.font = '11px JetBrains Mono, monospace';
  legend.forEach((l, i) => {
    const lx = 16, ly = H - 16 - (legend.length - 1 - i) * 20;
    ctx.beginPath(); ctx.arc(lx, ly, 5, 0, Math.PI*2);
    ctx.fillStyle = l.color; ctx.fill();
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(l.label, lx + 12, ly + 4);
  });

  // Step counter
  ctx.font = 'bold 13px JetBrains Mono, monospace';
  ctx.fillStyle = '#38bdf8';
  ctx.fillText(`STEP: ${simStep}`, W - 90, 24);
}

function updateMetrics(counts) {
  if (!counts) {
    if (simStates) {
      counts = {
        susceptible: simStates.filter(s => s === 0).length,
        infected: simStates.filter(s => s === 1).length,
        recovered: simStates.filter(s => s === 2).length,
        immunized: simStates.filter(s => s === 3).length,
        step: simStep
      };
    } else return;
  }
  document.getElementById('m-step').textContent = counts.step ?? simStep;
  document.getElementById('m-inf').textContent = counts.infected ?? 0;
  document.getElementById('m-rec').textContent = counts.recovered ?? 0;
  document.getElementById('m-imm').textContent = counts.immunized ?? 0;
  document.getElementById('m-sus').textContent = counts.susceptible ?? 0;
}

// ─── Propagation Chart ───────────────────────────────────────────────────────
function initPropChart() {
  const canvas = document.getElementById('prop-chart');
  if (propChart) { propChart.destroy(); propChart = null; }

  propChart = {
    canvas, ctx: canvas.getContext('2d'),
    data: { S: [], I: [], R: [], M: [], T: [] }
  };
  resetPropChart();
}

function resetPropChart() {
  propHistory = { S: [], I: [], R: [], M: [], T: [] };
  if (propChart) drawPropChart();
}

function updatePropChart(counts) {
  propHistory.S.push(counts.susceptible);
  propHistory.I.push(counts.infected);
  propHistory.R.push(counts.recovered);
  propHistory.M.push(counts.immunized);
  propHistory.T.push(simStep);
  drawPropChart();
}

function drawPropChart() {
  const canvas = document.getElementById('prop-chart');
  canvas.width = canvas.parentElement.clientWidth - 32;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const series = simIsTrue ? [
    { data: propHistory.I, color: '#10b981', label: 'Spread' },
    { data: propHistory.M, color: '#3b82f6', label: 'Verified' }
  ] : [
    { data: propHistory.I, color: '#ef4444', label: 'Infected' },
    { data: propHistory.M, color: '#3b82f6', label: 'Protected' }
  ];

  const T = propHistory.T.length;
  if (T < 2) {
    ctx.fillStyle = '#334155';
    ctx.font = '12px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText('Start simulation to see propagation curves', W/2, H/2);
    return;
  }

  const maxVal = Math.max(1, ...propHistory.S, ...propHistory.I, ...propHistory.R, ...propHistory.M);
  const pad = { t: 20, r: 16, b: 30, l: 40 };
  const cW = W - pad.l - pad.r, cH = H - pad.t - pad.b;

  // Grid lines
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  [0.25, 0.5, 0.75, 1].forEach(f => {
    const y = pad.t + cH * (1 - f);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + cW, y); ctx.stroke();
    ctx.fillStyle = '#334155'; ctx.font = '9px JetBrains Mono, monospace'; ctx.textAlign = 'right';
    ctx.fillText(Math.round(maxVal * f), pad.l - 4, y + 3);
  });

  // X axis labels
  ctx.fillStyle = '#334155'; ctx.font = '9px JetBrains Mono, monospace'; ctx.textAlign = 'center';
  [0, Math.floor(T/4), Math.floor(T/2), Math.floor(3*T/4), T-1].forEach(ti => {
    const x = pad.l + (ti / (T - 1)) * cW;
    ctx.fillText(propHistory.T[ti] ?? ti, x, H - 6);
  });

  // Lines
  series.forEach(s => {
    if (s.data.length < 2) return;
    ctx.beginPath();
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    s.data.forEach((v, i) => {
      const x = pad.l + (i / (T - 1)) * cW;
      const y = pad.t + cH * (1 - v / maxVal);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });

  // Legend
  ctx.font = '10px JetBrains Mono, monospace'; ctx.textAlign = 'left';
  series.forEach((s, i) => {
    ctx.fillStyle = s.color;
    ctx.fillRect(pad.l + i * 100, 4, 12, 3);
    ctx.fillText(s.label, pad.l + i * 100 + 16, 10);
  });
}

// ─── News Feed ───────────────────────────────────────────────────────────────
async function loadNews() {
  const loading = document.getElementById('news-loading');
  loading.style.display = 'flex';
  document.getElementById('news-container').innerHTML = '';

  try {
    const [indiaRes, worldRes] = await Promise.all([
      fetch('/api/news/india'),
      fetch('/api/news/world')
    ]);
    newsCache.india = await indiaRes.json();
    newsCache.world = await worldRes.json();
    renderNews(currentNewsTab);
    showToast('News feed updated', 'success');
  } catch (e) {
    showToast('Failed to load news: ' + e.message, 'error');
  } finally {
    loading.style.display = 'none';
  }
}

function switchNewsTab(tab, btn) {
  currentNewsTab = tab;
  document.querySelectorAll('.news-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (newsCache[tab]) renderNews(tab);
  else loadNews();
}

function renderNews(tab) {
  const items = newsCache[tab] || [];
  const container = document.getElementById('news-container');
  const isIndia = tab === 'india';

  if (!items.length) {
    container.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:13px;text-align:center;padding:40px">No news loaded. Click REFRESH FEED.</div>';
    return;
  }

  container.innerHTML = items.map(item => `
    <a class="news-card" href="${escHtml(item.link)}" target="_blank" rel="noopener noreferrer">
      <div class="news-badge ${isIndia ? 'badge-india' : 'badge-world'}">${isIndia ? '🇮🇳 INDIA' : '🌐 WORLD'}</div>
      <div class="news-headline">${escHtml(item.title)}</div>
      <div class="news-meta">
        <span class="news-src">${escHtml(item.source || 'News')}</span>
        <span class="news-ext">↗ Read article</span>
      </div>
    </a>`).join('');
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Enter key for fact check ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('claim-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runFactCheck(); }
  });

  initPropChart();

  // Auto-load news on first visit to news tab
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.textContent.includes('NEWS') && !newsCache.india) loadNews();
    });
  });

  // Resize handler for canvas
  window.addEventListener('resize', () => {
    if (networkData) renderNetwork();
    drawPropChart();
  });
});
