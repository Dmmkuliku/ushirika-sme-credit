/**
 * Session & central app state.
 * Token and user live in sessionStorage; UI state is in-memory.
 */

const TOKEN_KEY = 'ushirika_token';
const USER_KEY = 'ushirika_user';

const state = {
  token: null,
  user: null,
  listeners: new Set(),
};

function safeParse(json) {
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function hydrateSession() {
  try {
    state.token = sessionStorage.getItem(TOKEN_KEY);
    state.user = safeParse(sessionStorage.getItem(USER_KEY));
  } catch {
    state.token = null;
    state.user = null;
  }
  return getSession();
}

export function getSession() {
  return {
    token: state.token,
    user: state.user,
    isAuthenticated: Boolean(state.token && state.user),
    role: state.user?.role ? String(state.user.role).toLowerCase() : null,
  };
}

export function setSession(payload) {
  const token = payload.access_token || payload.token;
  if (!token || !payload.user) {
    throw new Error('Invalid session payload: access_token and user are required');
  }
  const user = normalizeUser(payload.user);
  state.token = token;
  state.user = user;
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* private mode / quota */
  }
  notify();
  return getSession();
}

export function updateUser(partial) {
  if (!state.user) return getSession();
  state.user = normalizeUser({ ...state.user, ...partial });
  try {
    sessionStorage.setItem(USER_KEY, JSON.stringify(state.user));
  } catch {
    /* ignore */
  }
  notify();
  return getSession();
}

export function clearSession() {
  state.token = null;
  state.user = null;
  try {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  } catch {
    /* ignore */
  }
  notify();
  return getSession();
}

function normalizeUser(user) {
  const role = String(user.role || '').toLowerCase();
  return {
    ...user,
    role: ['sme', 'lender', 'admin', 'subadmin'].includes(role) ? role : 'sme',
  };
}

export function subscribe(listener) {
  state.listeners.add(listener);
  return () => state.listeners.delete(listener);
}

function notify() {
  const snapshot = getSession();
  state.listeners.forEach((fn) => {
    try {
      fn(snapshot);
    } catch {
      /* isolate listener errors */
    }
  });
}

export function requireRole(expected) {
  const { isAuthenticated, role } = getSession();
  if (Array.isArray(expected)) return isAuthenticated && expected.includes(role);
  return isAuthenticated && role === expected;
}
