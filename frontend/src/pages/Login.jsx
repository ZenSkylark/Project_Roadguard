import { useState } from "react";
import { api, setToken } from "../api/client.js";
import ForgotPasswordModal from "../components/ForgotPasswordModal.jsx";

export default function Login({ onLogin, onRegister }) {
  const [step, setStep] = useState("credentials"); // credentials | select_method | enter_code
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState(null);
  const [availableMethods, setAvailableMethods] = useState([]);
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [mfaCode, setMfaCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showForgot, setShowForgot] = useState(false);

  // Step 1: Submit credentials
  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const form = new URLSearchParams();
      form.append("username", username);
      form.append("password", password);
      const res = await fetch("/api/auth/login", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Login failed");
      }
      const data = await res.json();
      if (data.mfa_required) {
        setMfaToken(data.mfa_token);
        setAvailableMethods(data.available_methods || []);
        setStep("select_method");
      } else {
        setToken(data.access_token);
        await onLogin();
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Step 2: Choose MFA method and request code
  async function chooseMethod(method) {
    setError("");
    setLoading(true);
    try {
      await api("/auth/mfa/request-code", {
        method: "POST",
        body: { mfa_token: mfaToken, method: method },
      });
      setSelectedMethod(method);
      setStep("enter_code");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Step 3: Verify the code
  async function handleMfaVerify(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api("/auth/mfa/verify-login", {
        method: "POST",
        body: { mfa_token: mfaToken, code: mfaCode },
      });
      setToken(data.access_token);
      await onLogin();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Resend code to the selected method
  async function handleResendMfa() {
    setError("");
    setLoading(true);
    try {
      await api("/auth/mfa/resend", {
        method: "POST",
        body: { mfa_token: mfaToken, method: selectedMethod },
      });
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const hasEmail = availableMethods.includes("email");
  const hasSms = availableMethods.includes("sms");

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-blue-900">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-96">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🛡️</div>
          <h1 className="text-2xl font-bold text-gray-800">Roadguard</h1>
          <p className="text-sm text-gray-500">Sign in to your account</p>
        </div>

        {/* STEP 1: Credentials */}
        {step === "credentials" && (
          <form onSubmit={handleSubmit}>
            <input type="text" placeholder="Username" value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-3" required />
            <input type="password" placeholder="Password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 mb-3" required />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full bg-blue-600 text-white font-semibold py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {loading ? "Signing in..." : "Sign In"}
            </button>
            <div className="mt-4 text-center">
              <button type="button" onClick={() => setShowForgot(true)}
                className="text-sm text-blue-600 hover:underline">
                Forgot Password?
              </button>
            </div>
            <div className="mt-4 text-center text-sm text-gray-500">
              Don't have an account?{" "}
              <button type="button" onClick={onRegister} className="text-blue-600 hover:underline">
                Register
              </button>
            </div>
          </form>
        )}

        {/* STEP 2: Choose MFA Method */}
        {step === "select_method" && (
          <div>
            <p className="text-sm text-gray-600 mb-4 text-center">
              Choose how you'd like to receive your verification code
            </p>
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            
            <div className="space-y-3">
              {/* Email Option */}
              <button
                onClick={() => chooseMethod("email")}
                disabled={!hasEmail || loading}
                className={`w-full flex items-center gap-3 p-4 rounded-lg border-2 transition ${
                  hasEmail
                    ? "border-blue-200 hover:border-blue-500 hover:bg-blue-50 cursor-pointer"
                    : "border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed"
                }`}
              >
                <span className="text-2xl">✉️</span>
                <div className="text-left">
                  <div className="font-semibold text-gray-800">Email</div>
                  <div className="text-xs text-gray-500">
                    {hasEmail ? "Send code to your email" : "Not set up"}
                  </div>
                </div>
              </button>

              {/* SMS Option */}
              <button
                onClick={() => chooseMethod("sms")}
                disabled={!hasSms || loading}
                className={`w-full flex items-center gap-3 p-4 rounded-lg border-2 transition ${
                  hasSms
                    ? "border-blue-200 hover:border-blue-500 hover:bg-blue-50 cursor-pointer"
                    : "border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed"
                }`}
              >
                <span className="text-2xl">📱</span>
                <div className="text-left">
                  <div className="font-semibold text-gray-800">SMS</div>
                  <div className="text-xs text-gray-500">
                    {hasSms ? "Send code to your phone" : "Not set up"}
                  </div>
                </div>
              </button>
            </div>

            <button
              onClick={() => setStep("credentials")}
              className="w-full mt-4 text-sm text-gray-500 hover:underline"
            >
              ← Back to login
            </button>
          </div>
        )}

        {/* STEP 3: Enter Code */}
        {step === "enter_code" && (
          <form onSubmit={handleMfaVerify}>
            <p className="text-sm text-gray-600 mb-3 text-center">
              Enter the 6-digit code sent via{" "}
              <span className="font-semibold">
                {selectedMethod === "email" ? "✉️ Email" : "📱 SMS"}
              </span>
            </p>
            <input type="text" placeholder="6-digit code" value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)} maxLength={6}
              className="w-full border rounded-lg px-3 py-2 mb-3 font-mono text-center text-xl tracking-[0.5em]"
              required />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <div className="flex gap-2 mb-3">
              <button type="button" onClick={handleResendMfa} disabled={loading}
                className="flex-1 border border-gray-300 text-gray-600 font-semibold py-2 rounded-lg hover:bg-gray-100 disabled:opacity-50">
                Resend
              </button>
              <button type="submit" disabled={loading || mfaCode.length !== 6}
                className="flex-1 bg-blue-600 text-white font-semibold py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {loading ? "Verifying..." : "Verify"}
              </button>
            </div>
            <button
              type="button"
              onClick={() => { setStep("select_method"); setMfaCode(""); setError(""); }}
              className="w-full text-sm text-gray-500 hover:underline"
            >
              ← Choose a different method
            </button>
          </form>
        )}
      </div>

      {showForgot && (
        <ForgotPasswordModal
          onClose={() => setShowForgot(false)}
          onSuccess={() => {
            setShowForgot(false);
            setUsername("");
            setPassword("");
          }}
        />
      )}
    </div>
  );
}