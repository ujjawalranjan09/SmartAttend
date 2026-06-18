const API_BASE = (import.meta.env.VITE_API_BASE as string) || "/api/v1";

let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
  if (token) localStorage.setItem("smartattend_token", token);
  else localStorage.removeItem("smartattend_token");
}

export function getToken(): string | null {
  if (_token) return _token;
  _token = localStorage.getItem("smartattend_token");
  return _token;
}

export class ApiError extends Error {
  status: number;
  detail?: unknown;
  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

export interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  query?: Record<string, unknown>;
  signal?: AbortSignal;
}

function buildQuery(q?: Record<string, unknown>): string {
  if (!q) return "";
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === null || v === "") continue;
    params.append(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

export async function api<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE}${path}${buildQuery(opts.query)}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(opts.headers || {}),
  };

  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    if (opts.body instanceof FormData) {
      body = opts.body;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }
  }

  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, { method: opts.method, headers, body, signal: opts.signal });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json().catch(() => null) : await res.text().catch(() => null);

  if (!res.ok) {
    const detail = (data && typeof data === "object" && "detail" in (data as any)) ? (data as any).detail : data;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((d: any) => d?.msg || JSON.stringify(d)).join(", ") : res.statusText;
    throw new ApiError(msg || `Request failed: ${res.status}`, res.status, detail);
  }
  return data as T;
}

/* ─── Auth ─── */
export const authApi = {
  login: (email: string, password: string) =>
    api<{ access_token: string; token_type: string }>("/auth/login", { method: "POST", body: { email, password } }),
  me: () => api<{ id: string; email: string; full_name: string; role: string; phone?: string }>("/auth/me"),
  logout: () => api<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  forgotPassword: (email: string) =>
    api<{ ok: boolean }>("/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: (token: string, password: string) =>
    api<{ ok: boolean }>("/auth/reset-password", { method: "POST", body: { token, password } }),
  updateProfile: (data: { full_name?: string; phone?: string }) =>
    api<{ ok: boolean }>("/auth/me", { method: "PATCH", body: data }),
};

/* ─── Sessions ─── */
export const sessionsApi = {
  list: (q?: Record<string, unknown>) => api<any>("/sessions", { query: q }),
  get: (id: string) => api<any>(`/sessions/${id}`),
  attendance: (id: string) => api<any>(`/sessions/${id}/attendance`),
  start: (data: { course_id: string; faculty_id: string; is_online?: boolean; meeting_url?: string; qr_rotation_interval_sec?: number }) =>
    api<any>("/sessions/start", { method: "POST", body: data }),
  end: (id: string) => api<any>(`/sessions/${id}/end`, { method: "POST" }),
  qr: (id: string) => api<any>(`/sessions/${id}/qr`, { method: "POST" }),
};

/* ─── Attendance ─── */
export const attendanceApi = {
  history: (q?: Record<string, unknown>) => api<any>("/attendance", { query: q }),
  mark: (data: { session_id: string; qr_token: string }) =>
    api<any>("/attendance/mark", { method: "POST", body: data }),
};

/* ─── Analytics ─── */
export const analyticsApi = {
  summary: () => api<any>("/analytics/summary"),
  student: (id?: string) => api<any>(id ? `/analytics/student/${id}` : "/analytics/student/me"),
  atRisk: (q?: Record<string, unknown>) => api<any>("/analytics/at-risk", { query: q }),
};

/* ─── Students ─── */
export const studentsApi = {
  list: (q?: Record<string, unknown>) => api<any>("/students", { query: q }),
  get: (id: string) => api<any>(`/students/${id}`),
  create: (data: any) => api<any>("/students/", { method: "POST", body: data }),
  update: (id: string, data: any) => api<any>(`/students/${id}`, { method: "PUT", body: data }),
  remove: (id: string) => api<any>(`/students/${id}`, { method: "DELETE" }),
};

/* ─── Alerts ─── */
export const alertsApi = {
  list: (q?: Record<string, unknown>) => api<any>("/alerts", { query: q }),
};

/* ─── Notifications ─── */
export const notificationsApi = {
  list: (q?: Record<string, unknown>) => api<any>("/notifications", { query: q }),
  markRead: (id: string) => api<any>(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => api<any>("/notifications/read-all", { method: "POST" }),
};

/* ─── Display ─── */
export const displayApi = {
  getToken: (sessionId: string) =>
    api<{ display_token: string }>(`/sessions/${sessionId}/display-token`, { method: "POST" }),
};

/* ─── Profile & Goals ─── */
export const profileApi = {
  get: () => api<any>("/profile/me"),
  create: (data: any) => api<any>("/profile/me", { method: "POST", body: data }),
  update: (data: any) => api<any>("/profile/me", { method: "PATCH", body: data }),
};

export const goalsApi = {
  list: () => api<any>("/goals"),
  create: (data: any) => api<any>("/goals", { method: "POST", body: data }),
  update: (id: string, data: any) => api<any>(`/goals/${id}`, { method: "PATCH", body: data }),
  delete: (id: string) => api<any>(`/goals/${id}`, { method: "DELETE" }),
  updateProgress: (id: string, data: { completed_hours: number; milestone_index?: number }) =>
    api<any>(`/goals/${id}/progress`, { method: "POST", body: data }),
};

/* ─── Daily Plan ─── */
export const dailyPlanApi = {
  getFreePeriods: (date: string) => api<any>(`/daily-plan/free-periods`, { query: { date } }),
  getRoutine: (date: string) => api<any>(`/daily-plan/routine`, { query: { date } }),
  invalidateRoutine: () => api<any>("/daily-plan/routine/invalidate", { method: "POST" }),
};

/* ─── Faces ─── */
export const facesApi = {
  status: () => api<any>("/faces/status"),
  enroll: (image: Blob) => {
    const fd = new FormData();
    fd.append("image", image, "enroll.jpg");
    return api<any>("/faces/enroll", { method: "POST", body: fd });
  },
  delete: () => api<any>("/faces/enroll", { method: "DELETE" }),
};

/* ─── Reports ─── */
export const reportsApi = {
  generate: (institution_id: string, data: any) =>
    api<any>("/reports/generate", { method: "POST", body: { institution_id, ...data } }),
  exportCsv: (institution_id: string) =>
    `${API_BASE}/reports/export/csv?institution_id=${institution_id}`,
  status: (job_id: string) => api<any>(`/reports/status/${job_id}`),
  downloadUrl: (job_id: string) => `${API_BASE}/reports/download/${job_id}`,
};

/* ─── Faculty ─── */
export const facultyApi = {
  list: (params?: { search?: string; department_id?: string; page?: number; page_size?: number }) =>
    api<any>(`/faculty/?${params ? new URLSearchParams(params as any).toString() : ""}`),
  get: (id: string) => api<any>(`/faculty/${id}`),
  create: (data: any) => api<any>("/faculty/", { method: "POST", body: data }),
  update: (id: string, data: any) => api<any>(`/faculty/${id}`, { method: "PUT", body: data }),
  remove: (id: string) => api<any>(`/faculty/${id}`, { method: "DELETE" }),
};

/* ─── Courses (needed for session start dialog) ─── */
export const coursesApi = {
  list: () => api<any>("/courses/"),
};
