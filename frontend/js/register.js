document.addEventListener('DOMContentLoaded', () => {
  // USERFLOW GUARD: If already registered, redirect to home.html
  checkUserflow(false, true);
});

async function submitRegistration(e){
  e.preventDefault();
  const btn=document.getElementById('reg-btn');
  const btnText=document.getElementById('reg-btn-text');
  btnText.textContent='⏳ Registering…';
  btn.disabled=true;

  const fd={
    name:document.getElementById('fn-name').value.trim(),
    phone:document.getElementById('fn-phone').value.trim(),
    crop:document.getElementById('fn-crop').value,
    state:document.getElementById('fn-state').value,
    village_code:document.getElementById('fn-village').value.trim()||'ASM-KAM-001',
    plot_area_acres:parseFloat(document.getElementById('fn-area').value)||2.0,
    language_preference:getLang(),
    consent_given:true,
    consent_timestamp:new Date().toISOString(),
  };

  try{
    // Capture DPDP consent
    await apiCall('/api/v1/compliance/consent/capture','POST',{
      farmer_id:'F_'+Date.now(),
      phone:fd.phone,
      consent_method:'app',
      data_uses:'weather_advisory,mandi_prices,risk_alerts',
    });
    // Register with AgriStack
    const reg=await apiCall('/api/v1/farmer/register','POST',fd);
    const farmer={...reg,...fd,registered_at:new Date().toISOString()};
    localStorage.setItem('ks_farmer',JSON.stringify(farmer));
    await saveFarmerLocally(farmer);
    toast('✅ Registered! Loading your advisory…');
    setTimeout(()=>window.location.replace('/home.html'),700);
  } catch{
    // Offline fallback
    const farmer={farmer_id:'LOCAL_'+Date.now(),...fd,registered_at:new Date().toISOString(),offline:true};
    localStorage.setItem('ks_farmer',JSON.stringify(farmer));
    await saveFarmerLocally(farmer);
    await queueForSync('/api/v1/farmer/register','POST',fd);
    toast('📵 Saved offline — will sync when connected');
    setTimeout(()=>window.location.replace('/home.html'),700);
  }

  btnText.textContent='✅ Register & Get Advisory';
  btn.disabled=false;
}
