/**
 * Ushirika — Tanzania SME / Lender portal entry.
 * Hash-based routing, session gate, inactivity auto-logout.
 */

import { hydrateSession, getSession, clearSession, requireRole } from './session.js';
import { createInactivityMonitor } from './inactivity.js';
import { showToast } from './ui.js';
import { renderAuthPage, bindAuthPage } from './pages/auth.js';
import { loadSmeOverview, loadSmeTransactions, loadSmeUpload } from './pages/sme.js';
import { loadLenderPortfolio } from './pages/lender.js';
import { loadAdminPage } from './pages/admin.js';
import { API_BASE } from './api.js';

hydrateSession();

const inactivity = createInactivityMonitor({
  isActive: () => getSession().isAuthenticated,
  onLogout: (reason) => {
    handleLogout(reason === 'inactivity' ? 'Signed out after 30 seconds of inactivity.' : undefined);
  },
});

function handleLogout(message) {
  clearSession();
  inactivity.stop();
  if (message) showToast(message, 'info');
  else showToast('You have been signed out.', 'info');
  window.location.hash = '#/login';
  route();
}

function parseRoute() {
  const raw = (window.location.hash || '#/').replace(/^#/, '') || '/';
  const path = raw.split('?')[0];
  const parts = path.split('/').filter(Boolean);
  return { path: '/' + parts.join('/'), parts };
}

function redirectForRole(role) {
  if (role === 'admin' || role === 'subadmin') window.location.hash = '#/admin';
  else if (role === 'lender') window.location.hash = '#/lender';
  else window.location.hash = '#/sme';
}

async function route() {
  const session = getSession();
  const { parts } = parseRoute();
  const app = document.getElementById('app');
  if (!app) return;

  const section = parts[0] || '';

  if (section === 'login' || section === 'register' || section === '') {
    if (session.isAuthenticated && (section === 'login' || section === 'register' || section === '')) {
      redirectForRole(session.role);
      return;
    }
    if (section === '' && !session.isAuthenticated) {
      window.location.hash = '#/login';
      return;
    }
    const mode = section === 'register' ? 'register' : 'login';
    inactivity.stop();
    app.innerHTML = renderAuthPage(mode);
    bindAuthPage(mode, {
      onSuccess: () => {
        const s = getSession();
        inactivity.start();
        redirectForRole(s.role);
      },
    });
    return;
  }

  if (!session.isAuthenticated) {
    showToast('Please sign in to continue.', 'info');
    window.location.hash = '#/login';
    return;
  }

  inactivity.start();

  if (section === 'sme') {
    if (!requireRole('sme')) {
      showToast('You are not authorized to view the SME workspace.', 'error');
      redirectForRole(session.role);
      return;
    }
    const sub = parts[1] || 'overview';
    if (sub === 'transactions') {
      await loadSmeTransactions(session, { onLogout: () => handleLogout() });
    } else if (sub === 'upload') {
      loadSmeUpload(session, { onLogout: () => handleLogout() });
    } else {
      await loadSmeOverview(session, { onLogout: () => handleLogout() });
    }
    return;
  }

  if (section === 'lender') {
    if (!requireRole('lender')) {
      showToast('You are not authorized to view the Lender workspace.', 'error');
      redirectForRole(session.role);
      return;
    }
    const selectedId = parts[1] === 'sme' && parts[2] ? decodeURIComponent(parts[2]) : null;
    await loadLenderPortfolio(session, {
      onLogout: () => handleLogout(),
      selectedId,
    });
    return;
  }

  if (section === 'admin') {
    if (!requireRole(['admin', 'subadmin'])) {
      showToast('Admin access required.', 'error');
      redirectForRole(session.role);
      return;
    }
    const sub = parts[1] || 'accounts';
    const editId = sub === 'edit' && parts[2] ? decodeURIComponent(parts[2]) : null;
    await loadAdminPage(session, {
      onLogout: () => handleLogout(),
      sub,
      editId,
    });
    return;
  }

  redirectForRole(session.role);
}

window.addEventListener('hashchange', () => {
  route();
});

console.info(`[Ushirika] API base: ${API_BASE}`);
if (getSession().isAuthenticated) inactivity.start();
route();
