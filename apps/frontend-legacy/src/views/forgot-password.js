import { authApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export function renderForgotPassword(container, state) {
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
        <h1 class="auth-title">Forgot Password</h1>
        <p class="auth-subtitle">Enter your email to receive a reset link</p>
        <form id="forgot-password-form" class="auth-form">
          <div class="form-group">
            <label for="fp-email">Email address</label>
            <input type="email" id="fp-email" placeholder="you@smartattend.in" required autocomplete="email" />
          </div>
          <button type="submit" class="btn btn-primary btn-full" id="fp-btn">
            <span>Send Reset Link</span>
          </button>
          <div id="fp-error" class="auth-error hidden"></div>
        </form>
        <div style="margin-top:var(--space-4);text-align:center">
          <a href="#/login" class="link">Back to sign in</a>
        </div>
      </div>
    </div>`;

  const form = document.getElementById('forgot-password-form');
  const btn = document.getElementById('fp-btn');
  const errEl = document.getElementById('fp-error');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('fp-email').value;
    btn.disabled = true;
    btn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Sending...';
    errEl.classList.add('hidden');
    try {
      await authApi.forgotPassword(email);
      showToast('Reset link sent! Check your email.', 'success');
      location.hash = 'login';
    } catch (err) {
      errEl.textContent = err.message || 'Failed to send reset link';
      errEl.classList.remove('hidden');
      btn.disabled = false;
      btn.innerHTML = '<span>Send Reset Link</span>';
    }
  });
}
