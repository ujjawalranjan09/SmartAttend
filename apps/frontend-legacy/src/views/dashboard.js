import { analyticsApi, sessionsApi, alertsApi, dailyPlanApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export async function renderDashboard(container, state) {
  const role = state.role || 'student';
  container.innerHTML = getDashboardSkeleton(role);

  try {
    if (role === 'student') await renderStudentDashboard(container, state);
    else if (role === 'faculty') await renderFacultyDashboard(container, state);
    else await renderAdminDashboard(container, state);
  } catch (err) {
    container.innerHTML = getErrorState('Failed to load dashboard. Make sure the backend is running.');
  }
}

async function renderStudentDashboard(container, state) {
  const userId = state.user?.id;
  let analytics = null;
  try { analytics = await analyticsApi.student(userId); } catch {}

  const pct = analytics?.overall_percentage || 74;
  const ringColor = pct >= 75 ? 'var(--color-success)' : pct >= 60 ? 'var(--color-warning)' : 'var(--color-error)';
  const circumference = 2 * Math.PI * 38;
  const offset = circumference - (pct / 100) * circumference;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">My Dashboard</h1>
        <p class="page-subtitle">Welcome back, ${state.user?.full_name?.split(' ')[0] || 'Student'}</p>
      </div>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon ${pct >= 75 ? 'green' : 'red'}">
          <i data-lucide="percent"></i>
        </div>
        <div>
          <div class="kpi-value" id="kpi-pct">${pct}%</div>
          <div class="kpi-label">Overall Attendance</div>
        </div>
        <div class="kpi-delta ${pct >= 75 ? 'up' : 'down'}">
          <i data-lucide="${pct >= 75 ? 'trending-up' : 'trending-down'}"></i>
          ${pct >= 75 ? 'On track' : 'Below 75% threshold'}
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon teal"><i data-lucide="calendar-check"></i></div>
        <div>
          <div class="kpi-value">${analytics?.attended_classes || 0}</div>
          <div class="kpi-label">Classes Attended</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon yellow"><i data-lucide="calendar-x"></i></div>
        <div>
          <div class="kpi-value">${analytics?.missed_classes || 0}</div>
          <div class="kpi-label">Classes Missed</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon ${(analytics?.can_miss_more || 0) > 0 ? 'teal' : 'red'}">
          <i data-lucide="shield"></i>
        </div>
        <div>
          <div class="kpi-value">${analytics?.can_miss_more ?? '-'}</div>
          <div class="kpi-label">Classes Can Still Miss</div>
        </div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <div><div class="card-title">Attendance Trend</div><div class="card-subtitle">Last 8 weeks</div></div>
        </div>
        <div class="chart-container">
          <canvas id="trend-chart" height="220"></canvas>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <div><div class="card-title">Course Breakdown</div></div>
        </div>
        <div id="course-list">
          ${(analytics?.by_course || []).map(c => `
            <div style="margin-bottom:var(--space-4)">
              <div style="display:flex;justify-content:space-between;margin-bottom:var(--space-2)">
                <span style="font-size:var(--text-xs);font-weight:500">${c.course_name}</span>
                <span style="font-size:var(--text-xs);font-weight:700;font-variant-numeric:tabular-nums">${c.percentage}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill ${c.percentage >= 75 ? 'high' : c.percentage >= 60 ? 'mid' : 'low'}" style="width:${c.percentage}%"></div>
              </div>
            </div>`).join('') || '<p class="text-muted" style="font-size:var(--text-xs)">No course data available</p>'}
        </div>
      </div>
    </div>

    <div class="card" id="routine-card" style="margin-top:var(--space-4)">
      <div class="card-header">
        <div><div class="card-title">Today's Routine</div><div class="card-subtitle" id="routine-gen-source"></div></div>
        <button class="btn btn-sm btn-ghost" onclick="location.hash='daily-plan'"><i data-lucide="external-link"></i> View all</button>
      </div>
      <div id="routine-preview">
        <div class="skeleton" style="height:80px"></div>
      </div>
    </div>`;

  // Render trend chart
  const trendData = analytics?.weekly_trend || Array.from({length:8}, (_,i) => ({ week: `W${i+1}`, pct: 70 + Math.random() * 20 }));
  renderLineChart('trend-chart', trendData.map(w => w.week || w.label), trendData.map(w => w.pct || w.percentage));

  // Load today's routine preview
  loadRoutinePreview();
}

async function loadRoutinePreview() {
  let routine = null;
  try { routine = await dailyPlanApi.getRoutine(new Date().toISOString().split('T')[0]); } catch {}
  const preview = document.getElementById('routine-preview');
  const source = document.getElementById('routine-gen-source');
  if (!preview) return;
  if (!routine || !routine.routine?.length) {
    preview.innerHTML = '<p class="text-muted" style="font-size:var(--text-sm);padding:var(--space-3) 0">No routine for today. <a href="#daily-plan" style="color:var(--color-primary)">Set up your day</a></p>';
    return;
  }
  if (source) {
    const gen = routine.generated_by;
    source.textContent = gen === 'llm' ? 'AI-generated plan' : gen === 'fallback' ? 'Basic plan' : 'Cached';
  }
  // Show next 3 items
  const items = routine.routine.slice(0, 4);
  preview.innerHTML = `<div class="routine-mini-list">${items.map(item => routineMiniItem(item)).join('')}</div>`;
}

function routineMiniItem(item) {
  const labels = { class: 'Class', study: 'Study', break: 'Break', free: 'Free' };
  const colors = { class: 'var(--color-primary)', study: 'var(--color-success)', break: 'var(--color-warning)', free: 'var(--color-text-muted)' };
  const bg = { class: 'var(--color-primary-highlight)', study: 'var(--color-success-highlight)', break: 'var(--color-warning-highlight)', free: 'var(--color-surface-offset)' };
  const title = item.course_name || item.title || labels[item.type] || item.type;
  return `<div style="display:flex;align-items:center;gap:var(--space-3);padding:var(--space-2) 0;border-bottom:1px solid var(--color-divider)">
    <div style="width:3px;height:36px;border-radius:2px;background:${colors[item.type] || 'var(--color-text-muted)'}"></div>
    <div style="flex:1">
      <div style="font-size:var(--text-sm);font-weight:500">${title}</div>
      <div style="font-size:var(--text-xs);color:var(--color-text-muted)">${item.start} – ${item.end}</div>
    </div>
    <span style="font-size:var(--text-xs);color:${colors[item.type] || 'var(--color-text-muted)'};font-weight:600;text-transform:uppercase;letter-spacing:0.05em">${labels[item.type] || item.type}</span>
  </div>`;

async function renderFacultyDashboard(container, state) {
  let sessions = [];
  let alerts = [];
  try {
    [sessions, alerts] = await Promise.all([
      sessionsApi.list({ limit: 5 }),
      alertsApi.list({ limit: 5, is_resolved: false }).catch(() => ({ items: [] })),
    ]);
  } catch {}

  const alertItems = alerts?.items || alerts || [];
  const unresolvedCount = alertItems.length;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Faculty Dashboard</h1>
        <p class="page-subtitle">${new Date().toLocaleDateString('en-IN', {weekday:'long', day:'numeric', month:'long'})}</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" id="start-session-btn"><i data-lucide="plus"></i> New Session</button>
      </div>
    </div>
    <div class="kpi-grid">
      <div class="kpi-card"><div class="kpi-icon teal"><i data-lucide="calendar"></i></div><div><div class="kpi-value">${sessions?.length || 0}</div><div class="kpi-label">Sessions This Week</div></div></div>
      <div class="kpi-card"><div class="kpi-icon green"><i data-lucide="users"></i></div><div><div class="kpi-value">--</div><div class="kpi-label">Avg Attendance Rate</div></div></div>
      <div class="kpi-card"><div class="kpi-icon ${unresolvedCount > 0 ? 'red' : 'yellow'}"><i data-lucide="bell-ring"></i></div><div><div class="kpi-value">${unresolvedCount}</div><div class="kpi-label">Unresolved Alerts</div></div></div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><div class="card-title">Recent Sessions</div><button class="btn btn-sm btn-ghost" onclick="location.hash='sessions'">View all</button></div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead><tr><th>Course</th><th>Date</th><th>Present</th><th>Status</th></tr></thead>
            <tbody>
              ${sessions.length ? sessions.map(s => `
                <tr>
                  <td><span style="font-weight:500">${s.course_name || s.course_id}</span></td>
                  <td>${new Date(s.start_time).toLocaleDateString('en-IN')}</td>
                  <td><span style="font-variant-numeric:tabular-nums">${s.present_count ?? '--'}/${s.total_enrolled ?? '--'}</span></td>
                  <td><span class="badge ${s.status === 'active' ? 'badge-present' : 'badge-muted'}">${s.status}</span></td>
                </tr>`).join('') : '<tr><td colspan="4" style="text-align:center;color:var(--color-text-muted);padding:2rem">No sessions yet</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <div><div class="card-title">Recent Alerts</div><div class="card-subtitle">Unresolved proxy and attendance anomalies</div></div>
          <button class="btn btn-sm btn-ghost" onclick="location.hash='alerts'">View all</button>
        </div>
        <div id="dashboard-alerts">
          ${alertItems.length ? alertItems.slice(0, 5).map(a => `
            <div class="alert-item" style="display:flex;align-items:center;gap:var(--space-3);padding:var(--space-3) 0;border-bottom:1px solid var(--color-border)">
              <span class="badge badge-proxy" style="font-size:var(--text-xs);white-space:nowrap">${a.alert_type || 'alert'}</span>
              <div style="flex:1;font-size:var(--text-sm)">
                <div style="font-weight:500">${a.student_name || 'Student'}</div>
                <div style="color:var(--color-text-muted);font-size:var(--text-xs)">${a.message?.slice(0, 60) || ''}</div>
              </div>
              <span style="font-size:var(--text-xs);color:var(--color-text-muted)">${new Date(a.created_at).toLocaleDateString('en-IN')}</span>
            </div>
          `).join('') : '<p style="padding:1rem;text-align:center;color:var(--color-text-muted);font-size:var(--text-sm)">No unresolved alerts</p>'}
        </div>
      </div>
    </div>`;
}

async function renderAdminDashboard(container, state) {
  let summary = null;
  try { summary = await analyticsApi.summary(); } catch {}

  const stats = summary || { total_students: 0, total_faculty: 0, avg_attendance: 0, at_risk_count: 0, active_sessions: 0 };
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">Admin Dashboard</h1><p class="page-subtitle">Institution Overview</p></div>
    </div>
    <div class="kpi-grid">
      <div class="kpi-card"><div class="kpi-icon teal"><i data-lucide="users"></i></div><div><div class="kpi-value">${stats.total_students}</div><div class="kpi-label">Total Students</div></div></div>
      <div class="kpi-card"><div class="kpi-icon green"><i data-lucide="graduation-cap"></i></div><div><div class="kpi-value">${stats.total_faculty}</div><div class="kpi-label">Faculty Members</div></div></div>
      <div class="kpi-card"><div class="kpi-icon ${stats.avg_attendance >= 75 ? 'green' : 'yellow'}"><i data-lucide="percent"></i></div><div><div class="kpi-value">${stats.avg_attendance}%</div><div class="kpi-label">Avg Attendance</div></div></div>
      <div class="kpi-card"><div class="kpi-icon red"><i data-lucide="alert-triangle"></i></div><div><div class="kpi-value">${stats.at_risk_count}</div><div class="kpi-label">At-Risk Students</div></div></div>
      <div class="kpi-card"><div class="kpi-icon teal"><i data-lucide="activity"></i></div><div><div class="kpi-value">${stats.active_sessions}</div><div class="kpi-label">Active Sessions Now</div></div></div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><div class="card-title">Attendance Trend</div></div>
        <div class="chart-container"><canvas id="admin-trend-chart" height="220"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Department Breakdown</div></div>
        <div class="chart-container"><canvas id="dept-chart" height="220"></canvas></div>
      </div>
    </div>`;

  const weeks = ['W1','W2','W3','W4','W5','W6','W7','W8'];
  const data = [72,74,71,76,78,75,79,77];
  renderLineChart('admin-trend-chart', weeks, data);

  const depts = summary?.by_department || [{name:'CS',pct:76},{name:'IT',pct:72},{name:'ECE',pct:68},{name:'ME',pct:74}];
  renderBarChart('dept-chart', depts.map(d => d.name || d.department), depts.map(d => d.pct || d.percentage));
}

function getDashboardSkeleton(role) {
  return `<div style="display:flex;flex-direction:column;gap:1.5rem">
    <div style="display:flex;flex-direction:column;gap:0.5rem">
      <div class="skeleton skeleton-heading"></div><div class="skeleton skeleton-text w60"></div>
    </div>
    <div class="kpi-grid">${Array(4).fill('<div class="kpi-card"><div class="skeleton" style="height:80px"></div></div>').join('')}</div>
    <div class="grid-2">${Array(2).fill('<div class="card"><div class="skeleton" style="height:200px"></div></div>').join('')}</div>
  </div>`;
}

function getErrorState(msg) {
  return `<div class="empty-state"><i data-lucide="wifi-off" style="width:48px;height:48px"></i><h3>Could not load data</h3><p>${msg}</p></div>`;
}

function renderLineChart(canvasId, labels, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;
  new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{ label: 'Attendance %', data, borderColor: '#4f98a3', backgroundColor: 'rgba(79,152,163,0.1)', fill: true, tension: 0.4, pointRadius: 4, pointBackgroundColor: '#4f98a3' }]
    },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100, ticks: { color: '#797876' }, grid: { color: 'rgba(255,255,255,0.05)' } }, x: { ticks: { color: '#797876' }, grid: { display: false } } } }
  });
}

function renderBarChart(canvasId, labels, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;
  new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ data, backgroundColor: data.map(v => v >= 75 ? '#6daa45' : v >= 60 ? '#e8af34' : '#dd6974'), borderRadius: 6 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100, ticks: { color: '#797876' }, grid: { color: 'rgba(255,255,255,0.05)' } }, x: { ticks: { color: '#797876' }, grid: { display: false } } } }
  });
}
