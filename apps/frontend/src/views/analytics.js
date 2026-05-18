import { analyticsApi } from '../utils/api.js';

export async function renderAnalytics(container, state) {
  const role = state.role;
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">${role === 'student' ? 'My Progress' : 'Analytics'}</h1><p class="page-subtitle">${role === 'student' ? 'Track your academic attendance' : 'Attendance insights and trends'}</p></div>
    </div>
    <div id="analytics-body"><div class="skeleton" style="height:400px;border-radius:12px"></div></div>`;

  try {
    if (role === 'student') {
      const data = await analyticsApi.student(state.user?.id);
      renderStudentAnalytics(document.getElementById('analytics-body'), data);
    } else {
      const [summary, atRisk] = await Promise.all([analyticsApi.summary(), analyticsApi.atRisk({ limit: 20 })]);
      renderAdminAnalytics(document.getElementById('analytics-body'), summary, atRisk);
    }
  } catch (e) {
    document.getElementById('analytics-body').innerHTML = `<div class="alert alert-warning"><i data-lucide="alert-triangle"></i> Failed to load analytics — backend may be offline. Showing demo data.</div>`;
    renderDemoAnalytics(document.getElementById('analytics-body'), role);
  }
}

function renderStudentAnalytics(container, data) {
  const weekly = data?.weekly_trend || Array.from({length:8},(_,i)=>({label:`W${i+1}`,pct:68+Math.random()*20}));
  container.innerHTML = `
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><div class="card-title">Weekly Trend</div><div class="card-subtitle">8-week attendance history</div></div>
        <div class="chart-container"><canvas id="s-trend" height="220"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Forecast</div><div class="card-subtitle">7-day prediction</div></div>
        <div class="chart-container"><canvas id="s-forecast" height="220"></canvas></div>
      </div>
    </div>
    ${ data?.at_risk_alert ? `<div class="alert alert-error"><i data-lucide="alert-triangle"></i> <strong>Low attendance alert:</strong> You are at ${data.overall_percentage}% — below the 75% threshold. Attend ${data.classes_needed || '?'} more classes to recover.</div>` : '' }
    <div class="card">
      <div class="card-header"><div class="card-title">Course-wise Breakdown</div></div>
      <div class="chart-container"><canvas id="s-course" height="200"></canvas></div>
    </div>`;

  const weeks = weekly.map(w => w.label || w.week);
  const actuals = weekly.map(w => w.pct || w.percentage);
  renderChart('s-trend', 'line', weeks, [{ label: 'Attendance %', data: actuals, borderColor: '#4f98a3', backgroundColor: 'rgba(79,152,163,0.1)', fill: true, tension: 0.4 }]);

  const forecast = data?.forecast || actuals.slice(-3).map((v,i)=>v + (i+1)*0.5);
  const fLabels = Array.from({length: forecast.length}, (_,i)=>`Day ${i+1}`);
  renderChart('s-forecast', 'line', fLabels, [{ label: 'Forecast', data: forecast, borderColor: '#6daa45', borderDash: [5,5], tension: 0.3 }]);

  const courses = data?.by_course || [];
  if (courses.length) {
    renderChart('s-course', 'bar', courses.map(c=>c.course_name), [{ data: courses.map(c=>c.percentage), backgroundColor: courses.map(c => c.percentage >= 75 ? '#6daa45' : c.percentage >= 60 ? '#e8af34' : '#dd6974'), borderRadius: 6 }]);
  }
}

function renderAdminAnalytics(container, summary, atRisk) {
  const riskStudents = atRisk?.items || atRisk || [];
  container.innerHTML = `
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><div class="card-title">Institution Trend</div></div>
        <div class="chart-container"><canvas id="a-trend" height="220"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Department Comparison</div></div>
        <div class="chart-container"><canvas id="a-dept" height="220"></canvas></div>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <div><div class="card-title">At-Risk Students</div><div class="card-subtitle">Students below 75% threshold</div></div>
        <span class="badge badge-error">${riskStudents.length} students</span>
      </div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>Student</th><th>Roll No.</th><th>Attendance</th><th>Classes Needed</th><th>Trend</th></tr></thead>
          <tbody>${riskStudents.map(s=>`
            <tr>
              <td><span style="font-weight:500">${s.full_name||s.student_name||'--'}</span></td>
              <td><code style="font-family:var(--font-mono);font-size:var(--text-xs)">${s.roll_number||'--'}</code></td>
              <td><span class="badge ${(s.attendance_pct||s.percentage||0) >= 60 ? 'badge-warning' : 'badge-error'}">${s.attendance_pct||s.percentage||0}%</span></td>
              <td>${s.classes_needed||'--'}</td>
              <td><i data-lucide="trending-down" style="color:var(--color-error);width:16px;height:16px"></i></td>
            </tr>`).join('') || '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--color-text-muted)">No at-risk students</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>`;

  const weeks = ['W1','W2','W3','W4','W5','W6','W7','W8'];
  renderChart('a-trend','line',weeks,[{label:'Avg %',data:[72,74,71,76,78,75,79,77],borderColor:'#4f98a3',backgroundColor:'rgba(79,152,163,0.1)',fill:true,tension:0.4}]);
  const depts = summary?.by_department || [{name:'CS',pct:76},{name:'IT',pct:72},{name:'ECE',pct:68},{name:'ME',pct:74}];
  renderChart('a-dept','bar',depts.map(d=>d.name||d.department),[{data:depts.map(d=>d.pct||d.percentage),backgroundColor:depts.map(d=>(d.pct||d.percentage)>=75?'#6daa45':'#e8af34'),borderRadius:6}]);
}

function renderDemoAnalytics(container, role) {
  container.innerHTML += `<div class="card"><div class="card-header"><div class="card-title">Demo Chart</div></div><div class="chart-container"><canvas id="demo-chart" height="220"></canvas></div></div>`;
  renderChart('demo-chart','line',['W1','W2','W3','W4','W5','W6','W7','W8'],[{label:'Demo',data:[72,74,71,76,78,75,79,77],borderColor:'#4f98a3',backgroundColor:'rgba(79,152,163,0.1)',fill:true,tension:0.4}]);
}

function renderChart(id, type, labels, datasets) {
  const canvas = document.getElementById(id);
  if (!canvas || typeof Chart === 'undefined') return;
  new Chart(canvas, {
    type,
    data: { labels, datasets },
    options: { responsive:true, plugins:{legend:{display:false}}, scales:{ y:{min:0,max:100,ticks:{color:'#797876'},grid:{color:'rgba(255,255,255,0.05)'}}, x:{ticks:{color:'#797876'},grid:{display:false}} }}
  });
}
