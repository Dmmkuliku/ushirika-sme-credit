/**
 * Auto-logout after 15 minutes of no mouse/keyboard/touch/scroll activity.
 * Warning overlay with countdown starts 60s before logout.
 */

import { t } from './i18n.js';

const IDLE_LIMIT_MS = 15 * 60_000;
const WARNING_AT_MS = 14 * 60_000;

const ACTIVITY_EVENTS = [
  'mousemove',
  'mousedown',
  'keydown',
  'touchstart',
  'touchmove',
  'scroll',
  'wheel',
  'pointerdown',
];

/**
 * @param {{ onLogout: () => void, isActive: () => boolean }} options
 */
export function createInactivityMonitor({ onLogout, isActive }) {
  let idleTimer = null;
  let warningTimer = null;
  let countdownInterval = null;
  let lastActivity = Date.now();
  let warningVisible = false;
  let started = false;

  const overlay = document.getElementById('inactivity-overlay');
  const countdownEl = document.getElementById('inactivity-countdown');
  const stayBtn = document.getElementById('inactivity-stay');
  const titleEl = document.getElementById('inactivity-title');
  const descEl = document.getElementById('inactivity-desc');

  function clearTimers() {
    if (idleTimer) window.clearTimeout(idleTimer);
    if (warningTimer) window.clearTimeout(warningTimer);
    if (countdownInterval) window.clearInterval(countdownInterval);
    idleTimer = warningTimer = countdownInterval = null;
  }

  function hideWarning() {
    warningVisible = false;
    if (overlay) overlay.hidden = true;
    if (countdownInterval) {
      window.clearInterval(countdownInterval);
      countdownInterval = null;
    }
  }

  function localizeOverlay() {
    if (titleEl) titleEl.textContent = t('inactivity.title');
    if (stayBtn) stayBtn.textContent = t('inactivity.stay');
    if (descEl) {
      const seconds = countdownEl?.textContent || '15';
      descEl.innerHTML = `${t('inactivity.descBefore')} <strong id="inactivity-countdown">${seconds}</strong> ${t('inactivity.descAfter')}`;
    }
  }

  function showWarning() {
    if (!isActive() || warningVisible) return;
    warningVisible = true;
    localizeOverlay();
    if (overlay) overlay.hidden = false;
    updateCountdown();
    countdownInterval = window.setInterval(updateCountdown, 200);
    stayBtn?.focus();
  }

  function updateCountdown() {
    const remaining = Math.max(0, IDLE_LIMIT_MS - (Date.now() - lastActivity));
    const seconds = Math.ceil(remaining / 1000);
    const el = document.getElementById('inactivity-countdown');
    if (el) el.textContent = String(seconds);
    if (remaining <= 0) {
      forceLogout();
    }
  }

  function forceLogout() {
    clearTimers();
    hideWarning();
    onLogout('inactivity');
  }

  function schedule() {
    clearTimers();
    if (!isActive()) return;

    const elapsed = Date.now() - lastActivity;
    const untilWarning = Math.max(0, WARNING_AT_MS - elapsed);
    const untilLogout = Math.max(0, IDLE_LIMIT_MS - elapsed);

    if (elapsed >= WARNING_AT_MS) {
      showWarning();
    } else {
      hideWarning();
      warningTimer = window.setTimeout(showWarning, untilWarning);
    }

    idleTimer = window.setTimeout(() => {
      if (Date.now() - lastActivity >= IDLE_LIMIT_MS) forceLogout();
    }, untilLogout);
  }

  function onActivity() {
    if (!isActive()) return;
    lastActivity = Date.now();
    if (warningVisible) hideWarning();
    schedule();
  }

  function onStay() {
    onActivity();
  }

  function start() {
    if (started) {
      lastActivity = Date.now();
      schedule();
      return;
    }
    started = true;
    lastActivity = Date.now();
    ACTIVITY_EVENTS.forEach((evt) => {
      const opts = evt === 'scroll' ? { capture: true, passive: true } : { passive: true };
      window.addEventListener(evt, onActivity, opts);
    });
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && isActive()) schedule();
    });
    stayBtn?.addEventListener('click', onStay);
    schedule();
  }

  function stop() {
    clearTimers();
    hideWarning();
    if (!started) return;
    ACTIVITY_EVENTS.forEach((evt) => {
      window.removeEventListener(evt, onActivity, evt === 'scroll' ? { capture: true } : undefined);
    });
    started = false;
  }

  function reset() {
    lastActivity = Date.now();
    hideWarning();
    if (started && isActive()) schedule();
  }

  return { start, stop, reset };
}
