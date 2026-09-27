import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";

export default function ForgotPassword() {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPw, setNewPw] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function requestReset(e) {
    e.preventDefault();
    try {
      await api("/auth/forgot-password", { method: "POST", body: { email } });
      setMsg("If the email exists, a token was sent to the backend console.");
      setStep(2);
    } catch (e) { setErr(e.message); }
  }

  async function submitReset(e) {
    e.preventDefault();
    try {
      await api("/auth/reset-password", { method: "POST", body: { token, new_password: newPw } });
      setMsg("Password reset! Redirecting to login...");
      setTimeout(() => window.location.href = "/login", 2000);
    } catch (e) { setErr(e.message); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <form onSubmit={step === 1 ? requestReset : submitReset} className="bg-white rounded-2xl shadow-2xl p-8 w-96">
        <h1 className="text-2xl font-black text-slate-800 text-center mb-6">Reset Password</h1>
        {step === 1 ? (
          <input required type="email" placeholder="Your Email" value={email} onChange={e => setEmail(e.target.value)} className="w-full border rounded-lg px-3 py-2 mb-4" />
        ) : (
          <>
            <input required placeholder="Reset Token" value={token} onChange={e => setToken(e.target.value)} className="w-full border rounded-lg px-3 py-2 mb-3 font-mono" />
            <input required type="password" placeholder="New Password" value={newPw} onChange={e => setNewPw(e.target.value)} className="w-full border rounded-lg px-3 py-2 mb-4" />
          </>
        )}
        {err && <p className="text-red-600 text-sm mb-3">{err}</p>}
        {msg && <p className="text-green-600 text-sm mb-3">{msg}</p>}
        <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 rounded-lg mb-3">
          {step === 1 ? "Send Reset Token" : "Reset Password"}
        </button>
        <p className="text-center text-sm text-slate-500"><Link to="/login" className="text-blue-600 font-bold">Back to Login</Link></p>
      </form>
    </div>
  );
}