import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Shell from "./components/Shell.jsx";
import HomeDashboard from "./pages/HomeDashboard.jsx";
import ViolationsLog from "./pages/ViolationsLog.jsx";
import AccountPage from "./pages/AccountPage.jsx";
import ConfigPage from "./pages/ConfigPage.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import { api, getToken, clearToken } from "./api/client.js";
import AuditLogsPage from "./pages/AuditLogsPage.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [mode, setMode] = useState("login");
  const [loading, setLoading] = useState(() => !!getToken());

  useEffect(() => {
    if (!getToken()) return;
    api("/accounts/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading Roadguard...</div>;
  }
  if (!user) {
    return mode === "register"
      ? <Register onDone={() => setMode("login")} />
      : <Login onLogin={async () => setUser(await api("/accounts/me"))}
               onRegister={() => setMode("register")} />;
  }

  return (
    <BrowserRouter>
      <ToastProvider>
        <Shell user={user} onLogout={() => { clearToken(); setUser(null); }}>
          <Routes>
            <Route path="/" element={<HomeDashboard user={user} />} />
            <Route path="/logs" element={<ViolationsLog user={user} />} />
            <Route path="/account" element={<AccountPage user={user} onUserChange={setUser} />} />
            <Route path="/config"
              element={user.position === "administrator" ? <ConfigPage user={user} /> : <Navigate to="/" replace />} />
            <Route path="/audit"
              element={user.position === "administrator" ? <AuditLogsPage /> : <Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Shell>
      </ToastProvider>
    </BrowserRouter>
  );
}