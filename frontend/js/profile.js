// profile.js — Profile page logic
document.addEventListener('DOMContentLoaded',()=>{
  const f=getFarmer();
  if(!f){
    document.getElementById('not-registered').classList.remove('hidden');
  } else {
    document.getElementById('registered-view').classList.remove('hidden');
    renderProfile(f);
    loadInsuranceTrail();
  }
});

function renderProfile(f){
  g('pf-name',f.name||'—');
  g('pf-detail',`${(f.crop||'').toUpperCase()} • ${f.state||''}`);
  g('pf-id','ID: '+(f.farmer_id||'—'));
  g('pf-crop',`${cropEmoji(f.crop)} ${(f.crop||'').toUpperCase()}`);
  g('pf-state',f.state||'—');
  g('pf-village',f.village_code||'—');
  g('pf-area',(f.plot_area_acres||'—')+' acres');
  g('pf-lang',getLang());
  g('pf-date',f.registered_at?new Date(f.registered_at).toLocaleDateString('en-IN',{dateStyle:'medium'}):'—');
}

function cropEmoji(c){ return {rice:'🌾',wheat:'🌿',maize:'🌽',cotton:'🪴',mustard:'🟡',soybean:'🫘'}[c]||'🌾'; }

async function loadInsuranceTrail(){
  const f=getFarmer(); if(!f) return;
  const list=document.getElementById('ins-trail');
  try{
    const data=await apiCall(`/api/v1/cross-domain/insurance-trail/${f.farmer_id}`);
    if(!data.events?.length){ renderEmptyTrail(); return; }
    list.innerHTML=data.events.slice(0,6).map(ev=>`
      <div class="ins-item fade">
        <div class="ins-id">Evidence #${ev.id}</div>
        <div class="ins-type">${(ev.event_type||'').replace(/_/g,' ')} — ${ev.crop||''}</div>
        <div class="ins-date">${new Date(ev.timestamp).toLocaleString('en-IN')}</div>
      </div>`).join('');
  } catch{
    try{
      const local=await dbGetAll('insuranceLog');
      if(local.length){
        list.innerHTML=local.slice(0,5).map(ev=>`
          <div class="ins-item fade">
            <div class="ins-id">${ev.offline?'Offline Event':'Evidence #'+(ev.id||'—')}</div>
            <div class="ins-type">${(ev.event_type||'logged').replace(/_/g,' ')} — ${ev.crop||''}</div>
            <div class="ins-date">${ev.timestamp||''}</div>
          </div>`).join('');
      } else { renderEmptyTrail(); }
    } catch { renderEmptyTrail(); }
  }
}

function renderEmptyTrail(){
  document.getElementById('ins-trail').innerHTML=`
    <div class="empty-state">
      <div class="empty-icon">🛡️</div>
      <div class="empty-title">No events yet</div>
      <div class="empty-sub">Go to Advisory → tap "Log Evidence" to build your insurance trail</div>
    </div>`;
}

async function requestErasure(){
  const f=getFarmer(); if(!f) return;
  if(!confirm('Request data erasure? Records will be deleted within 30 days (DPDP compliance).')) return;
  try{
    await apiCall('/api/v1/compliance/erasure/request','POST',{farmer_id:f.farmer_id});
    toast('✅ Erasure requested — deleted within 30 days');
  } catch{ toast('📵 Request queued for when online'); }
}

function signOut(){
  if(!confirm('Sign out?')) return;
  localStorage.removeItem('ks_farmer');
  window.location.replace('/');
}

function g(id,val){ const e=document.getElementById(id); if(e) e.textContent=val; }
