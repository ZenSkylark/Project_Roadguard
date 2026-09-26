import { useEffect, useState } from "react";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import { api, getToken, clearToken } from "./api/client.js";

export default function App() {
  const [user, setUser] = useState(null);
  // Lazy initializer: no effect needed to decide the initial loading state
  const [loading, setLoading] = useState(() => !!getToken());

  useEffect(() => {
    if (!getToken()) return;               // no synchronous setState anymore
    api("/accounts/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));   // setState only after the promise settles
  }, []);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading Roadguard...</div>;
  }
  return user
    ? <Dashboard user={user} onLogout={() => setUser(null)} />
    : <Login onLogin={async () => setUser(await api("/accounts/me"))} />;
}