import { showToast } from '../utils/toast.js';

export function renderSettings(container, state) {
  const user = state.user || {};
  container.innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">Settings</h1><p class="page-subtitle">Manage your account and preferences</p></div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><div class="card-title">Profile</div></div>
        <form id="profile-form" style="display:flex;flex-direction:column;gap:var(--space-4)">
          <div style="display:flex;align-items:center;gap:var(--space-4);margin-bottom:var(--space-2)">
            <div class="avatar" style="width:56px;height:56px;font-size:1.2rem">
              ${((user.full_name||user.email||'U').split(' ').map(n=>n[0]).join('').toUpperCase()).slice(0,2)}
            </div>
            <div><div style="font-weight:600">${user.full_name||'--'}</div><div style="font-size:var(--text-xs);color:var(--color-text-muted)">${user.email||''}</div></div>
          </div>
          <div class="form-group"><label>Full Name</label><input type="text" id="s-name" value="${user.full_name||''}" /></div>
          <div class="form-group"><label>Email</label><input type="email" id="s-email" value="${user.email||''}" disabled /></div>
          <div class="form-group"><label>Phone</label><input type="tel" id="s-phone" value="${user.phone||''}" placeholder="+91 XXXXXXXXXX" /></div>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </form>
      </div>
      <div style="display:flex;flex-direction:column;gap:var(--space-5)">
        <div class="card">
          <div class="card-header"><div class="card-title">Security</div></div>
          <div style="display:flex;flex-direction:column;gap:var(--space-3)">
            <button class="btn btn-secondary" id="change-pw-btn"><i data-lucide="lock"></i> Change Password</button>
            <button class="btn btn-secondary" id="totp-btn"><i data-lucide="shield"></i> Enable 2FA (TOTP)</button>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">Notifications</div></div>
          <div style="display:flex;flex-direction:column;gap:var(--space-3)">
            ${[
              ['Low attendance alerts', 'notif-low-att', true],
              ['Session start reminders', 'notif-session', true],
              ['Weekly report emails', 'notif-weekly', false],
              ['Push notifications', 'notif-push', true],
            ].map(([label, id, checked]) => `
              <label class="checkbox-label" style="justify-content:space-between">
                <span>${label}</span>
                <input type="checkbox" id="${id}" ${checked ? 'checked' : ''} />
              </label>`).join('')}
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">Appearance</div></div>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <span style="font-size:var(--text-sm)">Dark mode</span>
            <button data-theme-toggle class="btn btn-secondary btn-sm"><i data-lucide="moon"></i> Toggle</button>
          </div>
        </div>
      </div>
    </div>`;

  document.getElementById('profile-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('Profile updated', 'success');
  });
  document.getElementById('change-pw-btn')?.addEventListener('click', () => showToast('Password change email sent', 'info'));
  document.getElementById('totp-btn')?.addEventListener('click', () => showToast('2FA setup coming soon', 'info'));
}
