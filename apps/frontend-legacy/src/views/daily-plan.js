import { dailyPlanApi, profileApi, goalsApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export async function renderDailyPlan(container, state) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">My Day</h1>
        <p class="page-subtitle">Free periods, study suggestions, and your daily routine</p>
      </div>
    </div>
    <div class="dp-date-nav">
      <button class="icon-btn" id="dp-prev"><i data-lucide="chevron-left"></i></button>
      <input type="date" id="dp-date" value="${todayStr()}">
      <button class="icon-btn" id="dp-next"><i data-lucide="chevron-right"></i></button>
      <span id="dp-day-label" style="margin-left:var(--space-2);font-size:var(--text-sm);color:var(--color-text-muted)"></span>
    </div>
    <div class="profile-hint-banner hidden" id="dp-profile-hint" style="margin-bottom:var(--space-4)">
      <i data-lucide="info"></i>
      <span>Complete your profile to get personalized study suggestions</span>
      <a href="#profile" class="btn btn-sm btn-secondary">Set up profile</a>
    </div>
    <div class="dp-tabs">
      <button class="dp-tab active" data-tab="free-periods">Free Periods</button>
      <button class="dp-tab" data-tab="routine">Routine</button>
    </div>
    <div id="dp-content"></div>`;

  let currentDate = todayStr();
  let profile = null;
  try { profile = await profileApi.get(); } catch {}

  if (!profile) document.getElementById('dp-profile-hint')?.classList.remove('hidden');

  updateDayLabel(currentDate);

  document.getElementById('dp-date')?.addEventListener('change', (e) => {
    currentDate = e.target.value;
    updateDayLabel(currentDate);
    renderActiveTab();
  });

  document.getElementById('dp-prev')?.addEventListener('click', () => {
    const d = parseDate(currentDate);
    d.setDate(d.getDate() - 1);
    currentDate = formatDate(d);
    document.getElementById('dp-date').value = currentDate;
    updateDayLabel(currentDate);
    renderActiveTab();
  });

  document.getElementById('dp-next')?.addEventListener('click', () => {
    const d = parseDate(currentDate);
    d.setDate(d.getDate() + 1);
    currentDate = formatDate(d);
    document.getElementById('dp-date').value = currentDate;
    updateDayLabel(currentDate);
    renderActiveTab();
  });

  document.querySelectorAll('.dp-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.dp-tab').forEach(b => b.classList.toggle('active', b === btn));
      renderActiveTab();
    });
  });

  async function renderActiveTab() {
    const tab = document.querySelector('.dp-tab.active')?.dataset.tab || 'free-periods';
    const content = document.getElementById('dp-content');
    if (tab === 'free-periods') await renderFreePeriods(content, currentDate);
    else await renderRoutine(content, currentDate);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  renderActiveTab();
}

function updateDayLabel(dateStr) {
  const el = document.getElementById('dp-day-label');
  if (!el) return;
  const d = parseDate(dateStr);
  const diff = Math.round((d - new Date()) / 86400000);
  const label = diff === 0 ? 'Today' : diff === 1 ? 'Tomorrow' : diff === -1 ? 'Yesterday' : d.toLocaleDateString('en-IN', {weekday:'long', month:'short', day:'numeric'});
  el.textContent = label;
}

// ─── Free Periods Tab ──────────────────────────────────────────────────────────

async function renderFreePeriods(container, date) {
  container.innerHTML = '<div class="skeleton" style="height:400px"></div>';
  let data = null;
  try {
    data = await dailyPlanApi.getFreePeriods(date);
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><i data-lucide="calendar-x" style="width:48px;height:48px"></i><h3>Failed to load</h3><p>${e.message || 'Backend may be offline'}</p></div>`;
    return;
  }

  if (!data?.classes?.length && !data?.free_periods?.length) {
    container.innerHTML = `<div class="empty-state"><i data-lucide="calendar" style="width:48px;height:48px"></i><h3>No Schedule Data</h3><p>You have no classes or free periods for this day.</p></div>`;
    return;
  }

  const blocks = buildDayBlocks(data);
  container.innerHTML = `<div class="day-timeline">${blocks.map(b => timelineBlock(b, data.profile_incomplete)).join('')}</div>`;

  // Attach expand handlers for free periods
  document.querySelectorAll('.fp-expand').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = btn.closest('.timeline-block-free');
      card?.querySelector('.fp-suggestions')?.classList.toggle('hidden');
      btn.textContent = card?.querySelector('.fp-suggestions')?.classList.contains('hidden') ? 'Show Suggestions' : 'Hide Suggestions';
    });
  });
}

function buildDayBlocks(data) {
  const blocks = [];
  const classes = data.classes || [];
  const fps = data.free_periods || [];
  // Merge and sort by start time
  classes.forEach(c => blocks.push({ type: 'class', start: c.start_time, end: c.end_time, data: c }));
  fps.forEach(fp => blocks.push({ type: 'free', start: fp.start_time, end: fp.end_time, duration: fp.duration_minutes, suggestions: fp.suggestions || [] }));
  return blocks.sort((a, b) => a.start.localeCompare(b.start));
}

function timelineBlock(b, profileIncomplete) {
  if (b.type === 'class') {
    return `<div class="timeline-block-class">
      <div class="tl-time">${b.start} – ${b.end}</div>
      <div class="tl-block class-block">
        <div class="tl-block-title">${b.data.course_name}</div>
        <div class="tl-block-meta">${b.data.room || ''}</div>
        <div class="tl-block-badge class-badge">Class</div>
      </div>
    </div>`;
  } else {
    const suggestions = b.suggestions || [];
    const suggestionCards = suggestions.map(s => suggestionCard(s)).join('');
    return `<div class="timeline-block-free">
      <div class="tl-time">${b.start} – ${b.end} <span style="font-size:var(--text-xs);color:var(--color-text-muted)">(${b.duration} min)</span></div>
      <div class="tl-block free-block ${!suggestions.length ? 'no-suggestions' : ''}">
        <div class="tl-block-badge free-badge">Free Period</div>
        ${profileIncomplete ? '<div class="profile-mini-hint">Complete your profile for personalized suggestions</div>' : ''}
        ${suggestions.length ? `<div class="fp-suggestions">${suggestionCards}</div>` : '<p class="text-muted" style="font-size:var(--text-sm);padding:var(--space-2) 0">No suggestions available</p>'}
        ${suggestions.length ? `<button class="btn btn-ghost btn-sm fp-expand">Show Suggestions</button>` : ''}
      </div>
    </div>`;
  }
}

function suggestionCard(s) {
  const catColors = { academic: 'badge-primary', career: 'badge-success', skill: 'badge-info', project: 'badge-warning', exam_prep: 'badge-error', general: 'badge-muted' };
  return `
    <div class="suggestion-card">
      <div class="suggestion-header">
        <div class="suggestion-title">${s.title}</div>
        <span class="badge ${catColors[s.category] || 'badge-muted'}">${s.category}</span>
      </div>
      <p class="suggestion-desc">${s.description || ''}</p>
      <div class="suggestion-meta">
        <span><i data-lucide="clock" style="width:12px;height:12px"></i> ${s.duration_minutes} min</span>
        ${s.goal_id ? '<span><i data-lucide="target" style="width:12px;height:12px"></i> Linked goal</span>' : ''}
      </div>
    </div>`;
}

// ─── Routine Tab ───────────────────────────────────────────────────────────────

async function renderRoutine(container, date) {
  container.innerHTML = '<div class="skeleton" style="height:400px"></div><div style="text-align:center;margin-top:var(--space-3);color:var(--color-text-muted);font-size:var(--text-sm)">Generating your routine...</div>';
  let data = null;
  try {
    data = await dailyPlanApi.getRoutine(date);
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><i data-lucide="calendar-x"></i><h3>Failed to load routine</h3><p>${e.message || 'Backend may be offline'}</p></div>`;
    return;
  }

  const blocks = data?.routine || [];
  if (!blocks.length) {
    container.innerHTML = `<div class="empty-state"><i data-lucide="calendar"></i><h3>No Routine Available</h3><p>No classes or free periods for this day.</p></div>`;
    return;
  }

  const summary = data.summary || {};
  const genBy = data.generated_by;
  const profileIncomplete = data.profile_incomplete;

  container.innerHTML = `
    ${profileIncomplete ? '<div class="profile-hint-banner"><i data-lucide="info"></i><span>Set up your profile for a personalized AI routine</span><a href="#profile" class="btn btn-sm btn-secondary">Set up profile</a></div>' : ''}
    <div class="routine-summary-card">
      <div class="routine-summary-grid">
        <div class="rs-item"><div class="rs-val">${summary.total_classes ?? blocks.filter(b=>b.type==='class').length}</div><div class="rs-label">Classes</div></div>
        <div class="rs-item"><div class="rs-val">${summary.total_study_hours ?? '–'}</div><div class="rs-label">Study Hours</div></div>
        <div class="rs-item"><div class="rs-val">${summary.total_break_hours ?? '–'}</div><div class="rs-label">Break Hours</div></div>
        <div class="rs-item"><div class="rs-val">${summary.total_free_hours ?? '–'}</div><div class="rs-label">Free Time</div></div>
      </div>
      ${summary.daily_tip ? `<div class="routine-tip"><i data-lucide="lightbulb"></i> ${summary.daily_tip}</div>` : ''}
      ${genBy === 'fallback' ? '<div class="routine-source-badge"><i data-lucide="alert-circle"></i> Basic plan — AI planner unavailable</div>' : ''}
      ${genBy === 'cached' ? '<div class="routine-source-badge cached"><i data-lucide="cache"></i> Cached result</div>' : ''}
    </div>
    <button class="btn btn-secondary btn-sm" id="regen-routine-btn" style="margin-bottom:var(--space-4)"><i data-lucide="refresh-cw"></i> Regenerate</button>
    <div class="day-timeline">${blocks.map(b => routineBlock(b)).join('')}</div>`;

  document.getElementById('regen-routine-btn')?.addEventListener('click', async () => {
    // Invalidate cache and refetch
    try { await dailyPlanApi.invalidateRoutine(); } catch {}
    await renderRoutine(container, date);
  });
}

function routineBlock(b) {
  if (b.type === 'class') {
    return `<div class="timeline-block-class">
      <div class="tl-time">${b.start} – ${b.end}</div>
      <div class="tl-block class-block">
        <div class="tl-block-title">${b.course_name}</div>
        <div class="tl-block-meta">${b.room || ''} ${b.note ? '· ' + b.note : ''}</div>
        <div class="tl-block-badge class-badge">Class</div>
      </div>
    </div>`;
  }
  if (b.type === 'study') {
    const catColors = { academic: 'badge-primary', career: 'badge-success', skill: 'badge-info', project: 'badge-warning', exam_prep: 'badge-error' };
    const diffColors = { easy: 'badge-success', medium: 'badge-warning', hard: 'badge-error' };
    const dur = timeDiffMins(b.start, b.end);
    return `<div class="timeline-block-free">
      <div class="tl-time">${b.start} – ${b.end} <span style="font-size:var(--text-xs);color:var(--color-text-muted)">(${dur} min)</span></div>
      <div class="tl-block study-block">
        <div class="study-block-header">
          <div class="tl-block-badge study-badge">Study</div>
          <span class="badge ${catColors[b.category] || 'badge-muted'}">${b.category || ''}</span>
          ${b.difficulty ? `<span class="badge ${diffColors[b.difficulty] || 'badge-muted'}">${b.difficulty}</span>` : ''}
        </div>
        <div class="study-block-title">${b.title}</div>
        <p class="study-block-desc">${b.description || ''}</p>
        ${b.goal_title ? `<div class="study-block-goal"><i data-lucide="target" style="width:12px;height:12px"></i> ${b.goal_title}</div>` : ''}
      </div>
    </div>`;
  }
  if (b.type === 'break') {
    return `<div class="timeline-block-free">
      <div class="tl-time">${b.start} – ${b.end}</div>
      <div class="tl-block break-block">
        <div class="tl-block-badge break-badge">Break</div>
        <div class="study-block-title">${b.title || 'Break'}</div>
        ${b.suggestion ? `<p class="study-block-desc">${b.suggestion}</p>` : ''}
      </div>
    </div>`;
  }
  // free
  return `<div class="timeline-block-free">
    <div class="tl-time">${b.start} – ${b.end}</div>
    <div class="tl-block free-idle-block">
      <div class="tl-block-badge free-idle-badge">Free</div>
      <div class="study-block-title">${b.title || 'Rest / Personal Time'}</div>
    </div>
  </div>`;
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function todayStr() { return new Date().toISOString().split('T')[0]; }
function parseDate(s) { return new Date(s + 'T00:00:00'); }
function formatDate(d) { return d.toISOString().split('T')[0]; }
function timeDiffMins(start, end) {
  const [sh,sn] = start.split(':').map(Number);
  const [eh,en] = end.split(':').map(Number);
  return (eh*60+en) - (sh*60+sn);
}
