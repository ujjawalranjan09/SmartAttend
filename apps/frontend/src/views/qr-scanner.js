import { attendanceApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

let _scanner = null;

export async function renderQrScanner(container, state) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Scan QR Code</h1>
        <p class="page-subtitle">Point your camera at the session QR code to mark attendance</p>
      </div>
    </div>
    <div class="qr-scanner-wrapper">
      <div class="qr-scanner-card card">
        <div id="qr-reader"></div>
        <div id="qr-status" class="qr-status">
          <i data-lucide="camera"></i>
          <span>Initializing camera...</span>
        </div>
        <div id="qr-result" class="qr-result hidden"></div>
        <div class="qr-divider">
          <span>or enter code manually</span>
        </div>
        <form id="qr-manual-form" class="qr-manual-form">
          <input type="text" id="qr-manual-input" class="input" placeholder="Enter QR code" autocomplete="off" />
          <button type="submit" class="btn btn-primary">Submit</button>
        </form>
      </div>
    </div>
  `;

  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);

  document.getElementById('qr-manual-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const code = document.getElementById('qr-manual-input').value.trim();
    if (code) markAttendance(code);
  });

  await initCameraScanner();
}

async function initCameraScanner() {
  const statusEl = document.getElementById('qr-status');
  try {
    const { Html5Qrcode } = await loadQrLibrary();
    _scanner = new Html5Qrcode('qr-reader');
    await _scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        markAttendance(decodedText);
        stopScanner();
      },
      () => {}
    );
    statusEl.innerHTML = '<i data-lucide="camera"></i><span>Camera active — scan a QR code</span>';
    if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);
  } catch (err) {
    statusEl.innerHTML = '<i data-lucide="camera-off"></i><span>Camera unavailable — use manual entry below</span>';
    if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);
  }
}

function stopScanner() {
  if (_scanner) {
    _scanner.stop().catch(() => {});
    _scanner = null;
  }
}

async function markAttendance(code) {
  const resultEl = document.getElementById('qr-result');
  const statusEl = document.getElementById('qr-status');

  statusEl.innerHTML = '<i data-lucide="loader"></i><span>Submitting attendance...</span>';
  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);

  try {
    await attendanceApi.mark({ qr_token: code });
    resultEl.className = 'qr-result qr-success';
    resultEl.innerHTML = '<i data-lucide="check-circle"></i><span>Attendance marked successfully!</span>';
    resultEl.classList.remove('hidden');
    statusEl.innerHTML = '<i data-lucide="check-circle"></i><span>Done</span>';
    showToast('Attendance recorded!', 'success');
  } catch (err) {
    resultEl.className = 'qr-result qr-error';
    resultEl.innerHTML = `<i data-lucide="x-circle"></i><span>${err.message || 'Failed to mark attendance'}</span>`;
    resultEl.classList.remove('hidden');
    statusEl.innerHTML = '<i data-lucide="alert-circle"></i><span>Scan another code or try manual entry</span>';
    showToast(err.message || 'Failed to mark attendance', 'error');
  }
  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);
}

function loadQrLibrary() {
  return new Promise((resolve, reject) => {
    if (window.Html5Qrcode) {
      resolve(window);
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
    script.onload = () => {
      if (window.Html5Qrcode) resolve(window);
      else reject(new Error('html5-qrcode failed to load'));
    };
    script.onerror = () => reject(new Error('Failed to load QR library'));
    document.head.appendChild(script);
  });
}
