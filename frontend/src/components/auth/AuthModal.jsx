import React, { useState } from "react";

export function AuthModal({
  isOpen,
  onClose,
  onLogin,
  onRegister,
  authError,
  setAuthError,
  onRegistered
}) {
  const [mode, setMode] = useState("login"); // "login" or "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    if (setAuthError) setAuthError(null);

    try {
      if (mode === "login") {
        await onLogin(email, password);
        onClose();
      } else {
        const regData = await onRegister(email, password, fullName);
        onClose();
        if (onRegistered) onRegistered(regData);
      }
    } catch (err) {
      // Error managed via useAuth state
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs font-sans">
      <div className="relative w-full max-w-md bg-white border border-slate-200 rounded-xl shadow-xl p-6 overflow-hidden">
        {/* Header Strip */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100">
              <span className="material-symbols-outlined text-[20px]">
                {mode === "login" ? "lock" : "person_add"}
              </span>
            </span>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                {mode === "login" ? "Clinical Authentication" : "Register Clinical Account"}
              </h3>
              <p className="text-[11px] text-slate-500">
                {mode === "login" ? "Sign in to access patient records" : "Auto-provisions isolated patient container"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Mode Tabs */}
        <div className="flex border-b border-slate-200 mt-4">
          <button
            type="button"
            onClick={() => { setMode("login"); if (setAuthError) setAuthError(null); }}
            className={`flex-1 py-2 text-xs font-medium text-center transition-colors ${
              mode === "login"
                ? "text-teal-700 border-b-2 border-teal-700 font-semibold"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); if (setAuthError) setAuthError(null); }}
            className={`flex-1 py-2 text-xs font-medium text-center transition-colors ${
              mode === "register"
                ? "text-teal-700 border-b-2 border-teal-700 font-semibold"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Create New Account
          </button>
        </div>

        {/* Form Error Banner */}
        {authError && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 font-sans flex items-start gap-2">
            <span className="material-symbols-outlined text-sm text-rose-600 mt-0.5">error</span>
            <span>{authError}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          {mode === "register" && (
            <div>
              <label className="block text-[11px] font-medium text-slate-700 uppercase mb-1">
                Full Name / Clinician Title
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Dr. Sarah Connor, MD"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-teal-700 transition-colors"
              />
            </div>
          )}

          <div>
            <label className="block text-[11px] font-medium text-slate-700 uppercase mb-1">
              Institutional Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="clinician@hospital.org"
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-teal-700 transition-colors"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-700 uppercase mb-1">
              Secure Password
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-teal-700 transition-colors"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 rounded-lg text-white font-sans text-xs font-semibold tracking-wide transition-all flex items-center justify-center gap-2 shadow-sm"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">
                    {mode === "login" ? "key" : "how_to_reg"}
                  </span>
                  <span>{mode === "login" ? "ACCESS COMMAND CENTER" : "CREATE CLINICAL ACCOUNT"}</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Security Notice */}
        <div className="mt-4 pt-3 border-t border-slate-100 text-center">
          <p className="text-[11px] text-slate-400">
            Protected by 256-bit JWT Encryption &amp; Bcrypt Hashing.
          </p>
        </div>
      </div>
    </div>
  );
}
