import { useState, useCallback } from "react";
import { ToastContext } from "./toastContext.jsx";

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);

  const notify = useCallback((message, type = "success") => {
    setToast({ message, type, id: Date.now() });
    setTimeout(() => setToast(null), 4000);
  }, []);

  const colors = {
    success: "bg-emerald-600",
    error: "bg-red-600",
    info: "bg-blue-600",
  };

  return (
    <ToastContext.Provider value={notify}>
      {children}
      {toast && (
        <div key={toast.id}
          className={`fixed bottom-6 right-6 z-[100] px-5 py-3 rounded-xl shadow-2xl text-white font-semibold transition ${colors[toast.type] || colors.info}`}>
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
}