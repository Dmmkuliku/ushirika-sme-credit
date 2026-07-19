/**
 * Shared UI: toasts, loading/empty/error panels, shell chrome.
 */

import { escapeHtml, el, setText } from './utils.js';
import { t, langSwitchHtml, toggleLang } from './i18n.js';

export function showToast(message, type = 'info', durationMs = 4500) {
  const root = document.getElementById('toast-root');
  if (!root) return;

  const toast = el('div', {
    className: `toast toast-${type}`,
    attrs: { role: type === 'error' ? 'alert' : 'status' },
  });
  toast.appendChild(el('p', { className: 'toast-message', text: message }));
  const close = el('button', {
    className: 'toast-close',
    attrs: { type: 'button', 'aria-label': 'Dismiss notification' },
    text: '×',
  });
  close.addEventListener('click', () => toast.remove());
  toast.appendChild(close);
  root.appendChild(toast);

  window.setTimeout(() => {
    toast.classList.add('toast-out');
    window.setTimeout(() => toast.remove(), 280);
  }, durationMs);
}

export function loadingBlock(label) {
  const text = label || t('common.loading');
  return `
    <div class="state-block state-loading" role="status" aria-live="polite">
      <div class="spinner" aria-hidden="true"></div>
      <p>${escapeHtml(text)}</p>
    </div>
  `;
}

export function emptyBlock(title, description = '') {
  return `
    <div class="state-block state-empty">
      <h3>${escapeHtml(title)}</h3>
      ${description ? `<p>${escapeHtml(description)}</p>` : ''}
    </div>
  `;
}

export function errorBlock(title, description = '', retryId = null) {
  return `
    <div class="state-block state-error" role="alert">
      <h3>${escapeHtml(title)}</h3>
      ${description ? `<p>${escapeHtml(description)}</p>` : ''}
      ${
        retryId
          ? `<button type="button" class="btn btn-secondary" id="${escapeHtml(retryId)}">${escapeHtml(t('common.tryAgain'))}</button>`
          : ''
      }
    </div>
  `;
}

function roleLabel(role) {
  if (role === 'admin') return t('roles.admin');
  if (role === 'subadmin') return t('roles.subadmin');
  if (role === 'lender') return t('roles.lender');
  return t('roles.sme');
}

function roleHome(role) {
  if (role === 'admin' || role === 'subadmin') return 'admin';
  if (role === 'lender') return 'lender';
  return 'sme';
}

export function renderShell({ role, user, activeNav, mainHtml }) {
  const displayName =
    user?.full_name || user?.business_name || user?.email || roleLabel(role);

  const smeNav = [
    { id: 'overview', label: t('nav.overview'), href: '#/sme' },
    { id: 'transactions', label: t('nav.transactions'), href: '#/sme/transactions' },
    { id: 'upload', label: t('nav.upload'), href: '#/sme/upload' },
  ];
  const lenderNav = [
    { id: 'portfolio', label: t('nav.portfolio'), href: '#/lender' },
  ];
  const adminNav = [
    { id: 'accounts', label: t('nav.accounts'), href: '#/admin' },
    { id: 'ml', label: t('nav.mlMetrics'), href: '#/admin/ml' },
    { id: 'profile', label: t('nav.myProfile'), href: '#/admin/profile' },
    { id: 'create-lender', label: t('nav.createLender'), href: '#/admin/create-lender' },
    { id: 'create-sme', label: t('nav.createSme'), href: '#/admin/create-sme' },
    { id: 'create-subadmin', label: t('nav.createSubadmin'), href: '#/admin/create-subadmin' },
  ];

  let navItems;
  if (role === 'admin' || role === 'subadmin') navItems = adminNav;
  else if (role === 'lender') navItems = lenderNav;
  else navItems = smeNav;

  const navHtml = navItems
    .map(
      (item) => `
      <a
        href="${item.href}"
        class="nav-link${activeNav === item.id ? ' is-active' : ''}"
        ${activeNav === item.id ? 'aria-current="page"' : ''}
      >${escapeHtml(item.label)}</a>`
    )
    .join('');

  const profileBtn =
    `<button type="button" id="btn-my-profile" class="btn btn-ghost btn-sm">${escapeHtml(t('common.profile'))}</button>`;

  return `
    <div class="app-shell">
      <header class="topbar">
        <div class="topbar-brand">
          <a href="#/${roleHome(role)}" class="brand-mark" aria-label="${escapeHtml(t('brand.name'))} home">
            <span class="brand-glyph" aria-hidden="true"></span>
            <span class="brand-text">${escapeHtml(t('brand.name'))}</span>
          </a>
          <span class="brand-sub">${escapeHtml(t('brand.subtitle'))}</span>
        </div>
        <div class="topbar-toolbar">
          ${langSwitchHtml()}
          <button
            type="button"
            class="btn btn-ghost btn-sm nav-toggle"
            id="btn-nav-toggle"
            aria-expanded="false"
            aria-controls="primary-nav"
            aria-label="Menu"
          >
            <span class="nav-toggle-bars" aria-hidden="true"></span>
          </button>
        </div>
        <nav class="topbar-nav" id="primary-nav" aria-label="Primary">
          ${navHtml}
          <div class="topbar-user">
            <div class="user-meta">
              <span class="user-name">${escapeHtml(displayName)}</span>
              <span class="user-role">${escapeHtml(roleLabel(role))}</span>
            </div>
            ${profileBtn}
            <button type="button" id="btn-logout" class="btn btn-ghost btn-sm">${escapeHtml(t('common.logout'))}</button>
          </div>
        </nav>
      </header>
      <div class="nav-backdrop" id="nav-backdrop" hidden></div>
      <main id="main" class="main-content" tabindex="-1">
        ${mainHtml}
      </main>
    </div>
  `;
}

function closeMobileNav() {
  const shell = document.querySelector('.app-shell');
  const toggle = document.getElementById('btn-nav-toggle');
  const backdrop = document.getElementById('nav-backdrop');
  shell?.classList.remove('nav-open');
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
  if (backdrop) backdrop.hidden = true;
  document.body.classList.remove('nav-lock');
}

function openMobileNav() {
  const shell = document.querySelector('.app-shell');
  const toggle = document.getElementById('btn-nav-toggle');
  const backdrop = document.getElementById('nav-backdrop');
  shell?.classList.add('nav-open');
  if (toggle) toggle.setAttribute('aria-expanded', 'true');
  if (backdrop) backdrop.hidden = false;
  document.body.classList.add('nav-lock');
}

export function bindShellActions({ onLogout, onProfile }) {
  document.getElementById('btn-logout')?.addEventListener('click', () => {
    closeMobileNav();
    onLogout?.();
  });
  document.getElementById('btn-my-profile')?.addEventListener('click', () => {
    closeMobileNav();
    onProfile?.();
  });
  document.querySelectorAll('[data-lang-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => toggleLang());
  });

  const toggle = document.getElementById('btn-nav-toggle');
  const backdrop = document.getElementById('nav-backdrop');
  toggle?.addEventListener('click', () => {
    const open = document.querySelector('.app-shell')?.classList.contains('nav-open');
    if (open) closeMobileNav();
    else openMobileNav();
  });
  backdrop?.addEventListener('click', closeMobileNav);
  document.querySelectorAll('.topbar-nav .nav-link').forEach((link) => {
    link.addEventListener('click', closeMobileNav);
  });
}

export function bindLogout(onLogout) {
  bindShellActions({ onLogout });
}

export function drawMonthlyChart(canvas, series) {
  if (!canvas || !series?.length) return;

  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = canvas.clientHeight || 240;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.scale(dpr, dpr);

  const pad = { top: 16, right: 16, bottom: 36, left: 44 };
  const w = cssW - pad.left - pad.right;
  const h = cssH - pad.top - pad.bottom;

  const values = series.map((p) => Number(p.score ?? p.value ?? 0));
  const labels = series.map((p) => p.month || p.label || '');
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const range = max - min || 1;

  ctx.clearRect(0, 0, cssW, cssH);

  ctx.strokeStyle = 'rgba(15, 40, 48, 0.08)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (h * i) / 4;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + w, y);
    ctx.stroke();
    const tick = max - (range * i) / 4;
    ctx.fillStyle = 'rgba(15, 40, 48, 0.45)';
    ctx.font = '11px Manrope, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(String(Math.round(tick)), pad.left - 8, y + 4);
  }

  const points = values.map((v, i) => {
    const x = pad.left + (values.length === 1 ? w / 2 : (i / (values.length - 1)) * w);
    const y = pad.top + h - ((v - min) / range) * h;
    return { x, y };
  });

  const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + h);
  grad.addColorStop(0, 'rgba(26, 122, 109, 0.28)');
  grad.addColorStop(1, 'rgba(26, 122, 109, 0.02)');
  ctx.beginPath();
  points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
  ctx.lineTo(points[points.length - 1].x, pad.top + h);
  ctx.lineTo(points[0].x, pad.top + h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.beginPath();
  points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
  ctx.strokeStyle = '#1a7a6d';
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  ctx.stroke();

  points.forEach((p, i) => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = '#0b3d2e';
    ctx.fill();
    ctx.fillStyle = 'rgba(15, 40, 48, 0.55)';
    ctx.font = '10px Manrope, sans-serif';
    ctx.textAlign = 'center';
    const label = labels[i];
    const short =
      label.length > 8 && label.includes('-')
        ? label.slice(5)
        : label.slice(0, 7);
    ctx.fillText(short, p.x, cssH - 12);
  });
}

export function mountChartResize(canvas, series) {
  const draw = () => drawMonthlyChart(canvas, series);
  draw();
  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(draw) : null;
  if (ro) ro.observe(canvas.parentElement || canvas);
  return () => ro?.disconnect();
}

export function scoreRingSvg(score, locked) {
  const size = 140;
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const numeric = Number(score) || 0;
  const normalized = Math.max(0, Math.min(100, ((numeric - 300) / 550) * 100));
  const offset = c - (normalized / 100) * c;
  return `
    <svg class="score-ring" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" aria-hidden="true">
      <circle class="score-ring-track" cx="${size / 2}" cy="${size / 2}" r="${r}" stroke-width="${stroke}" fill="none" />
      <circle
        class="score-ring-value${locked ? ' is-locked' : ''}"
        cx="${size / 2}" cy="${size / 2}" r="${r}"
        stroke-width="${stroke}" fill="none"
        stroke-dasharray="${c}"
        stroke-dashoffset="${locked ? c : offset}"
        transform="rotate(-90 ${size / 2} ${size / 2})"
      />
    </svg>
  `;
}

export { el, setText };
