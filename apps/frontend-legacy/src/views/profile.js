import { profileApi, goalsApi, dailyPlanApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export async function renderProfile(container, state) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">My Profile</h1>
        <p class="page-subtitle">Your academic identity — interests, strengths, and goals</p>
      </div>
    </div>
    <div class="profile-tabs">
      <button class="profile-tab active" data-tab="profile">My Profile</button>
      <button class="profile-tab" data-tab="goals">My Goals</button>
    </div>
    <div id="profile-content"></div>`;

  document.querySelectorAll('.profile-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.profile-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === btn.dataset.tab));
      renderTab(btn.dataset.tab);
    });
  });

  renderTab('profile');
}

async function renderTab(tab) {
  const content = document.getElementById('profile-content');
  if (tab === 'profile') await renderProfileTab(content);
  else await renderGoalsTab(content);
}

// ─── Profile Tab ────────────────────────────────────────────────────────────────

async function renderProfileTab(container) {
  container.innerHTML = '<div class="skeleton" style="height:300px"></div>';
  let profile = null;
  try { profile = await profileApi.get(); }
  catch (e) { if (e.status !== 404) { container.innerHTML = '<div class="empty-state"><p>Failed to load profile.</p></div>'; return; } }

  if (!profile) {
    container.innerHTML = getCreateProfileForm(null);
    attachProfileFormHandlers(null);
  } else {
    container.innerHTML = getProfileDisplay(profile) + getEditProfileForm(profile);
    attachProfileFormHandlers(profile);
  }
}

function getProfileDisplay(p) {
  return `
    <div class="card profile-view" style="margin-bottom:var(--space-4)">
      <div class="card-header"><div class="card-title">Profile Overview</div></div>
      <div class="profile-grid">
        <div class="profile-field"><div class="profile-field-label">Interests</div>
          <div class="profile-tags">${(p.interests||[]).map(t => `<span class="tag tag-primary">${t}</span>`).join('') || '<span class="text-muted">None set</span>'}</div>
        </div>
        <div class="profile-field"><div class="profile-field-label">Strengths</div>
          <div class="profile-tags">${(p.strengths||[]).map(t => `<span class="tag tag-success">${t}</span>`).join('') || '<span class="text-muted">None set</span>'}</div>
        </div>
        <div class="profile-field"><div class="profile-field-label">Career Goals</div>
          <div class="profile-tags">${(p.career_goals||[]).map(t => `<span class="tag tag-warning">${t}</span>`).join('') || '<span class="text-muted">None set</span>'}</div>
        </div>
        <div class="profile-field"><div class="profile-field-label">Study Style</div>
          <div class="tag tag-muted">${p.preferred_study_style || 'Not set'}</div>
        </div>
        <div class="profile-field"><div class="profile-field-label">Daily Study Target</div>
          <div>${p.daily_study_hours_target} hours/day</div>
        </div>
      </div>
      <div style="margin-top:var(--space-4)">
        <button class="btn btn-secondary btn-sm" id="edit-profile-btn"><i data-lucide="edit-2"></i> Edit Profile</button>
      </div>
    </div>`;
}

function getCreateProfileForm(p) {
  return `
    <div class="card">
      <div class="card-header"><div class="card-title">Create Your Profile</div>
        <div class="card-subtitle">Tell us about yourself so we can personalize your daily plan</div>
      </div>
      <div class="card-body">${getProfileForm(p, false)}</div>
    </div>`;
}

function getEditProfileForm(p) {
  return `
    <div class="card hidden" id="profile-edit-card">
      <div class="card-header"><div class="card-title">Edit Profile</div></div>
      <div class="card-body">${getProfileForm(p, true)}</div>
    </div>`;
}

function getProfileForm(p, isEdit) {
  const interests = (p?.interests||[]).join(', ');
  const strengths = (p?.strengths||[]).join(', ');
  const career_goals = (p?.career_goals||[]).join(', ');
  return `
    <form id="profile-form" class="profile-form">
      <div class="form-group">
        <label>Interests <span class="text-muted">(comma-separated, Enter to add tag)</span></label>
        <div class="tag-input-wrap">
          <div class="tag-input-tags" id="tag-interests"></div>
          <input type="text" id="tag-interests-input" placeholder="e.g. machine learning, web dev" value="${isEdit ? '' : interests}">
        </div>
        ${!isEdit ? `<div class="form-hint">Type and press Enter or comma to add tags</div>` : ''}
      </div>
      <div class="form-group">
        <label>Strengths <span class="text-muted">(comma-separated)</span></label>
        <div class="tag-input-wrap">
          <div class="tag-input-tags" id="tag-strengths"></div>
          <input type="text" id="tag-strengths-input" placeholder="e.g. mathematics, programming" value="${isEdit ? '' : strengths}">
        </div>
      </div>
      <div class="form-group">
        <label>Career Goals <span class="text-muted">(comma-separated)</span></label>
        <div class="tag-input-wrap">
          <div class="tag-input-tags" id="tag-career_goals"></div>
          <input type="text" id="tag-career_goals-input" placeholder="e.g. software engineer, data analyst" value="${isEdit ? '' : career_goals}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Preferred Study Style</label>
          <select id="study-style">
            <option value="">Select...</option>
            ${['visual','reading','hands-on','group','mixed'].map(s => `<option value="${s}" ${p?.preferred_study_style === s ? 'selected' : ''}>${capitalize(s)}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label>Daily Study Hours Target</label>
          <input type="number" id="study-hours" min="1" max="12" value="${p?.daily_study_hours_target || 2}">
        </div>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary"><i data-lucide="save"></i> ${isEdit ? 'Update Profile' : 'Create Profile'}</button>
        ${isEdit ? `<button type="button" class="btn btn-ghost" id="cancel-edit">Cancel</button>` : ''}
      </div>
    </form>`;
}

function attachProfileFormHandlers(existingProfile) {
  if (existingProfile) {
    document.getElementById('edit-profile-btn')?.addEventListener('click', () => {
      document.getElementById('profile-edit-card')?.classList.remove('hidden');
    });
    document.getElementById('cancel-edit')?.addEventListener('click', () => {
      document.getElementById('profile-edit-card')?.classList.add('hidden');
    });
    // Pre-fill tags for edit mode
    setupTagInput('interests', existingProfile.interests || []);
    setupTagInput('strengths', existingProfile.strengths || []);
    setupTagInput('career_goals', existingProfile.career_goals || []);
  } else {
    // New profile — auto-tag from comma input on blur
    setupCommaTagInput('tag-interests-input', 'tag-interests', []);
    setupCommaTagInput('tag-strengths-input', 'tag-strengths', []);
    setupCommaTagInput('tag-career_goals-input', 'tag-career_goals', []);
  }

  const form = document.getElementById('profile-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<svg class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Saving...';

    const data = {
      interests: getTagValues('tag-interests'),
      strengths: getTagValues('tag-strengths'),
      career_goals: getTagValues('tag-career_goals'),
      preferred_study_style: document.getElementById('study-style')?.value || undefined,
      daily_study_hours_target: parseInt(document.getElementById('study-hours')?.value || '2'),
    };

    try {
      if (existingProfile) {
        await profileApi.update(data);
        showToast('Profile updated!', 'success');
        // Invalidate routine cache since profile changed
        try { await dailyPlanApi.invalidateRoutine(); } catch {}
      } else {
        await profileApi.create(data);
        showToast('Profile created!', 'success');
      }
      renderProfileTab(document.getElementById('profile-content'));
    } catch (err) {
      showToast(err.message || 'Failed to save profile', 'error');
      btn.disabled = false;
      btn.innerHTML = '<i data-lucide="save"></i> ' + (existingProfile ? 'Update Profile' : 'Create Profile');
    }
  });
}

// ─── Goals Tab ─────────────────────────────────────────────────────────────────

async function renderGoalsTab(container) {
  container.innerHTML = '<div class="skeleton" style="height:300px"></div>';
  let goals = [], profile = null;
  try {
    [goals, profile] = await Promise.all([
      goalsApi.list().then(r => r.items || []).catch(() => []),
      profileApi.get().catch(() => null),
    ]);
  } catch { /* show empty state */ }

  const allGoals = goals;
  container.innerHTML = `
    <div class="goals-header">
      <div>
        ${!profile ? '<div class="profile-hint-banner"><i data-lucide="info"></i> <span>Complete your profile to get personalized suggestions</span> <a href="#profile" class="btn btn-sm btn-secondary">Set up profile</a></div>' : ''}
      </div>
      <button class="btn btn-primary" id="add-goal-btn"><i data-lucide="plus"></i> Add Goal</button>
    </div>
    <div class="goals-filters">
      <button class="filter-btn active" data-filter="active">Active</button>
      <button class="filter-btn" data-filter="completed">Completed</button>
      <button class="filter-btn" data-filter="all">All</button>
    </div>
    <div id="goals-list"></div>`;

  // Filter state
  let activeFilter = 'active';

  function renderGoals(filter) {
    const filtered = filter === 'all' ? allGoals
      : filter === 'completed' ? allGoals.filter(g => g.status === 'completed')
      : allGoals.filter(g => g.status === 'active');

    const listEl = document.getElementById('goals-list');
    if (!filtered.length) {
      listEl.innerHTML = `<div class="empty-state" style="padding:3rem"><i data-lucide="target" style="width:40px;height:40px"></i><h3>No ${filter} goals</h3><p>${filter === 'active' ? 'Set your first goal to get started!' : 'Completed goals will appear here.'}</p></div>`;
    } else {
      listEl.innerHTML = `<div class="goals-grid">${filtered.map(g => goalCard(g)).join('')}</div>`;
    }

    filtered.forEach(g => {
      document.getElementById(`goal-expand-${g.id}`)?.addEventListener('click', () => expandGoal(g));
      document.getElementById(`goal-log-${g.id}`)?.addEventListener('click', () => showLogProgressModal(g));
      document.getElementById(`goal-delete-${g.id}`)?.addEventListener('click', () => deleteGoal(g.id));
    });

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b === btn));
      renderGoals(btn.dataset.filter);
    });
  });

  document.getElementById('add-goal-btn')?.addEventListener('click', () => showAddGoalModal());

  renderGoals('active');

  if (typeof lucide !== 'undefined') lucide.createIcons();
}

function goalCard(g) {
  const priorityColors = { high: 'badge-error', medium: 'badge-warning', low: 'badge-muted' };
  const catColors = { academic: 'badge-primary', career: 'badge-success', skill: 'badge-info', project: 'badge-warning', exam_prep: 'badge-error' };
  const pct = g.estimated_hours ? Math.round((g.completed_hours / g.estimated_hours) * 100) : 0;
  return `
    <div class="goal-card">
      <div class="goal-card-header">
        <div class="goal-title">${g.title}</div>
        <div style="display:flex;gap:var(--space-2);flex-wrap:wrap">
          <span class="badge ${catColors[g.category] || 'badge-muted'}">${g.category}</span>
          <span class="badge ${priorityColors[g.priority] || 'badge-muted'}">${g.priority}</span>
          <span class="badge badge-muted">${g.status}</span>
        </div>
      </div>
      ${g.target_date ? `<div class="goal-meta"><i data-lucide="calendar"></i> Due: ${new Date(g.target_date).toLocaleDateString('en-IN')}</div>` : ''}
      ${g.estimated_hours ? `
        <div class="goal-progress-section">
          <div class="goal-progress-header"><span>${g.completed_hours}/${g.estimated_hours} hrs</span><span>${pct}%</span></div>
          <div class="progress-bar"><div class="progress-fill ${pct >= 100 ? 'high' : 'mid'}" style="width:${Math.min(pct,100)}%"></div></div>
        </div>` : ''}
      ${(g.milestones||[]).length ? `<div class="goal-milestones">${g.milestones.map((m,i) => `<div class="milestone-item ${m.completed ? 'done' : ''}">${m.completed ? '✓' : (i+1)} ${m.title}</div>`).join('')}</div>` : ''}
      <div class="goal-actions">
        <button class="btn btn-sm btn-ghost" id="goal-expand-${g.id}">${g.description ? 'Details' : ''} <i data-lucide="${g.description ? 'chevron-down' : 'plus'}"></i></button>
        <button class="btn btn-sm btn-secondary" id="goal-log-${g.id}"><i data-lucide="clock"></i> Log Hours</button>
        <button class="btn btn-sm btn-ghost" id="goal-delete-${g.id}"><i data-lucide="trash-2"></i></button>
      </div>
      <div class="goal-detail hidden" id="goal-detail-${g.id}">
        ${g.description ? `<p style="font-size:var(--text-sm);color:var(--color-text-muted);margin:var(--space-2) 0">${g.description}</p>` : ''}
      </div>
    </div>`;
}

function expandGoal(g) {
  const detail = document.getElementById(`goal-detail-${g.id}`);
  detail?.classList.toggle('hidden');
}

async function deleteGoal(id) {
  if (!confirm('Abandon this goal? This marks it as abandoned.')) return;
  try {
    await goalsApi.delete(id);
    showToast('Goal abandoned', 'info');
    renderGoalsTab(document.getElementById('profile-content'));
  } catch (e) { showToast(e.message || 'Failed', 'error'); }
}

function showLogProgressModal(goal) {
  const modal = createModal('Log Progress', `
    <form id="log-progress-form">
      <div class="form-group">
        <label>Hours completed</label>
        <input type="number" id="log-hours" min="0.5" step="0.5" placeholder="e.g. 1.5" required>
      </div>
      ${(goal.milestones||[]).length ? `
        <div class="form-group">
          <label>Mark milestone done</label>
          <div class="milestone-checklist">
            ${goal.milestones.map((m,i) => `<label class="checkbox-label"><input type="checkbox" data-milestone="${i}" ${m.completed ? 'checked disabled' : ''}> ${m.title}</label>`).join('')}
          </div>
        </div>` : ''}
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Log Hours</button>
      </div>
    </form>`);

  document.getElementById('log-progress-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const hours = parseFloat(document.getElementById('log-hours').value);
    const milestoneIndex = [...modal.querySelectorAll('[data-milestone]')].findIndex(cb => cb.checked && !cb.disabled);
    const data = { completed_hours: hours };
    if (milestoneIndex >= 0) data.milestone_index = milestoneIndex;
    try {
      await goalsApi.updateProgress(goal.id, data);
      try { await dailyPlanApi.invalidateRoutine(); } catch {}
      modal.close();
      showToast('Progress logged!', 'success');
      renderGoalsTab(document.getElementById('profile-content'));
    } catch (e) { showToast(e.message || 'Failed', 'error'); }
  });
}

function showAddGoalModal() {
  const modal = createModal('Add New Goal', `
    <form id="add-goal-form">
      <div class="form-group"><label>Title *</label><input type="text" id="goal-title" required placeholder="e.g. Complete ML Course on Coursera"></div>
      <div class="form-group"><label>Description</label><textarea id="goal-desc" rows="2" placeholder="Optional details..."></textarea></div>
      <div class="form-row">
        <div class="form-group">
          <label>Category *</label>
          <select id="goal-cat" required>
            <option value="">Select...</option>
            ${['academic','career','skill','project','exam_prep'].map(c => `<option value="${c}">${capitalize(c)}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label>Priority</label>
          <select id="goal-priority">
            <option value="high">High</option>
            <option value="medium" selected>Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Target Date</label><input type="date" id="goal-date"></div>
        <div class="form-group"><label>Estimated Hours</label><input type="number" id="goal-est" min="1" placeholder="e.g. 40"></div>
      </div>
      <div class="form-group">
        <label>Milestones</label>
        <div id="milestone-list"></div>
        <button type="button" class="btn btn-ghost btn-sm" id="add-milestone-btn" style="margin-top:var(--space-2)"><i data-lucide="plus"></i> Add Milestone</button>
      </div>
      <div class="form-actions" style="margin-top:var(--space-4)">
        <button type="submit" class="btn btn-primary">Create Goal</button>
      </div>
    </form>`);

  // Milestone builder
  let milestoneCount = 0;
  document.getElementById('add-milestone-btn')?.addEventListener('click', () => {
    const list = document.getElementById('milestone-list');
    const id = milestoneCount++;
    list.insertAdjacentHTML('beforeend', `<div class="milestone-row" style="display:flex;gap:var(--space-2);margin-bottom:var(--space-2)"><input type="text" class="input milestone-title" data-ms="${id}" placeholder="Milestone title" style="flex:1"><button type="button" class="btn btn-ghost btn-sm" onclick="this.parentElement.remove()"><i data-lucide="x"></i></button></div>`);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  });

  document.getElementById('add-goal-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const milestones = [...document.querySelectorAll('.milestone-title')].map(el => ({ title: el.value, completed: false })).filter(m => m.title.trim());
    const data = {
      title: document.getElementById('goal-title').value,
      description: document.getElementById('goal-desc').value || undefined,
      category: document.getElementById('goal-cat').value,
      priority: document.getElementById('goal-priority').value,
      target_date: document.getElementById('goal-date').value || undefined,
      estimated_hours: parseInt(document.getElementById('goal-est').value) || undefined,
      milestones,
    };
    try {
      await goalsApi.create(data);
      try { await dailyPlanApi.invalidateRoutine(); } catch {}
      modal.close();
      showToast('Goal created!', 'success');
      renderGoalsTab(document.getElementById('profile-content'));
    } catch (e) { showToast(e.message || 'Failed to create goal', 'error'); }
  });
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function createModal(title, bodyHTML) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal"><div class="modal-header"><h3>${title}</h3><button class="icon-btn" id="modal-close-btn">&times;</button></div><div class="modal-body">${bodyHTML}</div></div>`;
  document.body.appendChild(overlay);
  overlay.querySelector('#modal-close-btn').onclick = () => modal.close();
  overlay.onclick = (e) => { if (e.target === overlay) modal.close(); };
  overlay.close = () => overlay.remove();
  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);
  return overlay;
}

function setupTagInput(id, initialTags) {
  const tags = [...initialTags];
  const wrap = document.getElementById(`tag-${id}`);
  const input = document.getElementById(`tag-${id}-input`);
  if (!wrap || !input) return;

  function renderTags() {
    wrap.innerHTML = tags.map(t => `<span class="tag tag-primary">${t}<button type="button" data-tag="${t}" class="tag-remove">&times;</button></span>`).join('');
    wrap.querySelectorAll('.tag-remove').forEach(btn => {
      btn.onclick = () => { tags.splice(tags.indexOf(btn.dataset.tag), 1); renderTags(); };
    });
  }

  function addTag(value) {
    const v = value.trim();
    if (v && !tags.includes(v)) { tags.push(v); renderTags(); }
  }

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(input.value.replace(',','')); input.value = ''; }
    if (e.key === 'Backspace' && !input.value && tags.length) { tags.pop(); renderTags(); }
  });
  input.addEventListener('blur', () => { if (input.value.trim()) { addTag(input.value); input.value = ''; } });
  renderTags();
}

function setupCommaTagInput(inputId, tagsId, initial) {
  const input = document.getElementById(inputId);
  const wrap = document.getElementById(tagsId);
  if (!input || !wrap) return;
  const tags = [...initial];
  function renderTags() {
    wrap.innerHTML = tags.map(t => `<span class="tag tag-primary">${t}<button type="button" data-tag="${t}" class="tag-remove">&times;</button></span>`).join('');
    wrap.querySelectorAll('.tag-remove').forEach(btn => {
      btn.onclick = () => { tags.splice(tags.indexOf(btn.dataset.tag), 1); renderTags(); };
    });
  }
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); const v = input.value.replace(',','').trim(); if (v && !tags.includes(v)) tags.push(v); input.value = ''; renderTags(); }
    if (e.key === 'Backspace' && !input.value && tags.length) { tags.pop(); renderTags(); }
  });
  renderTags();
}

function getTagValues(id) {
  const tags = [...document.querySelectorAll(`#${id} .tag-remove`)]
    .map(btn => btn.dataset.tag);
  const input = document.getElementById(`${id}-input`);
  if (input?.value.trim()) tags.push(input.value.trim());
  return tags;
}

function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1).replace('_',' ') : ''; }
