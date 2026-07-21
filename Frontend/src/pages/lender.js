/**
 * Lender dashboard: portfolio list, progressive NIDA search, tabbed SME detail.
 */

import * as api from '../api.js';
import {
  escapeHtml,
  formatTZS,
  formatScore,
  formatBirthDate,
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
import { businessTypeLabel, t, featureLabel } from '../i18n.js';
import { formatTzPhone } from '../form-validation.js';

function smeId(row) {
  return row?.sme_profile_id ?? row?.id ?? row?.sme_id ?? row?.user_id ?? row?.uuid ?? null;
}

function smeName(row) {
  return row?.full_name || row?.display_token || row?.business_name || row?.name || row?.email || `SME ${smeId(row) || ''}`;
}

function localizedRisk(value) {
  const key = String(value || '').toLowerCase();
  return ['low', 'medium', 'high', 'pending'].includes(key) ? t(`risk.${key}`) : String(value || '—');
}

function localizedPayment(value) {
  const key = String(value || '').toLowerCase();
  return ['pending', 'paid', 'partial', 'overdue', 'defaulted'].includes(key)
    ? t(`payment.${key}`)
    : String(value || '—');
}

function localizedModel(value) {
  const key = String(value || '').toLowerCase();
  const translated = t(`models.${key}`);
  return translated === `models.${key}` ? String(value || '—').replace(/_/g, ' ') : translated;
}

function bindLenderShell(onLogout) {
  const openProfile = () => openProfileModal('lender');
  bindShellActions({ onLogout, onProfile: openProfile });
  document.getElementById('btn-page-profile')?.addEventListener('click', openProfile);
}

/** Progressive NIDA filter: keep matches, sort closer prefixes first. */
function filterSortByNida(rows, prefix) {
  if (!prefix) return rows.slice();
  const matched = rows.filter((r) => String(r.nida || '').startsWith(prefix));
  return matched.sort((a, b) => {
    const an = String(a.nida || '');
    const bn = String(b.nida || '');
    const aExact = an === prefix ? 0 : 1;
    const bExact = bn === prefix ? 0 : 1;
    if (aExact !== bExact) return aExact - bExact;
    return an.localeCompare(bn);
  });
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
          <h1>${escapeHtml(t('lender.portfolioTitle'))}</h1>
          <p class="page-lead">${escapeHtml(t('lender.portfolioLead'))}</p>
        </div>
        <div class="page-actions">
          <button type="button" id="btn-page-profile" class="btn btn-secondary">${escapeHtml(t('nav.myProfile'))}</button>
        </div>
      </div>
      <form id="portfolio-filters" class="filter-bar" aria-label="${escapeHtml(t('lender.filterAria'))}">
        <div class="field field-grow">
          <label for="pf-q">${escapeHtml(t('common.search'))}</label>
          <input type="search" id="pf-q" name="q" placeholder="${escapeHtml(t('lender.searchPlaceholder'))}" />
        </div>
        <div class="field">
          <label for="pf-nida">${escapeHtml(t('lender.searchByNida'))}</label>
          <input type="text" id="pf-nida" inputmode="numeric" maxlength="20" placeholder="${escapeHtml(t('lender.nidaPlaceholder'))}" />
        </div>
        <div class="field">
          <label for="pf-risk">${escapeHtml(t('lender.risk'))}</label>
          <select id="pf-risk" name="risk">
            <option value="">${escapeHtml(t('common.all'))}</option>
            <option value="low">${escapeHtml(t('risk.low'))}</option>
            <option value="medium">${escapeHtml(t('risk.medium'))}</option>
            <option value="high">${escapeHtml(t('risk.high'))}</option>
          </select>
        </div>
        <div class="field">
          <label for="pf-min">${escapeHtml(t('lender.minScore'))}</label>
          <input type="number" id="pf-min" name="min_score" min="300" max="850" step="1" />
        </div>
        <div class="field">
          <label for="pf-max">${escapeHtml(t('lender.maxScore'))}</label>
          <input type="number" id="pf-max" name="max_score" min="300" max="850" step="1" />
        </div>
        <div class="filter-actions">
          <button type="submit" class="btn btn-primary">${escapeHtml(t('lender.filter'))}</button>
          <button type="reset" class="btn btn-ghost">${escapeHtml(t('common.reset'))}</button>
        </div>
      </form>
      <div class="lender-layout">
        <section class="panel portfolio-list-panel" aria-labelledby="portfolio-list-title">
          <div class="panel-header"><h2 id="portfolio-list-title">${escapeHtml(t('lender.portfolioSmes'))}</h2></div>
          <div id="portfolio-list">${loadingBlock(t('lender.loadingPortfolio'))}</div>
        </section>
        <section class="panel portfolio-detail-panel" aria-labelledby="portfolio-detail-title">
          <div class="panel-header"><h2 id="portfolio-detail-title">${escapeHtml(t('lender.smeDetail'))}</h2></div>
          <div id="portfolio-detail">
            ${emptyBlock(t('lender.selectSme'), t('lender.selectSmeLead'))}
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
  let allRows = [];
  let currentRows = [];

  function refreshListView() {
    const prefix = (nidaInput?.value || '').replace(/\D/g, '').slice(0, 20);
    currentRows = filterSortByNida(allRows, prefix);
    listHost.innerHTML = renderPortfolioList(currentRows, currentSelected);
    bindListClicks();
  }

  // Progressive NIDA: filter/sort list as digits are typed (no need for full 20)
  nidaInput?.addEventListener('input', debounce(async () => {
    const val = nidaInput.value.replace(/\D/g, '').slice(0, 20);
    if (nidaInput.value !== val) nidaInput.value = val;
    refreshListView();

    if (!val) return;

    // Unique local match → open detail
    if (currentRows.length === 1) {
      const id = smeId(currentRows[0]);
      if (id && String(id) !== String(currentSelected)) {
        currentSelected = id;
        refreshListView();
        window.location.hash = `#/lender/sme/${encodeURIComponent(id)}`;
        await loadDetail(id);
      }
      return;
    }

    // Exact 20-digit lookup via API
    if (val.length === 20) {
      detailHost.innerHTML = loadingBlock(t('lender.lookingUpNida'));
      try {
        const detail = await api.getLenderSmeByNida(val);
        const id = smeId(detail);
        currentSelected = id;
        refreshListView();
        const txPayload = await api.getLenderSmeTransactions(id).catch(() => ({ items: [] }));
        renderDetail(detailHost, detail, txPayload, id);
      } catch (err) {
        detailHost.innerHTML = errorBlock(t('lender.smeNotFound'), getErrorMessage(err));
      }
    }
  }, 280));

  async function fetchList() {
    const fd = new FormData(form);
    const params = {
      q: fd.get('q') || undefined,
      risk: fd.get('risk') || undefined,
      min_score: fd.get('min_score') || undefined,
      max_score: fd.get('max_score') || undefined,
    };
    listHost.innerHTML = loadingBlock(t('lender.loadingPortfolio'));
    try {
      const payload = await api.getLenderPortfolio(params);
      allRows = normalizeListPayload(payload, ['smes', 'items', 'data', 'results', 'portfolio']);
      refreshListView();
      if (currentSelected) {
        await loadDetail(currentSelected);
      } else if (currentRows.length === 1) {
        currentSelected = smeId(currentRows[0]);
        refreshListView();
        await loadDetail(currentSelected);
      }
    } catch (err) {
      listHost.innerHTML = errorBlock(t('lender.couldNotLoadPortfolio'), getErrorMessage(err), 'retry-pf');
      document.getElementById('retry-pf')?.addEventListener('click', fetchList);
    }
  }

  function bindListClicks() {
    listHost.querySelectorAll('[data-sme-id]').forEach((btn) => {
      btn.addEventListener('click', () => {
        currentSelected = btn.getAttribute('data-sme-id');
        refreshListView();
        window.location.hash = `#/lender/sme/${encodeURIComponent(currentSelected)}`;
        loadDetail(currentSelected);
      });
    });
  }

  async function loadDetail(id) {
    if (!id) return;
    detailHost.innerHTML = loadingBlock(t('lender.loadingDetail'));
    try {
      const [detail, txPayload] = await Promise.all([
        api.getLenderSmeDetail(id),
        api.getLenderSmeTransactions(id).catch(() => ({ items: [] })),
      ]);
      renderDetail(detailHost, detail, txPayload, id);
    } catch (err) {
      detailHost.innerHTML = errorBlock(t('lender.couldNotLoadSme'), getErrorMessage(err), 'retry-detail');
      document.getElementById('retry-detail')?.addEventListener('click', () => loadDetail(id));
    }
  }

  form?.addEventListener('submit', (e) => { e.preventDefault(); fetchList(); });
  form?.addEventListener('reset', () => {
    window.setTimeout(() => {
      if (nidaInput) nidaInput.value = '';
      fetchList();
    }, 0);
  });
  document.getElementById('pf-q')?.addEventListener('input', debounce(() => fetchList(), 400));

  await fetchList();
  return { loadDetail };
}

function renderPortfolioList(rows, selectedId) {
  if (!rows.length) return emptyBlock(t('lender.noSmes'), t('lender.noSmesLead'));
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
        const riskLabel = locked ? t('risk.pending') : localizedRisk(risk);
        return `
          <li>
            <button type="button" class="sme-list-item${isActive ? ' is-active' : ''}" data-sme-id="${escapeHtml(id)}" aria-pressed="${isActive ? 'true' : 'false'}">
              <span class="sme-list-name">${escapeHtml(smeName(row))}</span>
              <span class="sme-list-meta">
                <span class="risk-badge ${riskClass(locked ? '' : risk)}">${escapeHtml(riskLabel)}</span>
                <span>${escapeHtml(t('lender.score'))} ${escapeHtml(locked ? '—' : formatScore(score))}</span>
                <span>${escapeHtml(locked ? '—' : formatTZS(eligible))}</span>
                <span>${escapeHtml(tx != null ? `${formatNumber(tx, 0)} ${t('lender.txShort')}` : '—')}</span>
              </span>
              ${row.nida ? `<span class="sme-list-nida">${escapeHtml(row.nida)}</span>` : ''}
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
  const proba = detail?.probability_creditworthy;
  const modelVersion = detail?.model_version || '—';
  const primaryModel = detail?.primary_model || 'random_forest';
  const mlSummary = detail?.ml_summary || '';
  const featureRows = Array.isArray(detail?.ml_features_display) ? detail.ml_features_display : [];
  const outlierCount = detail?.outlier_transaction_count;
  const typicalVol = detail?.typical_volume_tzs;

  const transactions = normalizeListPayload(txPayload, ['transactions', 'items', 'data', 'results', 'history', 'months']);
  const monthlyHistory = normalizeListPayload(detail?.monthly_history || [], ['months', 'history', 'items', 'data']);
  const chartSeries = monthlyHistory.length > 0
    ? monthlyHistory.map((r) => ({
        month: r.year_month || r.month || r.period || formatMonthLabel(r.date),
        score: r.total_volume_tzs ?? r.score ?? r.value ?? r.transaction_count,
      }))
    : aggregateMonthlyVolume(transactions);

  const probaPct = Number.isFinite(Number(proba)) ? `${(Number(proba) * 100).toFixed(1)}%` : '—';
  const riskLabel = locked ? t('risk.pending') : localizedRisk(risk);

  const mlHtml = `
    <section class="detail-tab-panel ml-metrics-panel" data-tab-panel="ml" aria-labelledby="ml-metrics-title">
      <div class="ml-metrics-header">
        <h4 id="ml-metrics-title">${escapeHtml(t('lender.mlMetricsTitle'))}</h4>
        <span class="ml-chip">v${escapeHtml(String(modelVersion))}</span>
      </div>
      <p class="page-lead">${escapeHtml(mlSummary || t('lender.mlMetricsLead'))}</p>
      <div class="metric-grid metric-grid-compact" aria-label="${escapeHtml(t('lender.mlMetricsTitle'))}">
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.mlScore'))}</h4><p class="metric-value">${escapeHtml(locked ? t('sme.locked') : formatScore(score))}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.riskBand'))}</h4><p class="metric-value"><span class="risk-badge ${riskClass(locked ? '' : risk)}">${escapeHtml(riskLabel)}</span></p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.creditworthyProb'))}</h4><p class="metric-value">${escapeHtml(locked ? '—' : probaPct)}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.eligibleTzs'))}</h4><p class="metric-value metric-tzs">${escapeHtml(locked ? '—' : formatTZS(eligible))}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.primaryModel'))}</h4><p class="metric-value" style="font-size:1rem">${escapeHtml(localizedModel(primaryModel))}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.txUsed'))}</h4><p class="metric-value">${escapeHtml(txCount != null ? formatNumber(txCount, 0) : '—')}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.totalVolume'))}</h4><p class="metric-value metric-tzs">${escapeHtml(totalVolume != null ? formatTZS(totalVolume) : '—')}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.typicalVolume'))}</h4><p class="metric-value metric-tzs">${escapeHtml(typicalVol != null ? formatTZS(typicalVol) : '—')}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.unusualTxs'))}</h4><p class="metric-value">${escapeHtml(outlierCount != null ? formatNumber(outlierCount, 0) : '—')}</p></article>
      </div>
      ${locked
        ? emptyBlock(t('lender.scoreNotReady'), t('lender.scoreNotReadyLead', { count: detail?.transactions_needed ?? '—' }))
        : ''}
    </section>
  `;

  const signalsHtml = `
    <section class="detail-tab-panel" data-tab-panel="signals" hidden>
      <h4>${escapeHtml(t('lender.signalsTitle'))}</h4>
      ${locked
        ? emptyBlock(t('lender.scoreNotReady'), t('lender.scoreNotReadyLead', { count: detail?.transactions_needed ?? '—' }))
        : renderFeatureBars(featureRows)}
    </section>
  `;

  const txDataHtml = `
    <section class="detail-tab-panel" data-tab-panel="txdata" hidden>
      <h4>${escapeHtml(t('lender.txDataTitle'))}</h4>
      <div class="metric-grid metric-grid-compact">
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.txUsed'))}</h4><p class="metric-value">${escapeHtml(txCount != null ? formatNumber(txCount, 0) : '—')}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.totalVolume'))}</h4><p class="metric-value metric-tzs">${escapeHtml(totalVolume != null ? formatTZS(totalVolume) : '—')}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.typicalVolume'))}</h4><p class="metric-value metric-tzs">${escapeHtml(typicalVol != null ? formatTZS(typicalVol) : '—')}</p></article>
        <article class="metric-card"><h4 class="metric-label">${escapeHtml(t('lender.unusualTxs'))}</h4><p class="metric-value">${escapeHtml(outlierCount != null ? formatNumber(outlierCount, 0) : '—')}</p></article>
      </div>
      <p class="page-lead">${escapeHtml(t('lender.txDataLead'))}</p>
    </section>
  `;

  const historyHtml = `
    <section class="detail-tab-panel" data-tab-panel="history" hidden>
      <h4>${escapeHtml(t('lender.monthlyHistory'))}</h4>
      ${chartSeries.length
        ? `<div class="chart-wrap"><canvas id="lender-chart" width="640" height="220" role="img" aria-label="${escapeHtml(t('lender.monthlyHistory'))}"></canvas></div>`
        : emptyBlock(t('lender.noHistory'), t('lender.noHistoryLead'))}
    </section>
  `;

  const recentHtml = `
    <section class="detail-tab-panel" data-tab-panel="recent" hidden>
      <h4>${escapeHtml(t('lender.recentTx'))}</h4>
      ${renderMiniTxTable(transactions.filter((r) => r.amount_tzs != null || r.amount != null || r.transaction_ref || r.date || r.transaction_date))}
    </section>
  `;

  host.innerHTML = `
    <div class="detail-header">
      <div>
        <h3 class="detail-name">${escapeHtml(smeName(detail))}</h3>
        <p class="detail-sub">${escapeHtml(detail?.business_type ? businessTypeLabel(detail.business_type) : '')}${detail?.location ? ` · ${escapeHtml(detail.location)}` : ''}</p>
      </div>
      <button type="button" class="btn btn-secondary" id="btn-download-statement">${escapeHtml(t('lender.downloadStatement'))}</button>
    </div>

    <div class="profile-info-grid">
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.nida'))}</span><span>${escapeHtml(detail?.nida || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.fullName'))}</span><span>${escapeHtml(detail?.full_name || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.tin'))}</span><span>${escapeHtml(detail?.tin || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.phone'))}</span><span>${escapeHtml(detail?.phone ? formatTzPhone(detail.phone) : '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.email'))}</span><span>${escapeHtml(detail?.email || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.location'))}</span><span>${escapeHtml(detail?.location || '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.businessType'))}</span><span>${escapeHtml(detail?.business_type ? businessTypeLabel(detail.business_type) : '—')}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.nationality'))}</span><span>${escapeHtml(String(detail?.nationality || '').toLowerCase() === 'tanzanian' ? t('nationality.tanzanian') : (detail?.nationality || '—'))}</span></div>
      <div class="profile-info-item"><span class="profile-info-label">${escapeHtml(t('profile.dateOfBirth'))}</span><span>${escapeHtml(formatBirthDate(detail?.date_of_birth))}</span></div>
    </div>

    <div class="detail-tabs" role="tablist" aria-label="${escapeHtml(t('lender.detailTabs'))}">
      <button type="button" class="detail-tab is-active" role="tab" aria-selected="true" data-tab="ml">${escapeHtml(t('lender.tabMl'))}</button>
      <button type="button" class="detail-tab" role="tab" aria-selected="false" data-tab="signals">${escapeHtml(t('lender.tabSignals'))}</button>
      <button type="button" class="detail-tab" role="tab" aria-selected="false" data-tab="txdata">${escapeHtml(t('lender.tabTxData'))}</button>
      <button type="button" class="detail-tab" role="tab" aria-selected="false" data-tab="history">${escapeHtml(t('lender.tabHistory'))}</button>
      <button type="button" class="detail-tab" role="tab" aria-selected="false" data-tab="recent">${escapeHtml(t('lender.tabRecent'))}</button>
    </div>

    <div class="detail-tab-panels">
      ${mlHtml}
      ${signalsHtml}
      ${txDataHtml}
      ${historyHtml}
      ${recentHtml}
    </div>
  `;

  host.querySelectorAll('.detail-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      host.querySelectorAll('.detail-tab').forEach((b) => {
        const on = b === btn;
        b.classList.toggle('is-active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      host.querySelectorAll('[data-tab-panel]').forEach((panel) => {
        panel.hidden = panel.getAttribute('data-tab-panel') !== tab;
      });
      if (tab === 'history') {
        const canvas = document.getElementById('lender-chart');
        if (canvas && chartSeries.length) mountChartResize(canvas, chartSeries);
      }
    });
  });

  document.getElementById('btn-download-statement')?.addEventListener('click', async () => {
    try {
      await api.downloadLenderSmeStatement(id);
      showToast(t('lender.statementStarted'), 'success');
    } catch (err) {
      showToast(getErrorMessage(err, t('lender.downloadFailed')), 'error');
    }
  });
}

function renderFeatureBars(rows) {
  if (!rows.length) return emptyBlock(t('lender.noFeatures'), t('lender.noFeaturesLead'));
  const slice = rows.slice(0, 10);
  const numeric = slice
    .map((r) => ({ ...r, num: Number(r.value) }))
    .filter((r) => Number.isFinite(r.num));
  const maxAbs = Math.max(...numeric.map((r) => Math.abs(r.num)), 1);
  return `
    <div class="ml-feature-block">
      <h5 class="ml-feature-title">${escapeHtml(t('lender.signalsTitle'))}</h5>
      <ul class="ml-feature-list">
        ${slice.map((row) => {
          const val = Number(row.value);
          const width = Number.isFinite(val) ? Math.min(100, Math.round((Math.abs(val) / maxAbs) * 100)) : 8;
          const label = row.key ? featureLabel(row.key) : (row.name || t('lender.feature'));
          const shown = Number.isFinite(val)
            ? (Math.abs(val) >= 1000 ? formatNumber(val, 0) : formatNumber(val, 4))
            : String(row.value ?? '—');
          return `
            <li class="ml-feature-row">
              <div class="ml-feature-meta">
                <span>${escapeHtml(label)}</span>
                <strong>${escapeHtml(shown)}</strong>
              </div>
              <div class="ml-feature-track" aria-hidden="true"><span class="ml-feature-fill" style="width:${width}%"></span></div>
            </li>`;
        }).join('')}
      </ul>
    </div>
  `;
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
  if (!rows.length) return emptyBlock(t('lender.noTx'), t('lender.noTxLead'));
  const slice = rows.slice(0, 25);
  return `
    <div class="table-wrap" role="region" aria-label="${escapeHtml(t('lender.recentTx'))}" tabindex="0">
      <table class="data-table data-table-compact">
        <thead><tr>
          <th scope="col">${escapeHtml(t('sme.colDate'))}</th>
          <th scope="col">${escapeHtml(t('sme.reference'))}</th>
          <th scope="col">${escapeHtml(t('sme.colAmount'))}</th>
          <th scope="col">${escapeHtml(t('sme.colStatus'))}</th>
        </tr></thead>
        <tbody>
          ${slice.map((row) => `
            <tr>
              <td>${escapeHtml(formatDate(row.date || row.transaction_date || row.posted_at))}</td>
              <td>${escapeHtml(row.transaction_ref || row.description || row.narration || '—')}</td>
              <td class="num">${escapeHtml(formatTZS(row.amount_tzs ?? row.amount ?? row.value))}</td>
              <td>${escapeHtml(localizedPayment(row.payment_status || row.status || '—'))}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>
  `;
}
