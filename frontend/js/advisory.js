// advisory.js — Advisory page logic
const DEMO={precip_30d_mm:55,precip_7d_mm:12,avg_temp_c:30,max_temp_c:34,avg_humidity_pct:72,consecutive_humid_days:4,recent_rain_events:2,lat:26.14,lon:91.74};
let lastAdvisory=null;

document.addEventListener('DOMContentLoaded', () => {
  const f = checkUserflow(true);
  if (!f) return;
  const lang = getLang();
  document.getElementById('adv-lang-name').textContent = lang;
  document.getElementById('adv-lang-badge').textContent = lang.slice(0, 2).toUpperCase();
  document.getElementById('adv-crop').textContent = cropEmoji(f.crop) + ' ' + (f.crop || '').toUpperCase();
  document.getElementById('adv-date').textContent = new Date().toLocaleDateString('en-IN', { dateStyle: 'long' });
  loadAdvisory();
});

function cropEmoji(c){ return {rice:'🌾',wheat:'🌿',maize:'🌽',cotton:'🪴',mustard:'🟡',soybean:'🫘'}[c]||'🌾'; }

async function loadAdvisory(){
  const f=getFarmer(); if(!f) return;
  const btn=document.getElementById('adv-refresh-btn');
  if(btn){ btn.textContent='↻ …'; btn.disabled=true; }
  document.getElementById('adv-body').innerHTML='<div class="loading-row"><div class="spinner"></div>Generating your personalized advisory…</div>';
  document.getElementById('adv-pills').innerHTML='<span class="adv-pill">Loading…</span>';

  try{
    const [adv,labor]=await Promise.all([
      apiCall('/api/v1/advisory/generate','POST',{farmer_id:f.farmer_id,village_code:f.village_code,crop:f.crop,language:getLang(),state:f.state||'Assam',...DEMO}),
      apiCall('/api/v1/cross-domain/labor-advisory','POST',{max_temp_c:DEMO.max_temp_c,drought_score:55,humidity_pct:DEMO.avg_humidity_pct,crop:f.crop}).catch(()=>null),
    ]);
    adv._labor=labor;
    lastAdvisory=adv;
    renderAdvisory(adv,labor);
    if(typeof saveAdvisoryLocally==='function') saveAdvisoryLocally(f.farmer_id,adv);
  } catch{
    try{
      const cached=await dbGetAll('advisories');
      if(cached.length){ lastAdvisory=cached[cached.length-1]; renderAdvisory(lastAdvisory,null); document.getElementById('adv-cached-tag')?.classList.remove('hidden'); toast('📵 Showing cached advisory'); }
      else { document.getElementById('adv-body').textContent='❌ Unable to load. Check connection.'; }
    } catch{ document.getElementById('adv-body').textContent='❌ Unable to load. Check connection.'; }
  }

  if(btn){ btn.textContent='↻ Refresh'; btn.disabled=false; }
}

function renderAdvisory(adv,labor){
  const d=adv.risk?.drought, p=adv.risk?.pest, s=adv.sowing;
  // Advisory text
  document.getElementById('adv-body').textContent=adv.advisory||'Advisory not available.';
  document.getElementById('tts-btn').disabled=false;
  // Badges
  document.getElementById('adv-pills').innerHTML=`
    <span class="adv-pill">💧 Drought: ${d?.score??'—'}/100</span>
    <span class="adv-pill">🐛 Pest: ${p?.score??'—'}/100</span>
    <span class="adv-pill">🌐 ${getLang()}</span>
  `;
  // Risk detail cards
  if(d){ renderRD('drought',d.score,d.level,d.level==='LOW'?'Irrigation not urgent':'Consider irrigating soon'); }
  if(p){ renderRD('pest',p.score,p.level,p.likely_pests?.length?`Watch: ${p.likely_pests.slice(0,2).join(', ')}`:'No specific pests flagged'); }
  // Sowing
  if(s){
    const cm={OPTIMAL:'var(--forest-700)',ACCEPTABLE:'var(--amber-700)',WAIT:'#C2410C',NOT_RECOMMENDED:'var(--sienna-700)'};
    const bm={OPTIMAL:'var(--forest-50)',ACCEPTABLE:'var(--amber-50)',WAIT:'#FFF4EE',NOT_RECOMMENDED:'var(--sienna-50)'};
    g('sow-rec',s.recommendation); g('sow-detail',`${s.current_season} season`);
    const rec=document.getElementById('sow-rec'); if(rec) rec.style.color=cm[s.recommendation]||'var(--ink-900)';
    const ib=document.getElementById('sow-icon-bg'); if(ib) ib.style.background=bm[s.recommendation]||'var(--forest-50)';
  }
  // Labor
  if(labor){
    const safe=labor.heat_stress_level==='SAFE';
    const lc=document.getElementById('labor-card');
    if(lc){ lc.className=`labor-card ${safe?'labor-card-safe':'labor-card-warn'}`; }
    const lt=document.getElementById('labor-title');
    if(lt){ lt.style.color=safe?'var(--forest-700)':'var(--amber-700)'; lt.textContent=safe?'Safe to Work Today':'Heat Stress Advisory'; }
    g('labor-body',labor.advisory+(labor.drought_modifier?' '+labor.drought_modifier:''));
    const lh=document.getElementById('labor-hours-tag');
    if(lh){ lh.textContent='⏰ '+labor.safe_working_hours; lh.style.background=safe?'var(--forest-700)':'var(--amber-700)'; }
  }
}

function renderRD(type,score,level,hint){
  const lvl=level.toLowerCase();
  const clr={low:'var(--forest-500)',moderate:'var(--amber-500)',high:'#EA580C',critical:'var(--sienna-500)'}[lvl]||'var(--forest-500)';
  g(`rd-${type}-level`,`${level} (${score}/100)`);
  const el=document.getElementById(`rd-${type}-level`); if(el) el.style.color=clr;
  const bar=document.getElementById(`rd-${type}-bar`); if(bar){ bar.style.width=Math.min(100,score)+'%'; bar.style.background=clr; }
  const circle=document.getElementById(`rd-${type}-circle`); if(circle){ circle.textContent=score; circle.className=`rd-circle rdc-${lvl}`; }
  g(`rd-${type}-hint`,hint);
}

async function logInsuranceEvent(){
  if(!lastAdvisory){ toast('ℹ️ Load advisory first'); return; }
  const f=getFarmer(); if(!f) return;
  try{
    const r=await apiCall('/api/v1/cross-domain/insurance-log','POST',{farmer_id:f.farmer_id,event_type:'pest_spray',crop:f.crop,drought_score:lastAdvisory.risk?.drought?.score,pest_score:lastAdvisory.risk?.pest?.score,pest_detected:lastAdvisory.risk?.pest?.likely_pests?.join(', '),advisory_text:lastAdvisory.advisory?.slice(0,200)});
    toast(`🛡️ Logged! Evidence #${r.event_id}`);
    if(typeof dbAdd==='function') await dbAdd('insuranceLog',{...r,timestamp:new Date().toISOString()});
  } catch{
    if(typeof dbAdd==='function') await dbAdd('insuranceLog',{event_type:'pest_spray',crop:getFarmer()?.crop,timestamp:new Date().toISOString(),offline:true});
    toast('📵 Logged offline — will sync');
  }
}

async function playAudio(){
  if(!lastAdvisory) return;
  toast('🔊 Generating audio…');
  try{
    const resp=await fetch('/api/v1/advisory/tts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastAdvisory.advisory?.slice(0,400),language:getLang()})});
    if(resp.ok){ const url=URL.createObjectURL(await resp.blob()); new Audio(url).play(); }
    else toast('🔊 Add ELEVENLABS_API_KEY to enable voice');
  } catch{ toast('📵 Audio unavailable offline'); }
}

function g(id,val){ const e=document.getElementById(id); if(e) e.textContent=val; }
