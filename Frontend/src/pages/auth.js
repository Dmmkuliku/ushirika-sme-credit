/**
 * Login / Register screens.
 * Login: universal (NIDA / membership number + 4-digit PIN).
 * Register: SME self-registration only.
 */

import * as api from '../api.js';
import { setSession } from '../session.js';
import { escapeHtml, getErrorMessage } from '../utils.js';
import { showToast } from '../ui.js';

const BUSINESS_TYPES = [
  'Entrepreneur', 'Machinga', 'Retailer', 'Wholesaler', 'Manufacturer',
  'Farmer', 'Service Provider', 'Transport', 'Food Vendor', 'Other',
];

export function renderAuthPage(mode = 'login') {
  const isRegister = mode === 'register';
  return `
    <div class="auth-layout">
      <div class="auth-visual" aria-hidden="true">
        <div class="auth-visual-inner">
          <p class="auth-eyebrow">United Republic of Tanzania</p>
          <p class="auth-brand">Ushirika</p>
          <p class="auth-tagline">SME ecosystem banking — transparent scores, fair access to capital.</p>
        </div>
      </div>
      <div class="auth-panel">
        <main id="main" class="auth-main" tabindex="-1">
          <h1 class="auth-heading">${isRegister ? 'Create your SME account' : 'Welcome back'}</h1>
          <p class="auth-lead">
            ${isRegister
              ? 'Lender and admin accounts are created by the system administrator.'
              : 'Sign in with your ID and PIN.'}
          </p>
          <form id="auth-form" class="auth-form" novalidate>
            ${isRegister ? renderRegisterFields() : renderLoginFields()}
            <div id="auth-error" class="form-error" role="alert" hidden></div>
            <button type="submit" class="btn btn-primary btn-block" id="auth-submit">
              ${isRegister ? 'Create account' : 'Sign in'}
            </button>
          </form>
          <p class="auth-switch">
            ${isRegister
              ? 'Already registered? <a href="#/login">Sign in</a>'
              : 'New here? <a href="#/register">Create an account</a>'}
          </p>
        </main>
      </div>
    </div>
  `;
}

function renderLoginFields() {
  return `
    <div class="field">
      <label for="login_id">Your ID (NIDA / Membership Number)</label>
      <input id="login_id" name="login_id" type="text" autocomplete="username" required />
    </div>
    <div class="field">
      <label for="pin">PIN</label>
      <input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" autocomplete="current-password" required placeholder="4-digit PIN" />
    </div>
  `;
}

function renderRegisterFields() {
  const bizOptions = BUSINESS_TYPES.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
  return `
    <div class="field">
      <label for="nida">NIDA (National Identity Number)</label>
      <input id="nida" name="nida" type="text" inputmode="numeric" maxlength="20" pattern="[0-9]{20}" required placeholder="20-digit NIDA number" />
    </div>
    <div class="field">
      <label for="full_name">Full name</label>
      <input id="full_name" name="full_name" type="text" autocomplete="name" required maxlength="120" />
    </div>
    <div class="field">
      <label for="phone">Phone number</label>
      <input id="phone" name="phone" type="tel" required placeholder="+255..." />
    </div>
    <div class="field">
      <label for="email">Email <span class="optional">(optional)</span></label>
      <input id="email" name="email" type="email" autocomplete="email" maxlength="254" />
    </div>
    <div class="field">
      <label for="location">Location / Address</label>
      <input id="location" name="location" type="text" required />
    </div>
    <div class="field">
      <label for="business_type">Business type</label>
      <select id="business_type" name="business_type" required>
        <option value="">Select…</option>
        ${bizOptions}
      </select>
    </div>
    <div class="field">
      <label for="gender">Gender</label>
      <select id="gender" name="gender" required>
        <option value="">Select…</option>
        <option value="Male">Male</option>
        <option value="Female">Female</option>
        <option value="Other">Other</option>
      </select>
    </div>
    <div class="field">
      <label for="nationality">Nationality</label>
      <input id="nationality" name="nationality" type="text" value="Tanzanian" required />
    </div>
    <div class="field">
      <label for="date_of_birth">Date of birth</label>
      <input id="date_of_birth" name="date_of_birth" type="date" required />
    </div>
    <div class="field">
      <label for="pin">PIN</label>
      <input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="4-digit PIN" />
    </div>
    <div class="field">
      <label for="confirm_pin">Confirm PIN</label>
      <input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="Re-enter PIN" />
    </div>
  `;
}

export function bindAuthPage(mode, { onSuccess }) {
  const form = document.getElementById('auth-form');
  const errorEl = document.getElementById('auth-error');
  const submitBtn = document.getElementById('auth-submit');

  function showError(msg) {
    if (!errorEl) return;
    errorEl.hidden = false;
    errorEl.textContent = msg;
  }

  function clearError() {
    if (!errorEl) return;
    errorEl.hidden = true;
    errorEl.textContent = '';
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const fd = new FormData(form);

    if (mode === 'login') {
      const login_id = String(fd.get('login_id') || '').trim();
      const pin = String(fd.get('pin') || '');
      if (!login_id) { showError('ID is required.'); return; }
      if (!/^[0-9]{4}$/.test(pin)) { showError('PIN must be exactly 4 digits.'); return; }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Signing in…';
      try {
        const payload = await api.login({ login_id, pin });
        if (!payload?.access_token && !payload?.token) {
          throw new Error('Server did not return an access token.');
        }
        const token = payload.access_token || payload.token;
        let user = payload.user;
        if (!user) {
          setSession({ access_token: token, user: { login_id, role: payload.role || 'sme' } });
          user = await api.getMe();
        }
        setSession({
          access_token: token,
          user: { ...user, role: user.role || payload.role || 'sme' },
        });
        showToast('Signed in.', 'success');
        onSuccess();
      } catch (err) {
        const msg = getErrorMessage(err, 'Authentication failed');
        showError(msg);
        showToast(msg, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Sign in';
      }
    } else {
      const nida = String(fd.get('nida') || '').trim();
      const full_name = String(fd.get('full_name') || '').trim();
      const phone = String(fd.get('phone') || '').trim();
      const email = String(fd.get('email') || '').trim();
      const location = String(fd.get('location') || '').trim();
      const business_type = String(fd.get('business_type') || '');
      const gender = String(fd.get('gender') || '');
      const nationality = String(fd.get('nationality') || '').trim();
      const date_of_birth = String(fd.get('date_of_birth') || '');
      const pin = String(fd.get('pin') || '');
      const confirm_pin = String(fd.get('confirm_pin') || '');

      if (!/^[0-9]{20}$/.test(nida)) { showError('NIDA must be exactly 20 digits.'); return; }
      if (!full_name) { showError('Full name is required.'); return; }
      if (!phone) { showError('Phone number is required.'); return; }
      if (!location) { showError('Location is required.'); return; }
      if (!business_type) { showError('Please select a business type.'); return; }
      if (!gender) { showError('Please select a gender.'); return; }
      if (!date_of_birth) { showError('Date of birth is required.'); return; }
      if (!/^[0-9]{4}$/.test(pin)) { showError('PIN must be exactly 4 digits.'); return; }
      if (pin !== confirm_pin) { showError('PINs do not match.'); return; }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating…';
      try {
        await api.registerSme({ nida, phone, full_name, email, location, business_type, gender, nationality, date_of_birth, pin });
        const loginPayload = await api.login({ login_id: nida, pin });
        if (!loginPayload?.access_token && !loginPayload?.token) {
          throw new Error('Server did not return an access token.');
        }
        const token = loginPayload.access_token || loginPayload.token;
        let user = loginPayload.user;
        if (!user) {
          setSession({ access_token: token, user: { login_id: nida, role: 'sme' } });
          user = await api.getMe();
        }
        setSession({
          access_token: token,
          user: { ...user, role: user.role || 'sme' },
        });
        showToast('Account created successfully.', 'success');
        onSuccess();
      } catch (err) {
        const msg = getErrorMessage(err, 'Registration failed');
        showError(msg);
        showToast(msg, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create account';
      }
    }
  });
}

export { escapeHtml };
