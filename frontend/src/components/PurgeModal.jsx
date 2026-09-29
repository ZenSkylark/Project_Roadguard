import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "../components/toastContext.jsx";

export default function PurgeModal({ retentionDays, onClose }) {
  const [step, setStep] = useState("warning");   // warning -> code -> done
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const notify = useToast();

  async function sendCode() {
    setBusy(true);
    try {
      await api("/system/purge/challenge", { method: "POST" });
      setStep("code");
      notify("Confirmation code sent to your phone", "info");
    } catch (e) {
      notify(e.message, "error");
    } finally { setBusy(false); }
  }

  async function confirmPurge() {
    setBusy(true);
    try {
      const r = await api("/system/purge", { method: "POST", body: { code } });
      setResult(r);
      setStep("done");
      notify(`Purged ${r.violations_deleted} violation(s)`, "success");
    } catch (e) {
      notify(e.message, "error");
    } finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[90]">
      <div className="bg-white rounded-xl p-6 w-[420px] shadow-2xl">
        {step === "warning" && (
          <>
            <h3 className="text-lg font-black text-red-600 mb-2">⚠️ FINAL WARNING</h3>
            <p className="text-sm text-gray-700 mb-2">
              You are about to <b>permanently delete</b> all <b>finalized</b> violations older than{" "}
              <b>{retentionDays} days</b>, including their images and reports.
            </p>
            <p className="text-sm text-red-600 font-semibold mb-4">This action cannot be undone. Pending evidence is preserved.</p>
            <p className="text-xs text-gray-500 mb-4">To proceed, a one-time confirmation code will be texted to your registered phone.</p>
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={sendCode} disabled={busy} className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Confirmation Code"}
              </button>
            </div>
          </>
        )}

        {step === "code" && (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📱 Enter Confirmation Code</h3>
            <p className="text-sm text-gray-500 mb-4">Enter the 6-digit code sent to your phone to authorize the purge.</p>
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 font-mono text-center text-xl tracking-[0.5em]" />
            <div className="flex gap-2 mt-4">
              <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={confirmPurge} disabled={busy || code.length !== 6}
                className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50">
                {busy ? "Purging..." : "Confirm Purge"}
              </button>
            </div>
          </>
        )}

        {step === "done" && (
          <>
            <h3 className="text-lg font-bold text-emerald-600 mb-2">✅ Purge Complete</h3>
            <p className="text-sm text-gray-700 mb-4">
              Deleted <b>{result?.violations_deleted}</b> violation(s) and <b>{result?.files_deleted}</b> file(s).
            </p>
            <button onClick={onClose} className="w-full px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">Close</button>
          </>
        )}
      </div>
    </div>
  );
}