const TOKEN_KEY = "leave_tracker_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    data = null;
  }

  if (!res.ok) {
    const message = (data && data.error) || `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  login: (email, password) => request("POST", "/api/auth/login", { email, password }),
  me: () => request("GET", "/api/auth/me"),
  changePassword: (currentPassword, newPassword) =>
    request("PATCH", "/api/auth/password", { current_password: currentPassword, new_password: newPassword }),

  listEmployees: () => request("GET", "/api/employees"),
  getEmployee: (id) => request("GET", `/api/employees/${id}`),
  createEmployee: (payload) => request("POST", "/api/employees", payload),
  updateEmployee: (id, payload) => request("PATCH", `/api/employees/${id}`, payload),
  deactivateEmployee: (id) => request("DELETE", `/api/employees/${id}`),
  myBalance: () => request("GET", "/api/balance/me"),

  listLeave: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request("GET", `/api/leave${qs ? "?" + qs : ""}`);
  },
  createLeave: (payload) => request("POST", "/api/leave", payload),
  decideLeave: (id, status) => request("PATCH", `/api/leave/${id}/status`, { status }),
  cancelLeave: (id) => request("DELETE", `/api/leave/${id}`),

  getCalendar: (month) => request("GET", `/api/calendar?month=${month}`),

  getSettings: () => request("GET", "/api/settings"),
  updateSettings: (payload) => request("PATCH", "/api/settings", payload),
};
