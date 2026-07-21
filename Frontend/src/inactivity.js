/**
 * Auto-logout after 90 seconds without mouse/keyboard/touch/scroll activity.
 * Uses a wall-clock deadline so browser throttling or device sleep cannot
 * preserve an expired session.
 */

import { t } from './i18n.js';

const IDLE_LIMIT_MS = 90_000;
const WARNING_AT_MS = 75_000;

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
  let deadlineAt = lastActivity + IDLE_LIMIT_MS;
  let warningVisible = false;
  let started = false;
  let loggingOut = false;

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
  }

  function updateCountdown() {
    const remaining = Math.max(0, deadlineAt - Date.now());
    const seconds = Math.ceil(remaining / 1000);
    const el = document.getElementById('inactivity-countdown');
    if (el) el.textContent = String(seconds);
    if (remaining <= 0) {
      forceLogout();
    }
  }

  function forceLogout() {
    if (loggingOut) return;
    loggingOut = true;
    clearTimers();
    hideWarning();
    onLogout('inactivity');
  }

  function enforceDeadline(now = Date.now()) {
    if (!isActive() || now < deadlineAt) return false;
    forceLogout();
    return true;
  }

  function schedule() {
    clearTimers();
    if (!isActive()) return;

    const now = Date.now();
    if (enforceDeadline(now)) return;
    const elapsed = now - lastActivity;
    const untilWarning = Math.max(0, WARNING_AT_MS - elapsed);
    const untilLogout = Math.max(0, deadlineAt - now);

    if (elapsed >= WARNING_AT_MS) {
      showWarning();
    } else {
      hideWarning();
      warningTimer = window.setTimeout(showWarning, untilWarning);
    }

    idleTimer = window.setTimeout(() => {
      enforceDeadline();
    }, untilLogout);
  }

  function onActivity() {
    if (!isActive()) return;
    const now = Date.now();
    // Expire first: wake-up mouse/scroll events must not revive an expired session.
    if (enforceDeadline(now)) return;
    lastActivity = now;
    deadlineAt = now + IDLE_LIMIT_MS;
    if (warningVisible) hideWarning();
    schedule();
  }

  function onStay() {
    onActivity();
  }

  function onWake() {
    if (!started || !isActive()) return;
    if (!enforceDeadline()) schedule();
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') onWake();
  }

  function start() {
    if (started) {
      schedule();
      return;
    }
    started = true;
    loggingOut = false;
    lastActivity = Date.now();
    deadlineAt = lastActivity + IDLE_LIMIT_MS;
    ACTIVITY_EVENTS.forEach((evt) => {
      const opts = evt === 'scroll' ? { capture: true, passive: true } : { passive: true };
      window.addEventListener(evt, onActivity, opts);
    });
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('focus', onWake);
    window.addEventListener('pageshow', onWake);
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
    document.removeEventListener('visibilitychange', onVisibilityChange);
    window.removeEventListener('focus', onWake);
    window.removeEventListener('pageshow', onWake);
    stayBtn?.removeEventListener('click', onStay);
    started = false;
    loggingOut = false;
  }

  function reset() {
    lastActivity = Date.now();
    deadlineAt = lastActivity + IDLE_LIMIT_MS;
    loggingOut = false;
    hideWarning();
    if (started && isActive()) schedule();
  }

  return { start, stop, reset };
}
