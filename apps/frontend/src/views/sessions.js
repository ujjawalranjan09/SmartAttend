import { sessionsApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';
import { renderQR, startDynamicQR } from '../utils/qr.js';

export async function renderSessions(container, state) {
  const role = state.role;
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">${role === 'student' ? 'My Schedule' : 'Sessions'}</h1><p class="page-subtitle">${role === 'student' ? 'Your upcoming and past classes' : 'Manage and monitor class sessions'}</p></div>
      ${role !== 'student' ? '<div class="page-actions"><button class="btn btn-primary" id="new-session-btn"><i data-lucide="plus"></i> Create Session</button></div>' : ''}
    </div>
    <div class="filters-bar">
      <select id="filter-course"><option value="">All Courses</option></select>
      <select id="filter-status"><option value="">All Status</option><option>scheduled</option><option>active</option><option>completed</option></select>
      <input type="date" id="filter-date" />
    </div>
    <div id="sessions-list"><div class="skeleton" style="height:300px;border-radius:12px"></div></div>`;

  try {
    const sessions = await sessionsApi.list();
    renderSessionsList(document.getElementById('sessions-list'), sessions, role);
  } catch {
    document.getElementById('sessions-list').innerHTML = `<div class="empty-state"><i data-lucide="calendar"></i><h3>No sessions found</h3><p>Sessions will appear here once created.</p></div>`;
  }

  document.getElementById('new-session-btn')?.addEventListener('click', () => showNewSessionModal());
}

function renderSessionsList(container, sessions, role) {
  if (!sessions?.length) {
    container.innerHTML = `<div class="empty-state"><i data-lucide="calendar"></i><h3>No sessions yet</h3><p>${role === 'student' ? 'Your faculty will create sessions' : 'Create your first session to get started'}</p>${role !== 'student' ? '<button class="btn btn-primary" onclick="document.getElementById(\'new-session-btn\').click()">Create Session</button>' : ''}</div>`;
    return;
  }
  container.innerHTML = `<div class="grid-auto">${sessions.map(s => sessionCard(s, role)).join('')}</div>`;
  // Attach QR button handlers
  sessions.forEach(s => {
    document.getElementById(`qr-btn-${s.id}`)?.addEventListener('click', () => openQRModal(s));
    document.getElementById(`end-btn-${s.id}`)?.addEventListener('click', () => endSession(s.id));
  });
}

function sessionCard(s, role) {
  const statusColors = { active: 'badge-present', scheduled: 'badge-primary', completed: 'badge-muted', cancelled: 'badge-error' };
  return `
    <div class="session-card">
      <div class="session-card-header">
        <div>
          <div class="session-name">${s.course_name || s.course_id}</div>
          <div class="session-meta">${new Date(s.start_time).toLocaleString('en-IN', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</div>
        </div>
        <span class="badge ${statusColors[s.status] || 'badge-muted'}">${s.status}</span>
      </div>
      <div class="session-stats">
        <div class="session-stat"><div class="session-stat-val">${s.present_count ?? '--'}</div><div class="session-stat-label">Present</div></div>
        <div class="session-stat"><div class="session-stat-val">${s.total_enrolled ?? '--'}</div><div class="session-stat-label">Enrolled</div></div>
        <div class="session-stat"><div class="session-stat-val">${s.total_enrolled && s.present_count ? Math.round(s.present_count/s.total_enrolled*100) + '%' : '--'}</div><div class="session-stat-label">Rate</div></div>
      </div>
      <div class="session-actions">
        ${s.status === 'active' ? `<button id="qr-btn-${s.id}" class="btn btn-primary btn-sm"><i data-lucide="qr-code"></i> Show QR</button>` : ''}
        ${role !== 'student' && s.status === 'active' ? `<button id="end-btn-${s.id}" class="btn btn-secondary btn-sm"><i data-lucide="square"></i> End</button>` : ''}
        ${s.status === 'scheduled' && role !== 'student' ? `<button class="btn btn-primary btn-sm" onclick="startSession('${s.id}')"><i data-lucide="play"></i> Start</button>` : ''}
      </div>
    </div>`;
}

async function openQRModal(session) {
  const overlay = document.getElementById('qr-modal-overlay');
  const canvas = document.getElementById('qr-canvas');
  overlay.classList.remove('hidden');
  document.getElementById('qr-session-name').textContent = session.course_name || session.course_id;

  // Render initial QR
  const payload = JSON.stringify({ session_id: session.id, ts: Date.now() });
  if (typeof QRCode !== 'undefined') await renderQR(canvas, payload);

  const cleanup = startDynamicQR(canvas, session.id, async (id) => {
    try { return await sessionsApi.qr(id); } catch { return { token: `${id}-${Date.now()}`, expires_at: new Date(Date.now()+30000).toISOString() }; }
  });

  const closeQR = () => { cleanup(); overlay.classList.add('hidden'); };
  document.getElementById('close-qr').onclick = closeQR;
  document.getElementById('close-qr-btn').onclick = closeQR;
  overlay.onclick = (e) => { if (e.target === overlay) closeQR(); };

  document.getElementById('share-qr-btn')?.addEventListener('click', async () => {
    if (navigator.share) {
      await navigator.share({ title: 'SmartAttend QR', text: `Join session: ${session.course_name}` });
    } else { showToast('Copy the QR or screenshot to share', 'info'); }
  });
}

async function endSession(id) {
  try { await sessionsApi.end(id); showToast('Session ended', 'success'); location.reload(); }
  catch (e) { showToast('Failed to end session: ' + (e.message || ''), 'error'); }
}

function showNewSessionModal() {
  showToast('Session creation form coming soon', 'info');
}
