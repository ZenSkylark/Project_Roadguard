import { useState } from "react";
import { api } from "../api/client.js";
import MfaActivationModal from "../components/MfaActivationModal.jsx";
import { useToast } from "../components/toastContext.jsx";

function Row({ k, v }) {
  return (
    <>
      <dt className="text-slate-400">{k}</dt>
      <dd className="font-mono font-semibold text-slate-700">{v}</dd>
    </>
  );
}

function VerifiedBadge({ verified }) {
  return verified ? (
    <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-semibold">
      ✓ Verified
    </span>
  ) : (
    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-semibold">
      ⚠ Unverified
    </span>
  );
}

/* ---------- Disable MFA Modal ---------- */
function DisableMfaModal({ onClose, onDone }) {
  const [step, setStep] = useState("send");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const notify = useToast();

  async function sendCode() {
    setBusy(true);
    try {
      await api("/auth/mfa/disable", { method: "POST", body: { code: "" } });
      setStep("verify");
      notify("Confirmation code sent to your device", "info");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    try {
      await api("/auth/mfa/confirm-disable", { method: "POST", body: { code } });
      notify("MFA disabled", "success");
      onDone();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-xl p-6 w-96 shadow-2xl">
        {step === "send" ? (
          <>
            <h3 className="text-lg font-bold text-red-600 mb-2">Disable Two-Factor Authentication</h3>
            <p className="text-sm text-gray-600 mb-4">
              This removes the extra security layer from your account.
            </p>
            <div className="flex gap-2">
              <button onClick={onClose}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
              <button onClick={sendCode} disabled={busy}
                className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50">
                {busy ? "Sending..." : "Send Code"}
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-lg font-bold text-gray-800 mb-2">📱 Enter Confirmation Code</h3>
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 font-mono text-center text-xl tracking-[0.5em]" />
            <div className="flex gap-2 mt-4">
              <button onClick={onClose}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
              <button onClick={confirm} disabled={busy || code.length !== 6}
                className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50">
                {busy ? "Disabling..." : "Confirm"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ---------- Main Account Page ---------- */
export default function AccountPage({ user, onUserChange }) {
  const [info, setInfo] = useState({ email: user.email ?? "", phone_number: user.phone_number ?? "" });
  const [pw, setPw] = useState({ old_password: "", new_password: "", confirm: "" });
  const [showMfaChallenge, setShowMfaChallenge] = useState(false);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaModal, setMfaModal] = useState(false);
  const [disableModal, setDisableModal] = useState(false);
  const notify = useToast();

  async function refreshUser() {
    try {
      onUserChange(await api("/accounts/me"));
    } catch (e) {
      notify(e.message, "error");
    }
  }

  async function saveInfo(e) {
    e.preventDefault();
    try {
      const body = {};
      if (info.email) body.email = info.email;
      if (info.phone_number) body.phone_number = info.phone_number;
      onUserChange(await api("/accounts/me", { method: "PATCH", body }));
      notify("Profile updated", "success");
    } catch (err) {
      notify(err.message, "error");
    }
  }

  async function savePw(e) {
    e.preventDefault();
    if (pw.new_password !== pw.confirm) {
      notify("Passwords do not match", "error");
      return;
    }
    try {
      await api("/auth/change-password", {
        method: "POST",
        body: {
          old_password: pw.old_password,
          new_password: pw.new_password,
          code: mfaCode || undefined,
        },
      });
      setPw({ old_password: "", new_password: "", confirm: "" });
      setMfaCode("");
      setShowMfaChallenge(false);
      notify("Password changed", "success");
    } catch (err) {
      if (err.message && /mfa code required/i.test(err.message)) {
        setShowMfaChallenge(true);
        notify("MFA code sent — enter it to confirm", "info");
      } else {
        notify(err.message, "error");
      }
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-black text-slate-800">Account</h1>

      {/* Profile */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-4">Profile</h2>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <Row k="UID" v={user.uid} />
          <Row k="Username" v={user.username} />
          <Row k="Position" v={user.position} />
          <Row k="Last login" v={user.last_login ? new Date(user.last_login).toLocaleString() : "—"} />
        </dl>

        {/* Contact Verification Status */}
        <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg">✉️</span>
              <div>
                <div className="text-xs text-slate-400">Email</div>
                <div className="text-sm font-mono font-semibold text-slate-700">{user.email}</div>
              </div>
            </div>
            <VerifiedBadge verified={user.email_verified} />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg">📱</span>
              <div>
                <div className="text-xs text-slate-400">Phone Number</div>
                <div className="text-sm font-mono font-semibold text-slate-700">
                  {user.phone_number || "Not set"}
                </div>
              </div>
            </div>
            <VerifiedBadge verified={user.phone_verified} />
          </div>
        </div>
      </div>

      {/* Two-Factor Authentication */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold text-slate-800">🔐 Two-Factor Authentication</h2>
          {user.mfa_enabled ? (
            <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full font-semibold">
              ENABLED
            </span>
          ) : (
            <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-full font-semibold">
              DISABLED
            </span>
          )}
        </div>

        {user.mfa_enabled ? (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">
              {user.mfa_method === "email"
                ? `✉️ Email MFA active — codes sent to ${user.email}`
                : `📱 SMS MFA active — codes sent to ${user.phone_number || "your phone"}`}
            </p>
            <button onClick={() => setDisableModal(true)}
              className="px-4 py-2 rounded-lg border border-red-300 text-red-600 text-sm font-semibold hover:bg-red-50">
              Disable MFA
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">
              Add an extra layer of security to your account.
            </p>
            <button onClick={() => setMfaModal(true)}
              className="w-full px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-semibold hover:bg-amber-600">
              🔐 Activate MFA
            </button>
          </div>
        )}
      </div>

      {/* Edit Contact Info */}
      <form onSubmit={saveInfo} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-4">Edit Contact Info</h2>
        <label className="text-sm font-semibold text-slate-600 block mb-1">Email</label>
        <input value={info.email} onChange={(e) => setInfo({ ...info, email: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        <label className="text-sm font-semibold text-slate-600 block mb-1">Phone Number</label>
        <input value={info.phone_number ?? ""} onChange={(e) => setInfo({ ...info, phone_number: e.target.value })}
          placeholder="09XXXXXXXXX" className="w-full border rounded-lg px-3 py-2 mb-3 font-mono" />
        <button className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">
          Save Changes
        </button>
      </form>

      {/* Change Password */}
      <form onSubmit={savePw} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-4">Change Password</h2>
        {user.mfa_enabled && (
          <p className="text-xs text-slate-400 mb-3">
            🔐 This account requires MFA confirmation to change the password.
          </p>
        )}
        <input type="password" placeholder="Current password" value={pw.old_password}
          onChange={(e) => setPw({ ...pw, old_password: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        <input type="password" placeholder="New password (8+ chars, upper, lower, number)" value={pw.new_password}
          onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        <input type="password" placeholder="Confirm new password" value={pw.confirm}
          onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3" />
        {showMfaChallenge && (
          <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <label className="block text-sm font-semibold text-blue-700 mb-1">MFA Code Required</label>
            <input value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} maxLength={6}
              placeholder="6-digit code"
              className="w-full border rounded-lg px-3 py-2 font-mono text-center text-xl tracking-[0.5em]" />
          </div>
        )}
        <button className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">
          {showMfaChallenge ? "Confirm with MFA Code" : "Update Password"}
        </button>
      </form>

      {/* Modals */}
      {mfaModal && (
        <MfaActivationModal
          user={user}
          onClose={() => setMfaModal(false)}
          onActivated={() => { setMfaModal(false); refreshUser(); }}
          onUserRefresh={refreshUser}
        />
      )}
      {disableModal && (
        <DisableMfaModal onClose={() => setDisableModal(false)}
          onDone={() => { setDisableModal(false); refreshUser(); }} />
      )}
    </div>
  );
}