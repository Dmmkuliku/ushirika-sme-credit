/**
 * Shared profile modal for SME, lender, admin, and sub-admin roles.
 */

import * as api from '../api.js';
import { escapeHtml, formatBirthDate, getErrorMessage, capitalize } from '../utils.js';
import { showToast } from '../ui.js';
import { businessTypeLabel, genderLabel, t } from '../i18n.js';
import {
  bindImmediateEmailValidation,
  formatTzPhone,
  normalizeTzPhone,
  phoneInputHtml,
} from '../form-validation.js';

const BUSINESS_TYPES = [
  'Entrepreneur', 'Machinga', 'Retailer', 'Wholesaler', 'Manufacturer',
  'Farmer', 'Service Provider', 'Transport', 'Food Vendor', 'Other',
];

const GENDER_OPTIONS = ['Male', 'Female'];

function modalHost() {
  let host = document.getElementById('profile-modal-host');
  if (!host) {
    host = document.createElement('div');
    host.id = 'profile-modal-host';
    document.body.appendChild(host);
  }
  return host;
}

function closeModal() {
  const host = document.getElementById('profile-modal-host');
  if (host) host.innerHTML = '';
}

async function loadProfile(role) {
  if (role === 'sme') return api.getSmeProfile();
  if (role === 'lender') return api.getLenderProfile();
  if (role === 'admin' || role === 'subadmin') {
    try {
      return await api.getAdminProfile();
    } catch {
      // Fallback if /admin/profile is unavailable
      return api.getMe();
    }
  }
  throw new Error(`Unsupported role: ${role}`);
}

async function updateProfile(role, data) {
  if (role === 'sme') return api.updateSmeProfile(data);
  if (role === 'lender') return api.updateLenderProfile(data);
  if (role === 'admin' || role === 'subadmin') return api.updateAdminProfile(data);
  throw new Error(`Unsupported role: ${role}`);
}

function roleTitle(role) {
  if (role === 'admin') return t('profile.adminTitle');
  if (role === 'subadmin') return t('profile.subadminTitle');
  if (role === 'lender') return t('profile.lenderTitle');
  return t('profile.smeTitle');
}

function genderSelect(id, name, value) {
  const opts = GENDER_OPTIONS.map(
    (g) => {
      const label = g === 'Male' ? t('auth.genderMale') : t('auth.genderFemale');
      return `<option value="${escapeHtml(g)}"${g === value ? ' selected' : ''}>${escapeHtml(label)}</option>`;
    }
  ).join('');
  return `
    <div class="field">
      <label for="${id}">${escapeHtml(t('profile.gender'))}</label>
      <select id="${id}" name="${name}">
        <option value="">${escapeHtml(t('common.select'))}</option>
        ${opts}
      </select>
    </div>`;
}

function businessTypeSelect(value) {
  const opts = BUSINESS_TYPES.map(
    (bt) => `<option value="${escapeHtml(bt)}"${bt === value ? ' selected' : ''}>${escapeHtml(businessTypeLabel(bt))}</option>`
  ).join('');
  return `
    <div class="field">
      <label for="prof-business_type">${escapeHtml(t('profile.businessType'))}</label>
      <select id="prof-business_type" name="business_type">
        <option value="">${escapeHtml(t('common.select'))}</option>
        ${opts}
      </select>
    </div>`;
}

function viewFieldsHtml(role, profile) {
  const rows = [];

  if (role === 'sme') {
    rows.push([t('profile.fullName'), profile.full_name]);
    rows.push([t('profile.phone'), formatTzPhone(profile.phone)]);
    rows.push([t('profile.email'), profile.email || '—']);
    rows.push([t('profile.location'), profile.location]);
    rows.push([t('profile.businessType'), businessTypeLabel(profile.business_type)]);
    rows.push([t('profile.gender'), genderLabel(profile.gender)]);
    rows.push([t('profile.nida'), profile.nida]);
    rows.push([t('profile.tin'), profile.tin || '—']);
    rows.push([t('profile.loginId'), profile.nida]);
    rows.push([t('profile.dateOfBirth'), formatBirthDate(profile.date_of_birth)]);
  } else if (role === 'lender') {
    rows.push([t('profile.fullName'), profile.full_name]);
    rows.push([t('profile.gender'), genderLabel(profile.gender)]);
    rows.push([t('profile.organization'), profile.organization]);
    rows.push([t('profile.workEmail'), profile.work_email]);
    rows.push([t('profile.phone'), profile.phone ? formatTzPhone(profile.phone) : '—']);
    rows.push([t('profile.membership'), profile.membership_number]);
  } else {
    rows.push([t('profile.fullName'), profile.full_name]);
    rows.push([t('profile.gender'), genderLabel(profile.gender)]);
    rows.push([t('profile.loginId'), profile.login_id]);
    rows.push([t('profile.role'), capitalize(profile.role || role)]);
  }

  return `
    <dl class="profile-dl">
      ${rows
        .map(
          ([label, val]) =>
            `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(val != null && val !== '' ? String(val) : '—')}</dd>`
        )
        .join('')}
    </dl>`;
}

function editFormHtml(role, profile) {
  if (role === 'sme') {
    return `
      <form id="profile-edit-form" class="auth-form" novalidate>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-full_name">${escapeHtml(t('profile.fullName'))}</label>
            <input id="prof-full_name" name="full_name" type="text" required value="${escapeHtml(profile.full_name || '')}" />
          </div>
          <div class="field">
            <label for="prof-phone">${escapeHtml(t('profile.phone'))}</label>
            ${phoneInputHtml({ id: 'prof-phone', value: profile.phone, required: true })}
          </div>
        </div>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-email">${escapeHtml(t('profile.email'))}</label>
            <input id="prof-email" name="email" type="email" value="${escapeHtml(profile.email || '')}" />
          </div>
          <div class="field">
            <label for="prof-location">${escapeHtml(t('profile.location'))}</label>
            <input id="prof-location" name="location" type="text" required value="${escapeHtml(profile.location || '')}" />
          </div>
        </div>
        <div class="form-grid-2">
          ${businessTypeSelect(profile.business_type)}
          ${genderSelect('prof-gender', 'gender', profile.gender)}
        </div>
        <div class="profile-readonly-note">
          <p><strong>${escapeHtml(t('profile.readonly'))}:</strong> ${escapeHtml(t('profile.nida'))} ${escapeHtml(profile.nida || '—')}, ${escapeHtml(t('profile.tin'))} ${escapeHtml(profile.tin || '—')}, ${escapeHtml(t('profile.dateOfBirth'))} ${escapeHtml(formatBirthDate(profile.date_of_birth))}</p>
        </div>
        <div id="profile-edit-error" class="form-error" hidden></div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="profile-edit-cancel">${escapeHtml(t('common.cancel'))}</button>
          <button type="submit" class="btn btn-primary" id="profile-edit-save">${escapeHtml(t('profile.saveProfile'))}</button>
        </div>
      </form>`;
  }

  if (role === 'lender') {
    return `
      <form id="profile-edit-form" class="auth-form" novalidate>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-full_name">${escapeHtml(t('profile.fullName'))}</label>
            <input id="prof-full_name" name="full_name" type="text" required value="${escapeHtml(profile.full_name || '')}" />
          </div>
          ${genderSelect('prof-gender', 'gender', profile.gender)}
        </div>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-organization">${escapeHtml(t('profile.organization'))}</label>
            <input id="prof-organization" name="organization" type="text" required value="${escapeHtml(profile.organization || '')}" />
          </div>
          <div class="field">
            <label for="prof-work_email">${escapeHtml(t('profile.workEmail'))}</label>
            <input id="prof-work_email" name="work_email" type="email" required value="${escapeHtml(profile.work_email || '')}" />
          </div>
        </div>
        <div class="field">
          <label for="prof-phone">${escapeHtml(t('profile.phone'))} <span class="optional">${escapeHtml(t('common.optional'))}</span></label>
          ${phoneInputHtml({ id: 'prof-phone', value: profile.phone })}
        </div>
        <div class="profile-readonly-note">
          <p><strong>${escapeHtml(t('profile.readonly'))}:</strong> ${escapeHtml(t('profile.membership'))} ${escapeHtml(profile.membership_number || '—')}</p>
        </div>
        <div id="profile-edit-error" class="form-error" hidden></div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="profile-edit-cancel">${escapeHtml(t('common.cancel'))}</button>
          <button type="submit" class="btn btn-primary" id="profile-edit-save">${escapeHtml(t('profile.saveProfile'))}</button>
        </div>
      </form>`;
  }

  return `
    <form id="profile-edit-form" class="auth-form" novalidate>
      <div class="form-grid-2">
        <div class="field">
          <label for="prof-full_name">${escapeHtml(t('profile.fullName'))}</label>
          <input id="prof-full_name" name="full_name" type="text" required value="${escapeHtml(profile.full_name || '')}" />
        </div>
        ${genderSelect('prof-gender', 'gender', profile.gender)}
      </div>
      <div class="profile-readonly-note">
        <p><strong>${escapeHtml(t('profile.readonly'))}:</strong> ${escapeHtml(t('profile.loginId'))} ${escapeHtml(profile.login_id || '—')}, ${escapeHtml(t('profile.role'))} ${escapeHtml(capitalize(profile.role || role))}</p>
      </div>
      <div id="profile-edit-error" class="form-error" hidden></div>
      <div class="modal-actions">
        <button type="button" class="btn btn-ghost" id="profile-edit-cancel">${escapeHtml(t('common.cancel'))}</button>
        <button type="submit" class="btn btn-primary" id="profile-edit-save">${escapeHtml(t('profile.saveProfile'))}</button>
      </div>
    </form>`;
}

function pinSectionHtml() {
  return `
    <section class="profile-pin-section" aria-labelledby="pin-section-title">
      <h4 id="pin-section-title">${escapeHtml(t('profile.changePin'))}</h4>
      <form id="profile-pin-form" class="auth-form" novalidate>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-current-pin">${escapeHtml(t('profile.currentPin'))}</label>
            <input id="prof-current-pin" name="current_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="4 digits" />
          </div>
          <div class="field">
            <label for="prof-new-pin">${escapeHtml(t('profile.newPin'))}</label>
            <input id="prof-new-pin" name="new_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="4 digits" />
          </div>
        </div>
        <div class="field">
          <label for="prof-confirm-pin">${escapeHtml(t('profile.confirmNewPin'))}</label>
          <input id="prof-confirm-pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="Re-enter" />
        </div>
        <div id="profile-pin-error" class="form-error" hidden></div>
        <button type="submit" class="btn btn-secondary" id="profile-pin-save">${escapeHtml(t('profile.updatePin'))}</button>
      </form>
    </section>`;
}

function renderModal(role, profile, mode, { onUpdated }) {
  const host = modalHost();
  const isEdit = mode === 'edit';

  host.innerHTML = `
    <div class="modal-backdrop" id="profile-modal-backdrop">
      <div class="modal-dialog profile-card profile-modal-wide" role="dialog" aria-modal="true" aria-labelledby="profile-modal-title">
        <h3 id="profile-modal-title">${escapeHtml(roleTitle(role))}</h3>
        <div id="profile-modal-body">
          ${isEdit ? editFormHtml(role, profile) : viewFieldsHtml(role, profile)}
        </div>
        ${!isEdit ? `
          <div class="modal-actions profile-view-actions">
            <button type="button" class="btn btn-ghost" id="profile-close">${escapeHtml(t('common.close'))}</button>
            <button type="button" class="btn btn-primary" id="profile-edit-btn">${escapeHtml(t('profile.editProfile'))}</button>
          </div>
        ` : ''}
        ${pinSectionHtml()}
      </div>
    </div>
  `;

  document.getElementById('profile-close')?.addEventListener('click', closeModal);
  document.getElementById('profile-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'profile-modal-backdrop') closeModal();
  });

  document.getElementById('profile-edit-btn')?.addEventListener('click', () => {
    renderModal(role, profile, 'edit', { onUpdated });
    bindEditForm(role, profile, { onUpdated });
    bindPinForm();
  });

  if (isEdit) {
    bindEditForm(role, profile, { onUpdated });
  }

  bindPinForm();
}

function bindEditForm(role, profile, { onUpdated }) {
  const form = document.getElementById('profile-edit-form');
  const errEl = document.getElementById('profile-edit-error');
  const saveBtn = document.getElementById('profile-edit-save');
  bindImmediateEmailValidation(
    document.getElementById(role === 'lender' ? 'prof-work_email' : 'prof-email'),
    t('auth.errEmail'),
  );

  document.getElementById('profile-edit-cancel')?.addEventListener('click', () => {
    renderModal(role, profile, 'view', { onUpdated });
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }

    const fd = new FormData(form);
    let data = {};

    if (role === 'sme') {
      const email = String(fd.get('email') || '').trim();
      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errEmail'); }
        return;
      }
      const phone = normalizeTzPhone(fd.get('phone'));
      if (!phone) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errPhoneFormat'); }
        return;
      }
      data = {
        full_name: fd.get('full_name'),
        phone,
        email: email || undefined,
        location: fd.get('location'),
        business_type: fd.get('business_type'),
        gender: fd.get('gender'),
      };
    } else if (role === 'lender') {
      const work_email = String(fd.get('work_email') || '').trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(work_email)) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errEmail'); }
        return;
      }
      const phoneRaw = String(fd.get('phone') || '').trim();
      const phone = phoneRaw ? normalizeTzPhone(phoneRaw) : undefined;
      if (phoneRaw && !phone) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errPhoneFormat'); }
        return;
      }
      data = {
        full_name: fd.get('full_name'),
        gender: fd.get('gender'),
        organization: fd.get('organization'),
        work_email,
        phone,
      };
    } else {
      const full_name = String(fd.get('full_name') || '').trim();
      const gender = String(fd.get('gender') || '').trim();
      if (!full_name) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('profile.errFullName'); }
        return;
      }
      if (!gender || !['Male', 'Female'].includes(gender)) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('profile.errGender'); }
        return;
      }
      data = { full_name, gender };
    }

    saveBtn.disabled = true;
    saveBtn.textContent = t('profile.saving');
    try {
      await updateProfile(role, data);
      showToast(t('profile.profileUpdated'), 'success');
      // Reload full profile so view mode has all fields
      const refreshed = await loadProfile(role);
      onUpdated?.(refreshed);
      renderModal(role, refreshed, 'view', { onUpdated });
    } catch (err) {
      const msg = getErrorMessage(err, t('profile.updateFailed'));
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = t('profile.saveProfile');
    }
  });
}

function bindPinForm() {
  const form = document.getElementById('profile-pin-form');
  const errEl = document.getElementById('profile-pin-error');
  const saveBtn = document.getElementById('profile-pin-save');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }

    const current_pin = String(document.getElementById('prof-current-pin')?.value || '');
    const new_pin = String(document.getElementById('prof-new-pin')?.value || '');
    const confirm_pin = String(document.getElementById('prof-confirm-pin')?.value || '');

    if (!/^[0-9]{4}$/.test(current_pin)) {
      if (errEl) { errEl.hidden = false; errEl.textContent = t('profile.errCurrentPin'); }
      return;
    }
    if (!/^[0-9]{4}$/.test(new_pin)) {
      if (errEl) { errEl.hidden = false; errEl.textContent = t('profile.errNewPin'); }
      return;
    }
    if (new_pin !== confirm_pin) {
      if (errEl) { errEl.hidden = false; errEl.textContent = t('profile.errPinsMatch'); }
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = t('profile.updating');
    try {
      await api.changePin({ current_pin, new_pin });
      showToast(t('profile.pinUpdated'), 'success');
      form.reset();
    } catch (err) {
      const msg = getErrorMessage(err, t('profile.pinFailed'));
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = t('profile.updatePin');
    }
  });
}

/**
 * Open the shared profile modal for the given role.
 * @param {'sme'|'lender'|'admin'|'subadmin'} role
 * @param {{ onUpdated?: (profile: object) => void }} [options]
 */
export async function openProfileModal(role, { onUpdated } = {}) {
  const host = modalHost();
  host.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal-dialog profile-card">
        <p role="status">${escapeHtml(t('profile.loading'))}</p>
      </div>
    </div>
  `;

  try {
    const profile = await loadProfile(role);
    renderModal(role, profile, 'view', { onUpdated });
  } catch (err) {
    closeModal();
    showToast(getErrorMessage(err, t('profile.loadFailed')), 'error');
  }
}
