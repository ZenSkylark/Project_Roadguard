import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function OcrSelector({ user }) {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/system/ocr").then(setState).catch(() => setState(null));
  }, []);

  if (!state || user.position !== "administrator") return null;

  async function change(backend) {
    setBusy(true);
    try {
      await api("/system/ocr", { method: "PUT", body: { backend } });
      setState(await api("/system/ocr"));
    } catch (e) { alert(e.message); }
    finally { setBusy(false); }
  }

  return (
    <label className="flex items-center gap-2 text-xs text-slate-300">
      OCR
      <select disabled={busy} value={state.backend}
        onChange={(e) => change(e.target.value)}
        className="bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-sm">
        {state.options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}