export function toast(message, type = 'info', duration = 4000) {
  const icons = {
    success: '<i data-lucide="check-circle"></i>',
    error:   '<i data-lucide="alert-circle"></i>',
    info:    '<i data-lucide="info"></i>',
  };
  const container = document.getElementById('toast-container');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${message}</span>`;
  container.appendChild(el);

  if (typeof lucide !== 'undefined') lucide.createIcons({ el });

  setTimeout(() => {
    el.style.animation = 'slideIn 0.3s cubic-bezier(0.16,1,0.3,1) reverse';
    setTimeout(() => el.remove(), 300);
  }, duration);
}
