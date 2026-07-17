/**
 * Lender dashboard: portfolio list, NIDA search, SME detail with full fields, statement download.
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
  mountChartResize,
} from '../ui.js';
import { openProfileModal } from './profile.js';

function smeId(row) {
  return row?.sme_profile_id ?? row?.id ?? row?.sme_id ?? row?.user_id ?? row?.uuid ?? null;
}

function smeName(row) {
  return row?.full_name || row?.display_token || row?.business_name || row?.name || row?.email || `SME ${smeId(row) || ''}`;
}

function bindLenderShell(onLogout) {
  const openProfile = () => openProfileModal('lender');
  bindShellActions({ onLogout, onProfile: openProfile });
  document.getElementById('btn-page-profile')?.addEventListener('click', openProfile);
}

export async function loadLenderPortfolio(session, { onLogout, selectedId = null }) {
  const app = document.getElementById('app');
  app.innerHTML = renderShell({
    role: 'lender',
    user: session.user,
    activeNav: 'portfolio',
    mainHtml: `
      <div class="page-header">
        <div>
          <h1>SME portfolio</h1>
          <p class="page-lead">Search and review scored businesses</p>
        </div>
        <div class="page-actions">
          <button type="button" id="btn-page-profile" class="btn btn-secondary">My Profile</button>
        </div>
      </div>
      <form id="portfolio-filters" class="filter-bar" aria-label="Filter portfolio">
        <div class="field field-grow">
          <label for="pf-q">Search</label>
          <input type="search" id="pf-q" name="q" placeholder="Name or reference" />
        </div>
        <div class="field">
          <label for="pf-nida">Search by NIDA</label>
          <input type="text" id="pf-nida" inputmode="numeric" maxlength="20" placeholder="20-digit NIDA" />
        </div>
        <div class="field">
          <label for="pf-risk">Risk</label>
          <select id="pf-risk" name="risk">
            <option value="">All</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div class="field">
          <label for="pf-min">Min score</label>
          <input type="number" id="pf-min" name="min_score" min="300" max="850" step="1" />
        </div>
        <div class="field">
          <label for="pf-max">Max score</label>
          <input type="number" id="pf-max" name="max_score" min="300" max="850" step="1" />
        </div>
        <div class="filter-actions">
          <button type="submit" class="btn btn-primary">Filter</button>
          <button type="reset" class="btn btn-ghost">Reset</button>
        </div>
      </form>
      <div class="lender-layout">
        <section class="panel portfolio-list-panel" aria-labelledby="portfolio-list-title">
          <div class="panel-header"><h2 id="portfolio-list-title">Portfolio SMEs</h2></div>
          <div id="portfolio-list">${loadingBlock('Loading portfolio…')}</div>
        </section>
        <section class="panel portfolio-detail-panel" aria-labelledby="portfolio-detail-title">
          <div class="panel-header"><h2 id="portfolio-detail-title">SME detail</h2></div>
          <div id="portfolio-detail">
            ${emptyBlock('Select an SME', 'Choose a business from the portfolio list to view details.')}
          </div>
        </section>
      </div>
    `,
  });
  bindLenderShell(onLogout);

  const listHost = document.getElementById('portfolio-list');
  const detailHost = document.getElementById('portfolio-detail');
  const form = document.getElementById('portfolio-filters');
  const nidaInput = document.getElementById('pf-nida');
  let currentSelected = selectedId;
  let currentRows = [];

  // NIDA search
  nidaInput?.addEventListener('input', debounce(async () => {
    const val = nidaInput.value.trim();
    if (val.length === 20 && /^[0-9]{20}$/.test(val)) {
      detailHost.innerHTML = loadingBlock('Looking up NIDA…');
      try {
        const detail = await api.getLenderSmeByNida(val);
        const id = smeId(detail);
        const txPayload = await api.getLenderSmeTransactions(id).catch(() => ({ items: [] }));
        renderDetail(detailHost, detail, txPayload, id);
      } catch (err) {
        detailHost.innerHTML = errorBlock('SME not found', getErrorMessage(err));
      }
    }
  }, 500));

  async function fetchList() {
    const fd = new FormData(form);
    const params = {
      q: fd.get('q') || undefined,
      risk: fd.get('risk') || undefined,
      min_score: fd.get('min_score') || undefined,
      max_score: fd.get('max_score') || undefined,
    };
    listHost.innerHTML = loadingBlock('Loading portfolio…');
    try {
      const payload = await api.getLenderPortfolio(params);
      currentRows = normalizeListPayload(payload, ['smes', 'items', 'data', 'results', 'portfolio']);
      listHost.innerHTML = renderPortfolioList(currentRows, currentSelected);
      bindListClicks();
      if (currentSelected) {
        await loadDetail(currentSelected);
      } else if (currentRows.length === 1) {
        currentSelected = smeId(currentRows[0]);
        listHost.innerHTML = renderPortfolioList(currentRows, currentSelected);
        bindListClicks();
        await loadDetail(currentSelected);
      }
    } catch (err) {
      listHost.innerHTML = errorBlock('Could not load portfolio', getErrorMessage(err), 'retry-pf');
      document.getElementById('retry-pf')?.addEventListener('click', fetchList);
    }
  }

  function bindListClicks() {
    listHost.querySelectorAll('[data-sme-id]').forEach((btn) => {
      btn.addEventListener('click', () => {
        currentSelected = btn.getAttribute('data-sme-id');
        listHost.innerHTML = renderPortfolioList(currentRows, currentSelected);
        bindListClicks();
        window.location.hash = `#/lender/sme/${encodeURIComponent(currentSelected)}`;
        loadDetail(currentSelected);
      });
    });
  }

  async function loadDetail(id) {
    if (!id) return;
    detailHost.innerHTML = loadingBlock('Loading SME detail…');
    try {
      const [detail, txPayload] = await Promise.all([
        api.getLenderSmeDetail(id),
        api.getLenderSmeTransactions(id).catch(() => ({ items: [] })),
      ]);
      renderDetail(detailHost, detail, txPayload, id);
    } catch (err) {
      detailHost.innerHTML = errorBlock('Could not load SME', getErrorMessage(err), 'retry-detail');
      document.getElementById('retry-detail')?.addEventListener('click', () => loadDetail(id));
    }
  }

  form?.addEventListener('submit', (e) => { e.preventDefault(); fetchList(); });
  form?.addEventListener('reset', () => { window.setTimeout(fetchList, 0); });
  document.getElementById('pf-q')?.addEventListener('input', debounce(() => fetchList(), 400));

  await fetchList();
  return { loadDetail };
}

function renderPortfolioList(rows, selectedId) {
  if (!rows.length) return emptyBlock('No SMEs found', 'Try clearing filters or invite SMEs to the platform.');
  return `
    <ul class="sme-list">
      ${rows.map((row) => {
        const id = smeId(row);
        const score = row.latest_score ?? row.score ?? row.credit_score;
        const risk = row.risk ?? row.risk_level ?? row.risk_band ?? '—';
        const eligible = row.estimated_eligible_financing ?? row.eligible_financing_tzs ?? row.eligible_amount ?? null;
        const tx = row.transaction_count ?? row.transactions_count ?? row.tx_count ?? null;
        const locked = row.score_locked === true || row.is_locked === true || (tx != null && Number(tx) < 5 && score == null);
        const isActive = String(id) === String(selectedId);
        return `
          <li>
            <button type="button" class="sme-list-item${isActive ? ' is-active' : ''}" data-sme-id="${escapeHtml(id)}" aria-pressed="${isActive ? 'true' : 'false'}">
              <span class="sme-list-name">${escapeHtml(smeName(row))}</span>
              <span class="sme-list-meta">
                <span class="risk-badge ${riskClass(locked ? '' : risk)}">${escapeHtml(locked ? 'Pending' : capitalize(String(risk)))}</span>
                <span>Score ${escapeHtml(locked ? '—' : formatScore(score))}</span>
                <span>${escapeHtml(locked ? '—' : formatTZS(eligible))}</span>
                <span>${escapeHtml(tx != null ? `${formatNumber(tx, 0)} tx` : '—')}</span>
              </span>
            </button>
          </li>`;
      }).join('')}
    </ul>
  `;
}

function renderDetail(host, detail, txPayload, id) {
  const score = detail?.latest_score ?? detail?.score ?? detail?.credit_score;
  const risk = detail?.risk ?? detail?.risk_level ?? detail?.risk_band ?? '—';
  const eligible = detail?.estimated_eligible_financing ?? detail?.eligible_financing_tzs ?? detail?.eligible_amount ?? null;
  const txCount = detail?.transaction_count ?? detail?.transactions_count ?? detail?.tx_count ?? null;
  const totalVolume = detail?.total_volume ?? detail?.total_volume_tzs ?? null;
  const locked = detail?.score_locked === true || detail?.is_locked === true || (txCount != null && Number(txCount) < 5 && score == null);

  const transactions = normalizeListPayload(txPayload, ['transactions', 'items', 'data', 'results', 'history', 'months']);
  const monthlyHistory = normalizeListPayload(detail?.monthly_history || [], ['months', 'history', 'items', 'data']);
  const chartSeries = monthlyHistory.length > 0
    ? monthlyHistory.map((r) => ({
        month: r.year_month || r.month || r.period || formatMonthLabel(r.date),
        score: r.total_volume_tzs ?? r.score ?? r.value ?? r.transaction_count,
      }))
    : aggregateMonthlyVolume(transactions);

  host.innerHTML = `
    <div class="detail-header">
      <div>
        <h3 class="detail-name">${escapeHtml(smeName(detail))}</h3>
        <p class="detail-sub">${escapeHtml(detail?.business_type ? capitalize(detail.business_type) : '')}${detail?.location ? ` · ${escapeHtml(detail.location)}` : ''}</p>
      </div>
      <button type="button" class="btn btn-secondary" id="btn-download-statement">Download statement</button>
    </div>

    <div class="profile-info-grid">
      <div class="profile-info-item"><span class="profile-info-label">NIDA</span><span>${escapeHtml(detail?.nida || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">Full Name</span><span>${escapeHtml(detail?.full_name || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">Phone</span><span>${escapeHtml(detail?.phone || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">Email</span><span>${escapeHtml(detail?.email || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">Location</span><span>${escapeHtml(detail?.location || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">Business Type</span><span>${escapeHtml(detail?.business_type || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">Nationality</span><span>${escapeHtml(detail?.nationality || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">Date of Birth</span><span>${escapeHtml(formatDate(detail?.date_of_birth))}</span></div>
    </div>

    <div class="metric-grid metric-grid-compact" aria-label="SME metrics">
      <article class="metric-card"><h4 class="metric-label">Score</h4><p class="metric-value">${escapeHtml(locked ? 'Locked' : formatScore(score))}</p></article>
      <article class="metric-card"><h4 class="metric-label">Risk</h4><p class="metric-value"><span class="risk-badge ${riskClass(locked ? '' : risk)}">${escapeHtml(locked ? 'Pending' : capitalize(String(risk)))}</span></p></article>
      <article class="metric-card"><h4 class="metric-label">Eligible TZS</h4><p class="metric-value metric-tzs">${escapeHtml(locked ? '—' : formatTZS(eligible))}</p></article>
      <article class="metric-card"><h4 class="metric-label">Total Volume</h4><p class="metric-value metric-tzs">${escapeHtml(totalVolume != null ? formatTZS(totalVolume) : '—')}</p></article>
      <article class="metric-card"><h4 class="metric-label">Transactions</h4><p class="metric-value">${escapeHtml(txCount != null ? formatNumber(txCount, 0) : '—')}</p></article>
    </div>

    <div class="detail-section">
      <h4>Monthly transaction history</h4>
      ${chartSeries.length
        ? `<div class="chart-wrap"><canvas id="lender-chart" width="640" height="220" role="img" aria-label="Monthly transaction history"></canvas></div>`
        : emptyBlock('No history', 'This SME has no monthly series yet.')}
    </div>

    <div class="detail-section">
      <h4>Recent transactions</h4>
      ${renderMiniTxTable(transactions.filter((r) => r.amount_tzs != null || r.amount != null || r.transaction_ref || r.date || r.transaction_date))}
    </div>
  `;

  const canvas = document.getElementById('lender-chart');
  if (canvas && chartSeries.length) mountChartResize(canvas, chartSeries);

  document.getElementById('btn-download-statement')?.addEventListener('click', async () => {
    try {
      await api.downloadLenderSmeStatement(id);
      showToast('Statement download started.', 'success');
    } catch (err) {
      showToast(getErrorMessage(err, 'Download failed'), 'error');
    }
  });
}

function aggregateMonthlyVolume(transactions) {
  const map = new Map();
  transactions.forEach((row) => {
    const raw = row.date || row.transaction_date || row.posted_at;
    if (!raw) return;
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return;
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const amt = Math.abs(Number(row.amount_tzs ?? row.amount ?? 0));
    map.set(key, (map.get(key) || 0) + amt);
  });
  return [...map.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([month, score]) => ({ month, score }));
}

function renderMiniTxTable(rows) {
  if (!rows.length) return emptyBlock('No transactions', 'No transaction rows returned for this SME.');
  const slice = rows.slice(0, 25);
  return `
    <div class="table-wrap" role="region" aria-label="SME transactions" tabindex="0">
      <table class="data-table data-table-compact">
        <thead><tr><th scope="col">Date</th><th scope="col">Reference</th><th scope="col">Amount</th><th scope="col">Status</th></tr></thead>
        <tbody>
          ${slice.map((row) => `
            <tr>
              <td>${escapeHtml(formatDate(row.date || row.transaction_date || row.posted_at))}</td>
              <td>${escapeHtml(row.transaction_ref || row.description || row.narration || '—')}</td>
              <td class="num">${escapeHtml(formatTZS(row.amount_tzs ?? row.amount ?? row.value))}</td>
              <td>${escapeHtml(capitalize(row.payment_status || row.status || '—'))}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>
  `;
}
