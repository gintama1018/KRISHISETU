let currentEmail = '';

document.addEventListener('DOMContentLoaded', () => {
  // If already logged in, redirect to home.html
  checkUserflow(false, true);
});

async function handleLoginSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  const btnText = document.getElementById('login-btn-text');
  const emailInput = document.getElementById('login-email');
  currentEmail = emailInput.value.trim();

  if (!currentEmail) {
    toast('Please enter your email address');
    return;
  }

  btnText.textContent = 'Sending Code…';
  btn.disabled = true;

  try {
    const res = await apiCall('/api/v1/auth/login', 'POST', { email: currentEmail });
    toast(`Verification code sent to ${currentEmail}`);

    // If farmer profile was returned from Supabase, save temporarily
    if (res.farmer) {
      localStorage.setItem('ks_farmer', JSON.stringify({
        farmer_id: res.farmer.id || 'F_' + Date.now(),
        name: res.farmer.name || 'Farmer',
        crop: res.farmer.crop || 'rice',
        state: res.farmer.state || 'Assam',
        village_code: res.farmer.village_code || 'ASM-KAM-001',
        database: 'supabase_postgresql',
      }));
    }

    // Open OTP modal
    document.getElementById('otp-target-email').textContent = currentEmail;
    document.getElementById('otp-modal').classList.remove('hidden');
    document.getElementById('otp-code-input').focus();
  } catch (err) {
    toast('Login error: ' + (err.message || 'Check connection'));
  }

  btnText.textContent = 'Send Verification Code';
  btn.disabled = false;
}

async function verifyOTPCode() {
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
    const res = await apiCall('/api/v1/auth/verify-otp', 'POST', {
      email: currentEmail,
      token: code,
    });

    if (res.profile) {
      localStorage.setItem('ks_farmer', JSON.stringify({
        farmer_id: res.profile.id,
        name: res.profile.name,
        crop: res.profile.crop,
        state: res.profile.state,
        village_code: res.profile.village_code,
        database: 'supabase_postgresql',
      }));
    } else if (!getFarmer()) {
      // Create fallback profile if new user
      localStorage.setItem('ks_farmer', JSON.stringify({
        farmer_id: res.user_id || 'F_' + Date.now(),
        name: currentEmail.split('@')[0],
        crop: 'rice',
        state: 'Assam',
        village_code: 'ASM-KAM-001',
        database: 'supabase_postgresql',
      }));
    }

    toast('Signed in successfully! Loading dashboard…');
    setTimeout(() => window.location.replace('/home.html'), 750);
  } catch (err) {
    toast(err.message || 'Invalid verification code');
  }

  btnText.textContent = 'Verify & Sign In';
  btn.disabled = false;
}

function closeOTPModal() {
  document.getElementById('otp-modal').classList.add('hidden');
}
