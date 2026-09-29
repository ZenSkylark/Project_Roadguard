import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", icon: "🏠" },
  { to: "/logs", label: "Violation Log", icon: "📋" },
  { to: "/account", label: "Account", icon: "👤" },
  { to: "/config", label: "Configuration", icon: "⚙️", adminOnly: true },
  { to: "/audit", label: "Audit Trail", icon: "🕵️", adminOnly: true },
];

export default function Shell({ user, onLogout, children }) {
  const [toast, setToast] = useState("");
  const loc = useLocation();

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/live`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "new_violation") {
        setToast(`🚨 New ${msg.violation_type.replace(/_/g, " ")} detected (event ${msg.event_id})`);
        setTimeout(() => setToast(""), 5000);
      }
    };
    return () => ws.close();
  }, []);

  const current = NAV.find((n) => n.to === loc.pathname)?.label ?? "Dashboard";

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-slate-900 text-white px-6 py-3 flex items-center justify-between sticky top-0 z-40 shadow">
        <div className="flex items-center gap-3">
          <span className="text-xl font-black">🛡️ ROADGUARD</span>
          <span className="text-xs bg-slate-700 px-2 py-1 rounded-full uppercase">{user.position}</span>
          <span className="text-xs text-slate-400 font-mono">{user.uid}</span>
          {user.mfa_enabled && (
            <span className="text-xs bg-emerald-700 px-2 py-1 rounded-full font-semibold">MFA ON</span>
          )}
        </div>
        <nav className="flex items-center gap-1">
          {NAV.filter((n) => !n.adminOnly || user.position === "administrator").map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-lg text-sm font-semibold ${isActive ? "bg-blue-600" : "hover:bg-slate-700"}`}>
              {n.icon} {n.label}
            </NavLink>
          ))}
          <button onClick={onLogout}
            className="ml-3 px-3 py-1.5 rounded-lg bg-red-600/80 hover:bg-red-600 text-sm font-semibold">
            Logout
          </button>
        </nav>
      </header>

      <div className="px-6 py-2 text-xs text-slate-500 bg-white border-b border-gray-200">
        🏠 Home <span className="mx-1">/</span>
        <span className="font-semibold text-slate-700">{current}</span>
      </div>

      {toast && (
        <div className="fixed top-16 right-6 z-50 bg-red-600 text-white px-4 py-3 rounded-xl shadow-2xl font-semibold animate-pulse">
          {toast}
        </div>
      )}

      <main className="p-6">{children}</main>
    </div>
  );
}