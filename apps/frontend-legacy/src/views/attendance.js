import { attendanceApi, studentsApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';
import { checkGeoFence } from '../utils/qr.js';
import { store, offlineQueue } from '../utils/store.js';

export async function renderAttendance(container, state) {
  const role = state.role;
  if (role === 'student') {
    renderStudentAttendance(container, state);
  } else {
    renderFacultyAttendance(container, state);
  }
}

async function renderStudentAttendance(container, state) {
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">My Attendance</h1><p class="page-subtitle">Track your attendance across all courses</p></div>
      <div class="page-actions">
        <button class="btn btn-primary" id="mark-btn"><i data-lucide="scan-line"></i> Mark Attendance</button>
      </div>
    </div>
    <div class="tabs">
      <button class="tab-btn active" data-tab="overview">Overview</button>
      <button class="tab-btn" data-tab="history">History</button>
    </div>
    <div class="tab-panel active" id="tab-overview">
      <div id="overview-content"><div class="skeleton" style="height:200px;border-radius:12px"></div></div>
    </div>
    <div class="tab-panel" id="tab-history">
      <div id="history-content"><div class="skeleton" style="height:300px;border-radius:12px"></div></div>
    </div>`;

  setupTabs();

  try {
    const userId = state.user?.id;
    const records = await attendanceApi.history({ student_id: userId, limit: 50 });
    renderOverview(records);
    renderHistory(records);
  } catch {
    document.getElementById('overview-content').innerHTML = `<p class="text-muted">Could not load attendance data</p>`;
  }

  document.getElementById('mark-btn')?.addEventListener('click', () => showMarkModal());
}

function renderOverview(records) {
  const courses = {};
  (records?.items || records || []).forEach(r => {
    if (!courses[r.course_name || r.course_id]) courses[r.course_name || r.course_id] = { present: 0, total: 0 };
    courses[r.course_name || r.course_id].total++;
    if (r.status === 'present') courses[r.course_name || r.course_id].present++;
  });

  document.getElementById('overview-content').innerHTML = `
    <div class="grid-auto">
      ${Object.entries(courses).map(([name, c]) => {
        const pct = c.total ? Math.round(c.present / c.total * 100) : 0;
        const color = pct >= 75 ? 'var(--color-success)' : pct >= 60 ? 'var(--color-warning)' : 'var(--color-error)';
        const circumference = 2 * Math.PI * 38;
        const offset = circumference - (pct / 100) * circumference;
        return `
          <div class="card" style="align-items:center;text-align:center">
            <svg width="90" height="90" viewBox="0 0 90 90">
              <circle class="ring-bg" cx="45" cy="45" r="38" />
              <circle class="ring-fill" cx="45" cy="45" r="38"
                stroke="${color}"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${offset}"
                transform="rotate(-90 45 45)"
              />
              <text x="45" y="49" text-anchor="middle" font-size="16" font-weight="700" fill="currentColor">${pct}%</text>
            </svg>
            <div style="font-size:var(--text-sm);font-weight:600;margin-top:var(--space-2)">${name}</div>
            <div style="font-size:var(--text-xs);color:var(--color-text-muted)">${c.present}/${c.total} classes</div>
            <span class="badge ${pct >= 75 ? 'badge-success' : pct >= 60 ? 'badge-warning' : 'badge-error'}">${pct >= 75 ? 'Safe' : pct >= 60 ? 'At Risk' : 'Shortage'}</span>
          </div>`;
      }).join('') || '<div class="empty-state"><h3>No attendance records yet</h3></div>'}
    </div>`;
}

function renderHistory(records) {
  const rows = records?.items || records || [];
  document.getElementById('history-content').innerHTML = `
    <div class="table-wrapper">
      <table class="data-table">
        <thead><tr><th>Date</th><th>Course</th><th>Status</th><th>Marked By</th></tr></thead>
        <tbody>
          ${rows.length ? rows.map(r => `
            <tr>
              <td>${new Date(r.marked_at || r.created_at).toLocaleDateString('en-IN')}</td>
              <td>${r.course_name || r.course_id}</td>
              <td><span class="badge badge-${r.status === 'present' ? 'present' : r.status === 'late' ? 'late' : 'absent'}">${r.status}</span></td>
              <td><span class="badge badge-muted">${r.method || 'qr'}</span></td>
            </tr>`).join('') : '<tr><td colspan="4" style="text-align:center;padding:2rem;color:var(--color-text-muted)">No records found</td></tr>'}
        </tbody>
      </table>
    </div>`;
}

async function renderFacultyAttendance(container, state) {
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">Attendance Management</h1><p class="page-subtitle">View and manage student attendance with proxy risk indicators</p></div>
      <div class="page-actions">
        <button class="btn btn-secondary" id="export-csv-btn"><i data-lucide="download"></i> Export CSV</button>
      </div>
    </div>
    <div class="filters-bar">
      <select id="f-course"><option value="">All Courses</option></select>
      <input type="date" id="f-date" />
      <select id="f-status"><option value="">All Status</option><option>present</option><option>absent</option><option>late</option></select>
      <label class="checkbox-label" style="margin-left:auto;font-size:var(--text-sm)">
        <input type="checkbox" id="flagged-only" />
        <span>Show flagged only</span>
      </label>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-title">Attendance Records</div>
        <span id="proxy-count-badge" style="display:none" class="badge badge-proxy"></span>
      </div>
      <div id="attendance-table"><div class="skeleton" style="height:250px"></div></div>
    </div>`;

  try {
    const records = await attendanceApi.history({ limit: 100 });
    const rows = records?.items || records || [];

    // Count proxy suspected records
    const proxyCount = rows.filter(r => r.status === 'proxy_suspected' || (r.proxy_anomaly_score || 0) > 0.6).length;
    const proxyBadge = document.getElementById('proxy-count-badge');
    if (proxyCount > 0) {
      proxyBadge.style.display = 'inline-flex';
      proxyBadge.textContent = `${proxyCount} flagged`;
    }

    function renderRows(data) {
      return data.length ? data.map(r => {
        const riskScore = r.proxy_anomaly_score || r.proxy_risk_score || 0;
        const isFlagged = r.status === 'proxy_suspected' || riskScore > 0.6;
        const riskColor = riskScore > 0.6 ? 'var(--color-error)' : riskScore > 0.3 ? 'var(--color-warning)' : 'var(--color-success)';
        const riskLabel = riskScore > 0.6 ? 'High' : riskScore > 0.3 ? 'Medium' : 'Low';

        return `
          <tr class="${isFlagged ? 'proxy-flagged' : ''}" style="${isFlagged ? 'background:rgba(221,105,116,0.08);border-left:3px solid var(--color-error)' : ''}">
            <td><span style="font-weight:500">${r.student_name || r.student_id}</span></td>
            <td>${r.course_name || r.course_id}</td>
            <td>${new Date(r.marked_at || r.created_at).toLocaleDateString('en-IN')}</td>
            <td><span class="badge ${r.status === 'present' ? 'badge-present' : r.status === 'proxy_suspected' ? 'badge-proxy' : r.status === 'late' ? 'badge-late' : 'badge-absent'}">${r.status === 'proxy_suspected' ? 'Proxy Suspected' : r.status}</span></td>
            <td><span style="font-variant-numeric:tabular-nums">${r.face_confidence ? (r.face_confidence * 100).toFixed(1) + '%' : '--'}</span></td>
            <td>
              <span class="badge" style="background:${riskColor};color:#fff;font-weight:600">${(riskScore * 100).toFixed(0)}%</span>
              <span style="font-size:var(--text-xs);color:${riskColor};margin-left:4px">${riskLabel}</span>
            </td>
            <td>${r.verification_notes ? `<span style="font-size:var(--text-xs);color:var(--color-text-muted)">${r.verification_notes}</span>` : '--'}</td>
          </tr>`;
      }).join('') : '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--color-text-muted)">No records</td></tr>';
    }

    document.getElementById('attendance-table').innerHTML = `
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>Student</th><th>Course</th><th>Date</th><th>Status</th><th>Face Conf.</th><th>Risk Score</th><th>Notes</th></tr></thead>
          <tbody>${renderRows(rows)}</tbody>
        </table>
      </div>`;

    // Filter toggle
    document.getElementById('flagged-only')?.addEventListener('change', (e) => {
      const tbody = document.querySelector('#attendance-table tbody');
      if (e.target.checked) {
        const flagged = rows.filter(r => r.status === 'proxy_suspected' || (r.proxy_anomaly_score || 0) > 0.6);
        tbody.innerHTML = renderRows(flagged);
      } else {
        tbody.innerHTML = renderRows(rows);
      }
    });
  } catch {
    document.getElementById('attendance-table').innerHTML = `<p class="text-muted" style="padding:1rem">Failed to load records</p>`;
  }
}

function showMarkModal() {
  showToast('Scan the session QR code to mark attendance', 'info');
}

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab)?.classList.add('active');
    });
  });
}
