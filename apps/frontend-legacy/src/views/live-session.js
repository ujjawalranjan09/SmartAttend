import { displayApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

let currentSession = null;

export async function renderLiveSession(container, state, sessionId) {
  // Fetch session details
  let session = null;
  try {
    const res = await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/v1/sessions/${sessionId}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    });
    session = await res.json();
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>Could not load session.</p></div>';
    return;
  }
  currentSession = session;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Live Session</h1>
        <p class="page-subtitle">${session.course_name || 'Session'}</p>
      </div>
      <div class="page-actions" id="live-session-actions">
        <button class="btn btn-secondary" id="projector-btn"><i data-lucide="monitor"></i> Projector Mode</button>
        <button class="btn btn-primary" id="end-session-btn"><i data-lucide="square"></i> End Session</button>
      </div>
    </div>
    <div id="live-session-content">
      <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-icon green"><i data-lucide="users"></i></div><div><div class="kpi-value" id="live-present">—</div><div class="kpi-label">Present</div></div></div>
        <div class="kpi-card"><div class="kpi-icon teal"><i data-lucide="users"></i></div><div><div class="kpi-value" id="live-enrolled">—</div><div class="kpi-label">Enrolled</div></div></div>
        <div class="kpi-card"><div class="kpi-icon yellow"><i data-lucide="percent"></i></div><div><div class="kpi-value" id="live-pct">—%</div><div class="kpi-label">Attendance %</div></div></div>
      </div>
      <div id="attendance-feed" class="card" style="margin-top:var(--space-4)">
        <div class="card-header"><div class="card-title">Attendance Feed</div></div>
        <div id="feed-list"><p style="padding:var(--space-4);color:var(--color-text-muted);font-size:var(--text-sm)">Waiting for attendance events...</p></div>
      </div>
    </div>`;

  document.getElementById('projector-btn')?.addEventListener('click', () => openProjectorMode(session));
  document.getElementById('end-session-btn')?.addEventListener('click', () => endSession(session.id));

  // Load live data
  refreshLiveData(session.id);
  connectSessionWS(session.id);

  if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function refreshLiveData(sessionId) {
  try {
    const res = await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/v1/sessions/${sessionId}/attendance`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    });
    if (res.ok) {
      const data = await res.json();
      updateLiveStats(data);
      renderFeed(data.records || []);
    }
  } catch {}
}

function updateLiveStats(data) {
  const total = data.total || data.enrolled_count || 0;
  const present = (data.records || []).filter(r => r.status === 'present').length;
  const pct = total > 0 ? Math.round(present / total * 100) : 0;
  const el = id => document.getElementById(id);
  if (el('live-present')) el('live-present').textContent = present;
  if (el('live-enrolled')) el('live-enrolled').textContent = total;
  if (el('live-pct')) el('live-pct').textContent = pct + '%';
}

function renderFeed(records) {
  const list = document.getElementById('feed-list');
  if (!records.length) return;
  list.innerHTML = records.slice(-20).reverse().map(r => `
    <div style="display:flex;align-items:center;gap:var(--space-3);padding:var(--space-3) 0;border-bottom:1px solid var(--color-divider)">
      <div style="width:8px;height:8px;border-radius:50%;background:${r.status === 'present' ? 'var(--color-success)' : 'var(--color-error)'}"></div>
      <div style="flex:1">
        <div style="font-weight:500;font-size:var(--text-sm)">${r.student_name || 'Student'}</div>
        <div style="font-size:var(--text-xs);color:var(--color-text-muted)">${r.roll_number || ''} · ${r.method || 'qr'}</div>
      </div>
      <div style="font-size:var(--text-xs);color:var(--color-text-muted)">${r.marked_at ? new Date(r.marked_at).toLocaleTimeString('en-IN') : ''}</div>
    </div>`).join('');
}

function connectSessionWS(sessionId) {
  const wsBase = (window.API_BASE || 'http://localhost:8000').replace(/^http/, 'ws');
  const ws = new WebSocket(`${wsBase}/ws/session/${sessionId}`);
  ws.onmessage = (event) => {
    if (event.data === 'pong') return;
    try {
      const msg = JSON.parse(event.data);
      if (msg.event !== 'attendance_marked') return;
      const present = msg.present_count || 0;
      const total = msg.total_enrolled || 0;
      const pct = total > 0 ? Math.round(present / total * 100) : 0;
      if (document.getElementById('live-present')) document.getElementById('live-present').textContent = present;
      if (document.getElementById('live-enrolled')) document.getElementById('live-enrolled').textContent = total;
      if (document.getElementById('live-pct')) document.getElementById('live-pct').textContent = pct + '%';
      // Add to feed
      const list = document.getElementById('feed-list');
      if (list) {
        const entry = document.createElement('div');
        entry.style = 'display:flex;align-items:center;gap:var(--space-3);padding:var(--space-3) 0;border-bottom:1px solid var(--color-divider);animation:slideInRight 0.3s ease';
        entry.innerHTML = `<div style="width:8px;height:8px;border-radius:50%;background:var(--color-success)"></div><div style="flex:1"><div style="font-weight:500;font-size:var(--text-sm)">${msg.student_name || '—'}</div><div style="font-size:var(--text-xs);color:var(--color-text-muted)">${msg.roll_number || ''}</div></div><div style="font-size:var(--text-xs);color:var(--color-text-muted)">${msg.marked_at ? new Date(msg.marked_at).toLocaleTimeString('en-IN') : ''}</div>`;
        list.insertBefore(entry, list.firstChild);
        if (list.children.length > 20) list.removeChild(list.lastChild);
      }
    } catch {}
  };
}

async function openProjectorMode(session) {
  let token = null;
  try {
    const res = await displayApi.getToken(session.id);
    token = res.display_token;
  } catch (e) {
    showToast('Failed to get display token: ' + (e.message || ''), 'error');
    return;
  }
  const url = `${window.location.origin}${window.location.pathname.replace('index.html','')}classroom-display.html?session_id=${session.id}&token=${token}`;
  window.open(url, '_blank');
}

async function endSession(id) {
  if (!confirm('End this session?')) return;
  try {
    await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/v1/sessions/${id}/end`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}`, 'Content-Type': 'application/json' }
    });
    showToast('Session ended', 'success');
    location.hash = 'sessions';
    location.reload();
  } catch (e) { showToast('Failed to end: ' + (e.message || ''), 'error'); }
}
