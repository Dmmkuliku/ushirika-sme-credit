/**
 * Shared profile modal for SME, lender, admin, and sub-admin roles.
 */

import * as api from '../api.js';
import { escapeHtml, formatDate, getErrorMessage, capitalize } from '../utils.js';
import { showToast } from '../ui.js';

const BUSINESS_TYPES = [
  'Entrepreneur', 'Machinga', 'Retailer', 'Wholesaler', 'Manufacturer',
  'Farmer', 'Service Provider', 'Transport', 'Food Vendor', 'Other',
];

const GENDER_OPTIONS = ['Male', 'Female', 'Other'];

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
  if (role === 'admin') return 'Admin Profile';
  if (role === 'subadmin') return 'Sub-Admin Profile';
  if (role === 'lender') return 'Lender Profile';
  return 'SME Profile';
}

function genderSelect(id, name, value) {
  const opts = GENDER_OPTIONS.map(
    (g) => `<option value="${escapeHtml(g)}"${g === value ? ' selected' : ''}>${escapeHtml(g)}</option>`
  ).join('');
  return `
    <div class="field">
      <label for="${id}">Gender</label>
      <select id="${id}" name="${name}">
        <option value="">Select…</option>
        ${opts}
      </select>
    </div>`;
}

function businessTypeSelect(value) {
  const opts = BUSINESS_TYPES.map(
    (t) => `<option value="${escapeHtml(t)}"${t === value ? ' selected' : ''}>${escapeHtml(t)}</option>`
  ).join('');
  return `
    <div class="field">
      <label for="prof-business_type">Business type</label>
      <select id="prof-business_type" name="business_type">
        <option value="">Select…</option>
        ${opts}
      </select>
    </div>`;
}

function viewFieldsHtml(role, profile) {
  const rows = [];

  if (role === 'sme') {
    rows.push(['Full name', profile.full_name]);
    rows.push(['Phone', profile.phone]);
    rows.push(['Email', profile.email || '—']);
    rows.push(['Location', profile.location]);
    rows.push(['Business type', profile.business_type]);
    rows.push(['Gender', profile.gender]);
    rows.push(['Nationality', profile.nationality]);
    rows.push(['NIDA', profile.nida]);
    rows.push(['Login ID', profile.nida]);
    rows.push(['Date of birth', formatDate(profile.date_of_birth)]);
  } else if (role === 'lender') {
    rows.push(['Full name', profile.full_name]);
    rows.push(['Gender', profile.gender]);
    rows.push(['Organization', profile.organization]);
    rows.push(['Work email', profile.work_email]);
    rows.push(['Phone', profile.phone || '—']);
    rows.push(['Membership #', profile.membership_number]);
  } else {
    rows.push(['Full name', profile.full_name]);
    rows.push(['Gender', profile.gender]);
    rows.push(['Login ID', profile.login_id]);
    rows.push(['Role', capitalize(profile.role || role)]);
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
            <label for="prof-full_name">Full name</label>
            <input id="prof-full_name" name="full_name" type="text" required value="${escapeHtml(profile.full_name || '')}" />
          </div>
          <div class="field">
            <label for="prof-phone">Phone</label>
            <input id="prof-phone" name="phone" type="tel" required value="${escapeHtml(profile.phone || '')}" />
          </div>
        </div>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-email">Email</label>
            <input id="prof-email" name="email" type="email" value="${escapeHtml(profile.email || '')}" />
          </div>
          <div class="field">
            <label for="prof-location">Location</label>
            <input id="prof-location" name="location" type="text" required value="${escapeHtml(profile.location || '')}" />
          </div>
        </div>
        <div class="form-grid-2">
          ${businessTypeSelect(profile.business_type)}
          ${genderSelect('prof-gender', 'gender', profile.gender)}
        </div>
        <div class="field">
          <label for="prof-nationality">Nationality</label>
          <input id="prof-nationality" name="nationality" type="text" required value="${escapeHtml(profile.nationality || '')}" />
        </div>
        <div class="profile-readonly-note">
          <p><strong>Read-only:</strong> NIDA ${escapeHtml(profile.nida || '—')}, DOB ${escapeHtml(formatDate(profile.date_of_birth))}, Login ID ${escapeHtml(profile.nida || '—')}</p>
        </div>
        <div id="profile-edit-error" class="form-error" hidden></div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="profile-edit-cancel">Cancel</button>
          <button type="submit" class="btn btn-primary" id="profile-edit-save">Save profile</button>
        </div>
      </form>`;
  }

  if (role === 'lender') {
    return `
      <form id="profile-edit-form" class="auth-form" novalidate>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-full_name">Full name</label>
            <input id="prof-full_name" name="full_name" type="text" required value="${escapeHtml(profile.full_name || '')}" />
          </div>
          ${genderSelect('prof-gender', 'gender', profile.gender)}
        </div>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-organization">Organization</label>
            <input id="prof-organization" name="organization" type="text" required value="${escapeHtml(profile.organization || '')}" />
          </div>
          <div class="field">
            <label for="prof-work_email">Work email</label>
            <input id="prof-work_email" name="work_email" type="email" required value="${escapeHtml(profile.work_email || '')}" />
          </div>
        </div>
        <div class="field">
          <label for="prof-phone">Phone <span class="optional">(optional)</span></label>
          <input id="prof-phone" name="phone" type="tel" value="${escapeHtml(profile.phone || '')}" />
        </div>
        <div class="profile-readonly-note">
          <p><strong>Read-only:</strong> Membership # ${escapeHtml(profile.membership_number || '—')}</p>
        </div>
        <div id="profile-edit-error" class="form-error" hidden></div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="profile-edit-cancel">Cancel</button>
          <button type="submit" class="btn btn-primary" id="profile-edit-save">Save profile</button>
        </div>
      </form>`;
  }

  return `
    <form id="profile-edit-form" class="auth-form" novalidate>
      <div class="form-grid-2">
        <div class="field">
          <label for="prof-full_name">Full name</label>
          <input id="prof-full_name" name="full_name" type="text" required value="${escapeHtml(profile.full_name || '')}" />
        </div>
        ${genderSelect('prof-gender', 'gender', profile.gender)}
      </div>
      <div class="profile-readonly-note">
        <p><strong>Read-only:</strong> Login ID ${escapeHtml(profile.login_id || '—')}, Role ${escapeHtml(capitalize(profile.role || role))}</p>
      </div>
      <div id="profile-edit-error" class="form-error" hidden></div>
      <div class="modal-actions">
        <button type="button" class="btn btn-ghost" id="profile-edit-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary" id="profile-edit-save">Save profile</button>
      </div>
    </form>`;
}

function pinSectionHtml() {
  return `
    <section class="profile-pin-section" aria-labelledby="pin-section-title">
      <h4 id="pin-section-title">Change PIN</h4>
      <form id="profile-pin-form" class="auth-form" novalidate>
        <div class="form-grid-2">
          <div class="field">
            <label for="prof-current-pin">Current PIN</label>
            <input id="prof-current-pin" name="current_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="4 digits" />
          </div>
          <div class="field">
            <label for="prof-new-pin">New PIN</label>
            <input id="prof-new-pin" name="new_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="4 digits" />
          </div>
        </div>
        <div class="field">
          <label for="prof-confirm-pin">Confirm new PIN</label>
          <input id="prof-confirm-pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="Re-enter" />
        </div>
        <div id="profile-pin-error" class="form-error" hidden></div>
        <button type="submit" class="btn btn-secondary" id="profile-pin-save">Update PIN</button>
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
            <button type="button" class="btn btn-ghost" id="profile-close">Close</button>
            <button type="button" class="btn btn-primary" id="profile-edit-btn">Edit profile</button>
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

  document.getElementById('profile-edit-cancel')?.addEventListener('click', () => {
    renderModal(role, profile, 'view', { onUpdated });
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }

    const fd = new FormData(form);
    let data = {};

    if (role === 'sme') {
      data = {
        full_name: fd.get('full_name'),
        phone: fd.get('phone'),
        email: fd.get('email') || undefined,
        location: fd.get('location'),
        business_type: fd.get('business_type'),
        gender: fd.get('gender'),
        nationality: fd.get('nationality'),
      };
    } else if (role === 'lender') {
      data = {
        full_name: fd.get('full_name'),
        gender: fd.get('gender'),
        organization: fd.get('organization'),
        work_email: fd.get('work_email'),
        phone: fd.get('phone') || undefined,
      };
    } else {
      const full_name = String(fd.get('full_name') || '').trim();
      const gender = String(fd.get('gender') || '').trim();
      if (!full_name) {
        if (errEl) { errEl.hidden = false; errEl.textContent = 'Full name is required.'; }
        return;
      }
      if (!gender || !['Male', 'Female', 'Other'].includes(gender)) {
        if (errEl) { errEl.hidden = false; errEl.textContent = 'Please select a gender.'; }
        return;
      }
      data = { full_name, gender };
    }

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';
    try {
      await updateProfile(role, data);
      showToast('Profile updated.', 'success');
      // Reload full profile so view mode has all fields
      const refreshed = await loadProfile(role);
      onUpdated?.(refreshed);
      renderModal(role, refreshed, 'view', { onUpdated });
    } catch (err) {
      const msg = getErrorMessage(err, 'Could not update profile');
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save profile';
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
      if (errEl) { errEl.hidden = false; errEl.textContent = 'Current PIN must be exactly 4 digits.'; }
      return;
    }
    if (!/^[0-9]{4}$/.test(new_pin)) {
      if (errEl) { errEl.hidden = false; errEl.textContent = 'New PIN must be exactly 4 digits.'; }
      return;
    }
    if (new_pin !== confirm_pin) {
      if (errEl) { errEl.hidden = false; errEl.textContent = 'New PINs do not match.'; }
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = 'Updating…';
    try {
      await api.changePin({ current_pin, new_pin });
      showToast('PIN updated.', 'success');
      form.reset();
    } catch (err) {
      const msg = getErrorMessage(err, 'Could not change PIN');
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Update PIN';
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
        <p role="status">Loading profile…</p>
      </div>
    </div>
  `;

  try {
    const profile = await loadProfile(role);
    renderModal(role, profile, 'view', { onUpdated });
  } catch (err) {
    closeModal();
    showToast(getErrorMessage(err, 'Could not load profile'), 'error');
  }
}
