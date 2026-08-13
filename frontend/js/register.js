let pendingFormData = null;

document.addEventListener('DOMContentLoaded', () => {
  // USERFLOW GUARD: If already registered, redirect to home.html
  checkUserflow(false, true);
});

async function submitRegistration(e) {
  e.preventDefault();
  const btn = document.getElementById('reg-btn');
  const btnText = document.getElementById('reg-btn-text');

  const fd = {
    name: document.getElementById('fn-name').value.trim(),
    email: document.getElementById('fn-email').value.trim(),
    phone: document.getElementById('fn-phone').value.trim(),
    crop: document.getElementById('fn-crop').value,
    state: document.getElementById('fn-state').value,
    village_code: document.getElementById('fn-village').value.trim() || 'ASM-KAM-001',
    plot_area_acres: parseFloat(document.getElementById('fn-area').value) || 2.0,
    language_preference: getLang(),
    consent_given: true,
    consent_timestamp: new Date().toISOString(),
  };

  if (!fd.email) {
    toast('Please enter your email address');
    return;
  }

  btnText.textContent = 'Registering…';
  btn.disabled = true;

  try {
    // Call Real-Time Supabase Auth Sign Up & DB Insertion
    const res = await apiCall('/api/v1/auth/signup', 'POST', fd);

    pendingFormData = { ...fd, farmer_id: res.farmer_id };

    // Save temporary session in localStorage & IndexedDB
    const farmer = {
      farmer_id: res.farmer_id,
      ...fd,
      registered_at: new Date().toISOString(),
      database: 'supabase_postgresql',
    };
    localStorage.setItem('ks_farmer', JSON.stringify(farmer));
    if (typeof saveFarmerLocally === 'function') await saveFarmerLocally(farmer);

    // Open OTP modal for real-time verification
    document.getElementById('otp-target-email').textContent = fd.email;
    document.getElementById('otp-modal').classList.remove('hidden');
    document.getElementById('otp-code-input').focus();
    toast(`Verification code sent to ${fd.email}`);
  } catch (err) {
    // Offline fallback
    const offlineId = 'LOCAL_' + Date.now();
    const farmer = {
      farmer_id: offlineId,
      ...fd,
      registered_at: new Date().toISOString(),
      offline: true,
    };
    localStorage.setItem('ks_farmer', JSON.stringify(farmer));
    if (typeof saveFarmerLocally === 'function') await saveFarmerLocally(farmer);
    if (typeof queueForSync === 'function') await queueForSync('/api/v1/auth/signup', 'POST', fd);
    toast('Saved offline — redirecting to dashboard');
    setTimeout(() => window.location.replace('/home.html'), 750);
  }

  btnText.textContent = 'Register & Get Advisory';
  btn.disabled = false;
}

async function verifyRegistrationOTP() {
  const code = document.getElementById('otp-code-input').value.trim();
  const btn = document.getElementById('verify-btn');
  const btnText = document.getElementById('verify-btn-text');

  if (!code || code.length < 6) {
    toast('Please enter 6-digit code');
    return;
  }

  btnText.textContent = 'Verifying…';
  btn.disabled = true;

  try {
    const email = pendingFormData ? pendingFormData.email : document.getElementById('fn-email').value.trim();
    await apiCall('/api/v1/auth/verify-otp', 'POST', {
      email,
      token: code,
    });

    toast('Account verified! Loading your farm dashboard…');
    setTimeout(() => window.location.replace('/home.html'), 750);
  } catch (err) {
    toast(err.message || 'Invalid code — try again');
  }

  btnText.textContent = 'Verify & Create Account';
  btn.disabled = false;
}

function closeOTPModal() {
  document.getElementById('otp-modal').classList.add('hidden');
  window.location.replace('/home.html');
}
