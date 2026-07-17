/**
 * Auto-logout after exactly 30s of no mouse/keyboard/touch/scroll activity.
 * Warning overlay with countdown starts at 20s idle (10s remaining).
 */

const IDLE_LIMIT_MS = 30_000;
const WARNING_AT_MS = 20_000;

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

  function showWarning() {
    if (!isActive() || warningVisible) return;
    warningVisible = true;
    if (overlay) overlay.hidden = false;
    updateCountdown();
    countdownInterval = window.setInterval(updateCountdown, 200);
    stayBtn?.focus();
  }

  function updateCountdown() {
    const remaining = Math.max(0, IDLE_LIMIT_MS - (Date.now() - lastActivity));
    const seconds = Math.ceil(remaining / 1000);
    if (countdownEl) countdownEl.textContent = String(seconds);
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
