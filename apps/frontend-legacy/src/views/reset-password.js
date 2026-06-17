import { authApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export function renderResetPassword(container, state) {
  const params = new URLSearchParams(location.hash.replace('#reset-password?', ''));
  const token = params.get('token');

  container.innerHTML = `
    <div class="auth-screen" style="display:flex">
      <div class="auth-card">
        <div class="auth-logo">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-label="SmartAttend Logo">
            <rect width="40" height="40" rx="10" fill="#4f98a3"/>
            <path d="M10 20 L20 10 L30 20 L20 30 Z" stroke="white" stroke-width="2" fill="none"/>
            <circle cx="20" cy="20" r="4" fill="white"/>
            <path d="M20 10 L20 16 M20 24 L20 30 M10 20 L16 20 M24 20 L30 20" stroke="white" stroke-width="1.5"/>
          </svg>
          <span class="auth-logo-text">SmartAttend</span>
        </div>
        <h1 class="auth-title">Set New Password</h1>
        <p class="auth-subtitle">Choose a strong password for your account</p>
        <form id="reset-password-form" class="auth-form">
          <div class="form-group">
            <label for="rp-password">New Password</label>
            <input type="password" id="rp-password" placeholder="••••••••" required autocomplete="new-password" minlength="8" />
          </div>
          <div class="form-group">
            <label for="rp-confirm">Confirm Password</label>
            <input type="password" id="rp-confirm" placeholder="••••••••" required autocomplete="new-password" minlength="8" />
          </div>
          <button type="submit" class="btn btn-primary btn-full" id="rp-btn">
            <span>Reset Password</span>
          </button>
          <div id="rp-error" class="auth-error hidden"></div>
        </form>
        <div style="margin-top:var(--space-4);text-align:center">
          <a href="#/login" class="link">Back to sign in</a>
        </div>
      </div>
    </div>`;

  const form = document.getElementById('reset-password-form');
  const btn = document.getElementById('rp-btn');
  const errEl = document.getElementById('rp-error');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = document.getElementById('rp-password').value;
    const confirm = document.getElementById('rp-confirm').value;

    if (password !== confirm) {
      errEl.textContent = 'Passwords do not match';
      errEl.classList.remove('hidden');
      return;
    }

    if (password.length < 8) {
      errEl.textContent = 'Password must be at least 8 characters';
      errEl.classList.remove('hidden');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Resetting...';
    errEl.classList.add('hidden');
    try {
      await authApi.resetPassword(token, password);
      showToast('Password has been reset successfully!', 'success');
      location.hash = 'login';
    } catch (err) {
      errEl.textContent = err.message || 'Failed to reset password';
      errEl.classList.remove('hidden');
      btn.disabled = false;
      btn.innerHTML = '<span>Reset Password</span>';
    }
  });
}
