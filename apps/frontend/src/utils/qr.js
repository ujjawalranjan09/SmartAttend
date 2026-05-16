// QR code generation for session check-in tokens
export async function showQR(sessionId, sessionName) {
  const overlay = document.getElementById('qr-modal-overlay');
  const canvas  = document.getElementById('qr-canvas');
  const nameEl  = document.getElementById('qr-session-name');
  const expiryEl = document.getElementById('qr-expiry');

  if (!overlay || !canvas) return;
  overlay.classList.remove('hidden');
  nameEl.textContent = sessionName || 'Session';

  let intervalId = null;
  let secondsLeft = 30;

  async function refreshQR() {
    try {
      // Generate a time-based token: sessionId + floor(epoch/30s)
      const slot = Math.floor(Date.now() / 30000);
      const token = `${sessionId}:${slot}`;
      const payload = JSON.stringify({ session_id: sessionId, token, expires_at: (slot + 1) * 30 });

      await QRCode.toCanvas(canvas, payload, {
        width: 240,
        margin: 2,
        color: { dark: '#000000', light: '#ffffff' },
        errorCorrectionLevel: 'H',
      });
    } catch (e) { console.error('QR generation failed', e); }
  }

  await refreshQR();
  expiryEl.textContent = `Refreshes in 30s`;

  intervalId = setInterval(async () => {
    secondsLeft--;
    expiryEl.textContent = `Refreshes in ${secondsLeft}s`;
    if (secondsLeft <= 0) {
      secondsLeft = 30;
      await refreshQR();
    }
  }, 1000);

  // Close handlers
  const cleanup = () => { clearInterval(intervalId); overlay.classList.add('hidden'); };
  document.getElementById('close-qr').onclick = cleanup;
  document.getElementById('close-qr-btn').onclick = cleanup;
  overlay.onclick = (e) => { if (e.target === overlay) cleanup(); };

  document.getElementById('share-qr-btn').onclick = async () => {
    if (navigator.share) {
      await navigator.share({ title: `Attendance: ${sessionName}`, text: 'Scan to mark attendance' });
    } else {
      const url = canvas.toDataURL();
      const a = document.createElement('a');
      a.href = url; a.download = `qr-${sessionId}.png`; a.click();
    }
  };
}
