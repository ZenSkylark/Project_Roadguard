import { useState } from "react";
import { api } from "../api/client.js";
import MfaModal from "../components/MfaModal.jsx";
import { useToast } from "../components/toastContext.jsx";

function Row({ k, v }) {
  return (<><dt className="text-slate-400">{k}</dt><dd className="font-mono font-semibold text-slate-700">{v}</dd></>);
}

export default function AccountPage({ user, onUserChange }) {
  const [info, setInfo] = useState({ email: user.email ?? "", phone_number: user.phone_number ?? "" });
  const [pw, setPw] = useState({ old_password: "", new_password: "", confirm: "" });
  const [mfaModal, setMfaModal] = useState(false);
  const notify = useToast();

  async function saveInfo(e) {
    e.preventDefault();
    try {
      const body = {};
      if (info.email) body.email = info.email;
      if (info.phone_number) body.phone_number = info.phone_number;
      onUserChange(await api("/accounts/me", { method: "PATCH", body }));
      notify("Profile updated", "success");
    } catch (err) { notify(err.message, "error"); }
  }

  async function savePw(e) {
    e.preventDefault();
    if (pw.new_password !== pw.confirm) { notify("Passwords do not match", "error"); return; }
    try {
      await api("/auth/change-password", { method: "POST",
        body: { old_password: pw.old_password, new_password: pw.new_password } });
      setPw({ old_password: "", new_password: "", confirm: "" });
      notify("Password changed", "success");
    } catch (err) { notify(err.message, "error"); }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-black text-slate-800">Account</h1>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-slate-800">Profile</h2>
          {user.mfa_enabled ? (
            <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full font-semibold">MFA ON</span>
          ) : (
            <button onClick={() => setMfaModal(true)}
              className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-2 py-1 rounded-full font-semibold">
              Enable MFA
            </button>
          )}
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <Row k="UID" v={user.uid} />
          <Row k="Username" v={user.username} />
          <Row k="Position" v={user.position} />
          <Row k="Last login" v={user.last_login ? new Date(user.last_login).toLocaleString() : "—"} />
        </dl>
      </div>

      <form onSubmit={saveInfo} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-4">Edit Contact Info</h2>
        <label className="text-sm font-semibold text-slate-600 block mb-1">Email</label>
        <input value={info.email} onChange={(e) => setInfo({ ...info, email: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        <label className="text-sm font-semibold text-slate-600 block mb-1">Phone (for SMS MFA)</label>
        <input value={info.phone_number ?? ""} onChange={(e) => setInfo({ ...info, phone_number: e.target.value })}
          placeholder="09XXXXXXXXX" className="w-full border rounded-lg px-3 py-2 mb-3 font-mono" />
        <button className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">Save Changes</button>
      </form>

      <form onSubmit={savePw} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-4">Change Password</h2>
        <input type="password" placeholder="Current password" value={pw.old_password}
          onChange={(e) => setPw({ ...pw, old_password: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        <input type="password" placeholder="New password (8+ chars, upper, lower, number)" value={pw.new_password}
          onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        <input type="password" placeholder="Confirm new password" value={pw.confirm}
          onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        <button className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">Update Password</button>
      </form>

      {mfaModal && (
        <MfaModal onClose={() => setMfaModal(false)}
          onEnabled={async () => { setMfaModal(false); onUserChange(await api("/accounts/me")); }} />
      )}
    </div>
  );
}