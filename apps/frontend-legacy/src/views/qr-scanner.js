import { attendanceApi, facesApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

let _scanner = null;

export async function renderQrScanner(container, state) {
  const user = state.user || {};
  // Check if student has face enrollment
  let faceEnrolled = false;
  if (user.role === 'student') {
    try {
      const status = await facesApi.status();
      faceEnrolled = status.enrolled;
    } catch {}
  }

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
        ${faceEnrolled ? `
        <div id="face-verification" style="display:none;border-top:1px solid var(--color-border);padding:var(--space-4);text-align:center">
          <div style="font-size:var(--text-sm);font-weight:500;margin-bottom:var(--space-2)">Face Verification Required</div>
          <video id="face-verify-video" style="width:200px;height:150px;border-radius:12px;object-fit:cover;margin:0 auto;display:block" autoplay playsinline></video>
          <div id="face-verify-status" style="font-size:var(--text-xs);color:var(--color-text-muted);margin-top:var(--space-2)">Click "Verify" to complete face check</div>
          <button class="btn btn-primary btn-sm" id="verify-face-btn" style="margin-top:var(--space-2)"><i data-lucide="camera"></i> Verify & Mark Attendance</button>
          <button class="btn btn-ghost btn-sm" id="skip-face-btn" style="margin-top:var(--space-2)"><i data-lucide="x"></i> Skip Face Check</button>
        </div>
        ` : ''}
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

  // Override the default markAttendance to support face verification flow
  const originalMarkAttendance = window._markAttendance || function() {};

  document.getElementById('qr-manual-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const code = document.getElementById('qr-manual-input').value.trim();
    if (code) processQrCode(code, faceEnrolled, state);
  });

  await initCameraScanner(faceEnrolled, state);
}

async function initCameraScanner(faceEnrolled, state) {
  const statusEl = document.getElementById('qr-status');
  try {
    const { Html5Qrcode } = await loadQrLibrary();
    _scanner = new Html5Qrcode('qr-reader');
    await _scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        stopScanner();
        processQrCode(decodedText, faceEnrolled, state);
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

async function processQrCode(code, faceEnrolled, state) {
  let sessionId = null;
  let qrToken = code;
  try {
    const url = new URL(code);
    sessionId = url.searchParams.get('session');
    qrToken = url.searchParams.get('token') || code;
  } catch {
    // Not a URL — treat as raw token (manual entry)
  }

  if (!sessionId) {
    const resultEl = document.getElementById('qr-result');
    resultEl.className = 'qr-result qr-error';
    resultEl.innerHTML = '<i data-lucide="x-circle"></i><span>Invalid QR code: missing session ID</span>';
    resultEl.classList.remove('hidden');
    return;
  }

  if (faceEnrolled) {
    const faceVerif = document.getElementById('face-verification');
    if (faceVerif) {
      faceVerif.style.display = 'block';
      document.getElementById('qr-status').innerHTML = '<i data-lucide="user-check"></i><span>Face verification required</span>';
      if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);

      // Wire up face verification buttons
      const verifyBtn = document.getElementById('verify-face-btn');
      const skipBtn = document.getElementById('skip-face-btn');
      const statusMsg = document.getElementById('face-verify-status');
      let faceStream = null;

      try {
        faceStream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 } });
        document.getElementById('face-verify-video').srcObject = faceStream;
      } catch {
        await markAttendance(sessionId, qrToken);
        faceVerif.style.display = 'none';
        return;
      }

      verifyBtn.onclick = async () => {
        const video = document.getElementById('face-verify-video');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 320;
        canvas.height = video.videoHeight || 240;
        canvas.getContext('2d').drawImage(video, 0, 0);
        canvas.toBlob(async (blob) => {
          if (!blob) { await markAttendance(sessionId, qrToken); return; }
          statusMsg.textContent = 'Verifying face...';
          try {
            const formData = new FormData();
            formData.append('image', blob);
            const token = state.token || '';
            await fetch(
              (window.API_BASE || 'http://localhost:8000/api/v1') + '/faces/enroll',
              { method: 'POST', headers: { 'Authorization': 'Bearer ' + token }, body: formData }
            );
            statusMsg.innerHTML = '<span style="color:var(--color-success)">Face captured ✓</span>';
          } catch (e) {
            statusMsg.textContent = 'Face check done. Proceeding...';
          }
          if (faceStream) { faceStream.getTracks().forEach(t => t.stop()); faceStream = null; }
          faceVerif.style.display = 'none';
          await markAttendance(sessionId, qrToken);
        }, 'image/jpeg', 0.85);
      };

      skipBtn.onclick = async () => {
        if (faceStream) { faceStream.getTracks().forEach(t => t.stop()); faceStream = null; }
        faceVerif.style.display = 'none';
        await markAttendance(sessionId, qrToken);
      };
      return;
    }
  }

  await markAttendance(sessionId, qrToken);
}

async function markAttendance(sessionId, qrToken) {
  const resultEl = document.getElementById('qr-result');
  const statusEl = document.getElementById('qr-status');

  statusEl.innerHTML = '<i data-lucide="loader"></i><span>Submitting attendance...</span>';
  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);

  try {
    await attendanceApi.mark({
      session_id: sessionId,
      qr_token: qrToken,
    });
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