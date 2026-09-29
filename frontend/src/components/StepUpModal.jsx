import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./toastContext.jsx";

export default function StepUpModal({ title, description, purpose, onConfirm, onClose }) {
  const [step, setStep] = useState("intro");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const notify = useToast();

  async function sendCode() {
    setBusy(true);
    try {
      await api("/system/stepup/challenge", { method: "POST", body: { purpose } });
      setStep("code");
      notify("Confirmation code sent to your phone", "info");
    } catch (e) {
      notify(e.message, "error");
    } finally { setBusy(false); }
  }

  async function confirm() {
    setBusy(true);
    try {
      await onConfirm(code);
    } finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[90]">
      <div className="bg-white rounded-xl p-6 w-[420px] shadow-2xl">
        {step === "intro" ? (
          <>
            <h3 className="text-lg font-bold text-slate-800 mb-2">🔐 {title}</h3>
            <p className="text-sm text-gray-600 mb-4">{description}</p>
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={sendCode} disabled={busy}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Confirmation Code"}
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-lg font-bold text-slate-800 mb-2">📱 Enter Confirmation Code</h3>
            <p className="text-sm text-gray-500 mb-4">Enter the 6-digit code sent to your phone.</p>
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 font-mono text-center text-xl tracking-[0.5em]" />
            <div className="flex gap-2 mt-4">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={confirm} disabled={busy || code.length !== 6}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                {busy ? "Confirming..." : "Confirm"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}