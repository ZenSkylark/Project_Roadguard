import { useState } from "react";
import { api, setToken } from "../api/client.js";
import ForgotPasswordModal from "../components/ForgotPasswordModal.jsx";

export default function Login({ onLogin, onRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState(null);
  const [mfaCode, setMfaCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showForgot, setShowForgot] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const form = new URLSearchParams();
      form.append("username", username);
      form.append("password", password);
      const res = await fetch("/api/auth/login", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Login failed");
      }
      const data = await res.json();
      if (data.mfa_required) {
        setMfaToken(data.mfa_token);
      } else {
        setToken(data.access_token);
        await onLogin();
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaVerify(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api("/auth/mfa/verify-login", {
        method: "POST",
        body: { mfa_token: mfaToken, code: mfaCode },
      });
      setToken(data.access_token);
      await onLogin();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleResendMfa() {
    setError("");
    setLoading(true);
    try {
      await api("/auth/mfa/resend", {
        method: "POST",
        body: { mfa_token: mfaToken, code: "000000" },
      });
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-blue-900">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-96">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🛡️</div>
          <h1 className="text-2xl font-bold text-gray-800">Roadguard</h1>
          <p className="text-sm text-gray-500">Sign in to your account</p>
        </div>

        {!mfaToken ? (
          <form onSubmit={handleSubmit}>
            <input type="text" placeholder="Username" value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-3" required />
            <input type="password" placeholder="Password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-3" required />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full bg-blue-600 text-white font-semibold py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {loading ? "Signing in..." : "Sign In"}
            </button>
            <div className="mt-4 text-center">
              <button type="button" onClick={() => setShowForgot(true)}
                className="text-sm text-blue-600 hover:underline">
                Forgot Password?
              </button>
            </div>
            <div className="mt-4 text-center text-sm text-gray-500">
              Don't have an account?{" "}
              <button type="button" onClick={onRegister} className="text-blue-600 hover:underline">
                Register
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleMfaVerify}>
            <p className="text-sm text-gray-600 mb-3 text-center">
              Enter the 6-digit code sent to your device
            </p>
            <input type="text" placeholder="6-digit code" value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 mb-3 font-mono text-center text-xl tracking-[0.5em]"
              required />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <div className="flex gap-2 mb-3">
              <button type="button" onClick={handleResendMfa} disabled={loading}
                className="flex-1 border border-gray-300 text-gray-600 font-semibold py-2 rounded-lg hover:bg-gray-100 disabled:opacity-50">
                Resend
              </button>
              <button type="submit" disabled={loading || mfaCode.length !== 6}
                className="flex-1 bg-blue-600 text-white font-semibold py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {loading ? "Verifying..." : "Verify"}
              </button>
            </div>
            <button type="button" onClick={() => setMfaToken(null)}
              className="w-full text-sm text-gray-500 hover:underline">
              Back to login
            </button>
          </form>
        )}
      </div>

      {showForgot && (
        <ForgotPasswordModal
          onClose={() => setShowForgot(false)}
          onSuccess={() => {
            setShowForgot(false);
            setUsername("");
            setPassword("");
          }}
        />
      )}
    </div>
  );
}