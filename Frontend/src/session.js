/**
 * Session & central app state.
 * Token and user persist in localStorage so refresh / new tabs keep you signed in.
 */

const TOKEN_KEY = 'ushirika_token';
const USER_KEY = 'ushirika_user';

const state = {
  token: null,
  user: null,
  listeners: new Set(),
};

function storage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function safeParse(json) {
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function readStored() {
  const store = storage();
  if (!store) return { token: null, user: null };
  // Migrate older sessionStorage sessions once.
  try {
    const legacyToken = sessionStorage.getItem(TOKEN_KEY);
    const legacyUser = sessionStorage.getItem(USER_KEY);
    if (legacyToken && !store.getItem(TOKEN_KEY)) {
      store.setItem(TOKEN_KEY, legacyToken);
      if (legacyUser) store.setItem(USER_KEY, legacyUser);
    }
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  } catch {
    /* ignore */
  }
  return {
    token: store.getItem(TOKEN_KEY),
    user: safeParse(store.getItem(USER_KEY)),
  };
}

export function hydrateSession() {
  try {
    const stored = readStored();
    state.token = stored.token;
    state.user = stored.user;
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
    const store = storage();
    store?.setItem(TOKEN_KEY, token);
    store?.setItem(USER_KEY, JSON.stringify(user));
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
    storage()?.setItem(USER_KEY, JSON.stringify(state.user));
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
    const store = storage();
    store?.removeItem(TOKEN_KEY);
    store?.removeItem(USER_KEY);
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
