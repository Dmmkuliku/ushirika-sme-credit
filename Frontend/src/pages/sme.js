/**
 * SME dashboard: overview, transactions (with record form), CSV upload/export.
 */

import * as api from '../api.js';
import {
  escapeHtml,
  formatTZS,
  formatScore,
  formatDate,
  formatNumber,
  formatMonthLabel,
  riskClass,
  capitalize,
  normalizeListPayload,
  getErrorMessage,
  debounce,
} from '../utils.js';
import {
  renderShell,
  bindShellActions,
  loadingBlock,
  emptyBlock,
  errorBlock,
  showToast,
  scoreRingSvg,
  mountChartResize,
} from '../ui.js';
import { openProfileModal } from './profile.js';

function bindSmeShell(onLogout) {
  bindShellActions({
    onLogout,
    onProfile: () => openProfileModal('sme'),
  });
}

function txModalHost() {
  let host = document.getElementById('tx-modal-host');
  if (!host) {
    host = document.createElement('div');
    host.id = 'tx-modal-host';
    document.body.appendChild(host);
  }
  return host;
}

function closeTxModal() {
  const host = document.getElementById('tx-modal-host');
  if (host) host.innerHTML = '';
}

function toInputDate(val) {
  if (!val) return '';
  const raw = String(val);
  // Prefer calendar date from ISO string to avoid timezone day-shift
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
  const d = new Date(val);
  if (Number.isNaN(d.getTime())) return raw.slice(0, 10);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Convert HTML date input (YYYY-MM-DD) to ISO datetime for the API. */
function toApiDateTime(val) {
  if (!val) return undefined;
  const s = String(val).trim();
  if (!s) return undefined;
  if (s.includes('T')) return s;
  return `${s}T00:00:00`;
}

function truncateHash(hash) {
  if (!hash) return '—';
  const s = String(hash);
  return s.length <= 12 ? s : `${s.slice(0, 8)}…${s.slice(-4)}`;
}

function transactionCount(overview) {
  return (
    overview?.transaction_count ??
    overview?.transactions_count ??
    overview?.tx_count ??
    overview?.metrics?.transaction_count ??
    0
  );
}

function isScoreLocked(overview) {
  if (typeof overview?.score_locked === 'boolean') return overview.score_locked;
  if (typeof overview?.score_eligible === 'boolean') return !overview.score_eligible || overview.latest_score == null;
  if (typeof overview?.is_locked === 'boolean') return overview.is_locked;
  if (overview?.score_available === false) return true;
  return Number(transactionCount(overview)) < 5;
}

function componentsList(overview) {
  const raw =
    overview?.score_components ||
    overview?.components ||
    overview?.explainability ||
    overview?.factors ||
    [];
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === 'object') {
    return Object.entries(raw).map(([name, value]) => {
      if (value && typeof value === 'object') return { name, ...value };
      return { name, value, contribution: value };
    });
  }
  return [];
}

/* ─── Overview ─────────────────────────────────────────── */

export function renderSmeOverviewLoading(session) {
  return renderShell({
    role: 'sme',
    user: session.user,
    activeNav: 'overview',
    mainHtml: loadingBlock('Loading your credit overview…'),
  });
}

export async function loadSmeOverview(session, { onLogout }) {
  const app = document.getElementById('app');
  app.innerHTML = renderSmeOverviewLoading(session);
  bindSmeShell(onLogout);

  try {
    const [overview, history] = await Promise.all([
      api.getSmeOverview(),
      api.getSmeScoreHistory().catch(() => ({ months: [], history: [], items: [] })),
    ]);
    if (overview?.score_eligible && overview?.latest_score == null) {
      try {
        await api.requestCreditScore(true);
        const refreshed = await api.getSmeOverview();
        renderSmeOverview(session, refreshed, history, { onLogout });
        return;
      } catch {
        /* fall through */
      }
    }
    renderSmeOverview(session, overview, history, { onLogout });
  } catch (err) {
    app.innerHTML = renderShell({
      role: 'sme',
      user: session.user,
      activeNav: 'overview',
      mainHtml: errorBlock('Could not load overview', getErrorMessage(err), 'retry-overview'),
    });
    bindSmeShell(onLogout);
    document.getElementById('retry-overview')?.addEventListener('click', () => {
      loadSmeOverview(session, { onLogout });
    });
  }
}

function renderSmeOverview(session, overview, historyPayload, { onLogout }) {
  const locked = isScoreLocked(overview);
  const txCount = Number(transactionCount(overview));
  const score = overview?.latest_score ?? overview?.score ?? overview?.credit_score ?? null;
  const risk = overview?.risk ?? overview?.risk_level ?? overview?.risk_band ?? '—';
  const eligible =
    overview?.estimated_eligible_financing ??
    overview?.eligible_financing_tzs ??
    overview?.eligible_amount ??
    overview?.estimated_financing ??
    null;
  const components = componentsList(overview);
  const history = normalizeListPayload(historyPayload, ['months', 'history', 'items', 'data', 'series']);

  const lockNote = locked
    ? `Score unlocks after at least 5 recorded transactions. You currently have ${formatNumber(txCount, 0)}.`
    : `Based on ${formatNumber(txCount, 0)} transactions.`;

  const componentsHtml =
    components.length === 0
      ? emptyBlock('No explainability data', 'Component indicators will appear once scoring is available.')
      : `<ul class="component-list">
          ${components
            .map((c) => {
              const name = c.name || c.label || c.component || 'Factor';
              const value = c.contribution ?? c.value ?? c.score ?? c.weight;
              const impact = c.impact || c.direction || c.explanation || c.description || '';
              const pct =
                value != null && Math.abs(Number(value)) <= 1 && Number(value) !== 0
                  ? `${formatNumber(Number(value) * 100, 0)}%`
                  : value != null
                    ? formatNumber(value, 1)
                    : '—';
              return `
                <li class="component-item">
                  <div class="component-head">
                    <span class="component-name">${escapeHtml(name)}</span>
                    <span class="component-value">${escapeHtml(pct)}</span>
                  </div>
                  ${impact ? `<p class="component-impact">${escapeHtml(impact)}</p>` : ''}
                  <div class="component-bar" aria-hidden="true">
                    <span style="width:${Math.min(100, Math.abs(Number(value) <= 1 ? Number(value) * 100 : Number(value)) || 0)}%"></span>
                  </div>
                </li>`;
            })
            .join('')}
        </ul>`;

  const chartSection =
    history.length === 0
      ? emptyBlock('No monthly history yet', 'Upload transactions to build your score history.')
      : `<div class="chart-wrap"><canvas id="score-chart" width="640" height="240" role="img" aria-label="Monthly credit score history"></canvas></div>`;

  const mainHtml = `
    <div class="page-header">
      <div>
        <h1>Credit overview</h1>
        <p class="page-lead">${escapeHtml(lockNote)}</p>
      </div>
      <div class="page-actions">
        <button type="button" class="btn btn-secondary" id="btn-export-overview">Download e-statement</button>
        <a class="btn btn-primary" href="#/sme/upload">Upload CSV</a>
      </div>
    </div>
    <section class="metric-grid" aria-label="Key credit metrics">
      <article class="metric-card metric-score ${locked ? 'is-locked' : ''}">
        <h2 class="metric-label">Credit score</h2>
        <div class="score-display">
          ${scoreRingSvg(locked ? 0 : score, locked)}
          <div class="score-display-text">
            ${locked
              ? `<span class="score-locked-label">Locked</span>
                 <span class="score-locked-hint">${escapeHtml(`${txCount}/5 transactions`)}</span>`
              : `<span class="score-number">${escapeHtml(formatScore(score))}</span>
                 <span class="score-hint">out of 850</span>`
            }
          </div>
        </div>
      </article>
      <article class="metric-card">
        <h2 class="metric-label">Risk band</h2>
        <p class="metric-value">
          <span class="risk-badge ${riskClass(locked ? '' : risk)}">${escapeHtml(
            locked ? 'Pending' : capitalize(String(risk))
          )}</span>
        </p>
        <p class="metric-hint">Portfolio risk classification</p>
      </article>
      <article class="metric-card">
        <h2 class="metric-label">Est. eligible financing</h2>
        <p class="metric-value metric-tzs">${escapeHtml(locked ? '—' : formatTZS(eligible))}</p>
        <p class="metric-hint">Indicative TZS capacity</p>
      </article>
      <article class="metric-card">
        <h2 class="metric-label">Transactions</h2>
        <p class="metric-value">${escapeHtml(formatNumber(txCount, 0))}</p>
        <p class="metric-hint">${locked ? 'Need 5+ to unlock score' : 'Feeding your score model'}</p>
      </article>
    </section>
    <div class="split-panels">
      <section class="panel" aria-labelledby="components-title">
        <div class="panel-header">
          <h2 id="components-title">Score components</h2>
          <p>Explainability indicators behind your score</p>
        </div>
        ${locked ? emptyBlock('Components locked', 'Upload at least 5 transactions to view explainability.') : componentsHtml}
      </section>
      <section class="panel" aria-labelledby="history-title">
        <div class="panel-header">
          <h2 id="history-title">Monthly transaction history</h2>
          <p>Volume trend over recent months</p>
        </div>
        ${chartSection}
      </section>
    </div>
  `;

  const app = document.getElementById('app');
  app.innerHTML = renderShell({ role: 'sme', user: session.user, activeNav: 'overview', mainHtml });
  bindSmeShell(onLogout);

  const canvas = document.getElementById('score-chart');
  if (canvas && history.length) {
    const series = history.map((row) => ({
      month: row.year_month || row.month || row.period || row.label || formatMonthLabel(row.date),
      score: row.total_volume_tzs ?? row.score ?? row.value ?? row.credit_score ?? row.transaction_count,
    }));
    mountChartResize(canvas, series);
  }

  document.getElementById('btn-export-overview')?.addEventListener('click', async () => {
    try {
      await api.exportSmeStatement();
      showToast('E-statement download started.', 'success');
    } catch (err) {
      showToast(getErrorMessage(err, 'Export failed'), 'error');
    }
  });
}

/* ─── Transactions ─────────────────────────────────────── */

export async function loadSmeTransactions(session, { onLogout }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: 'sme',
    user: session.user,
    activeNav: 'transactions',
    mainHtml: `
      <div class="page-header">
        <div>
          <h1>Transactions</h1>
          <p class="page-lead">Record, filter and review your activity</p>
        </div>
        <div class="page-actions">
          <button type="button" class="btn btn-secondary" id="btn-toggle-record">Record Transaction</button>
          <button type="button" class="btn btn-secondary" id="btn-export-tx">Export CSV</button>
        </div>
      </div>

      <section id="record-tx-section" class="panel record-tx-panel" hidden>
        <div class="panel-header"><h3>Record a Transaction</h3></div>
        <form id="record-tx-form" class="auth-form" novalidate>
          <div class="form-grid-2">
            <div class="field"><label for="rtx-ref">Reference</label><input id="rtx-ref" name="transaction_ref" type="text" required /></div>
            <div class="field"><label for="rtx-cp-name">Counterparty Name</label><input id="rtx-cp-name" name="counterparty_name" type="text" required /></div>
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="rtx-cp-type">Counterparty Type</label>
              <select id="rtx-cp-type" name="counterparty_type" required>
                <option value="">Select…</option>
                <option value="supplier">Supplier</option>
                <option value="buyer">Buyer</option>
                <option value="distributor">Distributor</option>
                <option value="logistics">Logistics</option>
              </select>
            </div>
            <div class="field"><label for="rtx-order-type">Order Type</label>
              <select id="rtx-order-type" name="order_type" required>
                <option value="">Select…</option>
                <option value="purchase">Purchase</option>
                <option value="sale">Sale</option>
                <option value="service">Service</option>
              </select>
            </div>
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="rtx-amount">Amount (TZS)</label><input id="rtx-amount" name="amount_tzs" type="number" min="0" step="1" required /></div>
            <div class="field"><label for="rtx-status">Payment Status</label>
              <select id="rtx-status" name="payment_status" required>
                <option value="">Select…</option>
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="partial">Partial</option>
                <option value="overdue">Overdue</option>
                <option value="defaulted">Defaulted</option>
              </select>
            </div>
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="rtx-due">Due Date</label><input id="rtx-due" name="due_date" type="date" required /></div>
            <div class="field"><label for="rtx-paid">Paid Date <span class="optional">(optional)</span></label><input id="rtx-paid" name="paid_date" type="date" /></div>
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="rtx-date">Transaction Date</label><input id="rtx-date" name="transaction_date" type="date" required /></div>
            <div class="field"><label for="rtx-notes">Notes <span class="optional">(optional)</span></label><input id="rtx-notes" name="notes" type="text" /></div>
          </div>
          <div id="record-tx-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary" id="record-tx-submit">Save Transaction</button>
        </form>
      </section>

      <form id="tx-filters" class="filter-bar" aria-label="Filter transactions">
        <div class="field"><label for="tx-from">From</label><input type="date" id="tx-from" name="from" /></div>
        <div class="field"><label for="tx-to">To</label><input type="date" id="tx-to" name="to" /></div>
        <div class="field"><label for="tx-type">Order type</label>
          <select id="tx-type" name="type"><option value="">All</option><option value="sale">Sale</option><option value="purchase">Purchase</option><option value="service">Service</option></select>
        </div>
        <div class="field field-grow"><label for="tx-q">Search</label><input type="search" id="tx-q" name="q" placeholder="Description or reference" /></div>
        <div class="filter-actions">
          <button type="submit" class="btn btn-primary">Apply</button>
          <button type="reset" class="btn btn-ghost">Reset</button>
        </div>
      </form>
      <div id="tx-table-host">${loadingBlock('Loading transactions…')}</div>
      <div id="tx-modal-host"></div>
    `,
  });
  bindSmeShell(onLogout);

  const host = document.getElementById('tx-table-host');
  const form = document.getElementById('tx-filters');
  const recordSection = document.getElementById('record-tx-section');
  const recordForm = document.getElementById('record-tx-form');

  document.getElementById('btn-toggle-record')?.addEventListener('click', () => {
    if (recordSection) recordSection.hidden = !recordSection.hidden;
  });

  recordForm?.addEventListener('submit', (e) => {
    e.preventDefault();
    const errEl = document.getElementById('record-tx-error');
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }
    const fd = new FormData(recordForm);
    const data = {
      transaction_ref: String(fd.get('transaction_ref') || '').trim(),
      counterparty_name: String(fd.get('counterparty_name') || '').trim(),
      counterparty_type: fd.get('counterparty_type'),
      order_type: fd.get('order_type'),
      amount_tzs: Number(fd.get('amount_tzs')),
      payment_status: fd.get('payment_status'),
      due_date: toApiDateTime(fd.get('due_date')),
      paid_date: toApiDateTime(fd.get('paid_date')),
      transaction_date: toApiDateTime(fd.get('transaction_date')),
      notes: String(fd.get('notes') || '').trim() || undefined,
    };
    showCreateConfirmModal(data, async () => {
      const btn = document.getElementById('record-tx-submit');
      btn.disabled = true;
      btn.textContent = 'Saving…';
      try {
        await api.createTransaction(data);
        showToast('Transaction recorded.', 'success');
        recordForm.reset();
        recordSection.hidden = true;
        fetchAndRender();
      } catch (err) {
        const msg = getErrorMessage(err, 'Failed to record transaction');
        if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
        showToast(msg, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Save Transaction';
      }
    });
  });

  async function fetchAndRender() {
    const fd = new FormData(form);
    host.innerHTML = loadingBlock('Loading transactions…');
    try {
      const payload = await api.getSmeTransactions();
      let rows = normalizeListPayload(payload, ['transactions', 'items', 'data', 'results']);
      const from = fd.get('from');
      const to = fd.get('to');
      const type = String(fd.get('type') || '').toLowerCase();
      const q = String(fd.get('q') || '').trim().toLowerCase();

      rows = rows.filter((row) => {
        const dateRaw = row.transaction_date || row.date || row.posted_at;
        const d = dateRaw ? new Date(dateRaw) : null;
        if (from && d && !Number.isNaN(d.getTime()) && d < new Date(from)) return false;
        if (to && d && !Number.isNaN(d.getTime()) && d > new Date(`${to}T23:59:59`)) return false;
        if (type && String(row.order_type || '').toLowerCase() !== type) return false;
        if (q) {
          const hay = `${row.transaction_ref || ''} ${row.notes || ''} ${row.counterparty_type || ''} ${row.counterparty_name || ''} ${row.order_type || ''}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
      host.innerHTML = renderTxTable(rows);
      bindTxTableActions(rows, fetchAndRender);
    } catch (err) {
      host.innerHTML = errorBlock('Could not load transactions', getErrorMessage(err), 'retry-tx');
      document.getElementById('retry-tx')?.addEventListener('click', fetchAndRender);
    }
  }

  form?.addEventListener('submit', (e) => { e.preventDefault(); fetchAndRender(); });
  form?.addEventListener('reset', () => { window.setTimeout(fetchAndRender, 0); });
  document.getElementById('tx-q')?.addEventListener('input', debounce(() => fetchAndRender(), 400));

  document.getElementById('btn-export-tx')?.addEventListener('click', async () => {
    const fd = new FormData(form);
    try {
      await api.exportSmeStatement({
        from: fd.get('from') || undefined,
        to: fd.get('to') || undefined,
        type: fd.get('type') || undefined,
        q: fd.get('q') || undefined,
      });
      showToast('CSV export started.', 'success');
    } catch (err) {
      showToast(getErrorMessage(err, 'Export failed'), 'error');
    }
  });

  await fetchAndRender();
}

function showCreateConfirmModal(data, onConfirm) {
  const host = txModalHost();
  host.innerHTML = `
    <div class="modal-backdrop" id="tx-confirm-backdrop">
      <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="tx-confirm-title">
        <h3 id="tx-confirm-title">Confirm transaction</h3>
        <p>Please review the details before saving.</p>
        <ul class="confirm-summary">
          <li><span class="confirm-summary-label">Reference</span><span>${escapeHtml(data.transaction_ref || '—')}</span></li>
          <li><span class="confirm-summary-label">Counterparty</span><span>${escapeHtml(data.counterparty_name || '—')}</span></li>
          <li><span class="confirm-summary-label">Counterparty type</span><span>${escapeHtml(capitalize(data.counterparty_type || '—'))}</span></li>
          <li><span class="confirm-summary-label">Order type</span><span>${escapeHtml(capitalize(data.order_type || '—'))}</span></li>
          <li><span class="confirm-summary-label">Amount (TZS)</span><span>${escapeHtml(formatTZS(data.amount_tzs))}</span></li>
          <li><span class="confirm-summary-label">Payment status</span><span>${escapeHtml(capitalize(data.payment_status || '—'))}</span></li>
          <li><span class="confirm-summary-label">Due date</span><span>${escapeHtml(formatDate(data.due_date))}</span></li>
          <li><span class="confirm-summary-label">Paid date</span><span>${escapeHtml(data.paid_date ? formatDate(data.paid_date) : '—')}</span></li>
          <li><span class="confirm-summary-label">Transaction date</span><span>${escapeHtml(formatDate(data.transaction_date))}</span></li>
          ${data.notes ? `<li><span class="confirm-summary-label">Notes</span><span>${escapeHtml(data.notes)}</span></li>` : ''}
        </ul>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="tx-confirm-cancel">Cancel / Edit</button>
          <button type="button" class="btn btn-primary" id="tx-confirm-save">Confirm &amp; Save</button>
        </div>
      </div>
    </div>
  `;
  document.getElementById('tx-confirm-cancel')?.addEventListener('click', closeTxModal);
  document.getElementById('tx-confirm-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'tx-confirm-backdrop') closeTxModal();
  });
  document.getElementById('tx-confirm-save')?.addEventListener('click', async () => {
    closeTxModal();
    await onConfirm();
  });
}

function bindTxTableActions(rows, refresh) {
  const host = document.getElementById('tx-table-host');
  if (!host) return;

  host.querySelectorAll('[data-tx-edit]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-tx-edit');
      const row = rows.find((r) => String(r.id) === String(id));
      if (row) openEditTxModal(row, refresh);
    });
  });

  host.querySelectorAll('[data-tx-delete]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-tx-delete');
      const ref = btn.getAttribute('data-tx-ref') || id;
      showDeleteTxConfirm(id, ref, refresh);
    });
  });
}

function showDeleteTxConfirm(id, ref, refresh) {
  const host = txModalHost();
  host.innerHTML = `
    <div class="modal-backdrop" id="tx-delete-backdrop">
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <h3>Delete transaction?</h3>
        <p>Delete reference <strong>${escapeHtml(ref)}</strong>? This cannot be undone.</p>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="tx-delete-cancel">Cancel</button>
          <button type="button" class="btn btn-danger" id="tx-delete-confirm">Delete</button>
        </div>
      </div>
    </div>
  `;
  document.getElementById('tx-delete-cancel')?.addEventListener('click', closeTxModal);
  document.getElementById('tx-delete-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'tx-delete-backdrop') closeTxModal();
  });
  document.getElementById('tx-delete-confirm')?.addEventListener('click', async () => {
    const btn = document.getElementById('tx-delete-confirm');
    if (btn) { btn.disabled = true; btn.textContent = 'Deleting…'; }
    try {
      await api.deleteTransaction(id);
      closeTxModal();
      showToast('Transaction deleted.', 'success');
      await refresh();
    } catch (err) {
      if (btn) { btn.disabled = false; btn.textContent = 'Delete'; }
      showToast(getErrorMessage(err, 'Delete failed'), 'error');
    }
  });
}

function openEditTxModal(row, refresh) {
  const host = txModalHost();
  host.innerHTML = `
    <div class="modal-backdrop" id="tx-edit-backdrop">
      <div class="modal-dialog profile-modal-wide" role="dialog" aria-modal="true" aria-labelledby="tx-edit-title">
        <h3 id="tx-edit-title">Edit transaction</h3>
        <form id="edit-tx-form" class="auth-form" novalidate>
          <div class="form-grid-2">
            <div class="field"><label for="etx-ref">Reference</label><input id="etx-ref" name="transaction_ref" type="text" required value="${escapeHtml(row.transaction_ref || '')}" /></div>
            <div class="field"><label for="etx-cp-hash">Counterparty hash</label><input id="etx-cp-hash" type="text" readonly value="${escapeHtml(truncateHash(row.counterparty_hash))}" title="${escapeHtml(row.counterparty_hash || '')}" /></div>
          </div>
          <div class="field">
            <label for="etx-cp-name">New counterparty name <span class="optional">(leave blank to keep)</span></label>
            <input id="etx-cp-name" name="counterparty_name" type="text" />
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="etx-cp-type">Counterparty type</label>
              <select id="etx-cp-type" name="counterparty_type" required>
                ${['supplier', 'buyer', 'distributor', 'logistics'].map((v) =>
                  `<option value="${v}"${String(row.counterparty_type || '').toLowerCase() === v ? ' selected' : ''}>${capitalize(v)}</option>`
                ).join('')}
              </select>
            </div>
            <div class="field"><label for="etx-order-type">Order type</label>
              <select id="etx-order-type" name="order_type" required>
                ${['purchase', 'sale', 'service'].map((v) =>
                  `<option value="${v}"${String(row.order_type || '').toLowerCase() === v ? ' selected' : ''}>${capitalize(v)}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="etx-amount">Amount (TZS)</label><input id="etx-amount" name="amount_tzs" type="number" min="0" step="1" required value="${escapeHtml(String(row.amount_tzs ?? row.amount ?? ''))}" /></div>
            <div class="field"><label for="etx-status">Payment status</label>
              <select id="etx-status" name="payment_status" required>
                ${['pending', 'paid', 'partial', 'overdue', 'defaulted'].map((v) =>
                  `<option value="${v}"${String(row.payment_status || row.status || '').toLowerCase() === v ? ' selected' : ''}>${capitalize(v)}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="etx-due">Due date</label><input id="etx-due" name="due_date" type="date" required value="${escapeHtml(toInputDate(row.due_date))}" /></div>
            <div class="field"><label for="etx-paid">Paid date <span class="optional">(optional)</span></label><input id="etx-paid" name="paid_date" type="date" value="${escapeHtml(toInputDate(row.paid_date))}" /></div>
          </div>
          <div class="form-grid-2">
            <div class="field"><label for="etx-date">Transaction date</label><input id="etx-date" name="transaction_date" type="date" required value="${escapeHtml(toInputDate(row.transaction_date || row.date))}" /></div>
            <div class="field"><label for="etx-notes">Notes <span class="optional">(optional)</span></label><input id="etx-notes" name="notes" type="text" value="${escapeHtml(row.notes || '')}" /></div>
          </div>
          <div id="edit-tx-error" class="form-error" hidden></div>
          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" id="etx-cancel">Cancel</button>
            <button type="submit" class="btn btn-primary" id="etx-save">Save changes</button>
          </div>
        </form>
      </div>
    </div>
  `;

  document.getElementById('etx-cancel')?.addEventListener('click', closeTxModal);
  document.getElementById('tx-edit-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'tx-edit-backdrop') closeTxModal();
  });

  document.getElementById('edit-tx-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('edit-tx-error');
    const saveBtn = document.getElementById('etx-save');
    if (errEl) { errEl.hidden = true; errEl.textContent = ''; }

    const fd = new FormData(e.target);
    const data = {
      transaction_ref: String(fd.get('transaction_ref') || '').trim(),
      counterparty_type: fd.get('counterparty_type'),
      order_type: fd.get('order_type'),
      amount_tzs: Number(fd.get('amount_tzs')),
      payment_status: fd.get('payment_status'),
      due_date: toApiDateTime(fd.get('due_date')),
      paid_date: toApiDateTime(fd.get('paid_date')) || null,
      transaction_date: toApiDateTime(fd.get('transaction_date')),
      notes: String(fd.get('notes') || '').trim() || null,
    };
    const cpName = String(fd.get('counterparty_name') || '').trim();
    if (cpName) data.counterparty_name = cpName;

    if (!data.transaction_ref || !data.due_date || !data.transaction_date || !(data.amount_tzs > 0)) {
      const msg = 'Please fill reference, amount, due date, and transaction date.';
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';
    try {
      await api.updateTransaction(row.id, data);
      showToast('Transaction updated.', 'success');
      closeTxModal();
      await refresh();
    } catch (err) {
      const msg = getErrorMessage(err, 'Update failed');
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save changes';
    }
  });
}

function renderTxTable(rows) {
  if (!rows.length) return emptyBlock('No transactions found', 'Adjust filters or upload a CSV statement.');
  return `
    <div class="table-wrap" role="region" aria-label="Transaction table" tabindex="0">
      <table class="data-table">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Counterparty</th>
            <th scope="col">Order type</th>
            <th scope="col">Amount (TZS)</th>
            <th scope="col">Status</th>
            <th scope="col">Reference</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((row) => {
              const type = String(row.order_type || row.type || row.transaction_type || '').toLowerCase();
              const amount = row.amount_tzs ?? row.amount ?? row.value ?? 0;
              const status = row.payment_status || row.status || '—';
              const txId = row.id;
              const ref = row.transaction_ref || row.reference || row.ref || txId || '—';
              return `
                <tr>
                  <td>${escapeHtml(formatDate(row.date || row.transaction_date || row.posted_at))}</td>
                  <td>${escapeHtml(row.counterparty_name || truncateHash(row.counterparty_hash) || row.counterparty_type || row.description || '—')}</td>
                  <td><span class="type-pill type-${escapeHtml(type || 'unknown')}">${escapeHtml(capitalize(type || '—'))}</span></td>
                  <td class="num">${escapeHtml(formatTZS(amount))}</td>
                  <td>${escapeHtml(capitalize(String(status)))}</td>
                  <td>${escapeHtml(ref)}</td>
                  <td class="action-cell table-actions">
                    <button type="button" class="btn btn-ghost btn-sm" data-tx-edit="${escapeHtml(txId)}" aria-label="Edit transaction">Edit</button>
                    <button type="button" class="btn btn-danger btn-sm" data-tx-delete="${escapeHtml(txId)}" data-tx-ref="${escapeHtml(ref)}" aria-label="Delete transaction">Delete</button>
                  </td>
                </tr>`;
            })
            .join('')}
        </tbody>
      </table>
    </div>
  `;
}

/* ─── Upload ───────────────────────────────────────────── */

export function loadSmeUpload(session, { onLogout }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: 'sme',
    user: session.user,
    activeNav: 'upload',
    mainHtml: `
      <div class="page-header">
        <div>
          <h1>Upload CSV statement</h1>
          <p class="page-lead">Import bank transactions to update your credit profile</p>
        </div>
      </div>
      <div class="upload-layout">
        <section class="panel upload-panel" aria-labelledby="upload-title">
          <h2 id="upload-title">Select file</h2>
          <p class="help-text">
            Accepted format: CSV. Required columns:
            <code>transaction_ref</code>, <code>counterparty_name</code>, <code>counterparty_type</code>,
            <code>order_type</code>, <code>amount_tzs</code>, <code>payment_status</code>,
            <code>due_date</code>, <code>transaction_date</code>.
          </p>
          <div class="upload-actions">
            <button type="button" class="btn btn-secondary" id="btn-template">Download template</button>
            <button type="button" class="btn btn-ghost" id="btn-help" aria-expanded="false" aria-controls="upload-help">Formatting help</button>
          </div>
          <div id="upload-help" class="help-panel" hidden>
            <h3>CSV guidelines</h3>
            <ul>
              <li>Use UTF-8 encoding with a header row.</li>
              <li>Dates as ISO timestamps, e.g. <code>2025-01-15</code>.</li>
              <li>Amounts as positive numbers in TZS (no currency symbols).</li>
              <li><code>payment_status</code> one of: <code>pending</code>, <code>paid</code>, <code>partial</code>, <code>overdue</code>, <code>defaulted</code>.</li>
              <li>One supply-chain transaction per row.</li>
            </ul>
          </div>
          <form id="upload-form" class="upload-form">
            <label class="file-drop" for="csv-file">
              <input type="file" id="csv-file" name="file" accept=".csv,text/csv" required />
              <span class="file-drop-label"><strong>Choose a CSV file</strong><span>or drag and drop here</span></span>
              <span id="file-name" class="file-name"></span>
            </label>
            <div id="upload-feedback" class="form-error" role="alert" hidden></div>
            <button type="submit" class="btn btn-primary" id="btn-upload">Upload &amp; process</button>
          </form>
        </section>
        <aside class="panel tip-panel">
          <h2>Before you upload</h2>
          <ol>
            <li>Download the template to match column names.</li>
            <li>Export your e-statement from your bank if available.</li>
            <li>After 5+ transactions, your credit score unlocks on Overview.</li>
          </ol>
        </aside>
      </div>
    `,
  });
  bindSmeShell(onLogout);

  const form = document.getElementById('upload-form');
  const fileInput = document.getElementById('csv-file');
  const fileName = document.getElementById('file-name');
  const feedback = document.getElementById('upload-feedback');
  const submitBtn = document.getElementById('btn-upload');
  const drop = form?.querySelector('.file-drop');

  document.getElementById('btn-help')?.addEventListener('click', () => {
    const panel = document.getElementById('upload-help');
    const btn = document.getElementById('btn-help');
    const open = panel?.hidden;
    if (panel) panel.hidden = !open;
    btn?.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  document.getElementById('btn-template')?.addEventListener('click', async () => {
    try {
      await api.downloadSmeCsvTemplate();
      showToast('Template download started.', 'success');
    } catch (err) {
      showToast(getErrorMessage(err, 'Could not download template'), 'error');
    }
  });

  fileInput?.addEventListener('change', () => {
    if (fileName) fileName.textContent = fileInput.files?.[0]?.name || '';
  });

  ['dragenter', 'dragover'].forEach((evt) => {
    drop?.addEventListener(evt, (e) => { e.preventDefault(); drop.classList.add('is-dragover'); });
  });
  ['dragleave', 'drop'].forEach((evt) => {
    drop?.addEventListener(evt, (e) => { e.preventDefault(); drop.classList.remove('is-dragover'); });
  });
  drop?.addEventListener('drop', (e) => {
    const file = e.dataTransfer?.files?.[0];
    if (file && fileInput) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      if (fileName) fileName.textContent = file.name;
    }
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (feedback) { feedback.hidden = true; feedback.textContent = ''; feedback.className = 'form-error'; }
    const file = fileInput?.files?.[0];
    if (!file) {
      if (feedback) { feedback.hidden = false; feedback.textContent = 'Please choose a CSV file.'; }
      return;
    }
    if (!/\.csv$/i.test(file.name) && file.type && !file.type.includes('csv')) {
      if (feedback) { feedback.hidden = false; feedback.textContent = 'File must be a CSV.'; }
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading…';
    try {
      const result = await api.uploadSmeCsv(file);
      const imported = result?.imported ?? result?.rows_imported ?? result?.count ?? result?.created ?? null;
      const msg = imported != null
        ? `Upload successful — ${formatNumber(imported, 0)} transactions processed.`
        : result?.message || 'Upload successful.';
      if (feedback) { feedback.hidden = false; feedback.className = 'form-success'; feedback.textContent = msg; }
      showToast(msg, 'success');
      form.reset();
      if (fileName) fileName.textContent = '';
    } catch (err) {
      const msg = getErrorMessage(err, 'Upload failed');
      if (feedback) { feedback.hidden = false; feedback.className = 'form-error'; feedback.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Upload & process';
    }
  });
}
