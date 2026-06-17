// Toast notification system
export function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: 'check-circle', error: 'x-circle', warning: 'alert-triangle', info: 'info' };
  const colors = { success: 'var(--color-success)', error: 'var(--color-error)', warning: 'var(--color-warning)', info: 'var(--color-primary)' };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon" style="color:${colors[type]}">
      <i data-lucide="${icons[type]}"></i>
    </span>
    <span class="toast-msg">${message}</span>
    <button class="toast-close icon-btn" aria-label="Dismiss"><i data-lucide="x"></i></button>
  `;
  container.appendChild(toast);
  if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [toast] });

  const dismiss = () => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = '0.2s ease';
    setTimeout(() => toast.remove(), 200);
  };
  toast.querySelector('.toast-close').addEventListener('click', dismiss);
  if (duration > 0) setTimeout(dismiss, duration);
  return dismiss;
}
