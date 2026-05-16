// SmartAttend API client — wraps fetch with auth, caching, offline queue
const BASE = (typeof __API_URL__ !== 'undefined' ? __API_URL__ : '') || 'http://localhost:8000/api/v1';

let _token = null;
const _cache = new Map();
const _offlineQueue = [];

export function setToken(t) { _token = t; }
export function getToken() { return _token; }
export function clearToken() { _token = null; }

async function request(method, path, body = null, opts = {}) {
  const url = `${BASE}${path}`;
  const headers = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;

  let res;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: opts.signal,
    });
  } catch (err) {
    // Offline — queue write ops, return cached for reads
    if (method === 'GET') {
      const cached = _cache.get(path);
      if (cached) return { ...cached, _fromCache: true };
    } else {
      _offlineQueue.push({ method, path, body, ts: Date.now() });
    }
    throw new Error('network_offline');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail || 'request_failed'), { status: res.status, data: err });
  }

  if (res.status === 204) return null;
  const data = await res.json();

  // Cache successful GETs
  if (method === 'GET') {
    _cache.set(path, data);
    // Mark stale from SW cache header
    data._fromCache = res.headers.get('X-From-Cache') === 'true';
  }

  return data;
}

export const api = {
  get:    (path, opts) => request('GET',    path, null, opts),
  post:   (path, body) => request('POST',   path, body),
  put:    (path, body) => request('PUT',    path, body),
  patch:  (path, body) => request('PATCH',  path, body),
  delete: (path)       => request('DELETE', path),

  // Auth
  login:  (email, password) => request('POST', '/auth/login', { email, password }),
  me:     ()                => request('GET',  '/auth/me'),
  logout: ()                => { clearToken(); },

  // Dashboard
  dashboardStats:    ()           => request('GET', '/analytics/institution/summary'),
  weeklyTrend:       (courseId)   => request('GET', `/analytics/courses/${courseId}/trend`),
  atRisk:            ()           => request('GET', '/analytics/institution/at-risk'),

  // Sessions
  sessions:          (params = '') => request('GET', `/sessions${params}`),
  createSession:     (data)        => request('POST', '/sessions', data),
  startSession:      (id)          => request('POST', `/sessions/${id}/start`),
  endSession:        (id)          => request('POST', `/sessions/${id}/end`),
  sessionQR:         (id)          => request('GET',  `/sessions/${id}/qr`),

  // Attendance
  markAttendance:    (data)        => request('POST', '/attendance/mark', data),
  sessionAttendance: (sessionId)   => request('GET',  `/attendance/sessions/${sessionId}`),
  studentAttendance: (studentId)   => request('GET',  `/students/${studentId}/attendance`),

  // Students
  students:          (params = '') => request('GET', `/students${params}`),
  student:           (id)          => request('GET', `/students/${id}`),
  studentAlerts:     (id)          => request('GET', `/students/${id}/alerts`),
  createStudent:     (data)        => request('POST', '/students', data),
  updateStudent:     (id, data)    => request('PUT',  `/students/${id}`, data),

  // Faculty
  faculty:           (params = '') => request('GET', `/faculty${params}`),
  facultyAnalytics:  (id)          => request('GET', `/faculty/${id}/analytics`),

  // Reports
  exportCsv:         (params)      => `${BASE}/reports/export/csv?${new URLSearchParams(params)}`,
  generateReport:    (data)        => request('POST', '/reports/generate', data),
  attendanceSummary: (params)      => request('GET',  `/reports/summary?${new URLSearchParams(params)}`),

  // Alerts
  alerts:            ()            => request('GET', '/alerts'),

  getOfflineQueue: () => [..._offlineQueue],
  flushQueue: async () => {
    while (_offlineQueue.length > 0) {
      const item = _offlineQueue[0];
      try {
        await request(item.method, item.path, item.body);
        _offlineQueue.shift();
      } catch { break; }
    }
  },
};
