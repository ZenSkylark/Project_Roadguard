import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./toastContext.jsx";

export default function VerifyPhoneModal({ user, onClose, onVerified }) {
  const [step, setStep] = useState(user.phone_number ? "send" : "input");
  const [phone, setPhone] = useState(user.phone_number || "");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [exhausted, setExhausted] = useState(false);
  const notify = useToast();

  async function savePhoneAndSendCode() {
    if (!phone || phone.length < 10) {
      notify("Please enter a valid phone number", "error");
      return;
    }
    setBusy(true);
    try {
      await api("/accounts/me", { method: "PATCH", body: { phone_number: phone } });
      await api("/auth/phone/send-verify", { method: "POST", body: { phone_number: phone } });
      setStep("verify");
      setCode("");
      setExhausted(false);
      notify(`Code sent to ${phone}`, "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function sendCodeToExisting() {
    setBusy(true);
    try {
      await api("/auth/phone/send-verify", { method: "POST", body: { phone_number: user.phone_number } });
      setStep("verify");
      setCode("");
      setExhausted(false);
      notify(`Code sent to ${user.phone_number}`, "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setBusy(true);
    try {
      await api("/auth/phone/confirm-verify", {
        method: "POST",
        body: { phone_number: phone || user.phone_number, code }
      });
      notify("Phone verified successfully!", "success");
      onVerified();
    } catch (e) {
      notify(e.message, "error");
      if (/too many|request a new code/i.test(e.message)) setExhausted(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        {step === "input" ? (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📱 Add Phone Number</h3>
            <p className="text-sm text-gray-600 mb-4">Enter your phone number to receive a verification code.</p>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="09XXXXXXXXX"
              className="w-full border rounded-lg px-3 py-2 mb-4 font-mono" autoFocus />
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={savePhoneAndSendCode} disabled={busy || phone.length < 10}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Saving..." : "Send Code"}
              </button>
            </div>
          </>
        ) : step === "send" ? (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📱 Verify Phone</h3>
            <p className="text-sm text-gray-600 mb-4">
              We'll send a verification code to <strong>{user.phone_number}</strong>.
            </p>
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={sendCodeToExisting} disabled={busy}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Code"}
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📱 Enter Verification Code</h3>
            <p className="text-sm text-gray-500 mb-4">Check your phone for the 6-digit code.</p>
            {exhausted && (
              <div className="mb-3 p-3 bg-amber-50 border border-amber-300 rounded-lg text-amber-700 text-sm font-semibold">
                ⚠️ You ran out of attempts for this code. Press Resend to get a new one.
              </div>
            )}
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
              placeholder="6-digit code" disabled={exhausted}
              className={`w-full border rounded-lg px-3 py-2 mb-4 font-mono text-center text-xl tracking-[0.5em] ${
                exhausted ? "border-amber-400 bg-amber-50 text-amber-700" : ""
              }`}
              autoFocus />
            <div className="flex gap-2">
              <button onClick={() => setStep(user.phone_number ? "send" : "input")}
                className="flex-1 px-3 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 text-sm">
                Back
              </button>
              <button onClick={() => (user.phone_number ? sendCodeToExisting() : savePhoneAndSendCode())} disabled={busy}
                className="flex-1 px-3 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-50 text-sm">
                Resend
              </button>
              <button onClick={verify} disabled={busy || code.length !== 6 || exhausted}
                className="flex-1 px-3 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50 text-sm">
                {busy ? "..." : "Verify"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}