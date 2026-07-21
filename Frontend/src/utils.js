/**
 * Formatting, escaping, and small helpers.
 */

import { getLang, t } from './i18n.js';

function locale() {
  return getLang() === 'sw' ? 'sw-TZ' : 'en-TZ';
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function setText(el, value) {
  if (el) el.textContent = value == null ? '' : String(value);
}

/** Create element with optional class, attrs, and text (never innerHTML for user data). */
export function el(tag, { className, attrs = {}, text, children } = {}) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  Object.entries(attrs).forEach(([key, val]) => {
    if (val === false || val == null) return;
    if (val === true) node.setAttribute(key, '');
    else node.setAttribute(key, String(val));
  });
  if (text != null) node.textContent = String(text);
  if (children) children.forEach((child) => child && node.appendChild(child));
  return node;
}

export function formatTZS(amount) {
  if (amount == null || Number.isNaN(Number(amount))) return '—';
  try {
    return new Intl.NumberFormat('en-TZ', {
      style: 'currency',
      currency: 'TZS',
      maximumFractionDigits: 0,
    }).format(Number(amount));
  } catch {
    return `TZS ${Number(amount).toLocaleString('en-TZ')}`;
  }
}

export function formatNumber(value, digits = 0) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString('en-TZ', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatScore(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return formatNumber(value, 1);
}

export function formatDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString(locale(), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatBirthDate(value) {
  if (!value) return '—';
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[3]}-${match[2]}-${match[1]}` : String(value);
}

export function formatMonthLabel(value) {
  if (!value) return '—';
  // Accept "2024-01" or ISO date
  const d = /^\d{4}-\d{2}$/.test(value) ? new Date(`${value}-01T00:00:00`) : new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString(locale(), { month: 'short', year: 'numeric' });
}

export function riskClass(risk) {
  const r = String(risk || '').toLowerCase();
  if (r.includes('low')) return 'risk-low';
  if (r.includes('medium') || r.includes('moderate')) return 'risk-medium';
  if (r.includes('high')) return 'risk-high';
  return 'risk-unknown';
}

export function capitalize(value) {
  const s = String(value || '');
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

export function debounce(fn, ms = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

export function normalizeListPayload(payload, keys = ['items', 'data', 'results', 'transactions', 'smes']) {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === 'object') {
    for (const key of keys) {
      if (Array.isArray(payload[key])) return payload[key];
    }
  }
  return [];
}

export function getErrorMessage(err, fallback = t('common.unknownError')) {
  if (!err) return fallback;
  if (typeof err === 'string') return err;
  return err.message || fallback;
}
