// market.js — Market Prices page
let currentCommodity='Rice';

document.addEventListener('DOMContentLoaded',()=>{ loadPrices(); });

function selectCommodity(c,el){
  currentCommodity=c;
  document.querySelectorAll('.chip').forEach(ch=>ch.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('ph-commodity').textContent=c.toUpperCase();
  loadPrices();
}

async function loadPrices(){
  const state=document.getElementById('state-select')?.value||'Assam';
  document.getElementById('mandi-list').innerHTML='<div class="loading-row"><div class="spinner"></div>Fetching prices…</div>';
  document.getElementById('ph-price').textContent='₹…';

  try{
    const data=await apiCall(`/api/v1/prices/mandi?commodity=${encodeURIComponent(currentCommodity)}&state=${encodeURIComponent(state)}&limit=10`);
    renderPrices(data.prices||[],state);
  } catch{
    // Fallback mock
    const mock=[
      {Market:'Guwahati',Modal_x0020_Price:'1,520',Min_x0020_Price:'1,380',Max_x0020_Price:'1,700',Arrival_Date:'11/08/2026'},
      {Market:'Kamrup',Modal_x0020_Price:'1,480',Min_x0020_Price:'1,320',Max_x0020_Price:'1,650',Arrival_Date:'11/08/2026'},
      {Market:'Nalbari',Modal_x0020_Price:'1,500',Min_x0020_Price:'1,350',Max_x0020_Price:'1,680',Arrival_Date:'10/08/2026'},
    ];
    renderPrices(mock,state);
    toast('📵 Showing cached/demo prices');
  }
}

function renderPrices(prices,state){
  if(!prices.length){
    document.getElementById('mandi-list').innerHTML='<div class="empty-state"><div class="empty-icon">💰</div><div class="empty-title">No data available</div><div class="empty-sub">Try a different state or commodity</div></div>';
    return;
  }
  // Hero price
  const first=prices[0];
  const heroPrice=first.Modal_x0020_Price||first.modal_price||'—';
  document.getElementById('ph-price').textContent='₹'+heroPrice;

  // Trend
  const trend=calcTrend(prices);
  const tMap={rising:['📈 Rising','var(--forest-700)'],falling:['📉 Falling','var(--sienna-500)'],stable:['📊 Stable','var(--amber-700)']};
  const [tText,tColor]=tMap[trend];
  const tEl=document.getElementById('ph-trend');
  if(tEl){ tEl.querySelector('#ph-trend-icon').textContent=tText.split(' ')[0]; tEl.querySelector('#ph-trend-text').textContent=tText; }

  // Count
  const cnt=document.getElementById('price-count');
  if(cnt) cnt.textContent=`${prices.length} mandis`;

  // List
  document.getElementById('mandi-list').innerHTML=prices.slice(0,10).map(p=>`
    <div class="mandi-row fade">
      <div>
        <div class="mandi-mkt">🏪 ${p.Market||p.market||'Local Mandi'}</div>
        <div class="mandi-date">${p.Arrival_Date||p.arrival_date||'—'} · ${p.State||state}</div>
      </div>
      <div class="mandi-price-col">
        <div class="mandi-modal">₹${p.Modal_x0020_Price||p.modal_price||'—'}</div>
        <div class="mandi-range">Min ₹${p.Min_x0020_Price||'—'} · Max ₹${p.Max_x0020_Price||'—'}</div>
      </div>
    </div>
  `).join('');
}

function calcTrend(prices){
  const vals=prices.map(p=>parseFloat(p.Modal_x0020_Price?.replace(',','')||p.modal_price||0)).filter(v=>v>0);
  if(vals.length<3) return 'stable';
  const mid=Math.floor(vals.length/2);
  const a=vals.slice(0,mid).reduce((s,v)=>s+v,0)/mid;
  const b=vals.slice(mid).reduce((s,v)=>s+v,0)/(vals.length-mid);
  return b>a*1.025?'rising':b<a*0.975?'falling':'stable';
}
