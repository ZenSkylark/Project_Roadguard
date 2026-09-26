import { useState } from "react";
import { api } from "../api/client.js";

export default function PlateModal({ violation, onClose, onSaved }) {
  const [plate, setPlate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    setBusy(true); setError("");
    try {
      await api(`/violations/${violation.id}/plate`,
                { method: "PATCH", body: { plate_text: plate } });
      onSaved();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        <h3 className="text-lg font-bold text-gray-800 mb-1">Manual Plate Entry</h3>
        <p className="text-sm text-gray-500 mb-4">
          Event {violation.event_id} — OCR could not read this plate.
        </p>
        <input
          value={plate}
          onChange={(e) => setPlate(e.target.value.toUpperCase())}
          placeholder="ABC 1234"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 font-mono tracking-widest uppercase"
        />
        {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
        <div className="flex gap-2 mt-4">
          <button onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
            Cancel
          </button>
          <button onClick={save} disabled={busy || !plate}
            className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
            {busy ? "Saving..." : "Save Plate"}
          </button>
        </div>
      </div>
    </div>
  );
}