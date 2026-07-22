/**
 * Login / Register / Forgot PIN screens.
 * Login: universal (NIDA / membership number + 4-digit PIN).
 * Register: SME self-registration only (includes TIN).
 */

import * as api from '../api.js';
import { setSession } from '../session.js';
import { escapeHtml, getErrorMessage } from '../utils.js';
import { showToast } from '../ui.js';
import { businessTypeLabel, t, langSwitchHtml, toggleLang, getLang } from '../i18n.js';
import {
  bindConfirmPinField,
  bindExactDigitsValidation,
  bindImmediateEmailValidation,
  bindNidaMatchedDobValidation,
  bindPhoneField,
  bindPinField,
  bindRequiredField,
  dmyToIso,
  enforceSequentialFields,
  focusInvalidField,
  normalizeTzPhone,
  phoneInputHtml,
} from '../form-validation.js';

const BUSINESS_TYPES = [
  'Entrepreneur', 'Machinga', 'Retailer', 'Wholesaler', 'Manufacturer',
  'Farmer', 'Service Provider', 'Transport', 'Food Vendor', 'Other',
];

export function renderAuthPage(mode = 'login') {
  const isRegister = mode === 'register';
  const isForgot = mode === 'forgot-pin';

  let heading = t('auth.welcomeBack');
  let lead = t('auth.leadLogin');
  let submitLabel = t('auth.signIn');
  if (isRegister) {
    heading = t('auth.createAccount');
    lead = t('auth.leadRegister');
    submitLabel = t('auth.createAccountBtn');
  } else if (isForgot) {
    heading = t('auth.forgotTitle');
    lead = t('auth.leadForgot');
    submitLabel = t('auth.resetPin');
  }

  let fields;
  if (isRegister) fields = renderRegisterFields();
  else if (isForgot) fields = renderForgotFields();
  else fields = renderLoginFields();

  let switchHtml;
  if (isForgot) {
    switchHtml = `<a href="#/login">${t('auth.backToLogin')}</a>`;
  } else if (isRegister) {
    switchHtml = `${t('auth.alreadyRegistered')} <a href="#/login">${t('auth.signIn')}</a>`;
  } else {
    switchHtml = `${t('auth.newHere')} <a href="#/register">${t('auth.createAnAccount')}</a>`;
  }

  return `
    <div class="auth-layout">
      <div class="auth-lang-bar">${langSwitchHtml('lang-switch-auth')}</div>
      <div class="auth-visual" aria-hidden="true">
        <div class="auth-visual-inner">
          <p class="auth-eyebrow">${escapeHtml(t('brand.eyebrow'))}</p>
          <p class="auth-brand">${escapeHtml(t('brand.name'))}</p>
          <p class="auth-tagline">${escapeHtml(t('brand.tagline'))}</p>
        </div>
      </div>
      <div class="auth-panel">
        <main id="main" class="auth-main" tabindex="-1">
          <h1 class="auth-heading">${escapeHtml(heading)}</h1>
          <p class="auth-lead">${escapeHtml(lead)}</p>
          <form id="auth-form" class="auth-form" novalidate>
            ${fields}
            <div id="auth-error" class="form-error" role="alert" hidden></div>
            <button type="submit" class="btn btn-primary btn-block" id="auth-submit">
              ${escapeHtml(submitLabel)}
            </button>
          </form>
          <p class="auth-switch">${switchHtml}</p>
        </main>
      </div>
    </div>
  `;
}

function renderLoginFields() {
  return `
    <div class="field">
      <label for="login_id">${escapeHtml(t('auth.loginId'))}</label>
      <input id="login_id" name="login_id" type="text" maxlength="20" autocomplete="username" required />
    </div>
    <div class="field">
      <label for="pin">${escapeHtml(t('auth.pin'))}</label>
      <input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" autocomplete="current-password" required placeholder="${escapeHtml(t('auth.pinPlaceholder'))}" />
    </div>
    <p class="auth-forgot-link"><a href="#/forgot-pin">${escapeHtml(t('auth.forgotPinLink'))}</a></p>
  `;
}

function renderForgotFields() {
  return `
    <div class="field">
      <label for="login_id">${escapeHtml(t('auth.loginId'))}</label>
      <input id="login_id" name="login_id" type="text" maxlength="20" autocomplete="username" required />
    </div>
    <div class="field">
      <label for="date_of_birth">${escapeHtml(t('auth.dateOfBirth'))}</label>
      <input id="date_of_birth" name="date_of_birth" type="text" inputmode="numeric"
        maxlength="10" placeholder="DD-MM-YYYY" autocomplete="bday" required />
    </div>
    <div class="field">
      <label for="phone">${escapeHtml(t('auth.phone'))}</label>
      ${phoneInputHtml({ id: 'phone', required: true })}
      <p class="field-hint">${escapeHtml(t('auth.forgotPhoneHint'))}</p>
    </div>
    <div class="field">
      <label for="new_pin">${escapeHtml(t('auth.newPin'))}</label>
      <input id="new_pin" name="new_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.pinPlaceholder'))}" />
    </div>
    <div class="field">
      <label for="confirm_pin">${escapeHtml(t('auth.confirmPin'))}</label>
      <input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.confirmPinPlaceholder'))}" />
    </div>
  `;
}

function renderRegisterFields() {
  const bizOptions = BUSINESS_TYPES.map(
    (bt) => `<option value="${escapeHtml(bt)}">${escapeHtml(businessTypeLabel(bt))}</option>`,
  ).join('');
  return `
    <div class="field">
      <label for="nida">${escapeHtml(t('auth.nida'))}</label>
      <input id="nida" name="nida" type="text" inputmode="numeric" maxlength="20" pattern="[0-9]{20}" required placeholder="${escapeHtml(t('auth.nidaPlaceholder'))}" />
    </div>
    <div class="field">
      <label for="full_name">${escapeHtml(t('auth.fullName'))}</label>
      <input id="full_name" name="full_name" type="text" autocomplete="name" required maxlength="120" />
    </div>
    <div class="field">
      <label for="tin">${escapeHtml(t('auth.tin'))}</label>
      <input id="tin" name="tin" type="text" inputmode="numeric" required minlength="9" maxlength="9" pattern="[0-9]{9}" placeholder="${escapeHtml(t('auth.tinPlaceholder'))}" />
      <p class="field-hint">${escapeHtml(t('auth.tinHint'))}</p>
    </div>
    <div class="field">
      <label for="phone">${escapeHtml(t('auth.phone'))}</label>
      ${phoneInputHtml({ id: 'phone', required: true })}
      <p class="field-hint">${escapeHtml(t('auth.phoneHint'))}</p>
    </div>
    <div class="field">
      <label for="email">${escapeHtml(t('auth.email'))} <span class="optional">${escapeHtml(t('common.optional'))}</span></label>
      <input id="email" name="email" type="email" autocomplete="email" maxlength="254" />
    </div>
    <div class="field">
      <label for="location">${escapeHtml(t('auth.location'))}</label>
      <input id="location" name="location" type="text" required />
    </div>
    <div class="field">
      <label for="business_type">${escapeHtml(t('auth.businessType'))}</label>
      <select id="business_type" name="business_type" required>
        <option value="">${escapeHtml(t('common.select'))}</option>
        ${bizOptions}
      </select>
    </div>
    <div class="field">
      <label for="gender">${escapeHtml(t('auth.gender'))}</label>
      <select id="gender" name="gender" required>
        <option value="">${escapeHtml(t('common.select'))}</option>
        <option value="Male">${escapeHtml(t('auth.genderMale'))}</option>
        <option value="Female">${escapeHtml(t('auth.genderFemale'))}</option>
      </select>
    </div>
    <div class="field">
      <label for="date_of_birth">${escapeHtml(t('auth.dateOfBirth'))}</label>
      <input id="date_of_birth" name="date_of_birth" type="text" inputmode="numeric"
        maxlength="10" placeholder="DD-MM-YYYY" autocomplete="bday" required />
      <p class="field-hint">${escapeHtml(t('auth.ageHint'))}</p>
    </div>
    <div class="field">
      <label for="pin">${escapeHtml(t('auth.pin'))}</label>
      <input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.pinPlaceholder'))}" />
    </div>
    <div class="field">
      <label for="confirm_pin">${escapeHtml(t('auth.confirmPin'))}</label>
      <input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.confirmPinPlaceholder'))}" />
    </div>
  `;
}

function bindLangToggle(onLangChange) {
  document.querySelectorAll('[data-lang-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      toggleLang();
      onLangChange?.(getLang());
    });
  });
}

export function bindAuthPage(mode, { onSuccess, onLangChange }) {
  const form = document.getElementById('auth-form');
  const errorEl = document.getElementById('auth-error');
  const submitBtn = document.getElementById('auth-submit');

  bindLangToggle(onLangChange);

  bindExactDigitsValidation(document.getElementById('nida'), {
    length: 20,
    digitsOnlyMessage: t('auth.errNidaDigitsOnly'),
    exactLengthMessage: t('auth.errNida'),
  });
  bindImmediateEmailValidation(document.getElementById('email'), t('auth.errEmail'));
  bindPinField(document.getElementById('pin'), t('auth.errPinDigits'));
  if (mode === 'register') {
    bindNidaMatchedDobValidation({
      input: document.getElementById('date_of_birth'),
      nidaInput: document.getElementById('nida'),
      invalidDateMessage: t('auth.errDobFormat'),
      mismatchMessage: t('auth.errDobNidaMismatch'),
    });
    bindRequiredField(document.getElementById('full_name'), t('auth.errFullName'));
    bindExactDigitsValidation(document.getElementById('tin'), {
      length: 9,
      digitsOnlyMessage: t('auth.errTin'),
      exactLengthMessage: t('auth.errTin'),
    });
    bindPhoneField(document.getElementById('phone'), t('auth.errPhoneFormat'));
    bindRequiredField(document.getElementById('location'), t('auth.errLocation'));
    bindRequiredField(document.getElementById('business_type'), t('auth.errBusinessType'));
    bindRequiredField(document.getElementById('gender'), t('auth.errGender'));
    bindConfirmPinField(
      document.getElementById('confirm_pin'),
      document.getElementById('pin'),
      t('auth.errPinsMatch'),
    );
  }
  if (mode === 'forgot-pin') {
    const fLoginId = document.getElementById('login_id');
    const fDob = document.getElementById('date_of_birth');
    const fPhone = document.getElementById('phone');
    const fNewPin = document.getElementById('new_pin');
    const fConfirmPin = document.getElementById('confirm_pin');
    // Required binders first so format binders get the final say on validity.
    bindRequiredField(fLoginId, t('auth.errIdRequired'));
    bindRequiredField(fDob, t('auth.errDob'));
    bindRequiredField(fPhone, t('auth.errPhoneFormat'));
    bindRequiredField(fNewPin, t('auth.errPinDigits'));
    bindNidaMatchedDobValidation({
      input: fDob,
      invalidDateMessage: t('auth.errDobFormat'),
    });
    bindPhoneField(fPhone, t('auth.errPhoneFormat'));
    bindPinField(fNewPin, t('auth.errPinDigits'));
    bindConfirmPinField(fConfirmPin, fNewPin, t('auth.errPinsMatch'));
    // Each step must be completed before the next one can be filled.
    enforceSequentialFields([fLoginId, fDob, fPhone, fNewPin, fConfirmPin]);
  }

  if (mode === 'login' && api.isCloudDeployment()) {
    // Wake the cloud API quietly in the background — do not show progress to the user.
    api.ensureApiReady().catch(() => {});
  }

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
    // Show the message in the banner AND on the offending field itself.
    const fail = (msg, fieldId) => {
      showError(msg);
      focusInvalidField(document.getElementById(fieldId));
    };

    if (mode === 'login') {
      const login_id = String(fd.get('login_id') || '').trim();
      const pin = String(fd.get('pin') || '');
      if (!login_id) { fail(t('auth.errIdRequired'), 'login_id'); return; }
      if (!/^[0-9]{4}$/.test(pin)) { fail(t('auth.errPinDigits'), 'pin'); return; }

      submitBtn.disabled = true;
      submitBtn.textContent = t('auth.signingIn');
      try {
        // Keep the button on "Signing in…" — server wake-up stays invisible.
        await api.ensureApiReady();
        const payload = await api.login({ login_id, pin });
        if (!payload?.access_token && !payload?.token) {
          throw new Error(t('auth.errNoToken'));
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
        showToast(t('auth.signedIn'), 'success');
        onSuccess();
      } catch (err) {
        const msg = err?.detail === 'render_cold_start'
          ? t('auth.errServerWake')
          : getErrorMessage(err, t('auth.errAuth'));
        showError(msg);
        showToast(msg, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = t('auth.signIn');
      }
      return;
    }

    if (mode === 'forgot-pin') {
      const login_id = String(fd.get('login_id') || '').trim();
      const dobInput = String(fd.get('date_of_birth') || '');
      const date_of_birth = dmyToIso(dobInput);
      const phoneRaw = String(fd.get('phone') || '').trim();
      const phone = normalizeTzPhone(phoneRaw);
      const new_pin = String(fd.get('new_pin') || '');
      const confirm_pin = String(fd.get('confirm_pin') || '');

      if (!login_id) { fail(t('auth.errIdRequired'), 'login_id'); return; }
      if (!dobInput) { fail(t('auth.errDob'), 'date_of_birth'); return; }
      if (!date_of_birth) { fail(t('auth.errDobFormat'), 'date_of_birth'); return; }
      if (!phone) { fail(t('auth.errPhoneFormat'), 'phone'); return; }
      if (!/^[0-9]{4}$/.test(new_pin)) { fail(t('auth.errPinDigits'), 'new_pin'); return; }
      if (new_pin !== confirm_pin) { fail(t('auth.errPinsMatch'), 'confirm_pin'); return; }

      submitBtn.disabled = true;
      submitBtn.textContent = t('auth.resetting');
      try {
        await api.forgotPin({ login_id, date_of_birth, phone, new_pin });
        showToast(t('auth.pinReset'), 'success');
        window.location.hash = '#/login';
      } catch (err) {
        const msg = getErrorMessage(err, t('auth.errForgot'));
        showError(msg);
        showToast(msg, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = t('auth.resetPin');
      }
      return;
    }

    // register
    const nida = String(fd.get('nida') || '').trim();
    const full_name = String(fd.get('full_name') || '').trim();
    const tin = String(fd.get('tin') || '').trim();
    const phone = String(fd.get('phone') || '').trim();
    const email = String(fd.get('email') || '').trim();
    const location = String(fd.get('location') || '').trim();
    const business_type = String(fd.get('business_type') || '');
    const gender = String(fd.get('gender') || '');
    const dateOfBirthInput = String(fd.get('date_of_birth') || '');
    const date_of_birth = dmyToIso(dateOfBirthInput);
    const pin = String(fd.get('pin') || '');
    const confirm_pin = String(fd.get('confirm_pin') || '');

    if (!/^[0-9]{20}$/.test(nida)) { fail(t('auth.errNida'), 'nida'); return; }
    if (!full_name) { fail(t('auth.errFullName'), 'full_name'); return; }
    const tinClean = tin.replace(/\D/g, '');
    if (!/^[0-9]{9}$/.test(tinClean)) { fail(t('auth.errTin'), 'tin'); return; }
    const normalizedPhone = normalizeTzPhone(phone);
    if (!normalizedPhone) { fail(t('auth.errPhoneFormat'), 'phone'); return; }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { fail(t('auth.errEmail'), 'email'); return; }
    if (!location) { fail(t('auth.errLocation'), 'location'); return; }
    if (!business_type) { fail(t('auth.errBusinessType'), 'business_type'); return; }
    if (!gender) { fail(t('auth.errGender'), 'gender'); return; }
    if (!dateOfBirthInput) { fail(t('auth.errDob'), 'date_of_birth'); return; }
    if (!date_of_birth) { fail(t('auth.errDobFormat'), 'date_of_birth'); return; }
    if (nida.slice(0, 8) !== date_of_birth.replaceAll('-', '')) {
      fail(t('auth.errDobNidaMismatch'), 'date_of_birth');
      return;
    }
    if (!/^[0-9]{4}$/.test(pin)) { fail(t('auth.errPinDigits'), 'pin'); return; }
    if (pin !== confirm_pin) { fail(t('auth.errPinsMatch'), 'confirm_pin'); return; }

    submitBtn.disabled = true;
    submitBtn.textContent = t('auth.creating');
    try {
      await api.registerSme({
        nida, phone: normalizedPhone, full_name, email, location, business_type, gender,
        nationality: 'Tanzanian', date_of_birth, tin: tinClean, pin,
      });
      const loginPayload = await api.login({ login_id: nida, pin });
      if (!loginPayload?.access_token && !loginPayload?.token) {
        throw new Error(t('auth.errNoToken'));
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
      showToast(t('auth.accountCreated'), 'success');
      onSuccess();
    } catch (err) {
      const msg = getErrorMessage(err, t('auth.errRegister'));
      showError(msg);
      showToast(msg, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t('auth.createAccountBtn');
    }
  });
}

export { escapeHtml };
