// QR Code utilities — generation, geo-fencing, and BLE/WiFi proximity
export async function renderQR(canvasEl, data) {
  if (typeof QRCode === 'undefined') return;
  await QRCode.toCanvas(canvasEl, data, {
    width: 240,
    margin: 1,
    color: { dark: '#000000', light: '#ffffff' },
    errorCorrectionLevel: 'H',
  });
}

// Dynamic QR with rotating token (anti-sharing)
export function startDynamicQR(canvasEl, sessionId, getTokenFn, intervalMs = 30000) {
  let timer = null;
  async function refresh() {
    try {
      const qrData = await getTokenFn(sessionId);
      const payload = JSON.stringify({ session_id: sessionId, token: qrData.token, exp: qrData.expires_at });
      await renderQR(canvasEl, payload);
    } catch (e) { console.warn('QR refresh failed', e); }
  }
  refresh();
  timer = setInterval(refresh, intervalMs);
  return () => clearInterval(timer);
}

// Geo-fence check — returns true if user is within radius meters of target
export async function checkGeoFence(targetLat, targetLng, radiusMeters = 100) {
  return new Promise((resolve) => {
    if (!navigator.geolocation) { resolve({ allowed: false, reason: 'no_gps' }); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const dist = haversine(pos.coords.latitude, pos.coords.longitude, targetLat, targetLng);
        resolve({
          allowed: dist <= radiusMeters,
          distance: Math.round(dist),
          accuracy: pos.coords.accuracy,
          reason: dist > radiusMeters ? 'outside_fence' : 'ok',
        });
      },
      (err) => resolve({ allowed: false, reason: 'gps_error', error: err.message }),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );
  });
}

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// WiFi BSSID detection (Android Chrome, limited support)
export async function getWifiBSSID() {
  if (!navigator.connection) return null;
  return { type: navigator.connection.effectiveType, downlink: navigator.connection.downlink };
}

// BLE proximity scan stub (requires HTTPS + user permission)
export async function scanBLEProximity(serviceUUID) {
  if (!navigator.bluetooth) return { supported: false };
  try {
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ services: [serviceUUID] }],
      optionalServices: ['battery_service'],
    });
    return { supported: true, deviceId: device.id, name: device.name };
  } catch (e) {
    return { supported: true, error: e.message };
  }
}
