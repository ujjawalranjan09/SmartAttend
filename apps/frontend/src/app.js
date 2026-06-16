// SmartAttend — Main app entry point & router
import { setToken, getToken, authApi } from './utils/api.js';
import { store } from './utils/store.js';
import { showToast } from './utils/toast.js';
import { renderDashboard } from './views/dashboard.js';
import { renderSessions } from './views/sessions.js';
import { renderAttendance } from './views/attendance.js';
import { renderStudents } from './views/students.js';
import { renderAnalytics } from './views/analytics.js';
import { renderReports } from './views/reports.js';
import { renderSettings } from './views/settings.js';
import { renderQrScanner } from './views/qr-scanner.js';

// ---- Role-based nav config ----
const NAV = {
  admin: [
    { section: 'Overview' },
    { id: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
    { id: 'analytics', label: 'Analytics', icon: 'bar-chart-2' },
    { section: 'Management' },
    { id: 'students', label: 'Students', icon: 'users' },
    { id: 'sessions', label: 'Sessions', icon: 'calendar' },
    { id: 'attendance', label: 'Attendance', icon: 'check-square' },
    { section: 'Reports' },
    { id: 'reports', label: 'Reports', icon: 'file-text' },
    { section: 'System' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ],
  faculty: [
    { section: 'Overview' },
    { id: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
    { section: 'Teaching' },
    { id: 'sessions', label: 'My Sessions', icon: 'calendar' },
    { id: 'attendance', label: 'Attendance', icon: 'check-square' },
    { id: 'students', label: 'My Students', icon: 'users' },
    { section: 'Insights' },
    { id: 'analytics', label: 'Analytics', icon: 'bar-chart-2' },
    { id: 'reports', label: 'Reports', icon: 'file-text' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ],
  student: [
    { section: 'My Space' },
    { id: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
    { id: 'qr-scanner', label: 'Scan QR', icon: 'scan' },
    { id: 'attendance', label: 'My Attendance', icon: 'check-square' },
    { id: 'sessions', label: 'Schedule', icon: 'calendar' },
    { id: 'analytics', label: 'My Progress', icon: 'trending-up' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ],
};

const VIEWS = { dashboard: renderDashboard, sessions: renderSessions, attendance: renderAttendance, students: renderStudents, analytics: renderAnalytics, reports: renderReports, settings: renderSettings, 'qr-scanner': renderQrScanner };

// ---- Boot ----
document.addEventListener('DOMContentLoaded', () => {
  // Register service worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
    navigator.serviceWorker.addEventListener('message', (e) => {
      if (e.data?.type === 'SYNC_ATTENDANCE') syncOfflineQueue();
    });
  }

  // Offline/online detection
  window.addEventListener('offline', () => { store.set('isOffline', true); document.getElementById('offline-badge')?.classList.remove('hidden'); });
  window.addEventListener('online',  () => { store.set('isOffline', false); document.getElementById('offline-badge')?.classList.add('hidden'); syncOfflineQueue(); });

  setupAuthScreen();
  setupThemeToggle();
});

function setupThemeToggle() {
  const toggles = document.querySelectorAll('[data-theme-toggle]');
  const html = document.documentElement;
  const update = (theme) => {
    html.setAttribute('data-theme', theme);
    toggles.forEach(t => {
      t.innerHTML = theme === 'dark'
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    });
  };
  let theme = 'dark';
  update(theme);
  toggles.forEach(t => t.addEventListener('click', () => { theme = theme === 'dark' ? 'light' : 'dark'; update(theme); }));
}

// ---- Auth Screen ----
function setupAuthScreen() {
  const form = document.getElementById('login-form');
  const errEl = document.getElementById('auth-error');
  const toggleBtn = document.getElementById('toggle-password');
  const pwInput = document.getElementById('password');

  toggleBtn?.addEventListener('click', () => {
    const show = pwInput.type === 'password';
    pwInput.type = show ? 'text' : 'password';
    toggleBtn.innerHTML = show
      ? '<i data-lucide="eye-off"></i>'
      : '<i data-lucide="eye"></i>';
    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [toggleBtn] });
  });

  document.querySelectorAll('.demo-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('email').value = btn.dataset.email;
      document.getElementById('password').value = btn.dataset.pass;
    });
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    btn.disabled = true;
    btn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Signing in...';
    errEl.classList.add('hidden');
    try {
      const res = await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Login failed');
      const data = await res.json();
      setToken(data.access_token);
      const me = await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` }
      }).then(r => r.json());
      store.set('user', me);
      store.set('role', me.role?.toLowerCase() || 'student');
      bootApp();
    } catch (err) {
      errEl.textContent = err.message || 'Invalid credentials';
      errEl.classList.remove('hidden');
      btn.disabled = false;
      btn.innerHTML = '<span>Sign in</span>';
    }
  });

  if (typeof lucide !== 'undefined') lucide.createIcons();
}

// ---- App Boot (post-login) ----
function bootApp() {
  document.getElementById('auth-screen').classList.add('hidden');
  const shell = document.getElementById('app-shell');
  shell.classList.remove('hidden');

  const user = store.get('user');
  const role = store.get('role');

  // Set user info in sidebar
  const initials = ((user?.full_name || user?.email || 'U').split(' ').map(n => n[0]).join('').toUpperCase()).slice(0, 2);
  document.getElementById('nav-avatar').textContent = initials;
  document.getElementById('nav-username').textContent = user?.full_name || user?.email;
  document.getElementById('nav-role').textContent = role;
  document.getElementById('nav-role').className = `user-mini-role badge badge-${role}`;

  buildNav(role);
  setupSidebar();
  setupNotifications();
  setupLogout();

  const hash = location.hash.replace('#', '') || 'dashboard';
  navigate(hash);

  if (typeof lucide !== 'undefined') lucide.createIcons();
}

// ---- Nav Builder ----
function buildNav(role) {
  const nav = document.getElementById('sidebar-nav');
  const items = NAV[role] || NAV.student;
  nav.innerHTML = items.map(item => {
    if (item.section) return `<div class="nav-section-label">${item.section}</div>`;
    return `
      <button class="nav-item" data-view="${item.id}" aria-label="${item.label}">
        <i data-lucide="${item.icon}"></i>
        <span class="nav-label">${item.label}</span>
        ${item.badge ? `<span class="nav-badge" id="badge-${item.id}">${item.badge}</span>` : ''}
      </button>`;
  }).join('');

  nav.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      navigate(btn.dataset.view);
      // Close mobile sidebar
      document.getElementById('sidebar')?.classList.remove('mobile-open');
      document.getElementById('mobile-overlay')?.classList.remove('visible');
    });
  });
}

// ---- Navigation ----
function navigate(viewId) {
  if (!VIEWS[viewId]) viewId = 'dashboard';
  store.set('currentView', viewId);
  location.hash = viewId;

  // Update active nav item
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === viewId));

  // Update breadcrumb
  const label = document.querySelector(`.nav-item[data-view="${viewId}"] .nav-label`)?.textContent || viewId;
  document.getElementById('breadcrumb').textContent = label;

  // Render view
  const content = document.getElementById('main-content');
  content.innerHTML = '';
  VIEWS[viewId](content, store.getAll());

  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);
}

// ---- Sidebar ----
function setupSidebar() {
  let collapsed = false;
  // Mobile overlay
  const overlay = document.createElement('div');
  overlay.id = 'mobile-overlay';
  overlay.className = 'mobile-overlay';
  document.getElementById('app-shell').appendChild(overlay);

  document.getElementById('mobile-menu-btn')?.addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('mobile-open');
    overlay.classList.toggle('visible');
  });
  overlay.addEventListener('click', () => {
    document.getElementById('sidebar').classList.remove('mobile-open');
    overlay.classList.remove('visible');
  });

  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    collapsed = !collapsed;
    document.getElementById('app-shell').classList.toggle('sidebar-collapsed', collapsed);
  });
}

// ---- Notifications ----
function setupNotifications() {
  const btn = document.getElementById('notif-btn');
  const panel = document.getElementById('notif-panel');
  const list = document.getElementById('notif-list');

  const mockNotifs = [
    { id: 1, text: 'Ramesh Kumar has attendance below 75%', time: '2 min ago', unread: true },
    { id: 2, text: 'Session CS301 marked complete', time: '1 hr ago', unread: true },
    { id: 3, text: 'Weekly attendance report is ready', time: 'Yesterday', unread: false },
  ];

  const unreadCount = mockNotifs.filter(n => n.unread).length;
  if (unreadCount > 0) document.getElementById('notif-dot')?.classList.remove('hidden');

  list.innerHTML = mockNotifs.map(n => `
    <div class="notif-item ${n.unread ? 'unread' : ''}">
      <div class="notif-dot-icon"></div>
      <div class="notif-body">
        <p>${n.text}</p>
        <span class="notif-time">${n.time}</span>
      </div>
    </div>`).join('');

  btn?.addEventListener('click', (e) => {
    e.stopPropagation();
    panel.classList.toggle('hidden');
  });
  document.getElementById('close-notif')?.addEventListener('click', () => panel.classList.add('hidden'));
  document.addEventListener('click', (e) => {
    if (!panel.contains(e.target) && e.target !== btn) panel.classList.add('hidden');
  });
}

// ---- Logout ----
function setupLogout() {
  document.getElementById('logout-btn')?.addEventListener('click', () => {
    setToken(null);
    store.set('user', null);
    document.getElementById('app-shell').classList.add('hidden');
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('login-form').reset();
    showToast('Signed out successfully', 'info');
  });
}

// ---- Offline queue sync ----
async function syncOfflineQueue() {
  const { offlineQueue } = await import('./utils/store.js');
  const queue = await offlineQueue.getAll();
  if (!queue.length) return;
  showToast(`Syncing ${queue.length} offline attendance records...`, 'info');
  // POST each queued record to backend
  const { attendanceApi } = await import('./utils/api.js');
  let synced = 0;
  for (const record of queue) {
    try { await attendanceApi.mark(record); synced++; } catch {}
  }
  if (synced > 0) {
    await offlineQueue.clear();
    showToast(`${synced} attendance records synced!`, 'success');
  }
}
