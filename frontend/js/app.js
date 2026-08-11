// KrishiSetu — App JS v2 (multi-page)
const API = '';

// ── State ─────────────────────────────────────────────────────
let S = {
  farmer: null,
  language: 'English',
  isOnline: navigator.onLine,
  lastAdvisory: null,
  deferredInstallPrompt: null,
  currentCommodity: 'Rice',
  currentPage: 'home',
};

// ── Service Worker ────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

// ── Online / Offline ──────────────────────────────────────────
window.addEventListener('online', () => {
  S.isOnline = true;
  updateSyncDot();
  document.getElementById('offline-banner').classList.add('hidden');
  toast('✅ Back online — syncing…');
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((r) => r.sync?.register('sync-offline-queue'));
  }
});
window.addEventListener('offline', () => {
  S.isOnline = false;
  updateSyncDot();
  document.getElementById('offline-banner').classList.remove('hidden');
  toast('📵 Offline — data saved locally');
});

// ── Install Prompt ────────────────────────────────────────────
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  S.deferredInstallPrompt = e;
  document.getElementById('install-prompt').classList.remove('hidden');
});
function installPWA() {
  if (!S.deferredInstallPrompt) return;
  S.deferredInstallPrompt.prompt();
  S.deferredInstallPrompt.userChoice.then(() => {
    document.getElementById('install-prompt').classList.add('hidden');
    S.deferredInstallPrompt = null;
  });
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  S.language = localStorage.getItem('ks_lang') || 'English';
  const saved = localStorage.getItem('ks_farmer');
  if (saved) {
    S.farmer = JSON.parse(saved);
    showLoggedInState();
    await refreshHome();
  }
  updateSyncDot();
  updateLangUI();
  // Load market on first visit
  loadMarketPrices();
});

// ── Tab Navigation ────────────────────────────────────────────
function switchTab(tab) {
  // Hide all pages
  document.querySelectorAll('.page').forEach((p) => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));

  document.getElementById(`page-${tab}`).classList.add('active');
  document.getElementById(`tab-${tab}`)?.classList.add('active');
  S.currentPage = tab;

  // Lazy-load data when switching to advisory tab
  if (tab === 'advisory' && S.farmer && !S.lastAdvisory) {
    loadAdvisory();
  }
}

function goToRegister() {
  switchTab('profile');
}

// ── Show Logged In State ──────────────────────────────────────
function showLoggedInState() {
  // Home
  document.getElementById('onboard-view').classList.add('hidden');
  document.getElementById('home-view').classList.remove('hidden');

  // Profile
  document.getElementById('register-view').classList.add('hidden');
  document.getElementById('profile-view').classList.remove('hidden');

  // Fill profile info
  const f = S.farmer;
  document.getElementById('home-name').textContent = f.name || 'Farmer';
  document.getElementById('home-crop-tag').textContent = `🌾 ${(f.crop || '').toUpperCase()}`;
  document.getElementById('home-greeting').textContent = getGreeting();

  document.getElementById('pf-name').textContent = f.name || '—';
  document.getElementById('pf-crop-state').textContent = `${(f.crop || '').toUpperCase()} • ${f.state || ''}`;
  document.getElementById('pf-id').textContent = `ID: ${f.farmer_id || '—'}`;
  document.getElementById('pf-village').textContent = f.village_code || '—';
  document.getElementById('pf-state').textContent = f.state || '—';
  document.getElementById('pf-lang').textContent = S.language;
  document.getElementById('pf-date').textContent = f.registered_at
    ? new Date(f.registered_at).toLocaleDateString('en-IN')
    : new Date().toLocaleDateString('en-IN');

  // Advisory header
  document.getElementById('adv-crop-name').textContent = `${emojiForCrop(f.crop)} ${(f.crop || '').toUpperCase()}`;
  document.getElementById('adv-time').textContent = new Date().toLocaleDateString('en-IN', { dateStyle: 'long' });
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning,';
  if (h < 17) return 'Good afternoon,';
  return 'Good evening,';
}

function emojiForCrop(c) {
  const m = { rice: '🌾', wheat: '🌿', maize: '🌽', cotton: '🪴', mustard: '🟡', soybean: '🫘' };
  return m[(c || '').toLowerCase()] || '🌾';
}

// ── Farmer Registration ───────────────────────────────────────
async function submitFarmerForm(e) {
  e.preventDefault();
  const btn = document.getElementById('reg-btn');
  const btnText = document.getElementById('reg-btn-text');
  btnText.textContent = '⏳ Registering…';
  btn.disabled = true;

  const farmerData = {
    name: document.getElementById('fn-name').value,
    phone: document.getElementById('fn-phone').value,
    village_code: document.getElementById('fn-village').value,
    district: 'Kamrup',
    state: document.getElementById('fn-state').value,
    crop: document.getElementById('fn-crop').value,
    plot_area_acres: 2.0,
    language_preference: S.language,
    consent_given: document.getElementById('fn-consent').checked,
    consent_timestamp: new Date().toISOString(),
  };

  try {
    // DPDP consent
    await apiCall('/api/v1/compliance/consent/capture', 'POST', {
      farmer_id: `F_${Date.now()}`,
      phone: farmerData.phone,
      consent_method: 'app',
      data_uses: 'weather_advisory,mandi_prices,risk_alerts',
    });

    // AgriStack registration
    const reg = await apiCall('/api/v1/farmer/register', 'POST', farmerData);
    S.farmer = { ...reg, ...farmerData, registered_at: new Date().toISOString() };
    localStorage.setItem('ks_farmer', JSON.stringify(S.farmer));
    await saveFarmerLocally(S.farmer);

    toast('✅ Registered! Loading your advisory…');
    showLoggedInState();
    switchTab('home');
    await refreshHome();
    loadAdvisory();

  } catch {
    // Offline fallback
    const fid = `LOCAL_${Date.now()}`;
    S.farmer = { farmer_id: fid, ...farmerData, offline: true, registered_at: new Date().toISOString() };
    localStorage.setItem('ks_farmer', JSON.stringify(S.farmer));
    await saveFarmerLocally(S.farmer);
    await queueForSync('/api/v1/farmer/register', 'POST', farmerData);

    toast('📵 Saved offline — will sync when connected');
    showLoggedInState();
    switchTab('home');
    await refreshHome();
  }

  btn.disabled = false;
  btnText.textContent = '✅ Register & Get Advisory';
}

// ── Home / Advisory Data ──────────────────────────────────────
const DEMO_WEATHER = {
  precip_30d_mm: 55, precip_7d_mm: 12,
  avg_temp_c: 30, max_temp_c: 34,
  avg_humidity_pct: 72, consecutive_humid_days: 4,
  recent_rain_events: 2, lat: 26.14, lon: 91.74,
};

async function refreshHome() {
  const btn = document.getElementById('home-refresh-btn');
  if (btn) btn.textContent = '↻ Loading…';

  if (!S.farmer) return;

  try {
    const data = await loadAdvisoryData();
    if (data) renderHomeRisk(data);
  } catch { }

  if (btn) btn.textContent = '↻ Refresh';
  updateSyncDot();
}

async function loadAdvisory() {
  const btn = document.getElementById('adv-refresh-btn');
  if (btn) btn.textContent = '↻ …';

  // Show spinner
  document.getElementById('adv-text-body').innerHTML =
    '<div class="loading-row"><div class="spinner"></div>Generating your personalized advisory…</div>';
  document.getElementById('adv-badges').innerHTML = '<span class="advisory-badge">Loading…</span>';

  try {
    const data = await loadAdvisoryData();
    if (data) {
      S.lastAdvisory = data;
      renderAdvisoryPage(data);
      renderHomeRisk(data);
    }
  } catch {
    const cached = await dbGetAll('advisories');
    if (cached.length) {
      const last = cached[cached.length - 1];
      S.lastAdvisory = last;
      renderAdvisoryPage(last);
      toast('📵 Showing cached advisory');
    } else {
      document.getElementById('adv-text-body').textContent = '❌ Unable to load advisory. Check connection.';
    }
  }

  if (btn) btn.textContent = '↻ Refresh';
}

async function loadAdvisoryData() {
  const f = S.farmer;
  const payload = {
    farmer_id: f.farmer_id,
    village_code: f.village_code,
    crop: f.crop,
    language: S.language,
    state: f.state || 'Assam',
    ...DEMO_WEATHER,
  };

  const [data, labor] = await Promise.all([
    apiCall('/api/v1/advisory/generate', 'POST', payload),
    apiCall('/api/v1/cross-domain/labor-advisory', 'POST', {
      max_temp_c: DEMO_WEATHER.max_temp_c,
      drought_score: 55,
      humidity_pct: DEMO_WEATHER.avg_humidity_pct,
      crop: f.crop,
    }).catch(() => null),
  ]);

  data._labor = labor;
  await saveAdvisoryLocally(f.farmer_id, data);
  return data;
}

// ── Render Functions ──────────────────────────────────────────
function renderHomeRisk(data) {
  const d = data.risk?.drought;
  const p = data.risk?.pest;
  const s = data.sowing;
  const labor = data._labor;

  // Hero stats
  if (d) { el('home-drought-score').textContent = d.score; }
  if (p) { el('home-pest-score').textContent = p.score; }
  if (s) { el('home-sowing-rec').textContent = s.recommendation?.slice(0, 4); }

  // Risk tiles
  if (d) {
    el('rt-drought-score').textContent = d.score;
    el('rt-drought-level').textContent = d.level;
    applyLevelClass('rt-drought-level', d.level);
    el('drought-accent').className = `risk-tile-accent accent-${d.level.toLowerCase()}`;
  }
  if (p) {
    el('rt-pest-score').textContent = p.score;
    el('rt-pest-level').textContent = p.level;
    applyLevelClass('rt-pest-level', p.level);
    el('pest-accent').className = `risk-tile-accent accent-${p.level.toLowerCase()}`;
  }
  if (s) {
    el('rt-sow-rec').textContent = s.recommendation;
    el('rt-sow-season').textContent = s.current_season;
  }
  if (labor) {
    el('rt-labor-level').textContent = labor.heat_stress_level || '—';
    el('rt-labor-hours').textContent = (labor.safe_working_hours || '').split(' ').slice(0, 3).join(' ');
  }

  // Home alert strip
  const alertEl = el('home-alert-container');
  const composite = data.risk?.composite_level;
  if (composite === 'CRITICAL' || composite === 'HIGH') {
    alertEl.innerHTML = `
      <div class="alert-strip danger fade-in">
        <span class="alert-strip-icon">🚨</span>
        <div>
          <div class="alert-strip-title">Action Required — ${composite} Risk</div>
          <div class="alert-strip-body">Drought: ${d?.score}/100 | Pest: ${p?.score}/100. Go to Advisory tab for full details.</div>
        </div>
      </div>`;
  } else if (composite === 'MODERATE') {
    alertEl.innerHTML = `
      <div class="alert-strip warn fade-in">
        <span class="alert-strip-icon">⚠️</span>
        <div>
          <div class="alert-strip-title">Monitor Closely — Moderate Risk</div>
          <div class="alert-strip-body">Conditions are changing. Check your Advisory for specifics.</div>
        </div>
      </div>`;
  } else {
    alertEl.innerHTML = `
      <div class="alert-strip good fade-in">
        <span class="alert-strip-icon">✅</span>
        <div>
          <div class="alert-strip-title">Conditions Look Good</div>
          <div class="alert-strip-body">Low risk today. Continue regular monitoring.</div>
        </div>
      </div>`;
  }
}

function renderAdvisoryPage(data) {
  const d = data.risk?.drought;
  const p = data.risk?.pest;
  const s = data.sowing;
  const labor = data._labor;

  // Advisory text
  el('adv-text-body').textContent = data.advisory || 'Advisory not available.';
  if (data.cached) el('adv-cached-tag').classList.remove('hidden');
  else el('adv-cached-tag').classList.add('hidden');
  document.getElementById('tts-btn').disabled = false;

  // Badges
  if (d && p) {
    el('adv-badges').innerHTML = `
      <span class="advisory-badge">💧 Drought: ${d.score}/100</span>
      <span class="advisory-badge">🐛 Pest: ${p.score}/100</span>
      <span class="advisory-badge">🌐 ${S.language}</span>
    `;
  }

  // Risk detail cards
  if (d) {
    const lvl = d.level.toLowerCase();
    el('adv-drought-level').textContent = `${d.level} (${d.score}/100)`;
    applyLevelClass('adv-drought-level', d.level);
    el('adv-drought-bar').style.width = `${d.score}%`;
    el('adv-drought-bar').style.background = levelColor(d.level);
    el('adv-drought-circle').textContent = d.score;
    el('adv-drought-circle').className = `risk-score-circle circle-${lvl}`;
    el('adv-drought-hint').textContent = d.level === 'LOW' ? 'Irrigation not urgent' : 'Consider irrigation soon';
  }
  if (p) {
    const lvl = p.level.toLowerCase();
    el('adv-pest-level').textContent = `${p.level} (${p.score}/100)`;
    applyLevelClass('adv-pest-level', p.level);
    el('adv-pest-bar').style.width = `${p.score}%`;
    el('adv-pest-bar').style.background = levelColor(p.level);
    el('adv-pest-circle').textContent = p.score;
    el('adv-pest-circle').className = `risk-score-circle circle-${lvl}`;
    el('adv-pest-hint').textContent = p.likely_pests?.length
      ? `Watch for: ${p.likely_pests.slice(0, 2).join(', ')}`
      : 'No specific pests identified';
  }
  if (s) {
    const colorMap = { OPTIMAL: '#2D5A45', ACCEPTABLE: '#B5700D', WAIT: '#C2410C', NOT_RECOMMENDED: '#7F1D1D' };
    const bgMap = { OPTIMAL: '#EBF5EF', ACCEPTABLE: '#FBF3DC', WAIT: '#FFF0E8', NOT_RECOMMENDED: '#FFF5F5' };
    el('adv-sow-rec').textContent = s.recommendation;
    el('adv-sow-rec').style.color = colorMap[s.recommendation] || '#1C1917';
    el('sow-icon-wrap').style.background = bgMap[s.recommendation] || '#EBF5EF';
    el('adv-sow-detail').textContent = `${s.current_season} season • Month ${new Date().getMonth() + 1}`;
  }

  // Labor advisory
  if (labor) {
    el('labor-body-text').textContent = labor.advisory + (labor.drought_modifier ? ' ' + labor.drought_modifier : '');
    el('labor-safe-hours-tag').textContent = '⏰ ' + (labor.safe_working_hours || '—');
    // Color the card by stress level
    const labCard = el('labor-advisory-card');
    const stressColors = { SAFE: ['#F0FDF4','#BBF7D0'], CAUTION: ['#FBF3DC','#F0D08A'], WARNING: ['#FFF0E8','#FDBA74'], DANGER: ['#FFF5F5','#FECACA'], EXTREME: ['#FFF5F5','#FECACA'] };
    const [bg, border] = stressColors[labor.heat_stress_level] || stressColors.CAUTION;
    labCard.style.background = bg;
    labCard.style.borderColor = border;
  }
}

// ── Market Page ───────────────────────────────────────────────
async function loadMarketPrices() {
  const state = document.getElementById('mkt-state-select')?.value || 'Assam';
  el('mandi-list').innerHTML = '<div class="empty-state"><div class="spinner" style="margin:0 auto 12px;"></div><div class="empty-title">Loading…</div></div>';

  try {
    const data = await apiCall(`/api/v1/prices/mandi?commodity=${S.currentCommodity}&state=${encodeURIComponent(state)}&limit=10`);

    // Hero price
    const first = data.prices?.[0];
    el('mkt-commodity').textContent = S.currentCommodity;
    el('mkt-price').textContent = first ? `₹${first.Modal_x0020_Price || first.modal_price || '—'}` : '₹—';

    // Trend
    const trend = computeTrendFromPrices(data.prices || []);
    const trendMap = { rising: ['📈 Rising', '#2D5A45'], falling: ['📉 Falling', '#B45309'], stable: ['📊 Stable', '#78716C'] };
    const [tLabel, tColor] = trendMap[trend] || trendMap.stable;
    el('mkt-trend-label').textContent = tLabel;
    el('mkt-trend').style.color = tColor;
    el('mkt-trend').style.borderColor = tColor;
    el('mkt-trend').style.background = 'rgba(255,255,255,0.1)';

    // List
    if (!data.prices?.length) {
      el('mandi-list').innerHTML = '<div class="empty-state"><div class="empty-icon">💰</div><div class="empty-title">No data for this selection</div></div>';
      return;
    }
    el('mandi-list').innerHTML = data.prices.slice(0, 8).map((p) => `
      <div class="mandi-item fade-in">
        <div>
          <div class="mandi-market-name">🏪 ${p.Market || p.market || 'Local Market'}</div>
          <div class="mandi-date">${p.Arrival_Date || p.arrival_date || '—'} · ${p.State || state}</div>
        </div>
        <div class="mandi-price-col">
          <div class="mandi-modal-price">₹${p.Modal_x0020_Price || p.modal_price || '—'}</div>
          <div class="mandi-range">Min ₹${p.Min_x0020_Price || '—'} · Max ₹${p.Max_x0020_Price || '—'}</div>
        </div>
      </div>
    `).join('');
  } catch {
    // Mock fallback
    el('mkt-price').textContent = '₹1,520';
    el('mkt-trend-label').textContent = '📈 Rising (offline)';
    el('mandi-list').innerHTML = [
      { market: 'Guwahati', modal: '1,520', min: '1,380', max: '1,700', date: '11/08/2026' },
      { market: 'Kamrup', modal: '1,480', min: '1,320', max: '1,650', date: '11/08/2026' },
    ].map((p) => `
      <div class="mandi-item fade-in">
        <div>
          <div class="mandi-market-name">🏪 ${p.market}</div>
          <div class="mandi-date">${p.date} · Assam</div>
        </div>
        <div class="mandi-price-col">
          <div class="mandi-modal-price">₹${p.modal}</div>
          <div class="mandi-range">Min ₹${p.min} · Max ₹${p.max}</div>
        </div>
      </div>
    `).join('');
    toast('📵 Showing cached/mock prices');
  }
}

function selectCommodity(c, chipEl) {
  S.currentCommodity = c;
  document.querySelectorAll('.filter-chip').forEach((ch) => ch.classList.remove('active'));
  chipEl.classList.add('active');
  loadMarketPrices();
}

function computeTrendFromPrices(prices) {
  if (prices.length < 3) return 'stable';
  const vals = prices.map((p) => parseFloat(p.Modal_x0020_Price || p.modal_price || 0)).filter((v) => v > 0);
  if (vals.length < 3) return 'stable';
  const mid = Math.floor(vals.length / 2);
  const first = vals.slice(0, mid).reduce((a, b) => a + b, 0) / mid;
  const last = vals.slice(mid).reduce((a, b) => a + b, 0) / (vals.length - mid);
  if (last > first * 1.025) return 'rising';
  if (last < first * 0.975) return 'falling';
  return 'stable';
}

// ── Insurance ─────────────────────────────────────────────────
async function logInsuranceEvent() {
  if (!S.farmer || !S.lastAdvisory) { toast('ℹ️ Load advisory first'); return; }
  const d = S.lastAdvisory;
  try {
    const r = await apiCall('/api/v1/cross-domain/insurance-log', 'POST', {
      farmer_id: S.farmer.farmer_id,
      event_type: 'pest_spray',
      crop: S.farmer.crop,
      drought_score: d.risk?.drought?.score,
      pest_score: d.risk?.pest?.score,
      pest_detected: d.risk?.pest?.likely_pests?.join(', '),
      advisory_text: d.advisory?.slice(0, 200),
    });
    toast(`🛡️ Logged! Evidence ID: #${r.event_id}`);
    await dbAdd('insuranceLog', { ...r, timestamp: new Date().toISOString() });
  } catch {
    await dbAdd('insuranceLog', { event_type: 'pest_spray', crop: S.farmer.crop, timestamp: new Date().toISOString(), offline: true });
    toast('📵 Logged offline — will sync');
  }
}

async function loadInsuranceTrail() {
  const list = el('insurance-trail-list');
  if (!S.farmer) return;
  try {
    const data = await apiCall(`/api/v1/cross-domain/insurance-trail/${S.farmer.farmer_id}`);
    if (!data.events?.length) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">🛡️</div><div class="empty-title">No events yet</div><div class="empty-sub">Use "Log Evidence" on Advisory page</div></div>';
      return;
    }
    list.innerHTML = data.events.slice(0, 6).map((ev) => `
      <div class="insurance-item fade-in">
        <div class="insurance-item-id">Evidence #${ev.id}</div>
        <div class="insurance-item-type">${ev.event_type?.replace(/_/g, ' ')} — ${ev.crop}</div>
        <div class="insurance-item-date">${new Date(ev.timestamp).toLocaleString('en-IN')}</div>
      </div>
    `).join('');
  } catch {
    const local = await dbGetAll('insuranceLog');
    list.innerHTML = local.length
      ? local.slice(0, 4).map((ev) => `
          <div class="insurance-item fade-in">
            <div class="insurance-item-id">${ev.offline ? 'Offline Event' : `#${ev.id || '—'}`}</div>
            <div class="insurance-item-type">${ev.event_type || 'logged'} — ${ev.crop || ''}</div>
            <div class="insurance-item-date">${ev.timestamp || ''}</div>
          </div>`).join('')
      : '<div class="empty-state"><div class="empty-icon">🛡️</div><div class="empty-title">No events yet</div></div>';
  }
}

// ── Audio ─────────────────────────────────────────────────────
async function playAudio() {
  if (!S.lastAdvisory) return;
  toast('🔊 Generating audio…');
  try {
    const resp = await fetch('/api/v1/advisory/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: S.lastAdvisory.advisory?.slice(0, 400), language: S.language }),
    });
    if (resp.ok) {
      const url = URL.createObjectURL(await resp.blob());
      new Audio(url).play();
    } else {
      toast('🔊 Add ELEVENLABS_API_KEY to enable voice');
    }
  } catch { toast('📵 Audio unavailable offline'); }
}

// ── Language ──────────────────────────────────────────────────
function openLangSheet() { el('lang-sheet').classList.remove('hidden'); }
function closeLangSheet(e) { if (e.target === el('lang-sheet')) el('lang-sheet').classList.add('hidden'); }
function setLanguage(lang) {
  S.language = lang;
  localStorage.setItem('ks_lang', lang);
  el('lang-sheet').classList.add('hidden');
  updateLangUI();
  if (S.farmer && S.currentPage === 'advisory') loadAdvisory();
  toast(`🌐 ${lang}`);
}
function updateLangUI() {
  const shortLang = S.language.slice(0, 2).toUpperCase();
  if (el('adv-lang-label')) el('adv-lang-label').textContent = shortLang;
  if (el('pf-lang')) el('pf-lang').textContent = S.language;
  // Highlight selected in grid
  document.querySelectorAll('.lang-item').forEach((btn) => {
    btn.classList.toggle('selected', btn.textContent.trim().includes(S.language));
  });
}

// ── Account ───────────────────────────────────────────────────
async function requestErasure() {
  if (!S.farmer) return;
  if (!confirm('Request data erasure? Your records will be deleted within 30 days.')) return;
  try {
    await apiCall('/api/v1/compliance/erasure/request', 'POST', { farmer_id: S.farmer.farmer_id });
    toast('✅ Erasure requested — data deleted within 30 days');
  } catch { toast('📵 Request queued for when online'); }
}
function signOut() {
  if (!confirm('Sign out? Your local data will remain until you clear browser storage.')) return;
  localStorage.removeItem('ks_farmer');
  S.farmer = null;
  S.lastAdvisory = null;
  document.getElementById('onboard-view').classList.remove('hidden');
  document.getElementById('home-view').classList.add('hidden');
  document.getElementById('register-view').classList.remove('hidden');
  document.getElementById('profile-view').classList.add('hidden');
  switchTab('home');
  toast('Signed out');
}

// ── Sync Status ───────────────────────────────────────────────
async function updateSyncDot() {
  const dot = el('sync-dot');
  const text = el('sync-text');
  if (!dot) return;
  dot.className = `sync-dot ${S.isOnline ? 'on' : 'off'}`;
  text.textContent = S.isOnline ? 'Connected' : 'Offline';
  const count = await getPendingSyncCount().catch(() => 0);
  const pending = el('sync-pending');
  if (pending) pending.textContent = count > 0 ? `• ${count} pending` : '';
}

// ── Helpers ───────────────────────────────────────────────────
function el(id) { return document.getElementById(id); }

function levelColor(level) {
  return { LOW: '#4A8C6A', MODERATE: '#D4971A', HIGH: '#EA580C', CRITICAL: '#DC2626' }[level] || '#4A8C6A';
}

function applyLevelClass(id, level) {
  const el2 = el(id);
  if (!el2) return;
  el2.className = `risk-detail-level level-${level.toLowerCase()}`;
}

async function apiCall(endpoint, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(`${API}${endpoint}`, opts);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

function toast(msg, ms = 2800) {
  const t = el('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add('hidden'), ms);
}
