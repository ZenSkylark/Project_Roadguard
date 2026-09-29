import { useState } from "react";
import { api } from "../api/client.js";

export default function RetentionModal({ initialDays, onClose }) {
  const [days, setDays] = useState(initialDays);
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState(null);

  function handleChange(raw) {
    if (raw === "") { setDays(""); return; }
    const n = Number(raw);
    if (Number.isNaN(n)) return;
    setDays(String(Math.max(1, Math.min(3650, n))));   // 0 -> 1, instantly
  }

  async function save() {
    setBusy("save");
    try {
      await api("/system/retention", { method: "PUT", body: { days: Number(days) || 1 } });
      onClose();
    } catch (e) { alert(e.message); }
    finally { setBusy(""); }
  }

  async function purge() {
    if (!confirm(`Permanently delete FINALIZED violations older than ${days} days? Pending cases are kept.`)) return;
    setBusy("purge");
    try { setResult(await api("/system/purge", { method: "POST" })); }
    catch (e) { alert(e.message); }
    finally { setBusy(""); }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        <h3 className="text-lg font-bold text-gray-800 mb-1">🗑️ Storage Retention</h3>
        <p className="text-sm text-gray-500 mb-4">
          Finalized violations older than this window are auto-deleted every 24h
          (images + reports). Pending evidence is never auto-purged.
        </p>
        <label className="text-sm font-semibold text-slate-600">Retention window (days)</label>
        <input type="number" min="1" max="3650" value={days}
          onChange={(e) => handleChange(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 mt-1 font-mono" />
        {result && (
          <p className="text-emerald-600 text-sm mt-3">
            Purged {result.violations_deleted} violation(s), {result.files_deleted} file(s).
          </p>
        )}
        <div className="flex gap-2 mt-4">
          <button onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
            Close
          </button>
          <button onClick={purge} disabled={busy !== ""}
            className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50">
            {busy === "purge" ? "Purging..." : "Purge Now"}
          </button>
          <button onClick={save} disabled={busy !== ""}
            className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
            {busy === "save" ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}