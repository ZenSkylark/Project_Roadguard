import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./toastContext.jsx";

export default function MfaModal({ user, onClose, onEnabled }) {
  const [step, setStep] = useState("choose");
  const [method, setMethod] = useState("sms");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const notify = useToast();

  async function sendCode() {
    setBusy(true);
    try {
      const body = { method };
      if (method === "sms") body.phone_number = phone;
      await api("/auth/mfa/setup", { method: "POST", body });
      setStep("verify");
      notify(`Code sent to ${method === "email" ? user.email : phone}`, "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setBusy(true);
    try {
      await api("/auth/mfa/enable", { method: "POST", body: { code } });
      notify("MFA enabled successfully", "success");
      onEnabled();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function resendCode() {
    setBusy(true);
    try {
      const body = { method };
      if (method === "sms") body.phone_number = phone;
      await api("/auth/mfa/setup", { method: "POST", body });
      notify("Code resent", "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        {step === "choose" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-4">Enable Two-Factor Authentication</h3>
            <div className="space-y-3 mb-4">
              <label className="flex items-center gap-2">
                <input type="radio" value="sms" checked={method === "sms"} onChange={(e) => setMethod(e.target.value)} />
                <span>📱 SMS</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" value="email" checked={method === "email"} onChange={(e) => setMethod(e.target.value)} />
                <span>✉️ Email ({user.email})</span>
              </label>
            </div>
            {method === "sms" && (
              <input type="tel" placeholder="Phone number (e.g., 09171234567)" value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 mb-4" />
            )}
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
              <button onClick={sendCode} disabled={busy || (method === "sms" && !phone)}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Code"}
              </button>
            </div>
          </>
        )}

        {step === "verify" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">Verify Code</h3>
            <p className="text-sm text-gray-500 mb-4">
              Enter the 6-digit code sent to {method === "email" ? user.email : phone}
            </p>
            <input type="text" placeholder="6-digit code" value={code}
              onChange={(e) => setCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 mb-4 font-mono text-center text-xl tracking-[0.5em]" />
            <div className="flex gap-2">
              <button onClick={resendCode} disabled={busy}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-50">
                Resend
              </button>
              <button onClick={verify} disabled={busy || code.length !== 6}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Verifying..." : "Verify & Enable"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}