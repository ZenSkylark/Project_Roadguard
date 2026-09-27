import { useState } from "react";
import { api } from "../api/client.js";

export default function MfaModal({ onClose, onEnabled }) {
  const [step, setStep] = useState("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendCode() {
    setBusy(true); setError("");
    try {
      await api("/auth/mfa/setup", { method: "POST", body: { phone_number: phone } });
      setStep("code");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function enable() {
    setBusy(true); setError("");
    try {
      await api("/auth/mfa/enable", { method: "POST", body: { code } });
      onEnabled();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        <h3 className="text-lg font-bold text-gray-800 mb-1">📱 Two-Factor Authentication</h3>
        {step === "phone" ? (
          <>
            <p className="text-sm text-gray-500 mb-4">
              We will text a 6-digit verification code to your phone.
            </p>
            <input value={phone} onChange={(e) => setPhone(e.target.value)}
              placeholder="09XXXXXXXXX"
              className="w-full border rounded-lg px-3 py-2 font-mono" />
          </>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-4">
              Enter the 6-digit code sent to <span className="font-mono font-bold">{phone}</span>.
              <br />(Dev mode: the code prints in the backend console.)
            </p>
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 font-mono text-center text-xl tracking-[0.5em]" />
          </>
        )}
        {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
        <div className="flex gap-2 mt-4">
          <button onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
            Cancel
          </button>
          {step === "phone" ? (
            <button onClick={sendCode} disabled={busy || !phone}
              className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
              {busy ? "Sending..." : "Send Code"}
            </button>
          ) : (
            <button onClick={enable} disabled={busy || code.length !== 6}
              className="flex-1 px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-50">
              {busy ? "Verifying..." : "Enable MFA"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}