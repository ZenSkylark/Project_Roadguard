import { useEffect, useRef, useState } from "react";
import { api, clearToken } from "../api/client.js";
import ViolationCard from "../components/ViolationCard.jsx";
import PlateModal from "../components/PlateModal.jsx";
import OcrSelector from "../components/OcrSelector.jsx";
import MfaModal from "../components/MfaModal.jsx";
import ReportsTable from "../components/ReportsTable.jsx";

async function fetchViolations(filter) {
  return api(`/violations${filter ? `?status=${filter}` : ""}`);
}

export default function Dashboard({ user, onLogout, onUserChange }) {
  const [violations, setViolations] = useState([]);
  const [filter, setFilter] = useState("");
  const [modal, setModal] = useState(null);
  const [mfaModal, setMfaModal] = useState(false);
  const [view, setView] = useState("cards");
  const [toast, setToast] = useState("");
  const loadRef = useRef(() => {});

  async function load() {
    try {
      setViolations(await fetchViolations(filter));
    } catch (e) {
      console.error(e);
    }
  }

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    let alive = true;
    fetchViolations(filter)
      .then((data) => { if (alive) setViolations(data); })
      .catch((e) => console.error(e));
    return () => { alive = false; };
  }, [filter]);

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/live`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "new_violation") {
        setToast(`🚨 New ${msg.violation_type.replace(/_/g, " ")} detected (event ${msg.event_id})`);
        setTimeout(() => setToast(""), 5000);
        loadRef.current();
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between sticky top-0 z-40 shadow">
        <div className="flex items-center gap-3">
          <span className="text-xl font-black">🛡️ ROADGUARD</span>
          <span className="text-xs bg-slate-700 px-2 py-1 rounded-full uppercase tracking-wide">{user.position}</span>
          <span className="text-xs text-slate-400 font-mono">{user.uid}</span>
          {user.mfa_enabled ? (
            <span className="text-xs bg-emerald-700 px-2 py-1 rounded-full font-semibold">MFA ON</span>
          ) : (
            <button onClick={() => setMfaModal(true)}
              className="text-xs bg-amber-500 hover:bg-amber-600 px-2 py-1 rounded-full font-semibold">
              Enable MFA
            </button>
          )}
        </div>
        <div className="flex items-center gap-3">
          <OcrSelector user={user} />
          <div className="flex rounded-lg overflow-hidden border border-slate-600 text-xs">
            <button onClick={() => setView("cards")}
              className={`px-2 py-1 ${view === "cards" ? "bg-slate-600" : "bg-slate-800"}`}>Cards</button>
            <button onClick={() => setView("table")}
              className={`px-2 py-1 ${view === "table" ? "bg-slate-600" : "bg-slate-800"}`}>Table</button>
          </div>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}
            className="bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-sm">
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="finalized">Finalized</option>
          </select>
          <button onClick={() => { clearToken(); onLogout(); }}
            className="px-3 py-1.5 rounded-lg bg-red-600/80 hover:bg-red-600 text-sm font-semibold">
            Logout
          </button>
        </div>
      </header>

      {toast && (
        <div className="fixed top-16 right-6 z-50 bg-red-600 text-white px-4 py-3 rounded-xl shadow-2xl font-semibold animate-pulse">
          {toast}
        </div>
      )}

      <main className="p-6">
        <h2 className="text-lg font-bold text-gray-700 mb-4">Violations ({violations.length})</h2>
        {violations.length === 0 ? (
          <div className="text-center text-gray-400 py-24 border-2 border-dashed border-gray-300 rounded-2xl">
            No violations yet. Waiting for the Orange Pi to detect something...
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
      </main>

      {modal && (
        <PlateModal violation={modal} onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }} />
      )}
      {mfaModal && (
        <MfaModal onClose={() => setMfaModal(false)}
          onEnabled={async () => {
            setMfaModal(false);
            onUserChange(await api("/accounts/me"));
          }} />
      )}
    </div>
  );
}