const BASE = "/api";
let token = localStorage.getItem("rg_token");

export function setToken(t) {
  token = t;
  if (t) localStorage.setItem("rg_token", t);
  else localStorage.removeItem("rg_token");
}

export function getToken() {
  return token;
}

export function clearToken() {
  setToken(null);
}

// 401 messages that mean "wrong code", NOT "session expired"
const OTP_DETAILS = [
  "invalid otp", "invalid code", "invalid verification code",
  "otp expired", "verification code expired", "too many",
  "attempts remaining", "request a new code", "no otp issued",
];

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const isForm = options.body instanceof FormData;
  if (options.body && !isForm) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(BASE + path, {
    method: options.method || "GET",
    headers,
    body: isForm ? options.body : options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || "");
    const lower = detail.toLowerCase();
    const isOtpError = OTP_DETAILS.some((k) => lower.includes(k));

    // Only kill the session for REAL auth failures (bad/expired token)
    if (res.status === 401 && !isOtpError && token) {
      clearToken();
      window.location.href = "/";
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}