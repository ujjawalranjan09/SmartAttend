import { reportsApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export async function renderReports(container, state) {
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">Reports</h1><p class="page-subtitle">Generate and download attendance reports</p></div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><div class="card-title">Generate Report</div></div>
        <form id="report-form" style="display:flex;flex-direction:column;gap:var(--space-4)">
          <div class="form-group">
            <label>Report Type</label>
            <select id="report-type">
              <option value="attendance_summary">Attendance Summary</option>
              <option value="at_risk">At-Risk Students</option>
              <option value="course_report">Course Report</option>
              <option value="monthly">Monthly Report</option>
            </select>
          </div>
          <div class="form-group">
            <label>Format</label>
            <select id="report-format">
              <option value="csv">CSV (Excel compatible)</option>
              <option value="json">JSON</option>
            </select>
          </div>
          <div class="form-group">
            <label>From Date</label>
            <input type="date" id="report-from" />
          </div>
          <div class="form-group">
            <label>To Date</label>
            <input type="date" id="report-to" />
          </div>
          <button type="submit" class="btn btn-primary"><i data-lucide="file-down"></i> Generate Report</button>
        </form>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Quick Export</div></div>
        <div style="display:flex;flex-direction:column;gap:var(--space-3)">
          <button class="btn btn-secondary" id="export-all-csv"><i data-lucide="download"></i> Export All Attendance (CSV)</button>
          <button class="btn btn-secondary" id="export-atrisk-csv"><i data-lucide="alert-triangle"></i> Export At-Risk Students</button>
          <button class="btn btn-secondary" id="export-monthly"><i data-lucide="calendar"></i> Export Monthly Summary</button>
        </div>
        <div style="margin-top:var(--space-6)">
          <div class="card-title" style="margin-bottom:var(--space-3)">Recent Reports</div>
          <div id="recent-reports">
            <div class="empty-state" style="padding:var(--space-8)">
              <i data-lucide="file-text"></i>
              <h3>No reports yet</h3>
              <p>Generated reports will appear here</p>
            </div>
          </div>
        </div>
      </div>
    </div>`;

  document.getElementById('report-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    try {
      const payload = {
        report_type: document.getElementById('report-type').value,
        format: document.getElementById('report-format').value,
        date_from: document.getElementById('report-from').value || undefined,
        date_to: document.getElementById('report-to').value || undefined,
      };
      const result = await reportsApi.generate(payload);
      showToast('Report generation started! You will be notified when ready.', 'success');
      addRecentReport(result);
    } catch (e) {
      showToast('Failed to generate report: ' + (e.message || ''), 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i data-lucide="file-down"></i> Generate Report';
      if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [btn] });
    }
  });

  document.getElementById('export-all-csv')?.addEventListener('click', () => {
    const url = reportsApi.exportCsv();
    window.open(url, '_blank');
    showToast('Downloading CSV...', 'info');
  });
}

function addRecentReport(result) {
  const container = document.getElementById('recent-reports');
  const item = document.createElement('div');
  item.className = 'card';
  item.style.marginBottom = 'var(--space-3)';
  item.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:var(--text-sm);font-weight:500">${result.report_type || 'Report'}</div>
        <div style="font-size:var(--text-xs);color:var(--color-text-muted)">${new Date().toLocaleString('en-IN')}</div>
      </div>
      <span class="badge badge-warning">Processing</span>
    </div>`;
  container.innerHTML = '';
  container.appendChild(item);
}
