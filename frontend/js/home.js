// home.js — Home page logic with userflow guard & real offline alert dispatching

const DEMO = {
  precip_30d_mm: 55, precip_7d_mm: 12,
  avg_temp_c: 30, max_temp_c: 34,
  avg_humidity_pct: 72, consecutive_humid_days: 4,
  recent_rain_events: 2, lat: 26.14, lon: 91.74,
};

document.addEventListener('DOMContentLoaded', () => {
  // USERFLOW GUARD: If not registered, redirect to onboarding / register
  const farmer = checkUserflow(true);
  if (!farmer) return;

  // Set greeting
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning,' : hour < 17 ? 'Good afternoon,' : 'Good evening,';
  g('topbar-greeting', greeting);
  g('h-eyebrow', greeting);
  g('h-name', farmer.name || 'Farmer');
  g('h-crop-tag', `${cropEmoji(farmer.crop)} ${(farmer.crop || '').toUpperCase()}`);

  updateSyncStatus();
  refreshHomeRisk();
});

function cropEmoji(c) {
  return { rice: '🌾', wheat: '🌿', maize: '🌽', cotton: '🪴', mustard: '🟡', soybean: '🫘' }[(c || '').toLowerCase()] || '🌾';
}

async function refreshHomeRisk() {
  const farmer = getFarmer();
  if (!farmer) return;

  const btn = document.getElementById('refresh-btn');
  if (btn) { btn.textContent = '↻ …'; btn.disabled = true; }

  try {
    const [adv, labor] = await Promise.all([
      apiCall('/api/v1/advisory/generate', 'POST', {
        farmer_id: farmer.farmer_id,
        village_code: farmer.village_code,
        crop: farmer.crop,
        language: getLang(),
        state: farmer.state || 'Assam',
        ...DEMO,
      }),
      apiCall('/api/v1/cross-domain/labor-advisory', 'POST', {
        max_temp_c: DEMO.max_temp_c,
        drought_score: 55,
        humidity_pct: DEMO.avg_humidity_pct,
        crop: farmer.crop,
      }).catch(() => null),
    ]);

    renderTiles(adv, labor);
    renderPreview(adv);
    renderHeroStats(adv);
    renderAlert(adv);

    // REAL OFFLINE ALERT CHECK: If critical risk, send native push notification
    if (adv.risk?.composite_level === 'CRITICAL' || adv.risk?.composite_level === 'HIGH') {
      triggerOfflineAlert(
        `🚨 Alert: ${adv.risk.composite_level} Risk for ${farmer.crop.toUpperCase()}`,
        `Drought score: ${adv.risk?.drought?.score}/100, Pest score: ${adv.risk?.pest?.score}/100. Open advisory for action plan.`
      );
    }

    if (typeof saveAdvisoryLocally === 'function') {
      await saveAdvisoryLocally(farmer.farmer_id, { ...adv, _labor: labor });
    }
  } catch (err) {
    // Offline fallback from IndexedDB
    try {
      const cached = await dbGetAll('advisories');
      if (cached.length) {
        const last = cached[cached.length - 1];
        renderTiles(last, last._labor);
        renderPreview(last);
        renderHeroStats(last);
        renderAlert(last);
        toast('📵 Loaded offline cached advisory');
      }
    } catch {}
  }

  if (btn) { btn.textContent = '↻ Refresh'; btn.disabled = false; }
  updateSyncStatus();
}

function renderHeroStats(adv) {
  const d = adv.risk?.drought, p = adv.risk?.pest, s = adv.sowing;
  if (d) g('hs-drought', d.score);
  if (p) g('hs-pest', p.score);
  if (s) g('hs-sow', (s.recommendation || '—').slice(0, 4));
}

function renderTiles(adv, labor) {
  const d = adv.risk?.drought, p = adv.risk?.pest, s = adv.sowing;
  if (d) setTile('tile-drought', 'rt-d-score', 'rt-d-bar', d.score, d.level);
  if (p) setTile('tile-pest', 'rt-p-score', 'rt-p-bar', p.score, p.level);

  if (s) {
    const lvlMap = { OPTIMAL: 'low', ACCEPTABLE: 'moderate', WAIT: 'high', NOT_RECOMMENDED: 'critical' };
    const scoreMap = { OPTIMAL: 90, ACCEPTABLE: 60, WAIT: 30, NOT_RECOMMENDED: 10 };
    const lvl = lvlMap[s.recommendation] || 'low';
    const tile = document.getElementById('tile-sow');
    if (tile) tile.className = `risk-tile lvl-${lvl}`;
    g('rt-s-rec', s.recommendation);
    g('rt-s-badge', s.recommendation?.slice(0, 4));
    const bar = document.getElementById('rt-s-bar');
    if (bar) bar.style.width = scoreMap[s.recommendation] + '%';
  }

  if (labor) {
    const stressMap = { SAFE: 'low', CAUTION: 'moderate', WARNING: 'high', DANGER: 'critical', EXTREME: 'critical' };
    const scoreMap2 = { SAFE: 10, CAUTION: 35, WARNING: 60, DANGER: 80, EXTREME: 100 };
    const lvl = stressMap[labor.heat_stress_level] || 'moderate';
    const tile = document.getElementById('tile-labor');
    if (tile) tile.className = `risk-tile lvl-${lvl}`;
    g('rt-l-level', labor.heat_stress_level || '—');
    g('rt-l-badge', labor.heat_stress_level || '—');
    const bar = document.getElementById('rt-l-bar');
    if (bar) bar.style.width = (scoreMap2[labor.heat_stress_level] || 40) + '%';
  }
}

function setTile(tileId, scoreId, barId, score, level) {
  const lvl = level.toLowerCase();
  const tile = document.getElementById(tileId);
  if (tile) {
    tile.className = `risk-tile lvl-${lvl}`;
    const badge = tile.querySelector('.rt-badge');
    if (badge) badge.textContent = level;
  }
  g(scoreId, score);
  const bar = document.getElementById(barId);
  if (bar) bar.style.width = Math.min(100, score) + '%';
}

function renderPreview(adv) {
  const card = document.getElementById('adv-preview-card');
  if (!card) return;
  const text = adv.advisory || 'Advisory not available.';
  card.innerHTML = `
    <p style="font-size:.88rem;color:var(--ink-700);line-height:1.8;">${text.slice(0, 220)}…</p>
    <a href="/advisory.html" style="display:inline-block;margin-top:12px;font-size:.8rem;font-weight:700;color:var(--forest-700);text-decoration:none">Read full advisory →</a>
  `;
}

function renderAlert(adv) {
  const el = document.getElementById('home-alert');
  if (!el) return;
  const composite = adv.risk?.composite_level || 'LOW';
  if (composite === 'CRITICAL' || composite === 'HIGH') {
    el.innerHTML = `
      <div class="notice notice-danger fade">
        <span class="notice-icon">🚨</span>
        <div>
          <div class="notice-title">Action Required — ${composite} Risk</div>
          <div class="notice-body">Drought: ${adv.risk?.drought?.score}/100 · Pest: ${adv.risk?.pest?.score}/100. <a href="/advisory.html" style="color:var(--sienna-700);font-weight:700">View advisory →</a></div>
        </div>
      </div>`;
  } else if (composite === 'MODERATE') {
    el.innerHTML = `
      <div class="notice notice-warn fade">
        <span class="notice-icon">⚠️</span>
        <div>
          <div class="notice-title">Monitor Closely — Moderate Risk</div>
          <div class="notice-body">Conditions are changing. <a href="/advisory.html" style="color:var(--amber-700);font-weight:700">Check advisory →</a></div>
        </div>
      </div>`;
  } else {
    el.innerHTML = `
      <div class="notice notice-good fade">
        <span class="notice-icon">✅</span>
        <div>
          <div class="notice-title">Conditions Look Good</div>
          <div class="notice-body">Low risk today. Continue regular farm activities.</div>
        </div>
      </div>`;
  }
}

function updateSyncStatus() {
  const dot = document.getElementById('s-dot');
  const txt = document.getElementById('s-text');
  if (dot) dot.className = 's-dot ' + (navigator.onLine ? 's-on' : 's-off');
  if (txt) txt.textContent = navigator.onLine ? 'Connected' : 'Offline';
}

function g(id, val) {
  const e = document.getElementById(id);
  if (e) e.textContent = val;
}
