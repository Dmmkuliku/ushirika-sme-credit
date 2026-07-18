/**
 * Admin dashboard: account management, create lender/SME/sub-admin.
 */

import * as api from '../api.js';
import {
  escapeHtml,
  formatDate,
  capitalize,
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
import { t } from '../i18n.js';

const BUSINESS_TYPES = [
  'Entrepreneur', 'Machinga', 'Retailer', 'Wholesaler', 'Manufacturer',
  'Farmer', 'Service Provider', 'Transport', 'Food Vendor', 'Other',
];

function bindAdminShell(session, onLogout) {
  const openProfile = () => openProfileModal(session.role);
  bindShellActions({ onLogout, onProfile: openProfile });
  document.getElementById('btn-page-profile')?.addEventListener('click', openProfile);
}

export async function loadAdminPage(session, { onLogout, sub = 'accounts', editId = null }) {
  if (sub === 'profile') return loadAdminProfilePage(session, { onLogout });
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
          <h1>My Profile</h1>
          <p class="page-lead">View and edit your administrator account details, or change your PIN.</p>
        </div>
        <div class="page-actions">
          <button type="button" id="btn-open-profile" class="btn btn-primary">Open profile</button>
        </div>
      </div>
      <section class="panel" id="admin-profile-panel">
        ${loadingBlock('Loading your profile…')}
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
        <dt>Full name</dt><dd>${escapeHtml(profile.full_name || '—')}</dd>
        <dt>Login ID</dt><dd>${escapeHtml(profile.login_id || '—')}</dd>
        <dt>Role</dt><dd>${escapeHtml(capitalize(profile.role || session.role))}</dd>
        <dt>Gender</dt><dd>${escapeHtml(profile.gender || '—')}</dd>
        <dt>Status</dt><dd>${profile.is_active === false ? 'Inactive' : 'Active'}</dd>
      </dl>
      <div class="modal-actions" style="justify-content:flex-start;margin-top:1rem">
        <button type="button" class="btn btn-primary" id="btn-edit-profile-inline">Edit profile / Change PIN</button>
      </div>
    `;
    document.getElementById('btn-edit-profile-inline')?.addEventListener('click', open);
  } catch (err) {
    panel.innerHTML = errorBlock('Could not load profile', getErrorMessage(err), 'retry-admin-profile');
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
        <div><h1>Administration</h1><p class="page-lead">Manage all user accounts</p></div>
        <div class="page-actions">
          <button type="button" id="btn-page-profile" class="btn btn-secondary">My Profile</button>
        </div>
      </div>
      <div class="filter-bar">
        <div class="field">
          <label for="acct-role">Filter by role</label>
          <select id="acct-role">
            <option value="">All</option>
            <option value="sme">SME</option>
            <option value="lender">Lender</option>
            <option value="admin">Admin</option>
            <option value="subadmin">Sub-Admin</option>
          </select>
        </div>
      </div>
      <div id="acct-table-host">${loadingBlock('Loading accounts…')}</div>
      <div id="admin-modal-host"></div>
    `,
  });
  bindAdminShell(session, onLogout);

  const host = document.getElementById('acct-table-host');
  const modalHost = document.getElementById('admin-modal-host');
  const roleSelect = document.getElementById('acct-role');

  async function fetchAccounts() {
    const roleFilter = roleSelect?.value || undefined;
    host.innerHTML = loadingBlock('Loading accounts…');
    try {
      const payload = await api.getAdminAccounts({ role: roleFilter });
      const rows = normalizeListPayload(payload, ['accounts', 'items', 'data', 'results', 'users']);
      host.innerHTML = renderAccountsTable(rows);
      bindAccountActions(rows, host, modalHost);
    } catch (err) {
      host.innerHTML = errorBlock('Could not load accounts', getErrorMessage(err), 'retry-acct');
      document.getElementById('retry-acct')?.addEventListener('click', fetchAccounts);
    }
  }

  roleSelect?.addEventListener('change', fetchAccounts);
  await fetchAccounts();
}

function renderAccountsTable(rows) {
  if (!rows.length) return emptyBlock('No accounts found', 'Try changing the role filter.');
  return `
    <div class="table-wrap" role="region" aria-label="Accounts table" tabindex="0">
      <table class="data-table">
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Login ID</th>
            <th scope="col">Full Name</th>
            <th scope="col">Role</th>
            <th scope="col">Gender</th>
            <th scope="col">Status</th>
            <th scope="col">Created</th>
            <th scope="col">Actions</th>
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
                <td><span class="role-pill role-pill-${escapeHtml(r.role || 'sme')}">${escapeHtml(capitalize(r.role || 'sme'))}</span></td>
                <td>${escapeHtml(r.gender || '—')}</td>
                <td><span class="status-badge ${active ? 'status-active' : 'status-inactive'}">${active ? 'Active' : 'Inactive'}</span></td>
                <td>${escapeHtml(formatDate(r.created_at))}</td>
                <td class="action-cell">
                  <a href="#/admin/edit/${encodeURIComponent(id)}" class="btn btn-ghost btn-sm">Edit</a>
                  ${active
                    ? `<button type="button" class="btn btn-ghost btn-sm btn-danger-text" data-delete-id="${escapeHtml(id)}">Delete</button>`
                    : `<button type="button" class="btn btn-ghost btn-sm btn-success-text" data-restore-id="${escapeHtml(id)}">Restore</button>`
                  }
                  <button type="button" class="btn btn-ghost btn-sm" data-reset-pin-id="${escapeHtml(id)}">Reset PIN</button>
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
      showConfirmDialog(modalHost, 'Delete account?', 'This will soft-delete the account. You can restore it later.', async () => {
        try {
          await api.deleteAccount(id);
          showToast('Account deleted.', 'success');
          document.getElementById('acct-role')?.dispatchEvent(new Event('change'));
        } catch (err) {
          showToast(getErrorMessage(err, 'Delete failed'), 'error');
        }
      });
    });
  });

  host.querySelectorAll('[data-restore-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-restore-id');
      try {
        await api.restoreAccount(id);
        showToast('Account restored.', 'success');
        document.getElementById('acct-role')?.dispatchEvent(new Event('change'));
      } catch (err) {
        showToast(getErrorMessage(err, 'Restore failed'), 'error');
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
          <button type="button" class="btn btn-ghost" id="modal-cancel">Cancel</button>
          <button type="button" class="btn btn-primary btn-danger" id="modal-confirm">Confirm</button>
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
        <h3>Reset PIN</h3>
        <form id="reset-pin-form" class="auth-form">
          <div class="field">
            <label for="new-pin">New PIN</label>
            <input id="new-pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="4 digits" />
          </div>
          <div class="field">
            <label for="confirm-new-pin">Confirm PIN</label>
            <input id="confirm-new-pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="Re-enter" />
          </div>
          <div id="reset-pin-error" class="form-error" hidden></div>
          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" id="modal-cancel">Cancel</button>
            <button type="submit" class="btn btn-primary">Reset PIN</button>
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
      if (errEl) { errEl.hidden = false; errEl.textContent = 'PIN must be exactly 4 digits.'; }
      return;
    }
    if (pin !== confirm) {
      if (errEl) { errEl.hidden = false; errEl.textContent = 'PINs do not match.'; }
      return;
    }
    try {
      await api.resetPin(userId, pin);
      showToast('PIN has been reset.', 'success');
      host.innerHTML = '';
    } catch (err) {
      showToast(getErrorMessage(err, 'Reset failed'), 'error');
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
      <div class="page-header"><div><h1>Create Lender Account</h1></div></div>
      <div class="admin-form-wrap">
        <form id="create-form" class="auth-form panel" novalidate>
          <div class="field"><label for="membership_number">Membership Number</label><input id="membership_number" name="membership_number" type="text" required /></div>
          <div class="field"><label for="full_name">Full Name</label><input id="full_name" name="full_name" type="text" required /></div>
          <div class="field"><label for="gender">Gender</label><select id="gender" name="gender" required><option value="">Select…</option><option value="Male">Male</option><option value="Female">Female</option><option value="Other">Other</option></select></div>
          <div class="field"><label for="organization">Organization</label><input id="organization" name="organization" type="text" required placeholder="e.g. CRDB, NMB" /></div>
          <div class="field"><label for="work_email">Work Email</label><input id="work_email" name="work_email" type="email" required /></div>
          <div class="field"><label for="phone">Phone <span class="optional">(optional)</span></label><input id="phone" name="phone" type="tel" /></div>
          <div class="field"><label for="pin">PIN</label><input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="4 digits" /></div>
          <div class="field"><label for="confirm_pin">Confirm PIN</label><input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required /></div>
          <div id="create-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="create-submit">Create Lender</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);
  bindCreateForm('create-form', async (fd) => {
    const pin = fd.get('pin');
    const confirm_pin = fd.get('confirm_pin');
    if (!/^[0-9]{4}$/.test(pin)) return 'PIN must be exactly 4 digits.';
    if (pin !== confirm_pin) return 'PINs do not match.';
    await api.createLender({
      membership_number: fd.get('membership_number'),
      full_name: fd.get('full_name'),
      gender: fd.get('gender'),
      organization: fd.get('organization'),
      work_email: fd.get('work_email'),
      phone: fd.get('phone') || undefined,
      pin,
    });
    return null;
  }, 'Lender account created.');
}

/* ─── Create SME ─────────────────────────────────────────── */

function loadCreateSme(session, { onLogout }) {
  const bizOptions = BUSINESS_TYPES.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'create-sme',
    mainHtml: `
      <div class="page-header"><div><h1>Create SME Account</h1></div></div>
      <div class="admin-form-wrap">
        <form id="create-form" class="auth-form panel" novalidate>
          <div class="field"><label for="nida">NIDA</label><input id="nida" name="nida" type="text" inputmode="numeric" maxlength="20" pattern="[0-9]{20}" required placeholder="20 digits" /></div>
          <div class="field"><label for="full_name">Full Name</label><input id="full_name" name="full_name" type="text" required /></div>
          <div class="field"><label for="phone">Phone</label><input id="phone" name="phone" type="tel" required placeholder="+255..." /></div>
          <div class="field"><label for="email">Email <span class="optional">(optional)</span></label><input id="email" name="email" type="email" /></div>
          <div class="field"><label for="location">Location</label><input id="location" name="location" type="text" required /></div>
          <div class="field"><label for="business_type">Business Type</label><select id="business_type" name="business_type" required><option value="">Select…</option>${bizOptions}</select></div>
          <div class="field"><label for="gender">Gender</label><select id="gender" name="gender" required><option value="">Select…</option><option value="Male">Male</option><option value="Female">Female</option><option value="Other">Other</option></select></div>
          <div class="field"><label for="nationality">Nationality</label><input id="nationality" name="nationality" type="text" value="Tanzanian" required /></div>
          <div class="field"><label for="date_of_birth">Date of Birth</label><input id="date_of_birth" name="date_of_birth" type="date" required /></div>
          <div class="field"><label for="tin">${escapeHtml(t('admin.createSmeTin'))}</label><input id="tin" name="tin" type="text" required minlength="9" maxlength="20" placeholder="At least 9 characters" /></div>
          <div class="field"><label for="pin">PIN</label><input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="4 digits" /></div>
          <div class="field"><label for="confirm_pin">Confirm PIN</label><input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required /></div>
          <div id="create-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="create-submit">Create SME</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);
  bindCreateForm('create-form', async (fd) => {
    const nida = fd.get('nida');
    const pin = fd.get('pin');
    const confirm_pin = fd.get('confirm_pin');
    const tin = String(fd.get('tin') || '').trim().replace(/[^a-zA-Z0-9]/g, '');
    if (!/^[0-9]{20}$/.test(nida)) return 'NIDA must be exactly 20 digits.';
    if (tin.length < 9) return t('admin.tinRequired');
    if (!/^[0-9]{4}$/.test(pin)) return 'PIN must be exactly 4 digits.';
    if (pin !== confirm_pin) return 'PINs do not match.';
    await api.createSmeByAdmin({
      nida, full_name: fd.get('full_name'), phone: fd.get('phone'),
      email: fd.get('email') || undefined, location: fd.get('location'),
      business_type: fd.get('business_type'), gender: fd.get('gender'),
      nationality: fd.get('nationality'), date_of_birth: fd.get('date_of_birth'),
      tin, pin,
    });
    return null;
  }, 'SME account created.');
}

/* ─── Create Sub-Admin ───────────────────────────────────── */

function loadCreateSubAdmin(session, { onLogout }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'create-subadmin',
    mainHtml: `
      <div class="page-header"><div><h1>Create Sub-Admin Account</h1></div></div>
      <div class="admin-form-wrap">
        <form id="create-form" class="auth-form panel" novalidate>
          <div class="field"><label for="login_id">Login ID</label><input id="login_id" name="login_id" type="text" required /></div>
          <div class="field"><label for="full_name">Full Name</label><input id="full_name" name="full_name" type="text" required /></div>
          <div class="field"><label for="gender">Gender</label><select id="gender" name="gender" required><option value="">Select…</option><option value="Male">Male</option><option value="Female">Female</option><option value="Other">Other</option></select></div>
          <div class="field"><label for="organization">Organization</label><input id="organization" name="organization" type="text" required /></div>
          <div class="field"><label for="work_email">Work Email</label><input id="work_email" name="work_email" type="email" required /></div>
          <div class="field"><label for="pin">PIN</label><input id="pin" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="4 digits" /></div>
          <div class="field"><label for="confirm_pin">Confirm PIN</label><input id="confirm_pin" name="confirm_pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required /></div>
          <div id="create-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="create-submit">Create Sub-Admin</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);
  bindCreateForm('create-form', async (fd) => {
    const pin = fd.get('pin');
    const confirm_pin = fd.get('confirm_pin');
    if (!/^[0-9]{4}$/.test(pin)) return 'PIN must be exactly 4 digits.';
    if (pin !== confirm_pin) return 'PINs do not match.';
    await api.createSubAdmin({
      login_id: fd.get('login_id'),
      full_name: fd.get('full_name'),
      gender: fd.get('gender'),
      organization: fd.get('organization'),
      work_email: fd.get('work_email'),
      pin,
    });
    return null;
  }, 'Sub-Admin account created.');
}

function bindCreateForm(formId, handler, successMsg) {
  const form = document.getElementById(formId);
  const errEl = document.getElementById('create-error');
  const submitBtn = document.getElementById('create-submit');
  const origText = submitBtn?.textContent || 'Submit';

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }
    const fd = new FormData(form);
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating…';
    try {
      const validationError = await handler(fd);
      if (validationError) {
        if (errEl) { errEl.hidden = false; errEl.textContent = validationError; }
        return;
      }
      showToast(successMsg, 'success');
      form.reset();
    } catch (err) {
      const msg = getErrorMessage(err, 'Creation failed');
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
    mainHtml: loadingBlock('Loading account…'),
  });
  bindAdminShell(session, onLogout);

  try {
    const acct = await api.getAdminAccount(editId);
    renderEditForm(session, acct, { onLogout });
  } catch (err) {
    const main = document.getElementById('main');
    if (main) main.innerHTML = errorBlock('Could not load account', getErrorMessage(err));
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
      <div class="field"><label for="organization">Organization</label><input id="organization" name="organization" type="text" value="${escapeHtml(acct.organization || '')}" /></div>
      <div class="field"><label for="work_email">Work Email</label><input id="work_email" name="work_email" type="email" value="${escapeHtml(acct.work_email || '')}" /></div>
      <div class="field"><label for="phone">Phone</label><input id="phone" name="phone" type="tel" value="${escapeHtml(acct.phone || '')}" /></div>
    `;
  } else if (isSme) {
    const bizOptions = BUSINESS_TYPES.map(t =>
      `<option value="${escapeHtml(t)}" ${t === acct.business_type ? 'selected' : ''}>${escapeHtml(t)}</option>`
    ).join('');
    extraFields = `
      <div class="field"><label for="phone">Phone</label><input id="phone" name="phone" type="tel" value="${escapeHtml(acct.phone || '')}" /></div>
      <div class="field"><label for="email">Email</label><input id="email" name="email" type="email" value="${escapeHtml(acct.email || '')}" /></div>
      <div class="field"><label for="location">Location</label><input id="location" name="location" type="text" value="${escapeHtml(acct.location || '')}" /></div>
      <div class="field"><label for="business_type">Business Type</label><select id="business_type" name="business_type"><option value="">Select…</option>${bizOptions}</select></div>
    `;
  }

  app.innerHTML = renderShell({
    role: session.role, user: session.user, activeNav: 'accounts',
    mainHtml: `
      <div class="page-header">
        <div><h1>Edit Account</h1><p class="page-lead">${escapeHtml(acct.full_name || '')} — ${escapeHtml(capitalize(acctRole))}</p></div>
        <div class="page-actions"><a href="#/admin" class="btn btn-secondary">Back to accounts</a></div>
      </div>
      <div class="admin-form-wrap">
        <form id="edit-form" class="auth-form panel" novalidate>
          <div class="field"><label for="full_name">Full Name</label><input id="full_name" name="full_name" type="text" required value="${escapeHtml(acct.full_name || '')}" /></div>
          <div class="field"><label for="gender">Gender</label>
            <select id="gender" name="gender">
              <option value="">Select…</option>
              <option value="Male" ${acct.gender === 'Male' ? 'selected' : ''}>Male</option>
              <option value="Female" ${acct.gender === 'Female' ? 'selected' : ''}>Female</option>
              <option value="Other" ${acct.gender === 'Other' ? 'selected' : ''}>Other</option>
            </select>
          </div>
          <div class="field">
            <label for="is_active">Status</label>
            <select id="is_active" name="is_active">
              <option value="true" ${acct.is_active !== false ? 'selected' : ''}>Active</option>
              <option value="false" ${acct.is_active === false ? 'selected' : ''}>Inactive</option>
            </select>
          </div>
          ${extraFields}
          <div id="edit-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary btn-block" id="edit-submit">Save Changes</button>
        </form>
      </div>
    `,
  });
  bindAdminShell(session, onLogout);

  const form = document.getElementById('edit-form');
  const errEl = document.getElementById('edit-error');
  const submitBtn = document.getElementById('edit-submit');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving…';
    const fd = new FormData(form);
    const data = { full_name: fd.get('full_name'), gender: fd.get('gender'), is_active: fd.get('is_active') === 'true' };
    if (isLender) {
      data.organization = fd.get('organization');
      data.work_email = fd.get('work_email');
      data.phone = fd.get('phone') || undefined;
    } else if (isSme) {
      data.phone = fd.get('phone');
      data.email = fd.get('email') || undefined;
      data.location = fd.get('location');
      data.business_type = fd.get('business_type');
    }
    try {
      await api.updateAccount(acct.id || acct.user_id, data);
      showToast('Account updated.', 'success');
    } catch (err) {
      const msg = getErrorMessage(err, 'Update failed');
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Save Changes';
    }
  });
}
