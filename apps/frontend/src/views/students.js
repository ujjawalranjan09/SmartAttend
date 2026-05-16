import { studentsApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export async function renderStudents(container, state) {
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">Students</h1><p class="page-subtitle">Manage student enrollment and attendance</p></div>
      <div class="page-actions">
        <button class="btn btn-secondary" id="export-btn"><i data-lucide="download"></i> Export</button>
        <button class="btn btn-primary" id="add-student-btn"><i data-lucide="user-plus"></i> Add Student</button>
      </div>
    </div>
    <div class="filters-bar">
      <input type="text" id="search-students" placeholder="Search by name or roll no..." style="min-width:220px" />
      <select id="filter-dept"><option value="">All Departments</option></select>
      <select id="filter-risk"><option value="">All Students</option><option value="at_risk">At Risk (&lt;75%)</option><option value="safe">Safe (≥75%)</option></select>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-title">Student List</div>
        <span class="badge badge-muted" id="student-count">Loading...</span>
      </div>
      <div id="students-table"><div class="skeleton" style="height:300px"></div></div>
    </div>`;

  let allStudents = [];
  try {
    const data = await studentsApi.list({ limit: 100 });
    allStudents = data?.items || data || [];
    renderTable(allStudents);
    document.getElementById('student-count').textContent = `${allStudents.length} students`;
  } catch {
    document.getElementById('students-table').innerHTML = `<div class="empty-state"><i data-lucide="users"></i><h3>No students found</h3><p>Add students to get started</p></div>`;
  }

  document.getElementById('search-students')?.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = allStudents.filter(s =>
      (s.full_name || '').toLowerCase().includes(q) ||
      (s.roll_number || '').toLowerCase().includes(q) ||
      (s.email || '').toLowerCase().includes(q)
    );
    renderTable(filtered);
  });

  document.getElementById('filter-risk')?.addEventListener('change', (e) => {
    const val = e.target.value;
    const filtered = val === 'at_risk' ? allStudents.filter(s => (s.attendance_pct || 0) < 75)
      : val === 'safe' ? allStudents.filter(s => (s.attendance_pct || 0) >= 75)
      : allStudents;
    renderTable(filtered);
  });
}

function renderTable(students) {
  const tbody = document.getElementById('students-table');
  if (!students.length) {
    tbody.innerHTML = `<div class="empty-state"><i data-lucide="search"></i><h3>No students match</h3><p>Try a different filter or search</p></div>`;
    return;
  }
  tbody.innerHTML = `
    <div class="table-wrapper">
      <table class="data-table">
        <thead><tr><th>Name</th><th>Roll No.</th><th>Email</th><th>Attendance</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          ${students.map(s => {
            const pct = s.attendance_pct || 0;
            return `<tr>
              <td>
                <div style="display:flex;align-items:center;gap:0.5rem">
                  <div class="avatar" style="width:28px;height:28px;font-size:0.65rem">${(s.full_name||'U').split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase()}</div>
                  <span style="font-weight:500">${s.full_name || '--'}</span>
                </div>
              </td>
              <td><code style="font-family:var(--font-mono);font-size:var(--text-xs)">${s.roll_number || '--'}</code></td>
              <td style="color:var(--color-text-muted);font-size:var(--text-xs)">${s.email}</td>
              <td>
                <div class="progress-bar-wrap">
                  <div class="progress-bar" style="width:80px">
                    <div class="progress-fill ${pct >= 75 ? 'high' : pct >= 60 ? 'mid' : 'low'}" style="width:${pct}%"></div>
                  </div>
                  <span class="progress-val">${pct}%</span>
                </div>
              </td>
              <td><span class="badge ${pct >= 75 ? 'badge-success' : pct >= 60 ? 'badge-warning' : 'badge-error'}">${pct >= 75 ? 'Safe' : pct >= 60 ? 'At Risk' : 'Shortage'}</span></td>
              <td>
                <div style="display:flex;gap:0.5rem">
                  <button class="btn btn-sm btn-ghost" title="View details"><i data-lucide="eye"></i></button>
                  <button class="btn btn-sm btn-ghost" title="Edit"><i data-lucide="edit-2"></i></button>
                </div>
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}
