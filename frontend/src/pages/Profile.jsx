import { useState } from "react";
import { api } from "../api/client.js";

export default function Profile({ user, onUserUpdate }) {
  const [profile, setProfile] = useState({ username: user.username, email: user.email });
  const [pw, setPw] = useState({ old_password: "", new_password: "" });
  const [mfaCode, setMfaCode] = useState("");
  const [qrUrl, setQrUrl] = useState("");
  const [msg, setMsg] = useState("");

  async function updateProfile(e) {
    e.preventDefault();
    try {
      const res = await api("/accounts/me", { method: "PATCH", body: profile });
      onUserUpdate({ ...user, ...res });
      setMsg("Profile updated!");
    } catch (e) { setMsg("Error: " + e.message); }
  }

  async function changePw(e) {
    e.preventDefault();
    try {
      await api("/auth/change-password", { method: "POST", body: pw });
      setMsg("Password changed! You will be logged out.");
      setTimeout(() => window.location.href = "/login", 1500);
    } catch (e) { setMsg("Error: " + e.message); }
  }

  async function setupMfa() {
    await api("/auth/mfa/setup", { method: "POST" });
    const blob = await api("/auth/mfa/qr");
    setQrUrl(URL.createObjectURL(blob));
  }

  async function enableMfa(e) {
    e.preventDefault();
    try {
      await api("/auth/mfa/enable", { method: "POST", body: { code: mfaCode } });
      onUserUpdate({ ...user, mfa_enabled: true });
      setQrUrl(""); setMsg("MFA Enabled!");
    } catch (e) { setMsg("Error: " + e.message); }
  }

  async function disableMfa() {
    const pass = prompt("Enter your password to disable MFA:");
    if (!pass) return;
    try {
      await api("/auth/mfa/disable", { method: "POST", body: { password: pass } });
      onUserUpdate({ ...user, mfa_enabled: false });
      setMsg("MFA Disabled.");
    } catch (e) { setMsg("Error: " + e.message); }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Profile Settings</h1>
      {msg && <div className="p-3 bg-blue-100 text-blue-800 rounded-lg">{msg}</div>}
      
      <form onSubmit={updateProfile} className="bg-white p-6 rounded-xl shadow border space-y-3">
        <h2 className="font-bold text-lg">Profile Info</h2>
        <input className="w-full border rounded px-3 py-2" value={profile.username} onChange={e => setProfile({...profile, username: e.target.value})} />
        <input className="w-full border rounded px-3 py-2" value={profile.email} onChange={e => setProfile({...profile, email: e.target.value})} />
        <button className="bg-blue-600 text-white px-4 py-2 rounded font-bold">Update Profile</button>
      </form>

      <form onSubmit={changePw} className="bg-white p-6 rounded-xl shadow border space-y-3">
        <h2 className="font-bold text-lg">Change Password</h2>
        <input type="password" placeholder="Current Password" className="w-full border rounded px-3 py-2" value={pw.old_password} onChange={e => setPw({...pw, old_password: e.target.value})} />
        <input type="password" placeholder="New Password" className="w-full border rounded px-3 py-2" value={pw.new_password} onChange={e => setPw({...pw, new_password: e.target.value})} />
        <button className="bg-blue-600 text-white px-4 py-2 rounded font-bold">Change Password</button>
      </form>

      <div className="bg-white p-6 rounded-xl shadow border space-y-3">
        <h2 className="font-bold text-lg">Multi-Factor Authentication</h2>
        {user.mfa_enabled ? (
          <div className="flex items-center justify-between">
            <span className="text-green-600 font-bold">MFA is Enabled</span>
            <button onClick={disableMfa} className="bg-red-600 text-white px-4 py-2 rounded font-bold">Disable MFA</button>
          </div>
        ) : (
          <>
            <button onClick={setupMfa} className="bg-amber-500 text-white px-4 py-2 rounded font-bold">Setup MFA</button>
            {qrUrl && (
              <form onSubmit={enableMfa} className="mt-4 space-y-3">
                <p className="text-sm text-gray-600">Scan this QR code with Google Authenticator:</p>
                <img src={qrUrl} alt="MFA QR" className="mx-auto border p-2 rounded" />
                <input placeholder="6-digit code" className="w-full border rounded px-3 py-2 text-center font-mono text-xl" value={mfaCode} onChange={e => setMfaCode(e.target.value)} />
                <button className="w-full bg-green-600 text-white px-4 py-2 rounded font-bold">Verify & Enable</button>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
}