/**
 * FastAPI-aligned API client for the Tanzania SME / Lender portal.
 *
 * API base resolution (automatic switching):
 * 1. VITE_API_URL at build time (set on Vercel → your Render URL)
 * 2. In Vite dev → same-origin `/api` (proxied to local backend)
 * 3. Else localhost for preview builds without env
 */

function resolveApiBase() {
  const configured = (import.meta.env.VITE_API_URL || '').trim().replace(/\/$/, '');
  if (configured) {
    return configured.endsWith('/api') ? configured : `${configured}/api`;
  }
  // Local Vite: use proxy so we always hit the running backend
  if (import.meta.env.DEV) {
    return '/api';
  }
  return 'http://localhost:8000/api';
}

const API_BASE = resolveApiBase();

export class ApiError extends Error {
  constructor(message, { status = 0, detail = null, body = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

function getToken() {
  try {
    return sessionStorage.getItem('ushirika_token');
  } catch {
    return null;
  }
}

function formatDetail(detail) {
  if (detail == null) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object') {
          const loc = Array.isArray(item.loc) ? item.loc.filter((p) => p !== 'body').join('.') : '';
          return loc ? `${loc}: ${item.msg || JSON.stringify(item)}` : item.msg || JSON.stringify(item);
        }
        return String(item);
      })
      .join('; ');
  }
  if (typeof detail === 'object') {
    return detail.message || detail.msg || JSON.stringify(detail);
  }
  return String(detail);
}

async function parseBody(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
  if (
    contentType.includes('text/csv') ||
    contentType.includes('application/octet-stream') ||
    contentType.includes('application/vnd.ms-excel')
  ) {
    return response.blob();
  }
  const text = await response.text();
  return text || null;
}

/**
 * Low-level request helper.
 * @param {string} path - Absolute path starting with /
 * @param {RequestInit & { auth?: boolean, raw?: boolean }} options
 */
export async function request(path, options = {}) {
  const { auth = true, raw = false, headers: customHeaders, ...init } = options;
  const headers = new Headers(customHeaders || {});

  if (auth) {
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch (err) {
    throw new ApiError('Unable to reach the server. Check your connection and API URL.', {
      status: 0,
      detail: err?.message || String(err),
    });
  }

  if (raw) return response;

  // 204 No Content (e.g. DELETE) — nothing to parse
  if (response.status === 204) {
    if (!response.ok) {
      throw new ApiError(`Request failed (${response.status})`, { status: response.status });
    }
    return null;
  }

  const body = await parseBody(response);

  if (!response.ok) {
    const detail = body && typeof body === 'object' ? body.detail ?? body.message ?? body : body;
    const message =
      formatDetail(detail) ||
      `Request failed (${response.status}${response.statusText ? ` ${response.statusText}` : ''})`;
    throw new ApiError(message, { status: response.status, detail, body });
  }

  return body;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/* ─── Auth ─────────────────────────────────────────────── */

/** POST /auth/register — SME self-registration */
export function registerSme({ nida, phone, full_name, email, location, business_type, gender, nationality, date_of_birth, pin }) {
  return request('/auth/register', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ nida, phone, full_name, email: email || undefined, location, business_type, gender, nationality, date_of_birth, pin }),
  });
}

/** POST /auth/login — universal login */
export function login({ login_id, pin }) {
  return request('/auth/login', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ login_id, pin }),
  });
}

/** GET /auth/me */
export function getMe() {
  return request('/auth/me');
}

/** PUT /auth/change-pin */
export function changePin({ current_pin, new_pin }) {
  return request('/auth/change-pin', {
    method: 'PUT',
    body: JSON.stringify({ current_pin, new_pin }),
  });
}

/* ─── Admin ────────────────────────────────────────────── */

export function getAdminAccounts(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  });
  const query = qs.toString();
  return request(`/admin/accounts${query ? `?${query}` : ''}`);
}

export function getAdminAccount(userId) {
  return request(`/admin/accounts/${encodeURIComponent(userId)}`);
}

export function createLender(data) {
  return request('/admin/accounts/lender', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function createSubAdmin(data) {
  return request('/admin/accounts/subadmin', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function createSmeByAdmin(data) {
  return request('/admin/accounts/sme', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateAccount(userId, data) {
  return request(`/admin/accounts/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteAccount(userId) {
  return request(`/admin/accounts/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

export function restoreAccount(userId) {
  return request(`/admin/accounts/${encodeURIComponent(userId)}/restore`, {
    method: 'POST',
  });
}

export function resetPin(userId, pin) {
  return request(`/admin/accounts/${encodeURIComponent(userId)}/reset-pin`, {
    method: 'PUT',
    body: JSON.stringify({ pin }),
  });
}

export function getAdminProfile() {
  return request('/admin/profile');
}

export function updateAdminProfile(data) {
  return request('/admin/profile', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/* ─── SME ──────────────────────────────────────────────── */

export function getSmeOverview() {
  return request('/dashboard/sme');
}

export function getSmeProfile() {
  return request('/sme/profile');
}

export function updateSmeProfile(data) {
  return request('/sme/profile', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function getSmeScoreHistory() {
  return request('/credit/history/monthly');
}

export function requestCreditScore(forceRefresh = false) {
  return request('/credit/score', {
    method: 'POST',
    body: JSON.stringify({ force_refresh: forceRefresh }),
  });
}

export function getSmeTransactions(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  });
  const query = qs.toString();
  return request(`/transactions${query ? `?${query}` : ''}`);
}

export function createTransaction(data) {
  return request('/transactions', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateTransaction(id, data) {
  return request(`/transactions/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteTransaction(id) {
  return request(`/transactions/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export function uploadSmeCsv(file) {
  const form = new FormData();
  form.append('file', file);
  return request('/transactions/import', {
    method: 'POST',
    body: form,
  });
}

export async function downloadSmeCsvTemplate() {
  const response = await request('/transactions/template', { raw: true });
  if (!response.ok) {
    const body = await parseBody(response);
    const detail = body && typeof body === 'object' ? body.detail : body;
    throw new ApiError(formatDetail(detail) || 'Failed to download template', {
      status: response.status,
      detail,
      body,
    });
  }
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^\";]+)/i);
  const filename = match ? decodeURIComponent(match[1].replace(/"/g, '')) : 'transaction_template.csv';
  downloadBlob(blob, filename);
}

export async function exportSmeStatement(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  });
  const query = qs.toString();
  const response = await request(`/transactions/export/estatement${query ? `?${query}` : ''}`, {
    raw: true,
  });
  if (!response.ok) {
    const body = await parseBody(response);
    const detail = body && typeof body === 'object' ? body.detail : body;
    throw new ApiError(formatDetail(detail) || 'Failed to export statement', {
      status: response.status,
      detail,
      body,
    });
  }
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^\";]+)/i);
  const filename = match ? decodeURIComponent(match[1].replace(/"/g, '')) : 'e-statement.csv';
  downloadBlob(blob, filename);
}

/* ─── Lender ───────────────────────────────────────────── */

export function getLenderProfile() {
  return request('/lender/profile');
}

export function updateLenderProfile(data) {
  return request('/lender/profile', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function getLenderPortfolio(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  });
  const query = qs.toString();
  return request(`/lender/portfolio${query ? `?${query}` : ''}`);
}

export function getLenderSmeDetail(smeId) {
  return request(`/lender/sme/${encodeURIComponent(smeId)}`);
}

export function getLenderSmeByNida(nida) {
  return request(`/lender/sme/by-nida/${encodeURIComponent(nida)}`);
}

export function getLenderSmeTransactions(smeId, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  });
  const query = qs.toString();
  return request(`/lender/sme/${encodeURIComponent(smeId)}/transactions${query ? `?${query}` : ''}`);
}

export async function downloadLenderSmeStatement(smeId) {
  const response = await request(`/lender/sme/${encodeURIComponent(smeId)}/statement`, { raw: true });
  if (!response.ok) {
    const body = await parseBody(response);
    const detail = body && typeof body === 'object' ? body.detail : body;
    throw new ApiError(formatDetail(detail) || 'Failed to download statement', {
      status: response.status,
      detail,
      body,
    });
  }
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^\";]+)/i);
  const filename = match
    ? decodeURIComponent(match[1].replace(/"/g, ''))
    : `sme_${smeId}_statement.csv`;
  downloadBlob(blob, filename);
}

export { API_BASE };
