import { useState } from "react";
import { api } from "../api/client.js";

export default function Register({ onDone }) {
  const [form, setForm] = useState({ uid: "", username: "", email: "", password: "", position: "viewer" });
  const [error, setError] = useState("");
  const [ok, setOk] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const body = { username: form.username, email: form.email,
                     password: form.password, position: form.position };
      if (form.uid) body.uid = form.uid;
      setOk(await api("/accounts/register", { method: "POST", body }));
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-2xl p-8 w-96">
        <h1 className="text-2xl font-black text-slate-800 text-center">🛡️ ROADGUARD</h1>
        <p className="text-center text-slate-500 text-sm mb-6">Request an account</p>
        {ok ? (
          <div className="text-center">
            <p className="text-emerald-600 font-semibold mb-2">Account created!</p>
            <p className="text-sm text-slate-500 mb-4">
              Your ID Number: <span className="font-mono font-bold">{ok.uid}</span>
            </p>
            <button onClick={onDone}
              className="w-full bg-blue-600 text-white font-bold py-2.5 rounded-lg hover:bg-blue-700">
              Back to Login
            </button>
          </div>
        ) : (
          <>
            <input placeholder="ID Number (optional, e.g. RG-2026-0002)" value={form.uid}
              onChange={set("uid")} className="w-full border rounded-lg px-3 py-2 mb-2 font-mono text-sm" />
            <input placeholder="Username" value={form.username}
              onChange={set("username")} className="w-full border rounded-lg px-3 py-2 mb-2" />
            <input placeholder="Email" value={form.email}
              onChange={set("email")} className="w-full border rounded-lg px-3 py-2 mb-2" />
            <input type="password" placeholder="Password (8+ chars, upper, lower, number)"
              value={form.password} onChange={set("password")} className="w-full border rounded-lg px-3 py-2 mb-2" />
            <select value={form.position} onChange={set("position")}
              className="w-full border rounded-lg px-3 py-2 mb-4">
              <option value="viewer">Viewer — read-only</option>
              <option value="officer">Officer — can process violations</option>
            </select>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <button disabled={busy}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-2.5 rounded-lg">
              {busy ? "Creating..." : "Create Account"}
            </button>
            <button type="button" onClick={onDone}
              className="w-full mt-2 text-slate-500 text-sm hover:underline">Back to login</button>
          </>
        )}
      </form>
    </div>
  );
}