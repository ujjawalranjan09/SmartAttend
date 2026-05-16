// API utility — wraps fetch with auth headers, base URL, error handling
const BASE = (typeof window !== 'undefined' && window.API_BASE) || 'http://localhost:8000/api/v1';

let _token = null;
export const setToken = (t) => { _token = t; };
export const getToken = () => _token;

async function request(method, path, body, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal: opts.signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw { status: res.status, message: err.detail || JSON.stringify(err) };
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  get: (path, opts)      => request('GET',    path, null, opts),
  post: (path, body)     => request('POST',   path, body),
  put: (path, body)      => request('PUT',    path, body),
  patch: (path, body)    => request('PATCH',  path, body),
  delete: (path)         => request('DELETE', path),
};

// ---- Auth endpoints ----
export const authApi = {
  login: (email, password) => request('POST', '/auth/login', null, {}).then(() =>
    fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password }),
    }).then(r => r.json())
  ),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout', {}),
};

// ---- Student endpoints ----
export const studentsApi = {
  list: (params = {}) => api.get('/students?' + new URLSearchParams(params)),
  get: (id) => api.get(`/students/${id}`),
  attendance: (id, params = {}) => api.get(`/students/${id}/attendance?` + new URLSearchParams(params)),
  alerts: (id) => api.get(`/students/${id}/alerts`),
  create: (data) => api.post('/students', data),
  update: (id, data) => api.put(`/students/${id}`, data),
};

// ---- Faculty endpoints ----
export const facultyApi = {
  list: () => api.get('/faculty'),
  get: (id) => api.get(`/faculty/${id}`),
  sessions: (id) => api.get(`/faculty/${id}/sessions`),
  analytics: (id) => api.get(`/faculty/${id}/analytics`),
  create: (data) => api.post('/faculty', data),
  update: (id, data) => api.put(`/faculty/${id}`, data),
};

// ---- Sessions endpoints ----
export const sessionsApi = {
  list: (params = {}) => api.get('/sessions?' + new URLSearchParams(params)),
  get: (id) => api.get(`/sessions/${id}`),
  create: (data) => api.post('/sessions', data),
  start: (id) => api.post(`/sessions/${id}/start`, {}),
  end: (id) => api.post(`/sessions/${id}/end`, {}),
  qr: (id) => api.get(`/sessions/${id}/qr`),
  attendance: (id) => api.get(`/sessions/${id}/attendance`),
  override: (id, studentId, status) => api.post(`/sessions/${id}/override`, { student_id: studentId, status }),
};

// ---- Attendance endpoints ----
export const attendanceApi = {
  mark: (data) => api.post('/attendance/mark', data),
  history: (params = {}) => api.get('/attendance?' + new URLSearchParams(params)),
  summary: (params = {}) => api.get('/attendance/summary?' + new URLSearchParams(params)),
};

// ---- Analytics endpoints ----
export const analyticsApi = {
  student: (id) => api.get(`/analytics/student/${id}`),
  course: (id) => api.get(`/analytics/course/${id}`),
  atRisk: (params = {}) => api.get('/analytics/at-risk?' + new URLSearchParams(params)),
  summary: () => api.get('/analytics/summary'),
};

// ---- Reports endpoints ----
export const reportsApi = {
  generate: (data) => api.post('/reports/generate', data),
  exportCsv: (params = {}) => `${BASE}/reports/export/csv?` + new URLSearchParams({ ...params, token: _token }),
};
