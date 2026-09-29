import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

function Stat({ label, value, tone }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`text-2xl font-black ${tone}`}>{value}</p>
    </div>
  );
}

export default function HomeDashboard({ user }) {
  const [violations, setViolations] = useState([]);
  const [sys, setSys] = useState(null);

  useEffect(() => {
    let alive = true;
    api("/violations").then((d) => { if (alive) setViolations(d); }).catch(() => {});
    Promise.all([api("/system/ocr"), api("/system/retention")])
      .then(([o, r]) => { if (alive) setSys({ ocr: o.backend, days: r.retention_days }); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const pending = violations.filter((v) => v.status === "pending").length;
  const finalized = violations.filter((v) => v.status === "finalized").length;
  const recent = violations.slice(0, 5);

  const tiles = [
    { to: "/logs", icon: "📋", title: "Violation Log", desc: "Process pending reports, finalize cases, browse the deleted archive." },
    { to: "/account", icon: "👤", title: "Account", desc: "Profile, contact info, password, and two-factor authentication." },
    ...(user.position === "administrator"
      ? [{ to: "/config", icon: "⚙️", title: "Configuration", desc: "Retention policy, OCR engine, and report template engine." }]
      : []),
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-800">Welcome back, {user.username}</h1>
        <p className="text-sm text-slate-500">Live overview of the Roadguard enforcement network.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Pending" value={pending} tone="text-amber-600" />
        <Stat label="Finalized" value={finalized} tone="text-emerald-600" />
        <Stat label="OCR Engine" value={sys?.ocr ?? "…"} tone="text-blue-600" />
        <Stat label="Retention" value={sys ? `${sys.days}d` : "…"} tone="text-slate-600" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {tiles.map((t) => (
          <Link key={t.to} to={t.to}
            className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 hover:shadow-lg hover:-translate-y-0.5 transition">
            <div className="text-4xl mb-3">{t.icon}</div>
            <h2 className="font-bold text-slate-800">{t.title}</h2>
            <p className="text-sm text-slate-500 mt-1">{t.desc}</p>
            <span className="inline-block mt-3 text-blue-600 text-sm font-semibold">Open →</span>
          </Link>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-slate-800">Recent Activity</h2>
          <Link to="/logs" className="text-blue-600 text-sm font-semibold">View full log →</Link>
        </div>
        {recent.length === 0 ? (
          <p className="text-slate-400 text-sm">No violations recorded yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {recent.map((v) => (
              <li key={v.id} className="py-2 flex items-center justify-between text-sm">
                <span className="font-mono text-xs text-slate-500">{v.event_id}</span>
                <span className="font-mono font-bold">{v.plate_text || "NOT FILLED"}</span>
                <StatusBadge status={v.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}