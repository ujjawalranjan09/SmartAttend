import { showToast } from '../utils/toast.js';
import { facesApi } from '../utils/api.js';

export async function renderSettings(container, state) {
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
    </div>

    <!-- Face Enrollment Card -->
    ${user.role === 'student' ? `
    <div class="card" style="margin-top:var(--space-5)">
      <div class="card-header">
        <div><div class="card-title">Face Recognition</div><div class="card-subtitle">Enroll your face for biometric attendance verification</div></div>
        <div id="face-status-badge"></div>
      </div>
      <div id="face-enrollment-area" style="display:flex;flex-direction:column;align-items:center;gap:var(--space-4);padding:var(--space-6) 0">
        <div id="face-status-message">Loading face enrollment status...</div>
        <div id="face-preview" style="display:none;width:200px;height:200px;border-radius:50%;overflow:hidden;border:3px solid var(--color-primary)">
          <video id="face-video" style="width:100%;height:100%;object-fit:cover" autoplay playsinline></video>
          <canvas id="face-canvas" style="display:none"></canvas>
        </div>
        <div id="face-actions" style="display:flex;gap:var(--space-3)">
          <button class="btn btn-primary" id="enroll-face-btn" style="display:none"><i data-lucide="camera"></i> Enroll Face</button>
          <button class="btn btn-danger" id="remove-face-btn" style="display:none"><i data-lucide="trash-2"></i> Remove Enrollment</button>
          <button class="btn btn-secondary" id="capture-face-btn" style="display:none"><i data-lucide="camera"></i> Capture Photo</button>
          <button class="btn btn-ghost" id="cancel-face-btn" style="display:none"><i data-lucide="x"></i> Cancel</button>
        </div>
      </div>
    </div>
    ` : ''}`;

  // Wire up existing handlers
  document.getElementById('profile-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    showToast('Profile updated', 'success');
  });
  document.getElementById('change-pw-btn')?.addEventListener('click', () => showToast('Password change email sent', 'info'));
  document.getElementById('totp-btn')?.addEventListener('click', () => showToast('2FA setup coming soon', 'info'));

  // Face enrollment logic
  if (user.role === 'student') {
    await initFaceEnrollment(state);
  }
}

let faceStream = null;

async function initFaceEnrollment(state) {
  const statusMsg = document.getElementById('face-status-message');
  const badge = document.getElementById('face-status-badge');
  const enrollBtn = document.getElementById('enroll-face-btn');
  const removeBtn = document.getElementById('remove-face-btn');
  const captureBtn = document.getElementById('capture-face-btn');
  const cancelBtn = document.getElementById('cancel-face-btn');
  const preview = document.getElementById('face-preview');
  const video = document.getElementById('face-video');

  try {
    const status = await facesApi.status();
    if (status.enrolled) {
      statusMsg.innerHTML = `<i data-lucide="check-circle" style="color:var(--color-success);width:24px;height:24px"></i> Face enrolled on ${new Date(status.enrolled_at).toLocaleDateString()}`;
      badge.innerHTML = '<span class="badge badge-present">Enrolled</span>';
      enrollBtn.style.display = 'none';
      removeBtn.style.display = 'inline-flex';
      preview.style.display = 'none';
    } else {
      statusMsg.innerHTML = '<span style="color:var(--color-text-muted)">No face enrolled. Click "Enroll Face" to get started.</span>';
      badge.innerHTML = '<span class="badge badge-muted">Not Enrolled</span>';
      enrollBtn.style.display = 'inline-flex';
      removeBtn.style.display = 'none';
    }
  } catch (e) {
    statusMsg.innerHTML = '<span style="color:var(--color-error)">Failed to check enrollment status</span>';
  }

  enrollBtn?.addEventListener('click', async () => {
    try {
      faceStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      video.srcObject = faceStream;
      preview.style.display = 'block';
      enrollBtn.style.display = 'none';
      captureBtn.style.display = 'inline-flex';
      cancelBtn.style.display = 'inline-flex';
      statusMsg.innerHTML = 'Position your face in the frame and click "Capture Photo"';
    } catch (e) {
      showToast('Camera access denied. Please grant permission.', 'error');
    }
  });

  captureBtn?.addEventListener('click', async () => {
    const canvas = document.getElementById('face-canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      statusMsg.innerHTML = 'Uploading and processing face...';
      captureBtn.disabled = true;
      try {
        await facesApi.enroll(blob);
        showToast('Face enrolled successfully!', 'success');
        statusMsg.innerHTML = `<i data-lucide="check-circle" style="color:var(--color-success);width:24px;height:24px"></i> Face enrolled successfully`;
        badge.innerHTML = '<span class="badge badge-present">Enrolled</span>';
        enrollBtn.style.display = 'none';
        removeBtn.style.display = 'inline-flex';
        captureBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
        preview.style.display = 'none';
        stopFaceStream();
      } catch (e) {
        showToast(e?.message || 'Face enrollment failed', 'error');
        statusMsg.innerHTML = '<span style="color:var(--color-error)">Enrollment failed. Please try again.</span>';
      }
      captureBtn.disabled = false;
    }, 'image/jpeg', 0.85);
  });

  removeBtn?.addEventListener('click', async () => {
    if (!confirm('Remove your face enrollment? This cannot be undone.')) return;
    try {
      await facesApi.delete();
      showToast('Face enrollment removed', 'info');
      statusMsg.innerHTML = '<span style="color:var(--color-text-muted)">No face enrolled. Click "Enroll Face" to get started.</span>';
      badge.innerHTML = '<span class="badge badge-muted">Not Enrolled</span>';
      enrollBtn.style.display = 'inline-flex';
      removeBtn.style.display = 'none';
    } catch (e) {
      showToast('Failed to remove enrollment', 'error');
    }
  });

  cancelBtn?.addEventListener('click', () => {
    stopFaceStream();
    preview.style.display = 'none';
    enrollBtn.style.display = 'inline-flex';
    captureBtn.style.display = 'none';
    cancelBtn.style.display = 'none';
    statusMsg.innerHTML = '<span style="color:var(--color-text-muted)">No face enrolled. Click "Enroll Face" to get started.</span>';
  });
}

function stopFaceStream() {
  if (faceStream) {
    faceStream.getTracks().forEach(t => t.stop());
    faceStream = null;
  }
}