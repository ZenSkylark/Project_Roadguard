import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./toastContext.jsx";

export default function VerifyPhoneModal({ user, onClose, onVerified }) {
  const [step, setStep] = useState("phone");
  const [phone, setPhone] = useState(user.phone_number ?? "");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const notify = useToast();

  async function sendCode() {
    if (!phone) {
      notify("Please enter a phone number", "error");
      return;
    }
    setBusy(true);
    try {
      await api("/auth/phone/send-verify", { method: "POST", body: { phone_number: phone } });
      setStep("verify");
      notify("Verification code sent to your phone", "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setBusy(true);
    try {
      await api("/auth/phone/confirm-verify", { method: "POST", body: { phone_number: phone, code } });
      notify("Phone verified successfully!", "success");
      onVerified();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[70]">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        {step === "phone" ? (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📱 Verify Phone Number</h3>
            <p className="text-sm text-gray-600 mb-4">
              Enter your phone number to receive a verification code.
            </p>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              placeholder="09XXXXXXXXX"
              className="w-full border rounded-lg px-3 py-2 mb-4 font-mono" />
            <div className="flex gap-2">
              <button onClick={onClose}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
              <button onClick={sendCode} disabled={busy || !phone}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Code"}
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📲 Enter Verification Code</h3>
            <p className="text-sm text-gray-500 mb-4">
              Check your phone for the code sent to <strong>{phone}</strong>.
            </p>
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
              placeholder="6-digit code"
              className="w-full border rounded-lg px-3 py-2 mb-4 font-mono text-center text-xl tracking-[0.5em]" />
            <div className="flex gap-2">
              <button onClick={() => setStep("phone")}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Back
              </button>
              <button onClick={verify} disabled={busy || code.length !== 6}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Verifying..." : "Verify Phone"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}