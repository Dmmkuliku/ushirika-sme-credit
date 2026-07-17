/**
 * Shared UI: toasts, loading/empty/error panels, shell chrome.
 */

import { escapeHtml, el, setText } from './utils.js';

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

export function loadingBlock(label = 'Loading…') {
  return `
    <div class="state-block state-loading" role="status" aria-live="polite">
      <div class="spinner" aria-hidden="true"></div>
      <p>${escapeHtml(label)}</p>
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
          ? `<button type="button" class="btn btn-secondary" id="${escapeHtml(retryId)}">Try again</button>`
          : ''
      }
    </div>
  `;
}

function roleLabel(role) {
  if (role === 'admin') return 'Admin';
  if (role === 'subadmin') return 'Sub-Admin';
  if (role === 'lender') return 'Lender';
  return 'SME';
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
    { id: 'overview', label: 'Overview', href: '#/sme' },
    { id: 'transactions', label: 'Transactions', href: '#/sme/transactions' },
    { id: 'upload', label: 'Upload CSV', href: '#/sme/upload' },
  ];
  const lenderNav = [
    { id: 'portfolio', label: 'Portfolio', href: '#/lender' },
  ];
  const adminNav = [
    { id: 'accounts', label: 'Accounts', href: '#/admin' },
    { id: 'profile', label: 'My Profile', href: '#/admin/profile' },
    { id: 'create-lender', label: 'Create Lender', href: '#/admin/create-lender' },
    { id: 'create-sme', label: 'Create SME', href: '#/admin/create-sme' },
    { id: 'create-subadmin', label: 'Create Sub-Admin', href: '#/admin/create-subadmin' },
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
    `<button type="button" id="btn-my-profile" class="btn btn-ghost btn-sm">Profile</button>`;

  return `
    <div class="app-shell">
      <header class="topbar">
        <div class="topbar-brand">
          <a href="#/${roleHome(role)}" class="brand-mark" aria-label="Ushirika home">
            <span class="brand-glyph" aria-hidden="true"></span>
            <span class="brand-text">Ushirika</span>
          </a>
          <span class="brand-sub">Tanzania SME Banking</span>
        </div>
        <nav class="topbar-nav" aria-label="Primary">
          ${navHtml}
        </nav>
        <div class="topbar-user">
          <div class="user-meta">
            <span class="user-name">${escapeHtml(displayName)}</span>
            <span class="user-role">${escapeHtml(roleLabel(role))}</span>
          </div>
          ${profileBtn}
          <button type="button" id="btn-logout" class="btn btn-ghost btn-sm">Log out</button>
        </div>
      </header>
      <main id="main" class="main-content" tabindex="-1">
        ${mainHtml}
      </main>
    </div>
  `;
}

export function bindShellActions({ onLogout, onProfile }) {
  document.getElementById('btn-logout')?.addEventListener('click', onLogout);
  document.getElementById('btn-my-profile')?.addEventListener('click', onProfile);
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
