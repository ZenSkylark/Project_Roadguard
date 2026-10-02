import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./toastContext.jsx";

export default function MfaModal({ user, onClose, onEnabled }) {
  const [step, setStep] = useState("choose");
  const [method, setMethod] = useState(null);
  const [phone, setPhone] = useState(user.phone_number || "");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [exhausted, setExhausted] = useState(false);
  const notify = useToast();

  const hasEmail = !!user.email;

  async function startSetup(selectedMethod) {
    setMethod(selectedMethod);
    if (selectedMethod === "sms" && !phone) {
      setStep("phone_input");
      return;
    }
    setBusy(true);
    try {
      const body = { method: selectedMethod };
      if (selectedMethod === "sms") body.phone_number = phone;
      await api("/auth/mfa/setup", { method: "POST", body });
      setStep("verify");
      setCode("");
      setExhausted(false);
      notify(`Code sent via ${selectedMethod === "email" ? "✉️ Email" : "📱 SMS"}`, "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function savePhoneAndContinue() {
    if (!phone || phone.length < 10) {
      notify("Please enter a valid phone number", "error");
      return;
    }
    setBusy(true);
    try {
      await api("/accounts/me", { method: "PATCH", body: { phone_number: phone } });
      await api("/auth/mfa/setup", { method: "POST", body: { method: "sms", phone_number: phone } });
      setStep("verify");
      setCode("");
      setExhausted(false);
      notify("Code sent via 📱 SMS", "success");
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
      notify("MFA enabled successfully!", "success");
      onEnabled();
    } catch (e) {
      notify(e.message, "error");
      if (/too many|request a new code/i.test(e.message)) setExhausted(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-[420px] shadow-2xl">

        {step === "choose" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">🔐 Enable Two-Factor Authentication</h3>
            <p className="text-sm text-gray-600 mb-4">Choose your preferred verification method:</p>
            <div className="space-y-3 mb-4">
              <button onClick={() => startSetup("email")}
                disabled={!hasEmail || user.email_verified === false || busy}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border-2 transition-all ${
                  hasEmail && user.email_verified !== false
                    ? "border-blue-200 hover:border-blue-500 hover:bg-blue-50 hover:shadow-md"
                    : "border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed"
                }`}>
                <span className="text-3xl">✉️</span>
                <div className="text-left flex-1">
                  <div className="font-bold text-gray-800">Email</div>
                  <div className="text-xs text-gray-500">
                    {hasEmail && user.email_verified !== false
                      ? `Send code to ${user.email}`
                      : "Email not verified — verify first in Profile"}
                  </div>
                </div>
                {hasEmail && user.email_verified !== false && (
                  <span className="text-xs bg-emerald-100 text-emerald-600 px-2 py-0.5 rounded-full">Available</span>
                )}
              </button>

              <button onClick={() => startSetup("sms")} disabled={busy}
                className="w-full flex items-center gap-4 p-4 rounded-xl border-2 border-blue-200 hover:border-blue-500 hover:bg-blue-50 hover:shadow-md transition-all">
                <span className="text-3xl">📱</span>
                <div className="text-left flex-1">
                  <div className="font-bold text-gray-800">SMS</div>
                  <div className="text-xs text-gray-500">
                    {user.phone_number ? `Send code to ${user.phone_number}` : "Enter your phone number to receive codes"}
                  </div>
                </div>
                <span className="text-xs bg-emerald-100 text-emerald-600 px-2 py-0.5 rounded-full">Available</span>
              </button>
            </div>
            <button onClick={onClose} className="w-full text-sm text-gray-500 hover:underline">Cancel</button>
          </>
        )}

        {step === "phone_input" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📱 Enter Phone Number</h3>
            <p className="text-sm text-gray-600 mb-4">We'll send a verification code to this number.</p>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="09XXXXXXXXX"
              className="w-full border rounded-lg px-3 py-2 mb-4 font-mono text-lg" autoFocus />
            <div className="flex gap-2">
              <button onClick={() => setStep("choose")} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Back</button>
              <button onClick={savePhoneAndContinue} disabled={busy || phone.length < 10}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Code"}
              </button>
            </div>
          </>
        )}

        {step === "verify" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">
              {method === "email" ? "✉️" : "📱"} Enter Verification Code
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Check your {method === "email" ? "email inbox" : "phone"} for the 6-digit code.
            </p>
            {exhausted && (
              <div className="mb-3 p-3 bg-amber-50 border border-amber-300 rounded-lg text-amber-700 text-sm font-semibold">
                ⚠️ You ran out of attempts for this code. Press Resend to get a new one.
              </div>
            )}
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} placeholder="000000"
              disabled={exhausted}
              className={`w-full border rounded-lg px-3 py-3 mb-4 font-mono text-center text-2xl tracking-[0.5em] ${
                exhausted ? "border-amber-400 bg-amber-50 text-amber-700" : ""
              }`}
              autoFocus />
            <div className="flex gap-2">
              <button onClick={() => { setStep("choose"); setCode(""); setExhausted(false); }}
                className="flex-1 px-3 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 text-sm">
                Back
              </button>
              <button onClick={() => startSetup(method)} disabled={busy}
                className="flex-1 px-3 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-50 text-sm">
                Resend
              </button>
              <button onClick={verify} disabled={busy || code.length !== 6 || exhausted}
                className="flex-1 px-3 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-50 text-sm">
                {busy ? "..." : "Enable"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}