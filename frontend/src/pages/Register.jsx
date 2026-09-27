import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

export default function Register() {
  const [form, setForm] = useState({ username: "", email: "", password: "", position: "viewer" });
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const navigate = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      const res = await api("/accounts/register", { method: "POST", body: form });
      setMsg(`Success! UID: ${res.uid}. You can now log in.`);
      setTimeout(() => navigate("/login"), 2000);
    } catch (e) { setErr(e.message); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-2xl p-8 w-96">
        <h1 className="text-2xl font-black text-slate-800 text-center mb-6">Join Roadguard</h1>
        <input required placeholder="Username (lowercase)" value={form.username} onChange={e => setForm({...form, username: e.target.value})} className="w-full border rounded-lg px-3 py-2 mb-3" />
        <input required type="email" placeholder="Email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="w-full border rounded-lg px-3 py-2 mb-3" />
        <input required type="password" placeholder="Password (8+ chars)" value={form.password} onChange={e => setForm({...form, password: e.target.value})} className="w-full border rounded-lg px-3 py-2 mb-3" />
        <select value={form.position} onChange={e => setForm({...form, position: e.target.value})} className="w-full border rounded-lg px-3 py-2 mb-4">
          <option value="viewer">Viewer</option>
          <option value="officer">Officer</option>
        </select>
        {err && <p className="text-red-600 text-sm mb-3">{err}</p>}
        {msg && <p className="text-green-600 text-sm mb-3">{msg}</p>}
        <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 rounded-lg mb-3">Create Account</button>
        <p className="text-center text-sm text-slate-500">Already have an account? <Link to="/login" className="text-blue-600 font-bold">Sign In</Link></p>
      </form>
    </div>
  );
}