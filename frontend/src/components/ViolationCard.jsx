import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import StatusBadge from "./StatusBadge.jsx";

export default function ViolationCard({ v, user, onChanged, onEnterPlate }) {
  const [imgUrl, setImgUrl] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    let url = "";
    api(`/violations/${v.id}/image`)
      .then((blob) => { url = URL.createObjectURL(blob); setImgUrl(url); })
      .catch(() => setImgUrl(""));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [v.id]);

  async function act(fn, name) {
    setBusy(name);
    try { await fn(); onChanged(); }
    catch (e) { alert(e.message); }
    finally { setBusy(""); }
  }

  async function downloadReport() {
    const blob = await api(`/violations/${v.id}/report`);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `report_${v.id}.docx`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const canEdit = user.position !== "viewer";
  const isAdmin = user.position === "administrator";

  return (
    <div className="bg-white rounded-xl shadow border border-gray-200 overflow-hidden flex flex-col">
      {imgUrl
        ? <img src={imgUrl} alt="evidence" className="h-44 w-full object-cover bg-gray-100" />
        : <div className="h-44 w-full bg-gray-100 flex items-center justify-center text-gray-400 text-sm">no image</div>}
      <div className="p-4 flex flex-col gap-2 grow">
        <div className="flex items-center justify-between">
          <span className="font-bold text-gray-800">{v.violation_type.replace(/_/g, " ")}</span>
          <StatusBadge status={v.status} />
        </div>
        <div className="text-xs text-gray-500 space-y-0.5">
          <p>Event: <span className="font-mono">{v.event_id}</span></p>
          <p>Captured: {new Date(v.captured_at).toLocaleString()}</p>
          <p>Confidence: {(v.confidence * 100).toFixed(1)}%</p>
          <p>Plate: {v.plate_text
            ? <span className="font-mono font-bold text-gray-800">{v.plate_text} ({v.plate_source})</span>
            : <span className="text-amber-600 font-semibold">NOT FILLED</span>}</p>
        </div>
        <div className="mt-auto grid grid-cols-2 gap-2 pt-2">
          {canEdit && !v.plate_text && v.status === "pending" && (
            <button onClick={() => onEnterPlate(v)}
              className="col-span-2 px-3 py-1.5 rounded-lg bg-amber-500 text-white text-sm font-semibold hover:bg-amber-600">
              Enter Plate Manually
            </button>
          )}
          {canEdit && v.plate_text && v.status === "pending" && (
            <button disabled={busy === "finalize"}
              onClick={() => act(() => api(`/violations/${v.id}/finalize`, { method: "POST" }), "finalize")}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50">
              Finalize Report
            </button>
          )}
          {isAdmin && v.status !== "deleted" && (
            <button disabled={busy === "reject"}
              onClick={() => { if (confirm("Delete this evidence permanently?")) act(() => api(`/violations/${v.id}/reject`, { method: "POST" }), "reject"); }}
              className="px-3 py-1.5 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700 disabled:opacity-50">
              Reject & Delete
            </button>
          )}
          <button onClick={downloadReport}
            className="col-span-2 px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 text-sm font-semibold hover:bg-gray-100">
            Download .docx Report
          </button>
        </div>
      </div>
    </div>
  );
}