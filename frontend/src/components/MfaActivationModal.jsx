import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./toastContext.jsx";
import VerifyEmailModal from "./VerifyEmailModal.jsx";
import VerifyPhoneModal from "./VerifyPhoneModal.jsx";

export default function MfaActivationModal({ user, onClose, onActivated, onUserRefresh }) {
  const [step, setStep] = useState("check");
  const [chosenMethod, setChosenMethod] = useState(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [showVerifyEmail, setShowVerifyEmail] = useState(false);
  const [showVerifyPhone, setShowVerifyPhone] = useState(false);
  const notify = useToast();

  const hasVerifiedEmail = user.email_verified;
  const hasVerifiedPhone = user.phone_verified;
  const hasAnyVerified = hasVerifiedEmail || hasVerifiedPhone;

  async function chooseMethod(method) {
    setChosenMethod(method);
    setBusy(true);
    try {
      await api("/auth/mfa/setup", {
        method: "POST",
        body: { method: method === "email" ? "email" : "sms" }
      });
      setStep("verify_code");
      notify("MFA setup code sent", "info");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function confirmMfa() {
    setBusy(true);
    try {
      await api("/auth/mfa/enable", { method: "POST", body: { code } });
      notify("MFA activated successfully!", "success");
      onActivated();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function handleVerified() {
    setShowVerifyEmail(false);
    setShowVerifyPhone(false);
    onUserRefresh();
    setStep("check");
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl p-6 w-[440px] shadow-2xl">

          {step === "check" && (
            <>
              <h3 className="text-lg font-bold text-gray-800 mb-2">🔐 Activate Two-Factor Authentication</h3>

              {hasAnyVerified ? (
                <>
                  <p className="text-sm text-gray-600 mb-4">
                    Choose which verified method to use for MFA:
                  </p>
                  <div className="space-y-3">
                    {hasVerifiedEmail && (
                      <button onClick={() => chooseMethod("email")} disabled={busy}
                        className="w-full flex items-center gap-3 p-4 rounded-lg border-2 border-blue-200 hover:border-blue-500 hover:bg-blue-50 disabled:opacity-50">
                        <span className="text-2xl">✉️</span>
                        <div className="text-left">
                          <div className="font-semibold text-gray-800">Email MFA</div>
                          <div className="text-xs text-gray-500">{user.email}</div>
                        </div>
                      </button>
                    )}
                    {hasVerifiedPhone && (
                      <button onClick={() => chooseMethod("sms")} disabled={busy}
                        className="w-full flex items-center gap-3 p-4 rounded-lg border-2 border-blue-200 hover:border-blue-500 hover:bg-blue-50 disabled:opacity-50">
                        <span className="text-2xl">📱</span>
                        <div className="text-left">
                          <div className="font-semibold text-gray-800">SMS MFA</div>
                          <div className="text-xs text-gray-500">{user.phone_number}</div>
                        </div>
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                    <p className="text-sm text-amber-800 font-semibold mb-2">⚠️ Verification Required</p>
                    <p className="text-sm text-amber-700">
                      Verify your email or phone number before activating MFA:
                    </p>
                  </div>
                  <div className="space-y-3">
                    <button onClick={() => setShowVerifyEmail(true)}
                      className="w-full flex items-center gap-3 p-4 rounded-lg border-2 border-amber-200 hover:border-amber-500 hover:bg-amber-50">
                      <span className="text-2xl">✉️</span>
                      <div className="text-left">
                        <div className="font-semibold text-gray-800">Verify Email</div>
                        <div className="text-xs text-gray-500">{user.email}</div>
                      </div>
                    </button>
                    <button onClick={() => setShowVerifyPhone(true)}
                      className="w-full flex items-center gap-3 p-4 rounded-lg border-2 border-amber-200 hover:border-amber-500 hover:bg-amber-50">
                      <span className="text-2xl">📱</span>
                      <div className="text-left">
                        <div className="font-semibold text-gray-800">Verify Phone</div>
                        <div className="text-xs text-gray-500">{user.phone_number || "Add phone number"}</div>
                      </div>
                    </button>
                  </div>
                </>
              )}

              <button onClick={onClose}
                className="w-full mt-4 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
            </>
          )}

          {step === "verify_code" && (
            <>
              <h3 className="text-lg font-bold text-gray-800 mb-2">📲 Confirm MFA Activation</h3>
              <p className="text-sm text-gray-500 mb-4">
                Enter the code sent via{" "}
                <strong>{chosenMethod === "email" ? "✉️ Email" : "📱 SMS"}</strong>.
              </p>
              <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
                placeholder="6-digit code"
                className="w-full border rounded-lg px-3 py-2 mb-4 font-mono text-center text-xl tracking-[0.5em]" />
              <div className="flex gap-2">
                <button onClick={() => setStep("check")}
                  className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">
                  Back
                </button>
                <button onClick={confirmMfa} disabled={busy || code.length !== 6}
                  className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
                  {busy ? "Activating..." : "Activate MFA"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {showVerifyEmail && (
        <VerifyEmailModal user={user} onClose={() => setShowVerifyEmail(false)} onVerified={handleVerified} />
      )}
      {showVerifyPhone && (
        <VerifyPhoneModal user={user} onClose={() => setShowVerifyPhone(false)} onVerified={handleVerified} />
      )}
    </>
  );
}