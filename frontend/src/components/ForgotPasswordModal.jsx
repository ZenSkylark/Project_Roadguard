import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./toastContext.jsx";

export default function ForgotPasswordModal({ onClose, onSuccess }) {
  const [step, setStep] = useState("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const notify = useToast();

  async function sendCode() {
    setBusy(true);
    try {
      await api("/auth/forgot-password", { method: "POST", body: { email } });
      setStep("verify");
      notify("Reset code sent to your email", "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (password !== confirm) {
      notify("Passwords do not match", "error");
      return;
    }
    if (password.length < 8) {
      notify("Password must be at least 8 characters", "error");
      return;
    }
    
    setBusy(true);
    try {
      await api("/auth/reset-password", {
        method: "POST",
        body: { email, code, new_password: password }
      });
      notify("Password reset successful", "success");
      onSuccess();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        {step === "email" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">Forgot Password</h3>
            <p className="text-sm text-gray-500 mb-4">
              Enter your email to receive a password reset code
            </p>
            <input type="email" placeholder="Email address" value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-4" />
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
              <button onClick={sendCode} disabled={busy || !email}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Code"}
              </button>
            </div>
          </>
        )}

        {step === "verify" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">Reset Password</h3>
            <p className="text-sm text-gray-500 mb-4">
              Enter the code sent to {email}
            </p>
            <input type="text" placeholder="6-digit code" value={code}
              onChange={(e) => setCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 mb-3 font-mono text-center text-xl tracking-[0.5em]" />
            <input type="password" placeholder="New password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-3" />
            <input type="password" placeholder="Confirm password" value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-4" />
            <div className="flex gap-2">
              <button onClick={() => setStep("email")} className="px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Back
              </button>
              <button onClick={reset} disabled={busy || !code || !password || !confirm}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Resetting..." : "Reset Password"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}