import { useEffect, useState } from "react";
import { api } from "../api/client.js";

const ACTION_TONES = [
  ["purge", "bg-red-100 text-red-700"],
  ["reject", "bg-red-100 text-red-700"],
  ["password", "bg-purple-100 text-purple-700"],
  ["mfa", "bg-purple-100 text-purple-700"],
  ["login", "bg-emerald-100 text-emerald-700"],
  ["register", "bg-emerald-100 text-emerald-700"],
  ["finalize", "bg-emerald-100 text-emerald-700"],
  ["retention", "bg-orange-100 text-orange-700"],
  ["ocr", "bg-blue-100 text-blue-700"],
  ["template", "bg-blue-100 text-blue-700"],
  ["profile", "bg-blue-100 text-blue-700"],
  ["upload", "bg-slate-100 text-slate-700"],
];

function toneFor(action) {
  const hit = ACTION_TONES.find(([key]) => action.includes(key));
  return hit ? hit[1] : "bg-gray-100 text-gray-700";
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [action, setAction] = useState("");
  const [username, setUsername] = useState("");
  const [limit, setLimit] = useState(100);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    try {
      const params = new URLSearchParams();
      if (action) params.set("action", action);
      if (username) params.set("username", username);
      params.set("limit", String(limit));
      setLogs(await api(`/system/audit?${params.toString()}`));
    } catch (e) { console.error(e); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    let alive = true;
    api("/system/audit?limit=100")
      .then((d) => { if (alive) setLogs(d); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  function exportCsv() {
    const head = "timestamp,user,action,detail,ip\n";
    const rows = logs.map((l) =>
      [l.at, l.username, l.action, l.detail ?? "", l.ip ?? ""]
        .map((x) => `"${String(x).replaceAll('"', '""')}"`)
        .join(",")
    ).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([head + rows], { type: "text/csv" }));
    a.download = `audit_log_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black text-slate-800">🕵️ Audit Trail</h1>
        <div className="flex items-center gap-2">
          <button onClick={exportCsv}
            className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-sm font-semibold text-gray-700 hover:bg-gray-100">
            ⬇ Export CSV
          </button>
          <button onClick={load} disabled={busy}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:opacity-50">
            {busy ? "Loading..." : "🔄 Refresh"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs font-semibold text-slate-500 block mb-1">Action contains</label>
          <input value={action} onChange={(e) => setAction(e.target.value)}
            placeholder="e.g. purge, login, ocr"
            className="border rounded-lg px-3 py-1.5 text-sm font-mono" />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500 block mb-1">Username contains</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. admin"
            className="border rounded-lg px-3 py-1.5 text-sm font-mono" />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500 block mb-1">Limit</label>
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}
            className="border rounded-lg px-3 py-1.5 text-sm bg-white">
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </div>
        <button onClick={load}
          className="px-4 py-1.5 rounded-lg bg-slate-700 text-white text-sm font-semibold hover:bg-slate-800">
          Search
        </button>
      </div>

      <div className="overflow-x-auto bg-white rounded-xl shadow border border-gray-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-slate-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Timestamp</th>
              <th className="px-4 py-3 text-left">User</th>
              <th className="px-4 py-3 text-left">Action</th>
              <th className="px-4 py-3 text-left">Detail</th>
              <th className="px-4 py-3 text-left">IP</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No audit events match.</td></tr>
            ) : logs.map((l) => (
              <tr key={l.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs text-gray-500 whitespace-nowrap">
                  {l.at ? new Date(l.at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2 font-mono font-bold">{l.username}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${toneFor(l.action)}`}>
                    {l.action}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-600">{l.detail ?? "—"}</td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500">{l.ip ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}