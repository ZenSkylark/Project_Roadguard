import { useState } from "react";
import { api, setToken } from "../api/client.js";

export default function Login({ onLogin, onRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const res = await api("/auth/login", {
        method: "POST",
        form: new URLSearchParams({ username, password }),
      });
      if (res.mfa_required) { setMfaToken(res.mfa_token); return; }
      setToken(res.access_token);
      onLogin();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function submitMfa(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const res = await api("/auth/mfa/verify", {
        method: "POST", body: { mfa_token: mfaToken, code },
      });
      setToken(res.access_token);
      onLogin();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <form onSubmit={mfaToken ? submitMfa : submit} className="bg-white rounded-2xl shadow-2xl p-8 w-96">
        <h1 className="text-2xl font-black text-slate-800 text-center">🛡️ ROADGUARD</h1>
        <p className="text-center text-slate-500 text-sm mb-6">Violation Management System</p>
        {!mfaToken ? (
          <>
            <label className="block text-sm font-semibold text-slate-600 mb-1">Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-3" autoFocus />
            <label className="block text-sm font-semibold text-slate-600 mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-4" />
          </>
        ) : (
          <>
            <label className="block text-sm font-semibold text-slate-600 mb-1">Authenticator Code (6 digits)</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 mb-4 font-mono text-center text-xl tracking-[0.5em]" autoFocus />
          </>
        )}
        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
        <button disabled={busy}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-2.5 rounded-lg">
          {busy ? "Signing in..." : mfaToken ? "Verify" : "Sign In"}
        </button>
        <button type="button" onClick={onRegister}
          className="w-full mt-3 text-slate-500 text-sm hover:underline">
          Need an account? Request access
        </button>
      </form>
    </div>
  );
}