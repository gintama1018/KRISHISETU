// KrishiSetu — Officer Dashboard JS v3
// Matches dashboard.html v3 element IDs and warm earthy styling

const VILLAGES = [
  { code: 'ASM-KAM-001', name: 'Hajo Village',    lat: 26.23, lon: 91.53, farmers: 42, crop: 'rice',    drought: 78, pest: 62 },
  { code: 'ASM-KAM-002', name: 'Boko Village',     lat: 26.01, lon: 91.06, farmers: 28, crop: 'maize',   drought: 45, pest: 38 },
  { code: 'ASM-KAM-003', name: 'Chandrapur',       lat: 26.41, lon: 91.78, farmers: 63, crop: 'rice',    drought: 88, pest: 71 },
  { code: 'ASM-KAM-004', name: 'Rani Township',    lat: 26.12, lon: 91.45, farmers: 17, crop: 'mustard', drought: 22, pest: 18 },
  { code: 'ASM-NAL-001', name: 'Nalbari Central',  lat: 26.49, lon: 91.43, farmers: 55, crop: 'wheat',   drought: 55, pest: 48 },
  { code: 'ASM-NAL-002', name: 'Tihu',             lat: 26.35, lon: 91.64, farmers: 33, crop: 'rice',    drought: 35, pest: 82 },
  { code: 'ASM-NAL-003', name: 'Mukalmua',         lat: 26.51, lon: 91.72, farmers: 21, crop: 'rice',    drought: 68, pest: 55 },
];

const LEVEL_COLORS = {
  CRITICAL: '#B23B3B',
  HIGH:     '#EA580C',
  MODERATE: '#C17F24',
  LOW:      '#357352',
};

function getLevel(drought, pest) {
  const m = Math.max(drought, pest);
  if (m >= 70) return 'CRITICAL';
  if (m >= 45) return 'HIGH';
  if (m >= 20) return 'MODERATE';
  return 'LOW';
}

let map, riskChart, priceChart;

// ── Map Init ──────────────────────────────────────────────────
function initMap() {
  if (map) return;
  const mapEl = document.getElementById('officer-map');
  if (!mapEl) return;

  map = L.map('officer-map', { center: [26.2, 91.5], zoom: 9 });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
    maxZoom: 17,
  }).addTo(map);

  VILLAGES.forEach((v) => {
    const lv = getLevel(v.drought, v.pest);
    const color = LEVEL_COLORS[lv];
    const radius = 10 + v.farmers / 10;

    const circle = L.circleMarker([v.lat, v.lon], {
      radius,
      fillColor: color,
      color: '#FFFFFF',
      weight: 2,
      opacity: 0.9,
      fillOpacity: 0.75,
    }).addTo(map);

    circle.bindPopup(`
      <div style="font-family:'Inter',sans-serif;padding:8px;min-width:180px;">
        <div style="font-weight:800;font-size:0.92rem;color:#1A1714;margin-bottom:4px;">📍 ${v.name}</div>
        <div style="font-size:0.72rem;color:#6B6560;margin-bottom:8px;">${v.code}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.8rem;">
          <div><span style="color:#6B6560;">Farmers</span><br><strong>${v.farmers}</strong></div>
          <div><span style="color:#6B6560;">Crop</span><br><strong>${v.crop}</strong></div>
          <div><span style="color:#6B6560;">Drought</span><br><strong style="color:${LEVEL_COLORS[getLevel(v.drought,0)]}">${v.drought}/100</strong></div>
          <div><span style="color:#6B6560;">Pest</span><br><strong style="color:${LEVEL_COLORS[getLevel(0,v.pest)]}">${v.pest}/100</strong></div>
        </div>
        <div style="margin-top:8px;padding:4px 8px;border-radius:4px;background:${color}18;color:${color};font-weight:700;font-size:0.75rem;border:1px solid ${color}35;">
          ${lv} RISK
        </div>
      </div>
    `);
    circle.bindTooltip(v.name, { permanent: false, direction: 'top' });
  });
}

// ── Stats ─────────────────────────────────────────────────────
function updateStats() {
  const totalFarmers = VILLAGES.reduce((s, v) => s + v.farmers, 0);
  const criticals = VILLAGES.filter((v) => getLevel(v.drought, v.pest) === 'CRITICAL').length;
  const highs = VILLAGES.filter((v) => getLevel(v.drought, v.pest) === 'HIGH').length;
  const avgDrought = Math.round(VILLAGES.reduce((s, v) => s + v.drought, 0) / VILLAGES.length);

  g('st-farmers', totalFarmers);
  g('st-critical', criticals);
  g('st-high', highs);
  g('st-drought', avgDrought);
  g('st-advisories', Math.floor(totalFarmers * 0.72));
  g('st-villages', VILLAGES.length);
  g('df-updated', `Last updated: ${new Date().toLocaleTimeString('en-IN')}`);
}

// ── Alert List ────────────────────────────────────────────────
function renderAlerts() {
  const alerts = VILLAGES
    .map((v) => ({ ...v, lv: getLevel(v.drought, v.pest) }))
    .filter((v) => v.lv !== 'LOW')
    .sort((a, b) => ['CRITICAL', 'HIGH', 'MODERATE'].indexOf(a.lv) - ['CRITICAL', 'HIGH', 'MODERATE'].indexOf(b.lv));

  const list = document.getElementById('alert-list');
  if (!list) return;

  if (!alerts.length) {
    list.innerHTML = `<div style="color:var(--forest-700);text-align:center;padding:40px;font-size:0.85rem;">✅ No active alerts</div>`;
    return;
  }

  list.innerHTML = alerts.map((v) => `
    <div class="alert-item ai-${v.lv.toLowerCase()}">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span class="ai-village">${v.name}</span>
        <span class="pill p-${v.lv.toLowerCase()}">${v.lv}</span>
      </div>
      <div class="ai-detail">${v.farmers} farmers · ${v.crop} · Drought ${v.drought} · Pest ${v.pest}</div>
      <div class="ai-btns">
        <button class="ai-btn" onclick="sendVillageAlert('${v.name}')">📱 Broadcast Alert</button>
      </div>
    </div>
  `).join('');
}

// ── Village Table ─────────────────────────────────────────────
function renderTable() {
  const tbody = document.getElementById('vt-body');
  if (!tbody) return;

  tbody.innerHTML = VILLAGES.map((v) => {
    const lv = getLevel(v.drought, v.pest);
    const dLv = getLevel(v.drought, 0);
    const pLv = getLevel(0, v.pest);
    return `<tr>
      <td>
        <span class="vt-name">${v.name}</span>
        <span class="vt-code">${v.code}</span>
      </td>
      <td>${v.farmers}</td>
      <td>${v.crop}</td>
      <td><span class="pill p-${dLv.toLowerCase()}">${v.drought}/100</span></td>
      <td><span class="pill p-${pLv.toLowerCase()}">${v.pest}/100</span></td>
      <td><span class="pill p-${lv.toLowerCase()}">${lv}</span></td>
      <td>
        <button class="ai-btn" style="padding:4px 10px;font-size:0.72rem;" onclick="sendVillageAlert('${v.name}')">📱 Alert</button>
      </td>
    </tr>`;
  }).join('');
}

// ── Charts ────────────────────────────────────────────────────
function initCharts() {
  const chartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#6B6560', font: { family: 'Inter', size: 11 }, boxWidth: 12 } } },
    scales: {
      x: { grid: { color: 'rgba(26,23,20,0.04)' }, ticks: { color: '#A8A49E', font: { family: 'Inter', size: 11 } } },
      y: { grid: { color: 'rgba(26,23,20,0.04)' }, ticks: { color: '#A8A49E', font: { family: 'Inter', size: 11 } } },
    },
  };

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Today'];

  const rcCanvas = document.getElementById('risk-chart');
  if (rcCanvas) {
    if (riskChart) riskChart.destroy();
    riskChart = new Chart(rcCanvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: days,
        datasets: [
          {
            label: '💧 Drought Score',
            data: [52, 58, 65, 62, 70, 74, 78],
            borderColor: '#285F42',
            backgroundColor: 'rgba(40,95,66,0.06)',
            borderWidth: 2.5,
            tension: 0.4,
            fill: true,
            pointBackgroundColor: '#285F42',
          },
          {
            label: '🐛 Pest Score',
            data: [35, 40, 45, 50, 55, 62, 65],
            borderColor: '#C17F24',
            backgroundColor: 'rgba(193,127,36,0.06)',
            borderWidth: 2.5,
            tension: 0.4,
            fill: true,
            pointBackgroundColor: '#C17F24',
          },
        ],
      },
      options: { ...chartOpts, scales: { ...chartOpts.scales, y: { ...chartOpts.scales.y, min: 0, max: 100 } } },
    });
  }

  const pcCanvas = document.getElementById('price-chart');
  if (pcCanvas) {
    if (priceChart) priceChart.destroy();
    priceChart = new Chart(pcCanvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: days,
        datasets: [{
          label: '₹/quintal · Rice (Assam)',
          data: [1380, 1420, 1390, 1450, 1485, 1510, 1520],
          backgroundColor: 'rgba(40,95,66,0.2)',
          borderColor: '#285F42',
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: { ...chartOpts, scales: { ...chartOpts.scales, y: { ...chartOpts.scales.y, ticks: { ...chartOpts.scales.y.ticks, callback: (v) => '₹' + v } } } },
    });
  }
}

// ── Labor Advisory Summary ────────────────────────────────────
async function loadLaborSummary() {
  try {
    const r = await fetch('/api/v1/cross-domain/labor-advisory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_temp_c: 34, drought_score: 65, humidity_pct: 72, crop: 'rice' }),
    });
    const d = await r.json();
    const icons = { SAFE: '✅', CAUTION: '⚠️', WARNING: '🟠', DANGER: '🔴', EXTREME: '🚫' };

    g('l-icon', icons[d.heat_stress_level] || '⚠️');
    g('l-level', d.heat_stress_level);
    g('l-hours', d.safe_working_hours);
    g('l-detail', d.advisory + (d.drought_modifier ? ' ' + d.drought_modifier : ''));
  } catch {
    g('l-icon', '⚠️');
    g('l-level', 'WARNING');
    g('l-hours', 'Morning (6–9 AM) only');
    g('l-detail', 'High temperature forecast. Restrict field activities to early morning hours to prevent heat exhaustion.');
  }
}

// ── Broadcast Alert Toast ─────────────────────────────────────
function sendVillageAlert(name) {
  showToast(`📱 Broadcast alert sent to all farmers in ${name}!`);
}

function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.add('hidden'), 3000);
}

function g(id, val) {
  const e = document.getElementById(id);
  if (e) e.textContent = val;
}

function updateOnline() {
  const dot = document.getElementById('live-dot');
  const label = document.getElementById('live-label');
  if (navigator.onLine) {
    if (dot) dot.style.background = '#5BC280';
    if (label) label.textContent = 'Live';
  } else {
    if (dot) dot.style.background = '#B23B3B';
    if (label) label.textContent = 'Offline';
  }
}

// ── Main Load ─────────────────────────────────────────────────
async function loadAll() {
  updateStats();
  renderAlerts();
  renderTable();
  await loadLaborSummary();
}

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initCharts();
  loadAll();
  updateOnline();
  window.addEventListener('online', updateOnline);
  window.addEventListener('offline', updateOnline);
  setInterval(loadAll, 60000);
});
