// API utility — wraps fetch with auth headers, base URL, error handling
const BASE = (typeof window !== 'undefined' && window.API_BASE) || 'http://localhost:8000/api/v1';

/** Server origin without /api/v1 suffix (for raw fetch in app.js). */
export function getApiOrigin() {
  const base = (typeof window !== 'undefined' && window.API_BASE) || 'http://localhost:8000/api/v1';
  return base.replace(/\/api\/v\d+\/?$/, '') || 'http://localhost:8000';
}

export function formatApiError(detail) {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join(', ');
  }
  return String(detail);
}

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
    throw {
      status: res.status,
      message: formatApiError(err.detail) || JSON.stringify(err),
    };
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
  login: async (email, password) => {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw {
        status: res.status,
        message: formatApiError(data.detail) || 'Login failed',
      };
    }
    return data;
  },
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout', {}),
  register: (data) => api.post('/auth/register', data),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => api.post('/auth/reset-password', { token, new_password: newPassword }),
  changePassword: (currentPassword, newPassword) => api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
  verifyRegistration: (token) => api.post('/auth/verify-registration', { token }),
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

// ---- Faces endpoints ----
export const facesApi = {
  enroll: (imageFile) => {
    const formData = new FormData();
    formData.append('image', imageFile);
    const headers = {};
    if (_token) headers['Authorization'] = `Bearer ${_token}`;
    return fetch(`${BASE}/faces/enroll`, {
      method: 'POST',
      headers,
      body: formData,
    }).then(r => r.ok ? r.json() : r.json().then(e => { throw { status: r.status, message: e.detail }; }));
  },
  status: () => api.get('/faces/status'),
  delete: () => api.delete('/faces/enrollment'),
};

// ---- Notifications endpoints ----
export const notificationsApi = {
  list: (params = {}) => api.get('/notifications?' + new URLSearchParams(params)),
  markRead: (id) => api.patch(`/notifications/${id}/read`, {}),
  markAllRead: () => api.patch('/notifications/read-all', {}),
};

// ---- Alerts endpoints ----
export const alertsApi = {
  list: (params = {}) => api.get('/alerts?' + new URLSearchParams(params)),
  get: (id) => api.get(`/alerts/${id}`),
  resolve: (id) => api.patch(`/alerts/${id}/resolve`, {}),
};

// ---- Student Profile endpoints ----
export const profileApi = {
  get: () => api.get('/students/me/profile'),
  create: (data) => api.post('/students/me/profile', data),
  update: (data) => api.put('/students/me/profile', data),
};

// ---- Student Goals endpoints ----
export const goalsApi = {
  list: (params = {}) => api.get('/students/me/goals?' + new URLSearchParams(params)),
  create: (data) => api.post('/students/me/goals', data),
  get: (id) => api.get(`/students/me/goals/${id}`),
  update: (id, data) => api.put(`/students/me/goals/${id}`, data),
  updateProgress: (id, data) => api.patch(`/students/me/goals/${id}/progress`, data),
  delete: (id) => api.delete(`/students/me/goals/${id}`),
  listForStudent: (studentId, params = {}) => api.get(`/students/${studentId}/goals?` + new URLSearchParams(params)),
};

// ---- Daily Plan endpoints (free periods + routine) ----
export const dailyPlanApi = {
  getFreePeriods: (date) => api.get('/students/me/free-periods?' + new URLSearchParams(date ? { target_date: date } : {})),
  getFreePeriodsWeek: (weekStart) => api.get('/students/me/free-periods/week?' + new URLSearchParams({ week_start: weekStart })),
  getRoutine: (date) => api.get('/students/me/routine?' + new URLSearchParams(date ? { target_date: date } : {})),
  getRoutineWeekly: (weekStart) => api.get('/students/me/routine/weekly?' + new URLSearchParams({ week_start: weekStart })),
  invalidateRoutine: () => api.post('/students/me/routine/invalidate', {}),
};

// ---- Classroom Display endpoints ----
export const displayApi = {
  getToken: (sessionId) => api.get(`/sessions/${sessionId}/display-token`),
  getSession: (sessionId, token) => api.get(`/display/session/${sessionId}?` + new URLSearchParams({ token })),
};
