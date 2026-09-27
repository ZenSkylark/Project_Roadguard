import { useEffect, useState } from "react";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import { api, getToken, clearToken } from "./api/client.js";

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
  if (user) {
    return <Dashboard user={user} onLogout={() => setUser(null)} onUserChange={setUser} />;
  }
  return mode === "register"
    ? <Register onDone={() => setMode("login")} />
    : <Login onLogin={async () => setUser(await api("/accounts/me"))}
             onRegister={() => setMode("register")} />;
}