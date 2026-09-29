import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import ViolationCard from "../components/ViolationCard.jsx";
import PlateModal from "../components/PlateModal.jsx";
import ReportsTable from "../components/ReportsTable.jsx";

async function fetchViolations(filter) {
  return api(`/violations${filter ? `?status=${filter}` : ""}`);
}

export default function ViolationsLog({ user }) {
  const [violations, setViolations] = useState([]);
  const [filter, setFilter] = useState("");
  const [view, setView] = useState("cards");
  const [modal, setModal] = useState(null);
  const loadRef = useRef(() => {});

  async function load() {
    try { setViolations(await fetchViolations(filter)); }
    catch (e) { console.error(e); }
  }

  useEffect(() => { loadRef.current = load; });

  useEffect(() => {
    let alive = true;
    fetchViolations(filter).then((d) => { if (alive) setViolations(d); }).catch(() => {});
    return () => { alive = false; };
  }, [filter]);

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/live`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "new_violation") loadRef.current();
    };
    return () => ws.close();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black text-slate-800">Violation Log</h1>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg overflow-hidden border border-gray-300 text-xs">
            <button onClick={() => setView("cards")}
              className={`px-2 py-1 ${view === "cards" ? "bg-slate-700 text-white" : "bg-white"}`}>Cards</button>
            <button onClick={() => setView("table")}
              className={`px-2 py-1 ${view === "table" ? "bg-slate-700 text-white" : "bg-white"}`}>Table</button>
          </div>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-white">
            <option value="">All active</option>
            <option value="pending">Pending</option>
            <option value="finalized">Finalized</option>
            <option value="deleted">Deleted (archive)</option>
          </select>
        </div>
      </div>

      {violations.length === 0 ? (
        <div className="text-center text-gray-400 py-24 border-2 border-dashed border-gray-300 rounded-2xl bg-white">
          No violations in this view. Waiting for the Orange Pi...
        </div>
      ) : view === "cards" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {violations.map((v) => (
            <ViolationCard key={v.id} v={v} user={user} onChanged={load} onEnterPlate={setModal} />
          ))}
        </div>
      ) : (
        <ReportsTable violations={violations} user={user} onChanged={load} onEnterPlate={setModal} />
      )}

      {modal && (
        <PlateModal violation={modal} onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }} />
      )}
    </div>
  );
}