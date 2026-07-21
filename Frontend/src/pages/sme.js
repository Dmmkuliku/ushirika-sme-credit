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
import { t, featureLabel } from '../i18n.js';
import { todayIso } from '../form-validation.js';

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
  return `${s}T00:00:00Z`;
}

function paymentLabel(status) {
  const key = String(status || '').toLowerCase();
  const map = {
    pending: t('payment.pending'),
    paid: t('payment.paid'),
    partial: t('payment.partial'),
    overdue: t('payment.overdue'),
    defaulted: t('payment.defaulted'),
  };
  return map[key] || capitalize(String(status || '—'));
}

function partyLabel(type) {
  const key = String(type || '').toLowerCase();
  if (key === 'buyer') return t('party.buyer');
  if (key === 'seller') return t('party.seller');
  return capitalize(String(type || '—'));
}

function orderLabel(type) {
  const key = String(type || '').toLowerCase();
  if (key === 'sale') return t('order.sale');
  if (key === 'purchase') return t('order.purchase');
  if (key === 'service') return t('order.service');
  return capitalize(String(type || '—'));
}

function riskLabel(risk, locked) {
  if (locked) return t('risk.pending');
  const key = String(risk || '').toLowerCase();
  if (key.includes('low')) return t('risk.low');
  if (key.includes('medium') || key.includes('med')) return t('risk.medium');
  if (key.includes('high')) return t('risk.high');
  return capitalize(String(risk || '—'));
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

/** Prefer score_components_display; fall back to snake_case map via featureLabel. */
const CRUCIAL_COMPONENT_KEYS = new Set([
  'payment_consistency',
  'on_time_rate',
  'default_rate',
  'payment_delay_avg',
  'typical_volume_tzs',
  'turnover_tzs',
  'transaction_frequency',
  'volume_trend',
  'compliance_rate',
  'outlier_transaction_count',
]);

function componentsList(overview) {
  const display = overview?.score_components_display;
  if (Array.isArray(display) && display.length) {
    return display
      .filter((c) => !c.key || CRUCIAL_COMPONENT_KEYS.has(c.key))
      .map((c) => ({
        name: c.name || (c.key ? featureLabel(c.key) : 'Factor'),
        value: c.value,
        key: c.key,
      }));
  }

  const raw =
    overview?.score_components ||
    overview?.components ||
    overview?.explainability ||
    overview?.factors ||
    [];
  if (Array.isArray(raw)) {
    return raw
      .map((c) => {
        if (c && typeof c === 'object') {
          const key = c.key || c.name;
          return {
            name: c.name || (key ? featureLabel(key) : 'Factor'),
            value: c.contribution ?? c.value ?? c.score ?? c.weight,
            key,
          };
        }
        return { name: String(c), value: null };
      })
      .filter((c) => !c.key || CRUCIAL_COMPONENT_KEYS.has(c.key));
  }
  if (raw && typeof raw === 'object') {
    return Object.entries(raw)
      .filter(([name, v]) => CRUCIAL_COMPONENT_KEYS.has(name) && !Array.isArray(v) && typeof v !== 'object')
      .map(([name, value]) => ({
        name: featureLabel(name),
        value,
        key: name,
      }));
  }
  return [];
}

/* ─── Overview ─────────────────────────────────────────── */

export function renderSmeOverviewLoading(session) {
  return renderShell({
    role: 'sme',
    user: session.user,
    activeNav: 'overview',
    mainHtml: loadingBlock(t('sme.loadingOverview')),
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
      mainHtml: errorBlock(t('sme.couldNotLoadOverview'), getErrorMessage(err), 'retry-overview'),
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
  const outlierCount = overview?.outlier_transaction_count;
  const modelVersion = overview?.model_version;

  const lockNote = locked
    ? t('sme.scoreUnlocks', { count: formatNumber(txCount, 0) })
    : t('sme.basedOnTx', { count: formatNumber(txCount, 0) });

  const notesHtml = [
    outlierCount != null && Number(outlierCount) > 0
      ? `<p class="score-note">${escapeHtml(t('sme.outlierNote', { count: formatNumber(outlierCount, 0) }))}</p>`
      : '',
    modelVersion
      ? `<p class="score-note score-note-muted">${escapeHtml(t('sme.modelVersion', { version: modelVersion }))}</p>`
      : '',
  ].join('');

  const componentsHtml =
    components.length === 0
      ? emptyBlock(t('sme.noExplain'), t('sme.componentsAppear'))
      : `<ul class="component-list">
          ${components
            .map((c) => {
              const name = c.name || 'Factor';
              const value = c.value;
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
                  <div class="component-bar" aria-hidden="true">
                    <span style="width:${Math.min(100, Math.abs(Number(value) <= 1 ? Number(value) * 100 : Number(value)) || 0)}%"></span>
                  </div>
                </li>`;
            })
            .join('')}
        </ul>`;

  const chartSection =
    history.length === 0
      ? emptyBlock(t('sme.noHistory'), t('sme.uploadForHistory'))
      : `<div class="chart-wrap"><canvas id="score-chart" width="640" height="240" role="img" aria-label="${escapeHtml(t('sme.monthlyHistory'))}"></canvas></div>`;

  const mainHtml = `
    <div class="page-header">
      <div>
        <h1>${escapeHtml(t('sme.creditOverview'))}</h1>
        <p class="page-lead">${escapeHtml(lockNote)}</p>
        ${notesHtml}
      </div>
      <div class="page-actions">
        <button type="button" class="btn btn-secondary" id="btn-export-overview">${escapeHtml(t('sme.downloadStatement'))}</button>
        <a class="btn btn-primary" href="#/sme/upload">${escapeHtml(t('sme.uploadCsv'))}</a>
      </div>
    </div>
    <section class="metric-grid" aria-label="Key credit metrics">
      <article class="metric-card metric-score ${locked ? 'is-locked' : ''}">
        <h2 class="metric-label">${escapeHtml(t('sme.creditScore'))}</h2>
        <div class="score-display">
          ${scoreRingSvg(locked ? 0 : score, locked)}
          <div class="score-display-text">
            ${locked
              ? `<span class="score-locked-label">${escapeHtml(t('sme.locked'))}</span>
                 <span class="score-locked-hint">${escapeHtml(`${txCount}/5`)}</span>`
              : `<span class="score-number">${escapeHtml(formatScore(score))}</span>
                 <span class="score-hint">${escapeHtml(t('sme.outOf850'))}</span>`
            }
          </div>
        </div>
      </article>
      <article class="metric-card">
        <h2 class="metric-label">${escapeHtml(t('sme.riskBand'))}</h2>
        <p class="metric-value">
          <span class="risk-badge ${riskClass(locked ? '' : risk)}">${escapeHtml(riskLabel(risk, locked))}</span>
        </p>
        <p class="metric-hint">${escapeHtml(t('sme.portfolioRisk'))}</p>
      </article>
      <article class="metric-card">
        <h2 class="metric-label">${escapeHtml(t('sme.estFinancing'))}</h2>
        <p class="metric-value metric-tzs">${escapeHtml(locked ? '—' : formatTZS(eligible))}</p>
        <p class="metric-hint">${escapeHtml(t('sme.indicativeTzs'))}</p>
      </article>
      <article class="metric-card">
        <h2 class="metric-label">${escapeHtml(t('sme.transactions'))}</h2>
        <p class="metric-value">${escapeHtml(formatNumber(txCount, 0))}</p>
        <p class="metric-hint">${escapeHtml(locked ? t('sme.need5') : t('sme.feedingModel'))}</p>
      </article>
    </section>
    <div class="split-panels">
      <section class="panel" aria-labelledby="components-title">
        <div class="panel-header">
          <h2 id="components-title">${escapeHtml(t('sme.scoreComponents'))}</h2>
          <p>${escapeHtml(t('sme.explainability'))}</p>
        </div>
        ${locked ? emptyBlock(t('sme.componentsLocked'), t('sme.upload5Explain')) : componentsHtml}
      </section>
      <section class="panel" aria-labelledby="history-title">
        <div class="panel-header">
          <h2 id="history-title">${escapeHtml(t('sme.monthlyHistory'))}</h2>
          <p>${escapeHtml(t('sme.volumeTrend'))}</p>
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
      showToast(t('sme.statementStarted'), 'success');
    } catch (err) {
      showToast(getErrorMessage(err, t('sme.exportFailed')), 'error');
    }
  });
}

/* ─── Transaction form fields (create + edit) ──────────── */

function recordTxFieldsHtml(prefix, row = null) {
  const id = (name) => `${prefix}-${name}`;
  const val = (key, fallback = '') => (row ? escapeHtml(String(row[key] ?? fallback)) : '');
  const sel = (field, options) =>
    options
      .map(([v, label]) => {
        const selected = row && String(row[field] || '').toLowerCase() === v ? ' selected' : '';
        return `<option value="${v}"${selected}>${escapeHtml(label)}</option>`;
      })
      .join('');

  return `
    <div class="form-grid-2">
      <div class="field">
        <label for="${id('ref')}">${escapeHtml(t('sme.reference'))}</label>
        <input id="${id('ref')}" name="transaction_ref" type="text" required value="${val('transaction_ref')}" />
      </div>
      <div class="field">
        <label for="${id('cp-tin')}">${escapeHtml(t('sme.otherPartyTin'))}</label>
        <input id="${id('cp-tin')}" name="counterparty_tin" type="text" inputmode="numeric" required minlength="9" maxlength="9" pattern="[0-9]{9}" placeholder="9 digits" value="${val('counterparty_tin')}" />
        <p class="field-hint">${escapeHtml(t('sme.otherPartyTinHint'))}</p>
      </div>
    </div>
    <div class="form-grid-2">
      <div class="field">
        <label for="${id('cp-name')}">${escapeHtml(t('sme.otherPartyName'))}</label>
        <input id="${id('cp-name')}" name="counterparty_name" type="text" required value="${val('counterparty_name')}" />
      </div>
      <div class="field">
        <label for="${id('cp-type')}">${escapeHtml(t('sme.partyType'))}</label>
        <select id="${id('cp-type')}" name="counterparty_type" required>
          <option value="">${escapeHtml(t('common.select'))}</option>
          ${sel('counterparty_type', [
            ['buyer', t('party.buyer')],
            ['seller', t('party.seller')],
          ])}
        </select>
      </div>
    </div>
    <div class="form-grid-2">
      <div class="field">
        <label for="${id('order-type')}">${escapeHtml(t('sme.orderType'))}</label>
        <select id="${id('order-type')}" name="order_type" required>
          <option value="">${escapeHtml(t('common.select'))}</option>
          ${sel('order_type', [
            ['sale', t('order.sale')],
            ['purchase', t('order.purchase')],
            ['service', t('order.service')],
          ])}
        </select>
      </div>
      <div class="field">
        <label for="${id('amount')}">${escapeHtml(t('sme.amountTzs'))}</label>
        <input id="${id('amount')}" name="amount_tzs" type="number" min="0" step="1" required value="${row ? escapeHtml(String(row.amount_tzs ?? row.amount ?? '')) : ''}" />
      </div>
    </div>
    <div class="form-grid-2">
      <div class="field">
        <label for="${id('status')}">${escapeHtml(t('sme.paymentStatus'))}</label>
        <select id="${id('status')}" name="payment_status" required>
          <option value="">${escapeHtml(t('common.select'))}</option>
          ${sel('payment_status', [
            ['pending', t('payment.pending')],
            ['paid', t('payment.paid')],
            ['partial', t('payment.partial')],
            ['overdue', t('payment.overdue')],
            ['defaulted', t('payment.defaulted')],
          ])}
        </select>
      </div>
      <div class="field">
        <label for="${id('date')}">${escapeHtml(t('sme.transactionDate'))}</label>
        <input id="${id('date')}" name="transaction_date" type="date" max="${todayIso()}" required value="${row ? escapeHtml(toInputDate(row.transaction_date || row.date)) : ''}" />
      </div>
    </div>
    <div class="field">
      <label for="${id('notes')}">${escapeHtml(t('sme.notes'))} <span class="optional">${escapeHtml(t('common.optional'))}</span></label>
      <input id="${id('notes')}" name="notes" type="text" value="${val('notes')}" />
    </div>
  `;
}

function parseTxFormData(fd) {
  return {
    transaction_ref: String(fd.get('transaction_ref') || '').trim(),
    counterparty_tin: String(fd.get('counterparty_tin') || '').trim().replace(/\D/g, ''),
    counterparty_name: String(fd.get('counterparty_name') || '').trim(),
    counterparty_type: String(fd.get('counterparty_type') || ''),
    order_type: String(fd.get('order_type') || ''),
    amount_tzs: Number(fd.get('amount_tzs')),
    payment_status: String(fd.get('payment_status') || ''),
    transaction_date: toApiDateTime(fd.get('transaction_date')),
    notes: String(fd.get('notes') || '').trim() || undefined,
  };
}

function validateTxData(data) {
  if (!data.transaction_ref || !(data.amount_tzs > 0) || !data.transaction_date) {
    return t('sme.fillRequired');
  }
  if (String(data.transaction_date).slice(0, 10) > todayIso()) {
    return t('sme.errFutureDate');
  }
  if (!/^[0-9]{9}$/.test(data.counterparty_tin || '')) {
    return t('sme.errTinExact');
  }
  if (!data.counterparty_name || !data.counterparty_type || !data.order_type || !data.payment_status) {
    return t('sme.fillRequired');
  }
  return null;
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
          <h1>${escapeHtml(t('sme.txTitle'))}</h1>
          <p class="page-lead">${escapeHtml(t('sme.txLead'))}</p>
        </div>
        <div class="page-actions">
          <button type="button" class="btn btn-secondary" id="btn-toggle-record">${escapeHtml(t('sme.recordTx'))}</button>
          <button type="button" class="btn btn-secondary" id="btn-export-tx">${escapeHtml(t('sme.exportCsv'))}</button>
        </div>
      </div>

      <section id="record-tx-section" class="panel record-tx-panel" hidden>
        <div class="panel-header"><h3>${escapeHtml(t('sme.recordPanelTitle'))}</h3></div>
        <form id="record-tx-form" class="auth-form" novalidate>
          ${recordTxFieldsHtml('rtx')}
          <div id="record-tx-error" class="form-error" hidden></div>
          <button type="submit" class="btn btn-primary" id="record-tx-submit">${escapeHtml(t('sme.saveTx'))}</button>
        </form>
      </section>

      <form id="tx-filters" class="filter-bar" aria-label="Filter transactions">
        <div class="field"><label for="tx-from">${escapeHtml(t('sme.from'))}</label><input type="date" id="tx-from" name="from" /></div>
        <div class="field"><label for="tx-to">${escapeHtml(t('sme.to'))}</label><input type="date" id="tx-to" name="to" /></div>
        <div class="field"><label for="tx-type">${escapeHtml(t('sme.orderType'))}</label>
          <select id="tx-type" name="type">
            <option value="">${escapeHtml(t('common.all'))}</option>
            <option value="sale">${escapeHtml(t('order.sale'))}</option>
            <option value="purchase">${escapeHtml(t('order.purchase'))}</option>
            <option value="service">${escapeHtml(t('order.service'))}</option>
          </select>
        </div>
        <div class="field field-grow"><label for="tx-q">${escapeHtml(t('common.search'))}</label><input type="search" id="tx-q" name="q" placeholder="${escapeHtml(t('sme.searchPlaceholder'))}" /></div>
        <div class="filter-actions">
          <button type="submit" class="btn btn-primary">${escapeHtml(t('common.apply'))}</button>
          <button type="reset" class="btn btn-ghost">${escapeHtml(t('common.reset'))}</button>
        </div>
      </form>
      <div id="tx-table-host">${loadingBlock(t('sme.loadingTx'))}</div>
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
    const data = parseTxFormData(new FormData(recordForm));
    const validationError = validateTxData(data);
    if (validationError) {
      if (errEl) { errEl.hidden = false; errEl.textContent = validationError; }
      return;
    }
    showCreateConfirmModal(data, async () => {
      const btn = document.getElementById('record-tx-submit');
      btn.disabled = true;
      btn.textContent = t('sme.saving');
      try {
        await api.createTransaction(data);
        showToast(t('sme.txRecorded'), 'success');
        recordForm.reset();
        recordSection.hidden = true;
        fetchAndRender();
      } catch (err) {
        const msg = getErrorMessage(err, t('sme.failedRecord'));
        if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
        showToast(msg, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = t('sme.saveTx');
      }
    });
  });

  async function fetchAndRender() {
    const fd = new FormData(form);
    host.innerHTML = loadingBlock(t('sme.loadingTx'));
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
          const hay = `${row.transaction_ref || ''} ${row.notes || ''} ${row.counterparty_tin || ''} ${row.counterparty_name || ''} ${row.order_type || ''}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
      host.innerHTML = renderTxTable(rows);
      bindTxTableActions(rows, fetchAndRender);
    } catch (err) {
      host.innerHTML = errorBlock(t('sme.couldNotLoadTx'), getErrorMessage(err), 'retry-tx');
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
      showToast(t('sme.csvExportStarted'), 'success');
    } catch (err) {
      showToast(getErrorMessage(err, t('sme.exportFailed')), 'error');
    }
  });

  await fetchAndRender();
}

function showCreateConfirmModal(data, onConfirm) {
  const host = txModalHost();
  host.innerHTML = `
    <div class="modal-backdrop" id="tx-confirm-backdrop">
      <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="tx-confirm-title">
        <h3 id="tx-confirm-title">${escapeHtml(t('sme.confirmTitle'))}</h3>
        <p>${escapeHtml(t('sme.confirmLead'))}</p>
        <ul class="confirm-summary">
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.reference'))}</span><span>${escapeHtml(data.transaction_ref || '—')}</span></li>
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.otherPartyName'))}</span><span>${escapeHtml(data.counterparty_name || '—')}</span></li>
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.otherPartyTin'))}</span><span>${escapeHtml(data.counterparty_tin || '—')}</span></li>
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.partyType'))}</span><span>${escapeHtml(partyLabel(data.counterparty_type))}</span></li>
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.orderType'))}</span><span>${escapeHtml(orderLabel(data.order_type))}</span></li>
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.amountTzs'))}</span><span>${escapeHtml(formatTZS(data.amount_tzs))}</span></li>
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.paymentStatus'))}</span><span>${escapeHtml(paymentLabel(data.payment_status))}</span></li>
          <li><span class="confirm-summary-label">${escapeHtml(t('sme.transactionDate'))}</span><span>${escapeHtml(formatDate(data.transaction_date))}</span></li>
          ${data.notes ? `<li><span class="confirm-summary-label">${escapeHtml(t('sme.notes'))}</span><span>${escapeHtml(data.notes)}</span></li>` : ''}
        </ul>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="tx-confirm-cancel">${escapeHtml(t('sme.cancelEdit'))}</button>
          <button type="button" class="btn btn-primary" id="tx-confirm-save">${escapeHtml(t('sme.confirmSave'))}</button>
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
        <h3>${escapeHtml(t('sme.deleteTitle'))}</h3>
        <p>${escapeHtml(t('sme.deleteConfirm', { ref }))}</p>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="tx-delete-cancel">${escapeHtml(t('common.cancel'))}</button>
          <button type="button" class="btn btn-danger" id="tx-delete-confirm">${escapeHtml(t('common.delete'))}</button>
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
    if (btn) { btn.disabled = true; btn.textContent = t('sme.deleting'); }
    try {
      await api.deleteTransaction(id);
      closeTxModal();
      showToast(t('sme.txDeleted'), 'success');
      await refresh();
    } catch (err) {
      if (btn) { btn.disabled = false; btn.textContent = t('common.delete'); }
      showToast(getErrorMessage(err, t('sme.deleteFailed')), 'error');
    }
  });
}

function openEditTxModal(row, refresh) {
  const host = txModalHost();
  host.innerHTML = `
    <div class="modal-backdrop" id="tx-edit-backdrop">
      <div class="modal-dialog profile-modal-wide" role="dialog" aria-modal="true" aria-labelledby="tx-edit-title">
        <h3 id="tx-edit-title">${escapeHtml(t('sme.editTitle'))}</h3>
        <form id="edit-tx-form" class="auth-form" novalidate>
          ${recordTxFieldsHtml('etx', row)}
          <div id="edit-tx-error" class="form-error" hidden></div>
          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" id="etx-cancel">${escapeHtml(t('common.cancel'))}</button>
            <button type="submit" class="btn btn-primary" id="etx-save">${escapeHtml(t('sme.saveChanges'))}</button>
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

    const data = parseTxFormData(new FormData(e.target));
    const validationError = validateTxData(data);
    if (validationError) {
      if (errEl) { errEl.hidden = false; errEl.textContent = validationError; }
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = t('sme.saving');
    try {
      await api.updateTransaction(row.id, data);
      showToast(t('sme.txUpdated'), 'success');
      closeTxModal();
      await refresh();
    } catch (err) {
      const msg = getErrorMessage(err, t('sme.updateFailed'));
      if (errEl) { errEl.hidden = false; errEl.textContent = msg; }
      showToast(msg, 'error');
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = t('sme.saveChanges');
    }
  });
}

function renderTxTable(rows) {
  if (!rows.length) return emptyBlock(t('sme.noTx'), t('sme.adjustFilters'));
  return `
    <div class="table-wrap" role="region" aria-label="Transaction table" tabindex="0">
      <table class="data-table">
        <thead>
          <tr>
            <th scope="col">${escapeHtml(t('sme.colDate'))}</th>
            <th scope="col">${escapeHtml(t('sme.colName'))}</th>
            <th scope="col">${escapeHtml(t('sme.colTin'))}</th>
            <th scope="col">${escapeHtml(t('sme.colAmount'))}</th>
            <th scope="col">${escapeHtml(t('sme.colStatus'))}</th>
            <th scope="col">${escapeHtml(t('common.edit'))} / ${escapeHtml(t('common.delete'))}</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((row) => {
              const amount = row.amount_tzs ?? row.amount ?? row.value ?? 0;
              const status = row.payment_status || row.status || '—';
              const txId = row.id;
              const ref = row.transaction_ref || row.reference || row.ref || txId || '—';
              const outlier = row.is_outlier
                ? ` <span class="outlier-badge" title="${escapeHtml(t('sme.outlierBadge'))}">${escapeHtml(t('sme.outlierBadge'))}</span>`
                : '';
              return `
                <tr class="${row.is_outlier ? 'is-outlier' : ''}">
                  <td>${escapeHtml(formatDate(row.date || row.transaction_date || row.posted_at))}</td>
                  <td>${escapeHtml(row.counterparty_name || '—')}${outlier}</td>
                  <td>${escapeHtml(row.counterparty_tin || '—')}</td>
                  <td class="num">${escapeHtml(formatTZS(amount))}</td>
                  <td>${escapeHtml(paymentLabel(status))}</td>
                  <td class="action-cell table-actions">
                    <button type="button" class="btn btn-ghost btn-sm" data-tx-edit="${escapeHtml(txId)}" aria-label="${escapeHtml(t('common.edit'))}">${escapeHtml(t('common.edit'))}</button>
                    <button type="button" class="btn btn-danger btn-sm" data-tx-delete="${escapeHtml(txId)}" data-tx-ref="${escapeHtml(ref)}" aria-label="${escapeHtml(t('common.delete'))}">${escapeHtml(t('common.delete'))}</button>
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
          <h1>${escapeHtml(t('sme.uploadTitle'))}</h1>
          <p class="page-lead">${escapeHtml(t('sme.uploadLead'))}</p>
        </div>
      </div>
      <div class="upload-layout">
        <section class="panel upload-panel" aria-labelledby="upload-title">
          <h2 id="upload-title">${escapeHtml(t('sme.selectFile'))}</h2>
          <p class="help-text">
            ${escapeHtml(t('sme.acceptedFormat'))}
            <code>transaction_ref</code>, <code>counterparty_tin</code>, <code>counterparty_name</code>,
            <code>counterparty_type</code>, <code>order_type</code>, <code>amount_tzs</code>,
            <code>payment_status</code>, <code>transaction_date</code>.
          </p>
          <div class="upload-actions">
            <button type="button" class="btn btn-secondary" id="btn-template">${escapeHtml(t('sme.downloadTemplate'))}</button>
            <button type="button" class="btn btn-ghost" id="btn-help" aria-expanded="false" aria-controls="upload-help">${escapeHtml(t('sme.formattingHelp'))}</button>
          </div>
          <div id="upload-help" class="help-panel" hidden>
            <h3>${escapeHtml(t('sme.csvGuidelines'))}</h3>
            <ul>
              <li>${escapeHtml(t('sme.csvUtf8'))}</li>
              <li>${escapeHtml(t('sme.csvDates'))}</li>
              <li>${escapeHtml(t('sme.csvAmounts'))}</li>
              <li>${escapeHtml(t('sme.csvStatus'))}</li>
              <li>${escapeHtml(t('sme.csvOneRow'))}</li>
            </ul>
          </div>
          <form id="upload-form" class="upload-form">
            <label class="file-drop" for="csv-file">
              <input type="file" id="csv-file" name="file" accept=".csv,text/csv" required />
              <span class="file-drop-label"><strong>${escapeHtml(t('sme.chooseCsv'))}</strong><span>${escapeHtml(t('sme.orDrag'))}</span></span>
              <span id="file-name" class="file-name"></span>
            </label>
            <div id="upload-feedback" class="form-error" role="alert" hidden></div>
            <div id="upload-progress" class="upload-progress" hidden>
              <div class="upload-progress-bar" id="upload-progress-bar"></div>
              <p id="upload-progress-text">${escapeHtml(t('sme.processingMl'))}</p>
            </div>
            <button type="submit" class="btn btn-primary" id="btn-upload">${escapeHtml(t('sme.uploadProcess'))}</button>
          </form>
          <div id="ml-result-host" class="ml-result-host" hidden></div>
        </section>
        <aside class="panel tip-panel">
          <h2>${escapeHtml(t('sme.beforeUpload'))}</h2>
          <ol>
            <li>${escapeHtml(t('sme.tip1'))}</li>
            <li>${escapeHtml(t('sme.tip2'))}</li>
            <li>${escapeHtml(t('sme.tip3'))}</li>
            <li>${escapeHtml(t('sme.tip4'))}</li>
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
  const progress = document.getElementById('upload-progress');
  const progressBar = document.getElementById('upload-progress-bar');
  const progressText = document.getElementById('upload-progress-text');
  const resultHost = document.getElementById('ml-result-host');
  const drop = form?.querySelector('.file-drop');

  function setProgress(pct, text) {
    if (progress) progress.hidden = false;
    if (progressBar) progressBar.style.width = `${Math.max(5, Math.min(100, pct))}%`;
    if (progressText && text) progressText.textContent = text;
  }

  function renderMlResult(result) {
    if (!resultHost) return;
    if (!result?.score_ready) {
      resultHost.hidden = false;
      resultHost.innerHTML = `
        <section class="ml-metrics-panel">
          <h4>${escapeHtml(t('sme.mlPendingTitle'))}</h4>
          <p class="page-lead">${escapeHtml(result?.message || t('sme.mlNeedMore', { count: result?.transactions_needed ?? 5 }))}</p>
          <a class="btn btn-secondary" href="#/sme">${escapeHtml(t('sme.backOverview'))}</a>
        </section>`;
      return;
    }
    const proba = Number(result.probability_creditworthy);
    const probaPct = Number.isFinite(proba) ? `${(proba * 100).toFixed(1)}%` : '—';
    const rows = Array.isArray(result.ml_features_display) ? result.ml_features_display.slice(0, 10) : [];
    const training = result?.model_training_summary && typeof result.model_training_summary === 'object'
      ? result.model_training_summary
      : null;
    const trainingHtml = training
      ? (result.model_training_scheduled || training.note)
        ? `
        <div class="detail-section" style="margin-top:0.9rem">
          <h5 class="ml-feature-title">${escapeHtml(t('sme.trainingOutputTitle'))}</h5>
          <p class="help-text">${escapeHtml(training.note || t('sme.trainingScheduled'))}</p>
        </div>`
        : `
        <div class="detail-section" style="margin-top:0.9rem">
          <h5 class="ml-feature-title">${escapeHtml(t('sme.trainingOutputTitle'))}</h5>
          <ul class="ml-feature-list">
            <li class="ml-feature-row"><div class="ml-feature-meta"><span>${escapeHtml(t('sme.trainingVersion'))}</span><strong>${escapeHtml(String(result.model_training_version || '—'))}</strong></div></li>
            <li class="ml-feature-row"><div class="ml-feature-meta"><span>RF Accuracy</span><strong>${escapeHtml(training.rf_accuracy != null ? formatNumber(training.rf_accuracy * 100, 2) + '%' : '—')}</strong></div></li>
            <li class="ml-feature-row"><div class="ml-feature-meta"><span>RF ROC-AUC</span><strong>${escapeHtml(training.rf_roc_auc != null ? formatNumber(training.rf_roc_auc * 100, 2) + '%' : '—')}</strong></div></li>
            <li class="ml-feature-row"><div class="ml-feature-meta"><span>LR ROC-AUC</span><strong>${escapeHtml(training.lr_roc_auc != null ? formatNumber(training.lr_roc_auc * 100, 2) + '%' : '—')}</strong></div></li>
            <li class="ml-feature-row"><div class="ml-feature-meta"><span>${escapeHtml(t('sme.trainingProfilesUsed'))}</span><strong>${escapeHtml(training.real_sme_profiles_used != null ? formatNumber(training.real_sme_profiles_used, 0) : '—')}</strong></div></li>
            <li class="ml-feature-row"><div class="ml-feature-meta"><span>${escapeHtml(t('sme.trainingComparison'))}</span><strong>${escapeHtml(training.rf_outperforms_baseline ? 'RF > LR' : 'RF ≤ LR')}</strong></div></li>
          </ul>
        </div>`
      : '';
    resultHost.hidden = false;
    resultHost.innerHTML = `
      <section class="ml-metrics-panel" aria-live="polite">
        <div class="ml-metrics-header">
          <h4>${escapeHtml(t('sme.mlReadyTitle'))}</h4>
          <span class="ml-chip">v${escapeHtml(String(result.model_version || '—'))}</span>
        </div>
        <p class="page-lead">${escapeHtml(result.message || t('sme.mlReadyLead'))}</p>
        <div class="metric-grid metric-grid-compact">
          <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('sme.mlScore'))}</h4><p class="metric-value">${escapeHtml(formatScore(result.score))}</p></article>
          <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('sme.mlRisk'))}</h4><p class="metric-value"><span class="risk-badge ${riskClass(result.risk_band)}">${escapeHtml(riskLabel(result.risk_band, false))}</span></p></article>
          <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('sme.mlProb'))}</h4><p class="metric-value">${escapeHtml(probaPct)}</p></article>
          <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('sme.mlEligible'))}</h4><p class="metric-value metric-tzs">${escapeHtml(formatTZS(result.eligible_financing_tzs))}</p></article>
        </div>
        ${rows.length ? `
          <h5 class="ml-feature-title">${escapeHtml(t('sme.mlSignals'))}</h5>
          <ul class="ml-feature-list">
            ${rows.map((row) => {
              const label = row.name || row.key || 'Signal';
              const val = row.value;
              const shown = typeof val === 'number'
                ? (Math.abs(val) >= 1000 ? formatNumber(val, 0) : formatNumber(val, 4))
                : String(val ?? '—');
              return `<li class="ml-feature-row"><div class="ml-feature-meta"><span>${escapeHtml(label)}</span><strong>${escapeHtml(shown)}</strong></div></li>`;
            }).join('')}
          </ul>` : ''}
        ${trainingHtml}
        <div class="upload-actions" style="margin-top:1rem">
          <a class="btn btn-primary" href="#/sme">${escapeHtml(t('sme.viewFullOverview'))}</a>
        </div>
      </section>`;
  }

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
      showToast(t('sme.templateStarted'), 'success');
    } catch (err) {
      showToast(getErrorMessage(err, t('sme.templateFailed')), 'error');
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
    if (resultHost) { resultHost.hidden = true; resultHost.innerHTML = ''; }
    const file = fileInput?.files?.[0];
    if (!file) {
      if (feedback) { feedback.hidden = false; feedback.textContent = t('sme.pleaseChooseCsv'); }
      return;
    }
    if (!/\.csv$/i.test(file.name) && file.type && !file.type.includes('csv')) {
      if (feedback) { feedback.hidden = false; feedback.textContent = t('sme.mustBeCsv'); }
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = t('sme.uploading');
    setProgress(18, t('sme.processingUpload'));
    try {
      await api.ensureApiReady({
        onProgress: ({ attempt, maxAttempts }) => {
          setProgress(12, t('auth.wakingServerProgress', { attempt, max: maxAttempts }));
        },
      });
      setProgress(18, t('sme.processingUpload'));
      const uploadPromise = api.uploadSmeCsv(file);
      // Soft progress while waiting for import + ML score
      let tick = 18;
      const timer = window.setInterval(() => {
        tick = Math.min(88, tick + 7);
        setProgress(tick, tick < 45 ? t('sme.processingUpload') : t('sme.processingMl'));
      }, 450);

      const result = await uploadPromise;
      window.clearInterval(timer);
      setProgress(100, t('sme.processingDone'));

      const imported = result?.imported ?? 0;
      const skipped = result?.skipped ?? 0;
      const errors = Array.isArray(result?.errors) ? result.errors : [];
      let msg = imported > 0
        ? t('sme.uploadOk', { count: formatNumber(imported, 0) })
        : (result?.message || t('sme.uploadOkGeneric'));
      if (skipped) msg += ` ${t('sme.uploadSkipped', { count: formatNumber(skipped, 0) })}`;
      if (errors.length) msg += ` ${t('sme.uploadRowErrors', { count: formatNumber(errors.length, 0) })}`;

      if (imported === 0 && errors.length) {
        if (feedback) {
          feedback.hidden = false;
          feedback.className = 'form-error';
          feedback.textContent = `${msg}\n${errors.slice(0, 5).join('\n')}`;
        }
        showToast(t('sme.uploadFailed'), 'error');
        return;
      }

      if (feedback) {
        feedback.hidden = false;
        feedback.className = errors.length ? 'form-warning' : 'form-success';
        feedback.textContent = errors.length ? `${msg}\n${errors.slice(0, 3).join('\n')}` : msg;
      }
      showToast(msg, errors.length ? 'info' : 'success');
      renderMlResult(result);
      form.reset();
      if (fileName) fileName.textContent = '';
      if (result?.score_ready) {
        window.setTimeout(() => { window.location.hash = '#/sme'; }, 2200);
      }
    } catch (err) {
      const msg = err?.detail === 'request_timeout'
        ? t('sme.uploadTimeout')
        : getErrorMessage(err, t('sme.uploadFailed'));
      if (feedback) { feedback.hidden = false; feedback.className = 'form-error'; feedback.textContent = msg; }
      showToast(msg, 'error');
      if (progress) progress.hidden = true;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t('sme.uploadProcess');
      window.setTimeout(() => { if (progress) progress.hidden = true; }, 800);
    }
  });
}
