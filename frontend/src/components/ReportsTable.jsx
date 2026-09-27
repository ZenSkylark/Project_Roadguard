import { api } from "../api/client.js";
import StatusBadge from "./StatusBadge.jsx";

export default function ReportsTable({ violations, user, onChanged, onEnterPlate }) {
  const canEdit = user.position !== "viewer";
  const isAdmin = user.position === "administrator";

  async function downloadReport(id) {
    const blob = await api(`/violations/${id}/report`);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `report_${id}.docx`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="overflow-x-auto bg-white rounded-xl shadow border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-slate-100 text-slate-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-3 text-left">ID</th>
            <th className="px-4 py-3 text-left">Event</th>
            <th className="px-4 py-3 text-left">Violation</th>
            <th className="px-4 py-3 text-left">Plate</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-left">Captured</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {violations.map((v) => (
            <tr key={v.id} className="border-t border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-2 font-mono text-xs">#{v.id}</td>
              <td className="px-4 py-2 font-mono text-xs">{v.event_id}</td>
              <td className="px-4 py-2">{v.violation_type.replace(/_/g, " ")}</td>
              <td className="px-4 py-2 font-mono font-bold">
                {v.plate_text || <span className="text-amber-600">NOT FILLED</span>}
              </td>
              <td className="px-4 py-2"><StatusBadge status={v.status} /></td>
              <td className="px-4 py-2 text-xs text-gray-500">{new Date(v.captured_at).toLocaleString()}</td>
              <td className="px-4 py-2 text-right space-x-2 whitespace-nowrap">
                {canEdit && !v.plate_text && v.status === "pending" && (
                  <button onClick={() => onEnterPlate(v)}
                    className="px-2 py-1 rounded bg-amber-500 text-white text-xs font-semibold hover:bg-amber-600">Plate</button>
                )}
                {canEdit && v.plate_text && v.status === "pending" && (
                  <button onClick={() => api(`/violations/${v.id}/finalize`, { method: "POST" }).then(onChanged).catch((e) => alert(e.message))}
                    className="px-2 py-1 rounded bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700">Finalize</button>
                )}
                {isAdmin && v.status !== "deleted" && (
                  <button onClick={() => { if (confirm("Delete this evidence permanently?")) api(`/violations/${v.id}/reject`, { method: "POST" }).then(onChanged).catch((e) => alert(e.message)); }}
                    className="px-2 py-1 rounded bg-red-600 text-white text-xs font-semibold hover:bg-red-700">Reject</button>
                )}
                <button onClick={() => downloadReport(v.id)}
                  className="px-2 py-1 rounded border border-gray-300 text-gray-700 text-xs font-semibold hover:bg-gray-100">.docx</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}