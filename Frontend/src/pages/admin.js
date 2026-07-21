/**
 * Admin dashboard: account management, create lender/SME/sub-admin.
 */

import * as api from '../api.js';
import {
  escapeHtml,
  formatDate,
  normalizeListPayload,
  getErrorMessage,
} from '../utils.js';
import {
  renderShell,
  bindShellActions,
  loadingBlock,
  emptyBlock,
  errorBlock,
  showToast,
} from '../ui.js';
import { openProfileModal } from './profile.js';
import { businessTypeLabel, genderLabel, t } from '../i18n.js';
import {
  bindExactDigitsValidation,
  bindImmediateEmailValidation,
  bindNidaMatchedDobValidation,
  dmyToIso,
  normalizeTzPhone,
  phoneInputHtml,
} from '../form-validation.js';

const BUSINESS_TYPES = [
  'Entrepreneur', 'Machinga', 'Retailer', 'Wholesaler', 'Manufacturer',
  'Farmer', 'Service Provider', 'Transport', 'Food Vendor', 'Other',
];

function genderOptions(selected = '') {
  return ['Male', 'Female'].map(
    (value) => `<option value="${value}"${selected === value ? ' selected' : ''}>${escapeHtml(genderLabel(value))}</option>`,
  ).join('');
}

function businessTypeOptions(selected = '') {
  return BUSINESS_TYPES.map(
    (value) => `<option value="${escapeHtml(value)}"${selected === value ? ' selected' : ''}>${escapeHtml(businessTypeLabel(value))}</option>`,
  ).join('');
}

function roleText(role) {
  const normalized = String(role || '').toLowerCase();
  return t(`roles.${normalized}`);
}

function bindAdminShell(session, onLogout) {
  const openProfile = () => openProfileModal(session.role);
  bindShellActions({ onLogout, onProfile: openProfile });
  document.getElementById('btn-page-profile')?.addEventListener('click', openProfile);
}

export async function loadAdminPage(session, { onLogout, sub = 'accounts', editId = null }) {
  if (sub === 'profile') return loadAdminProfilePage(session, { onLogout });
  if (sub === 'ml') {
    window.location.hash = '#/admin';
    return loadAccounts(session, { onLogout });
  }
  if (sub === 'create-lender') return loadCreateLender(session, { onLogout });
  if (sub === 'create-sme') return loadCreateSme(session, { onLogout });
  if (sub === 'create-subadmin') return loadCreateSubAdmin(session, { onLogout });
  if (sub === 'edit' && editId) return loadEditAccount(session, { onLogout, editId });
  return loadAccounts(session, { onLogout });
}

async function loadAdminProfilePage(session, { onLogout }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: session.role,
    user: session.user,
    activeNav: 'profile',
    mainHtml: `
      <div class="page-header">
        <div>
          <h1>${escapeHtml(t('nav.myProfile'))}</h1>
          <p class="page-lead">${escapeHtml(t('admin.profileLead'))}</p>
        </div>
        <div class="page-actions">
          <button type="button" id="btn-open-profile" class="btn btn-primary">${escapeHtml(t('admin.openProfile'))}</button>
        </div>
      </div>
      <section class="panel" id="admin-profile-panel">
        ${loadingBlock(t('profile.loading'))}
      </section>
    `,
  });
  bindAdminShell(session, onLogout);

  const panel = document.getElementById('admin-profile-panel');
  const open = () => openProfileModal(session.role, {
    onUpdated: (p) => {
      if (p?.full_name) {
        const nameEl = document.querySelector('.user-name');
        if (nameEl) nameEl.textContent = p.full_name;
      }
    },
  });

  document.getElementById('btn-open-profile')?.addEventListener('click', open);

  try {
    const profile = await api.getAdminProfile().catch(() => api.getMe());
    panel.innerHTML = `
      <dl class="profile-dl profile-dl-inline">
        <dt>${escapeHtml(t('profile.fullName'))}</dt><dd>${escapeHtml(profile.full_name || '—')}</dd>
        <dt>${escapeHtml(t('profile.loginId'))}</dt><dd>${escapeHtml(profile.login_id || '—')}</dd>
        <dt>${escapeHtml(t('profile.role'))}</dt><dd>${escapeHtml(roleText(profile.role || session.role))}</dd>
        <dt>${escapeHtml(t('profile.gender'))}</dt><dd>${escapeHtml(genderLabel(profile.gender) || '—')}</dd>
        <dt>${escapeHtml(t('common.status'))}</dt><dd>${escapeHtml(profile.is_active === false ? t('common.inactive') : t('common.active'))}</dd>
      </dl>
      <div class="modal-actions" style="justify-content:flex-start;margin-top:1rem">
        <button type="button" class="btn btn-primary" id="btn-edit-profile-inline">${escapeHtml(t('admin.editProfilePin'))}</button>
      </div>
    `;
    document.getElementById('btn-edit-profile-inline')?.addEventListener('click', open);
  } catch (err) {
    panel.innerHTML = errorBlock(t('profile.loadFailed'), getErrorMessage(err), 'retry-admin-profile');
    document.getElementById('retry-admin-profile')?.addEventListener('click', () => loadAdminProfilePage(session, { onLogout }));
  }
}

/* ─── Accounts List ──────────────────────────────────────── */

async function loadAccounts(session, { onLogout }) {
  const app = document.getElementById('app');
  const role = session.role;
  app.innerHTML = renderShell({
    role, user: session.user, activeNav: 'accounts',
    mainHtml: `
      <div class="page-header">
        <div><h1>${escapeHtml(t('admin.title'))}</h1><p class="page-lead">${escapeHtml(t('admin.lead'))}</p></div>
        <div class="page-actions">
          <button type="button" id="btn-page-profile" class="btn btn-secondary">${escapeHtml(t('nav.myProfile'))}</button>
        </div>
      </div>
      <div class="filter-bar">
        <div class="field">
          <label for="acct-role">${escapeHtml(t('admin.filterByRole'))}</label>
          <select id="acct-role">
            <option value="">${escapeHtml(t('admin.roleFilterAll'))}</option>
            <option value="sme">${escapeHtml(t('roles.sme'))}</option>
            <option value="lender">${escapeHtml(t('roles.lender'))}</option>
            <option value="admin">${escapeHtml(t('roles.admin'))}</option>
            <option value="subadmin">${escapeHtml(t('roles.subadmin'))}</option>
          </select>
        </div>
      </div>
      <div id="acct-table-host">${loadingBlock(t('admin.loadingAccounts'))}</div>
      <div id="admin-modal-host"></div>
    `,
  });
  bindAdminShell(session, onLogout);

  const host = document.getElementById('acct-table-host');
  const modalHost = document.getElementById('admin-modal-host');
  const roleSelect = document.getElementById('acct-role');

  async function fetchAccounts() {
    const roleFilter = roleSelect?.value || undefined;
    host.innerHTML = loadingBlock(t('admin.loadingAccounts'));
    try {
      const payload = await api.getAdminAccounts({ role: roleFilter });
      const rows = normalizeListPayload(payload, ['accounts', 'items', 'data', 'results', 'users']);
      host.innerHTML = renderAccountsTable(rows);
      bindAccountActions(rows, host, modalHost);
    } catch (err) {
      host.innerHTML = errorBlock(t('admin.loadAccountsFailed'), getErrorMessage(err), 'retry-acct');
      document.getElementById('retry-acct')?.addEventListener('click', fetchAccounts);
    }
  }

  roleSelect?.addEventListener('change', fetchAccounts);
  await fetchAccounts();
}

function renderAccountsTable(rows) {
  if (!rows.length) return emptyBlock(t('admin.noAccounts'), t('admin.noAccountsLead'));
  return `
    <div class="table-wrap" role="region" aria-label="${escapeHtml(t('admin.accountsTableAria'))}" tabindex="0">
      <table class="data-table">
        <thead>
          <tr>
            <th scope="col">${escapeHtml(t('admin.colId'))}</th>
            <th scope="col">${escapeHtml(t('profile.loginId'))}</th>
            <th scope="col">${escapeHtml(t('profile.fullName'))}</th>
            <th scope="col">${escapeHtml(t('profile.role'))}</th>
            <th scope="col">${escapeHtml(t('profile.gender'))}</th>
            <th scope="col">${escapeHtml(t('common.status'))}</th>
            <th scope="col">${escapeHtml(t('common.created'))}</th>
            <th scope="col">${escapeHtml(t('common.actions'))}</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => {
            const id = r.id || r.user_id || '';
            const loginId = r.login_id || r.nida || r.membership_number || '—';
            const active = r.is_active !== false;
            return `
              <tr>
                <td>${escapeHtml(String(id).slice(0, 8))}</td>
                <td>${escapeHtml(loginId)}</td>
                <td>${escapeHtml(r.full_name || '—')}</td>
                <td><span class="role-pill role-pill-${escapeHtml(r.role || 'sme')}">${escapeHtml(roleText(r.role || 'sme'))}</span></td>
                <td>${escapeHtml(genderLabel(r.gender) || '—')}</td>
                <td><span class="status-badge ${active ? 'status-active' : 'status-inactive'}">${escapeHtml(active ? t('common.active') : t('common.inactive'))}</span></td>
                <td>${escapeHtml(formatDate(r.created_at))}</td>
                <td class="action-cell">
                  <a href="#/admin/edit/${encodeURIComponent(id)}" class="btn btn-ghost btn-sm">${escapeHtml(t('common.edit'))}</a>
                  ${active
                    ? `<button type="button" class="btn btn-ghost btn-sm btn-danger-text" data-delete-id="${escapeHtml(id)}">${escapeHtml(t('common.delete'))}</button>`
                    : `<button type="button" class="btn btn-ghost btn-sm btn-success-text" data-restore-id="${escapeHtml(id)}">${escapeHtml(t('common.restore'))}</button>`
                  }
                  <button type="button" class="btn btn-ghost btn-sm" data-reset-pin-id="${escapeHtml(id)}">${escapeHtml(t('auth.resetPin'))}</button>
                </td>
              </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function bindAccountActions(rows, host, modalHost) {
  host.querySelectorAll('[data-delete-id]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-delete-id');
      showConfirmDialog(modalHost, t('admin.deleteTitle'), t('admin.deleteConfirm'), async () => {
        try {
          await api.deleteAccount(id);
          showToast(t('admin.deleted'), 'success');
          document.getElementById('acct-role')?.dispatchEvent(new Event('change'));
        } catch (err) {
          showToast(getErrorMessage(err, t('admin.deleteFailed')), 'error');
        }
      });
    });
  });

  host.querySelectorAll('[data-restore-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-restore-id');
      try {
        await api.restoreAccount(id);
        showToast(t('admin.restored'), 'success');
        document.getElementById('acct-role')?.dispatchEvent(new Event('change'));
      } catch (err) {
        showToast(getErrorMessage(err, t('admin.restoreFailed')), 'error');
      }
    });
  });

  host.querySelectorAll('[data-reset-pin-id]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-reset-pin-id');
      showResetPinDialog(modalHost, id);
    });
  });
}

function showConfirmDialog(host, title, message, onConfirm) {
  host.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal-dialog">
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(message)}</p>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="modal-cancel">${escapeHtml(t('common.cancel'))}</button>
          <button type="button" class="btn btn-primary btn-danger" id="modal-confirm">${escapeHtml(t('common.confirm'))}</button>
        </div>
      </div>
    </div>
  `;
  document.getElementById('modal-cancel')?.addEventListener('click', () => { host.innerHTML = ''; });
  document.getElementById('modal-confirm')?.addEventListener('click', async () => {
    host.innerHTML = '';
    await onConfirm();
  });
}

function showResetPinDialog(host, userId) {
  host.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal-dialog">
        <h3>${escapeHtml(t('admin.resetPinTitle'))}</h3>
        <form id="reset-pin-form" class="auth-form">
          <div class="field">
            <label for="new-pin">${escapeHtml(t('auth.newPin'))}</label>
            <input id="new-pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.pinPlaceholder'))}" />
          </div>
          <div class="field">
            <label for="confirm-new-pin">${escapeHtml(t('auth.confirmPin'))}</label>
            <input id="confirm-new-pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.confirmPinPlaceholder'))}" />
          </div>
          <div id="reset-pin-error" class="form-error" hidden></div>
          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" id="modal-cancel">${escapeHtml(t('common.cancel'))}</button>
            <button type="submit" class="btn btn-primary">${escapeHtml(t('auth.resetPin'))}</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.getElementById('modal-cancel')?.addEventListener('click', () => { host.innerHTML = ''; });
  document.getElementById('reset-pin-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pin = document.getElementById('new-pin')?.value || '';
    const confirm = document.getElementById('confirm-new-pin')?.value || '';
    const errEl = document.getElementById('reset-pin-error');
    if (!/^[0-9]{4}$/.test(pin)) {
      if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errPinDigits'); }
      return;
    }
    if (pin !== confirm) {
      if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errPinsMatch'); }
      return;
    }
    try {
      await api.resetPin(userId, pin);
      showToast(t('admin.pinResetOk'), 'success');
      host.innerHTML = '';
    } catch (err) {
      showToast(getErrorMessage(err, t('admin.resetFailed')), 'error');
      host.innerHTML = '';
    }
  });
}

/* ─── Create Lender ──────────────────────────────────────── */

function loadCreateLender(session, { onLogout }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'create-lender',
    mainHtml: `
      <div class="page-header"><div><h1>${escapeHtml(t('admin.createLenderTitle'))}</h1></div></div>
      <div class="admin-form-wrap">
        <form id="create-form" class="auth-form panel" novalidate>
          <div class="field"><label for="membership_number">${escapeHtml(t('profile.membership'))}</label><input id="membership_number" name="membership_number" type="text" required /></div>
          <div class="field"><label for="full_name">${escapeHtml(t('profile.fullName'))}</label><input id="full_name" name="full_name" type="text" required /></div>
          <div class="field"><label for="gender">${escapeHtml(t('auth.gender'))}</label><select id="gender" name="gender" required><option value="">${escapeHtml(t('common.select'))}</option>${genderOptions()}</select></div>
          <div class="field"><label for="organization">${escapeHtml(t('profile.organization'))}</label><input id="organization" name="organization" type="text" required placeholder="${escapeHtml(t('admin.orgPlaceholder'))}" /></div>
          <div class="field"><label for="work_email">${escapeHtml(t('profile.workEmail'))}</label><input id="work_email" name="work_email" type="email" required /></div>
          <div class="field"><label for="phone">${escapeHtml(t('profile.phone'))} <span class="optional">${escapeHtml(t('common.optional'))}</span></label>${phoneInputHtml({ id: 'phone' })}</div>
          <div class="field"><label for="pin">${escapeHtml(t('auth.pin'))}</label><input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.pinPlaceholder'))}" /></div>
          <div class="field"><label for="confirm_pin">${escapeHtml(t('auth.confirmPin'))}</label><input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required /></div>
          <div id="create-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="create-submit">${escapeHtml(t('nav.createLender'))}</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);
  bindCreateForm('create-form', async (fd) => {
    const pin = fd.get('pin');
    const confirm_pin = fd.get('confirm_pin');
    if (!/^[0-9]{4}$/.test(pin)) return t('auth.errPinDigits');
    if (pin !== confirm_pin) return t('auth.errPinsMatch');
    const work_email = String(fd.get('work_email') || '').trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(work_email)) return t('auth.errEmail');
    const phoneRaw = String(fd.get('phone') || '').trim();
    const phone = phoneRaw ? normalizeTzPhone(phoneRaw) : undefined;
    if (phoneRaw && !phone) return t('auth.errPhoneFormat');
    await api.createLender({
      membership_number: fd.get('membership_number'),
      full_name: fd.get('full_name'),
      gender: fd.get('gender'),
      organization: fd.get('organization'),
      work_email,
      phone,
      pin,
    });
    return null;
  }, t('admin.lenderCreated'));
}

/* ─── Create SME ─────────────────────────────────────────── */

function loadCreateSme(session, { onLogout }) {
  const bizOptions = businessTypeOptions();
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'create-sme',
    mainHtml: `
      <div class="page-header"><div><h1>${escapeHtml(t('admin.createSmeTitle'))}</h1></div></div>
      <div class="admin-form-wrap">
        <form id="create-form" class="auth-form panel" novalidate>
          <div class="field"><label for="nida">${escapeHtml(t('auth.nida'))}</label><input id="nida" name="nida" type="text" inputmode="numeric" maxlength="20" pattern="[0-9]{20}" required placeholder="${escapeHtml(t('auth.nidaPlaceholder'))}" /></div>
          <div class="field"><label for="full_name">${escapeHtml(t('auth.fullName'))}</label><input id="full_name" name="full_name" type="text" required /></div>
          <div class="field"><label for="phone">${escapeHtml(t('auth.phone'))}</label>${phoneInputHtml({ id: 'phone', required: true })}</div>
          <div class="field"><label for="email">${escapeHtml(t('auth.email'))} <span class="optional">${escapeHtml(t('common.optional'))}</span></label><input id="email" name="email" type="email" /></div>
          <div class="field"><label for="location">${escapeHtml(t('auth.location'))}</label><input id="location" name="location" type="text" required /></div>
          <div class="field"><label for="business_type">${escapeHtml(t('auth.businessType'))}</label><select id="business_type" name="business_type" required><option value="">${escapeHtml(t('common.select'))}</option>${bizOptions}</select></div>
          <div class="field"><label for="gender">${escapeHtml(t('auth.gender'))}</label><select id="gender" name="gender" required><option value="">${escapeHtml(t('common.select'))}</option>${genderOptions()}</select></div>
          <div class="field"><label for="date_of_birth">${escapeHtml(t('auth.dateOfBirth'))}</label><input id="date_of_birth" name="date_of_birth" type="text" inputmode="numeric" maxlength="10" placeholder="DD-MM-YYYY" autocomplete="bday" required /><p class="field-hint">${escapeHtml(t('auth.ageHint'))}</p></div>
          <div class="field"><label for="tin">${escapeHtml(t('admin.createSmeTin'))}</label><input id="tin" name="tin" type="text" inputmode="numeric" required minlength="9" maxlength="9" pattern="[0-9]{9}" placeholder="${escapeHtml(t('auth.tinPlaceholder'))}" /></div>
          <div class="field"><label for="pin">${escapeHtml(t('auth.pin'))}</label><input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.pinPlaceholder'))}" /></div>
          <div class="field"><label for="confirm_pin">${escapeHtml(t('auth.confirmPin'))}</label><input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required /></div>
          <div id="create-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="create-submit">${escapeHtml(t('nav.createSme'))}</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);
  bindCreateForm('create-form', async (fd) => {
    const nida = fd.get('nida');
    const pin = fd.get('pin');
    const confirm_pin = fd.get('confirm_pin');
    const tin = String(fd.get('tin') || '').trim().replace(/\D/g, '');
    if (!/^[0-9]{20}$/.test(nida)) return t('auth.errNida');
    if (!/^[0-9]{9}$/.test(tin)) return t('admin.tinRequired');
    if (!/^[0-9]{4}$/.test(pin)) return t('auth.errPinDigits');
    if (pin !== confirm_pin) return t('auth.errPinsMatch');
    const email = String(fd.get('email') || '').trim();
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return t('auth.errEmail');
    const phone = normalizeTzPhone(fd.get('phone'));
    if (!phone) return t('auth.errPhoneFormat');
    const dateOfBirth = dmyToIso(String(fd.get('date_of_birth') || ''));
    if (!dateOfBirth) return t('auth.errDobFormat');
    if (String(nida).slice(0, 8) !== dateOfBirth.replaceAll('-', '')) {
      return t('auth.errDobNidaMismatch');
    }
    await api.createSmeByAdmin({
      nida, full_name: fd.get('full_name'), phone,
      email: email || undefined, location: fd.get('location'),
      business_type: fd.get('business_type'), gender: fd.get('gender'),
      nationality: 'Tanzanian', date_of_birth: dateOfBirth,
      tin, pin,
    });
    return null;
  }, t('admin.smeCreated'));
}

/* ─── Create Sub-Admin ───────────────────────────────────── */

function loadCreateSubAdmin(session, { onLogout }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'create-subadmin',
    mainHtml: `
      <div class="page-header"><div><h1>${escapeHtml(t('admin.createSubadminTitle'))}</h1></div></div>
      <div class="admin-form-wrap">
        <form id="create-form" class="auth-form panel" novalidate>
          <div class="field"><label for="login_id">${escapeHtml(t('profile.loginId'))}</label><input id="login_id" name="login_id" type="text" required /></div>
          <div class="field"><label for="full_name">${escapeHtml(t('profile.fullName'))}</label><input id="full_name" name="full_name" type="text" required /></div>
          <div class="field"><label for="gender">${escapeHtml(t('auth.gender'))}</label><select id="gender" name="gender" required><option value="">${escapeHtml(t('common.select'))}</option>${genderOptions()}</select></div>
          <div class="field"><label for="organization">${escapeHtml(t('profile.organization'))}</label><input id="organization" name="organization" type="text" required /></div>
          <div class="field"><label for="work_email">${escapeHtml(t('profile.workEmail'))}</label><input id="work_email" name="work_email" type="email" required /></div>
          <div class="field"><label for="pin">${escapeHtml(t('auth.pin'))}</label><input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="${escapeHtml(t('auth.pinPlaceholder'))}" /></div>
          <div class="field"><label for="confirm_pin">${escapeHtml(t('auth.confirmPin'))}</label><input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required /></div>
          <div id="create-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="create-submit">${escapeHtml(t('nav.createSubadmin'))}</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);
  bindCreateForm('create-form', async (fd) => {
    const pin = fd.get('pin');
    const confirm_pin = fd.get('confirm_pin');
    if (!/^[0-9]{4}$/.test(pin)) return t('auth.errPinDigits');
    if (pin !== confirm_pin) return t('auth.errPinsMatch');
    const work_email = String(fd.get('work_email') || '').trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(work_email)) return t('auth.errEmail');
    await api.createSubAdmin({
      login_id: fd.get('login_id'),
      full_name: fd.get('full_name'),
      gender: fd.get('gender'),
      organization: fd.get('organization'),
      work_email,
      pin,
    });
    return null;
  }, t('admin.subadminCreated'));
}

function bindCreateForm(formId, handler, successMsg) {
  const form = document.getElementById(formId);
  const errEl = document.getElementById('create-error');
  const submitBtn = document.getElementById('create-submit');
  const origText = submitBtn?.textContent || t('common.submit');
  bindExactDigitsValidation(form?.querySelector('input[name="nida"]'), {
    length: 20,
    digitsOnlyMessage: t('auth.errNidaDigitsOnly'),
    exactLengthMessage: t('auth.errNida'),
  });
  bindNidaMatchedDobValidation({
    input: form?.querySelector('input[name="date_of_birth"]'),
    nidaInput: form?.querySelector('input[name="nida"]'),
    invalidDateMessage: t('auth.errDobFormat'),
    mismatchMessage: t('auth.errDobNidaMismatch'),
  });
  bindImmediateEmailValidation(
    form?.querySelector('input[type="email"]'),
    t('auth.errEmail'),
  );

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }
    const fd = new FormData(form);
    submitBtn.disabled = true;
    submitBtn.textContent = t('auth.creating');
    try {
      const validationError = await handler(fd);
      if (validationError) {
        if (errEl) { errEl.hidden = false; errEl.textContent = validationError; }
        return;
      }
      showToast(successMsg, 'success');
      form.reset();
    } catch (err) {
      const msg = getErrorMessage(err, t('admin.createFailed'));
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = origText;
    }
  });
}

/* ─── Edit Account ───────────────────────────────────────── */

async function loadEditAccount(session, { onLogout, editId }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'accounts',
    mainHtml: loadingBlock(t('admin.loadingAccount')),
  });
  bindAdminShell(session, onLogout);

  try {
    const acct = await api.getAdminAccount(editId);
    renderEditForm(session, acct, { onLogout });
  } catch (err) {
    const main = document.getElementById('main');
    if (main) main.innerHTML = errorBlock(t('admin.loadAccountFailed'), getErrorMessage(err));
  }
}

function renderEditForm(session, acct, { onLogout }) {
  const app = document.getElementById('app');
  const acctRole = String(acct.role || '').toLowerCase();
  const isLender = acctRole === 'lender';
  const isSme = acctRole === 'sme';

  let extraFields = '';
  if (isLender) {
    extraFields = `
      <div class="field"><label for="organization">${escapeHtml(t('profile.organization'))}</label><input id="organization" name="organization" type="text" value="${escapeHtml(acct.organization || '')}" /></div>
      <div class="field"><label for="work_email">${escapeHtml(t('profile.workEmail'))}</label><input id="work_email" name="work_email" type="email" value="${escapeHtml(acct.work_email || '')}" /></div>
      <div class="field"><label for="phone">${escapeHtml(t('profile.phone'))}</label>${phoneInputHtml({ id: 'phone', value: acct.phone })}</div>
    `;
  } else if (isSme) {
    const bizOptions = businessTypeOptions(acct.business_type);
    extraFields = `
      <div class="field"><label for="phone">${escapeHtml(t('profile.phone'))}</label>${phoneInputHtml({ id: 'phone', value: acct.phone, required: true })}</div>
      <div class="field"><label for="email">${escapeHtml(t('profile.email'))}</label><input id="email" name="email" type="email" value="${escapeHtml(acct.email || '')}" /></div>
      <div class="field"><label for="location">${escapeHtml(t('profile.location'))}</label><input id="location" name="location" type="text" value="${escapeHtml(acct.location || '')}" /></div>
      <div class="field"><label for="business_type">${escapeHtml(t('auth.businessType'))}</label><select id="business_type" name="business_type"><option value="">${escapeHtml(t('common.select'))}</option>${bizOptions}</select></div>
    `;
  }

  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'accounts',
    mainHtml: `
      <div class="page-header">
        <div><h1>${escapeHtml(t('admin.editTitle'))}</h1><p class="page-lead">${escapeHtml(acct.full_name || '')} — ${escapeHtml(roleText(acctRole))}</p></div>
        <div class="page-actions"><a href="#/admin" class="btn btn-secondary">${escapeHtml(t('admin.backToAccounts'))}</a></div>
      </div>
      <div class="admin-form-wrap">
        <form id="edit-form" class="auth-form panel" novalidate>
          <div class="field"><label for="full_name">${escapeHtml(t('profile.fullName'))}</label><input id="full_name" name="full_name" type="text" required value="${escapeHtml(acct.full_name || '')}" /></div>
          <div class="field"><label for="gender">${escapeHtml(t('auth.gender'))}</label>
            <select id="gender" name="gender">
              <option value="">${escapeHtml(t('common.select'))}</option>
              ${genderOptions(acct.gender)}
            </select>
          </div>
          <div class="field">
            <label for="is_active">${escapeHtml(t('common.status'))}</label>
            <select id="is_active" name="is_active">
              <option value="true" ${acct.is_active !== false ? 'selected' : ''}>${escapeHtml(t('common.active'))}</option>
              <option value="false" ${acct.is_active === false ? 'selected' : ''}>${escapeHtml(t('common.inactive'))}</option>
            </select>
          </div>
          ${extraFields}
          <div id="edit-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="edit-submit">${escapeHtml(t('admin.saveChanges'))}</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);

  const form = document.getElementById('edit-form');
  const errEl = document.getElementById('edit-error');
  const submitBtn = document.getElementById('edit-submit');
  bindImmediateEmailValidation(
    form?.querySelector('input[type="email"]'),
    t('auth.errEmail'),
  );

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }
    submitBtn.disabled = true;
    submitBtn.textContent = t('admin.saving');
    const fd = new FormData(form);
    const data = { full_name: fd.get('full_name'), gender: fd.get('gender'), is_active: fd.get('is_active') === 'true' };
    if (isLender) {
      data.organization = fd.get('organization');
      data.work_email = fd.get('work_email');
      const phoneRaw = String(fd.get('phone') || '').trim();
      data.phone = phoneRaw ? normalizeTzPhone(phoneRaw) : undefined;
      if (phoneRaw && !data.phone) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errPhoneFormat'); }
        submitBtn.disabled = false;
        submitBtn.textContent = t('admin.saveChanges');
        return;
      }
    } else if (isSme) {
      data.phone = normalizeTzPhone(fd.get('phone'));
      if (!data.phone) {
        if (errEl) { errEl.hidden = false; errEl.textContent = t('auth.errPhoneFormat'); }
        submitBtn.disabled = false;
        submitBtn.textContent = t('admin.saveChanges');
        return;
      }
      data.email = fd.get('email') || undefined;
      data.location = fd.get('location');
      data.business_type = fd.get('business_type');
    }
    try {
      await api.updateAccount(acct.id || acct.user_id, data);
      showToast(t('admin.updated'), 'success');
    } catch (err) {
      const msg = getErrorMessage(err, t('admin.updateFailed'));
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t('admin.saveChanges');
    }
  });
}
