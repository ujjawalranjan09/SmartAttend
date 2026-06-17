import { sessionsApi, displayApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';
import { renderQR, startDynamicQR } from '../utils/qr.js';
import { renderError, renderLoading, renderEmpty } from '../utils/ui.js';

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
    <div id="sessions-list"></div>`;

  const listEl = document.getElementById('sessions-list');
  renderLoading(listEl, 3);

  try {
    const sessions = await sessionsApi.list();
    if (!sessions?.length) {
      renderEmpty(listEl, 'calendar', 'No sessions yet', role === 'student' ? 'Your faculty will create sessions' : 'Create your first session to get started');
    } else {
      renderSessionsList(listEl, sessions, role);
    }
  } catch {
    renderError(listEl, 'Failed to load sessions. Please try again.', () => renderSessions(container, state));
  }

  document.getElementById('new-session-btn')?.addEventListener('click', () => showNewSessionModal());
}

function renderSessionsList(container, sessions, role) {
  if (!sessions?.length) {
    renderEmpty(container, 'calendar', 'No sessions yet', role === 'student' ? 'Your faculty will create sessions' : 'Create your first session to get started');
    return;
  }
  container.innerHTML = `<div class="grid-auto">${sessions.map(s => sessionCard(s, role)).join('')}</div>`;
  // Attach QR button handlers
  sessions.forEach(s => {
    document.getElementById(`qr-btn-${s.id}`)?.addEventListener('click', () => openQRModal(s));
    document.getElementById(`end-btn-${s.id}`)?.addEventListener('click', () => endSession(s.id));
    document.getElementById(`display-btn-${s.id}`)?.addEventListener('click', () => openDisplayModal(s));
  });
}

function sessionCard(s, role) {
  const statusColors = { active: 'badge-present', scheduled: 'badge-primary', completed: 'badge-muted', cancelled: 'badge-error', ended: 'badge-muted' };
  const startTime = s.start_time || s.started_at || s.created_at;
  const dateStr = startTime ? new Date(startTime).toLocaleString('en-IN', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : 'No time';

  return `
    <div class="session-card">
      <div class="session-card-header">
        <div>
          <div class="session-name">${s.course_name || s.course_id || 'Session'}</div>
          <div class="session-meta">${dateStr}</div>
        </div>
        <span class="badge ${statusColors[s.status] || 'badge-muted'}">${s.status || 'unknown'}</span>
      </div>
      <div class="session-stats">
        <div class="session-stat"><div class="session-stat-val">${s.present_count ?? s.attendance_count ?? '--'}</div><div class="session-stat-label">Present</div></div>
        <div class="session-stat"><div class="session-stat-val">${s.total_enrolled ?? s.enrolled_count ?? '--'}</div><div class="session-stat-label">Enrolled</div></div>
        <div class="session-stat"><div class="session-stat-val">${(s.total_enrolled || s.enrolled_count) && (s.present_count || s.attendance_count) ? Math.round((s.present_count || s.attendance_count)/(s.total_enrolled || s.enrolled_count)*100) + '%' : '--'}</div><div class="session-stat-label">Rate</div></div>
      </div>
      <div class="session-actions">
        ${s.status === 'active' ? `<button id="qr-btn-${s.id}" class="btn btn-primary btn-sm"><i data-lucide="qr-code"></i> Show QR</button>` : ''}
        ${role !== 'student' && s.status === 'active' ? `<button id="display-btn-${s.id}" class="btn btn-secondary btn-sm"><i data-lucide="monitor"></i> Display</button>` : ''}
        ${role !== 'student' && s.status === 'active' ? `<button id="end-btn-${s.id}" class="btn btn-secondary btn-sm"><i data-lucide="square"></i> End</button>` : ''}
        ${(s.status === 'scheduled' || !s.status) && role !== 'student' ? `<button class="btn btn-primary btn-sm" onclick="startSession('${s.id}')"><i data-lucide="play"></i> Start</button>` : ''}
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

async function openDisplayModal(session) {
  let token = null;
  try {
    const res = await displayApi.getToken(session.id);
    token = res.display_token;
  } catch (e) {
    showToast('Failed to get display token: ' + (e.message || ''), 'error');
    return;
  }

  // Pass current API origin so display page can reach backend in production.
  const apiOrigin = window.API_BASE
    ? window.API_BASE.replace(/\/api\/v\d+\/?$/, '')
    : window.location.origin;
  const displayUrl = `${window.location.origin}/classroom-display.html?session_id=${session.id}&token=${token}&api=${encodeURIComponent(apiOrigin)}`;
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal" style="max-width:520px">
      <div class="modal-header">
        <h3>Classroom Display</h3>
        <button class="icon-btn" id="close-display">&times;</button>
      </div>
      <div class="modal-body">
        <p style="font-size:var(--text-sm);color:var(--color-text-muted);margin-bottom:var(--space-4)">Project this link on the classroom screen. Students will see attendance update in real-time.</p>
        <div class="form-group">
          <label>Display URL</label>
          <div style="display:flex;gap:var(--space-2)">
            <input type="text" id="display-url" readonly value="${displayUrl}" style="flex:1;background:var(--color-surface-offset)">
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="copy-display-url"><i data-lucide="copy"></i> Copy Link</button>
        <button class="btn btn-primary" id="open-display-url"><i data-lucide="external-link"></i> Open in New Tab</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  overlay.querySelector('#close-display').onclick = () => overlay.remove();
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  overlay.querySelector('#copy-display-url').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(displayUrl);
      showToast('Link copied!', 'success');
    } catch { showToast('Copy failed — copy the URL manually', 'error'); }
  });

  overlay.querySelector('#open-display-url').addEventListener('click', () => {
    window.open(displayUrl, '_blank');
  });

  if (typeof lucide !== 'undefined') lucide.createIcons();
}

// Make startSession globally available (called from inline onclick in session cards)
window.startSession = async function(sessionId) {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    // If it's already a scheduled session, we may want a different endpoint in future.
    // For now we treat "Start" as ensuring it's active (or re-use start for demo).
    showToast('Starting session...', 'info');

    // Call the start endpoint again (or a dedicated start) - backend will handle if needed
    const res = await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/v1/sessions/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({
        course_id: 'c0a14390-dbbe-4a7c-8c1b-fff241955cb4',
        faculty_id: user.id,
        is_online: false
      })
    });

    if (res.ok) {
      showToast('Session is now active', 'success');
      location.reload();
    } else {
      showToast('Could not start session', 'error');
    }
  } catch (e) {
    showToast('Start failed: ' + (e.message || ''), 'error');
  }
};

function showNewSessionModal() {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>Create New Session</h3>
        <button class="icon-btn" id="close-create">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Course</label>
          <select id="create-course" class="input">
            <option value="c0a14390-dbbe-4a7c-8c1b-fff241955cb4">Data Structures & Algorithms (IT401)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Mode</label>
          <select id="create-mode" class="input">
            <option value="false">In-person</option>
            <option value="true">Online</option>
          </select>
        </div>
        <p class="text-muted" style="font-size:0.85rem">This will immediately start an active session.</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="cancel-create">Cancel</button>
        <button class="btn btn-primary" id="confirm-create">Start Session</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  const close = () => modal.remove();
  modal.querySelector('#close-create').onclick = close;
  modal.querySelector('#cancel-create').onclick = close;

  modal.querySelector('#confirm-create').onclick = async () => {
    const btn = modal.querySelector('#confirm-create');
    btn.disabled = true;
    btn.textContent = 'Starting...';

    try {
      // Use the current logged in user as faculty
      const user = window.__currentUser || JSON.parse(localStorage.getItem('user') || '{}');
      const facultyId = user.id;

      if (!facultyId) {
        throw new Error('No logged in faculty user found. Please re-login.');
      }

      const courseId = modal.querySelector('#create-course').value;
      const isOnline = modal.querySelector('#create-mode').value === 'true';

      const res = await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/v1/sessions/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify({
          course_id: courseId,
          faculty_id: facultyId,
          is_online: isOnline,
          qr_rotation_interval_sec: 30
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to create session');
      }

      showToast('Session started successfully!', 'success');
      close();
      // Refresh the sessions list
      location.reload();
    } catch (e) {
      showToast('Failed to start session: ' + (e.message || ''), 'error');
      btn.disabled = false;
      btn.textContent = 'Start Session';
    }
  };
}
