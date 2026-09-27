import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function Accounts() {
  const [users, setUsers] = useState([]);

  // Manual refresh after edits (event-driven, so setState is fine here)
  async function load() {
    try {
      setUsers(await api("/accounts"));
    } catch (e) {
      console.error(e);
    }
  }

  // Initial fetch: setState happens ONLY after the promise resolves
  useEffect(() => {
    let alive = true;
    api("/accounts")
      .then((data) => { if (alive) setUsers(data); })
      .catch((e) => console.error(e));
    return () => { alive = false; };
  }, []);

  async function updatePosition(uid, position) {
    await api(`/accounts/${uid}/position`, { method: "PATCH", body: { position } });
    load();
  }

  async function updateStatus(uid, is_active) {
    await api(`/accounts/${uid}/status`, { method: "PATCH", body: { is_active } });
    load();
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Admin: User Management</h1>
      <div className="bg-white rounded-xl shadow border overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="p-4">UID</th>
              <th className="p-4">Username</th>
              <th className="p-4">Email</th>
              <th className="p-4">Position</th>
              <th className="p-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.uid} className="border-b hover:bg-gray-50">
                <td className="p-4 font-mono text-xs">{u.uid}</td>
                <td className="p-4 font-bold">{u.username}</td>
                <td className="p-4 text-sm text-gray-600">{u.email}</td>
                <td className="p-4">
                  <select value={u.position} onChange={e => updatePosition(u.uid, e.target.value)} className="border rounded px-2 py-1 text-sm">
                    <option value="viewer">Viewer</option>
                    <option value="officer">Officer</option>
                    <option value="administrator">Administrator</option>
                  </select>
                </td>
                <td className="p-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={u.is_active} onChange={e => updateStatus(u.uid, e.target.checked)} className="w-4 h-4" />
                    <span className={`text-sm font-bold ${u.is_active ? 'text-green-600' : 'text-red-600'}`}>
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}