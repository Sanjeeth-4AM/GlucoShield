import React from "react";
import {
  Shield,
  Layers,
  RefreshCw,
  Wifi,
  Menu,
  X,
  User as UserIcon,
  LogOut,
  Lock,
  Bell,
  CheckCircle2
} from "lucide-react";

export function Header({
  isDemoMode,
  setIsDemoMode,
  backendHealth,
  currentScenario,
  setCurrentScenario,
  onRefresh,
  isLoading,
  mobileMenuOpen,
  setMobileMenuOpen,
  user,
  isAuthenticated,
  patientProfile,
  onOpenAuthModal,
  onOpenOnboarding,
  onLogout,
  activePatientId = "PATIENT_A",
  onSelectPatient
}) {
  const patientDisplayName = patientProfile?.patient_display_id || (activePatientId === "PATIENT_B" ? "Patient B (Hyperglycemic 24h Profile)" : "Patient A (Stable Euglycemic)");
  const patientId = patientProfile?.id ? patientProfile.id.slice(0, 10) : (activePatientId === "PATIENT_B" ? "PT-B" : "PT-A");
  const isSynthetic = isDemoMode || Boolean(patientProfile?.patient_display_id?.startsWith("DEMO"));

  // Strictly derive diagnosis from dataset metadata — never infer or invent
  const diagnosis = patientProfile?.diabetes_type
    ? patientProfile.diabetes_type
    : (patientProfile?.is_t1dm === 1.0 || patientProfile?.is_t1dm === 1)
    ? "Type 1 Diabetes (T1D)"
    : (patientProfile?.is_t1dm === 0.0 || patientProfile?.is_t1dm === 0)
    ? "Type 2 Diabetes (T2D)"
    : "Not available";

  return (
    <header className="sticky top-0 z-40 h-16 bg-surface/90 backdrop-blur-xl border-b border-surface-container flex items-center justify-between px-4 sm:px-6 lg:px-7 shadow-[0_1px_8px_rgba(0,0,0,0.03)] select-none max-w-full overflow-hidden">
      {/* Left: Mobile Trigger & Patient Badge */}
      <div className="flex items-center gap-space-sm min-w-0">
        <button
          onClick={() => setMobileMenuOpen && setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden text-on-surface-variant hover:text-on-surface p-1.5 rounded-lg bg-surface-container shrink-0"
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <div className="flex items-center gap-space-sm min-w-0">
          <div className="px-space-sm py-1 bg-surface-container-low rounded flex items-center gap-space-xs border border-surface-container min-w-0">
            <span className="material-symbols-outlined text-primary text-base shrink-0">person</span>
            <span className="font-label-md text-label-md text-on-surface font-semibold truncate max-w-[120px] sm:max-w-[180px]">
              Patient: {patientDisplayName}
            </span>
            <span className="font-code-sm text-code-sm text-on-surface-variant hidden md:inline shrink-0">
              ({patientId})
            </span>
            <span className="text-outline-variant hidden md:inline">•</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant font-medium hidden md:inline shrink-0" data-testid="header-patient-diagnosis">
              {diagnosis}
            </span>
          </div>
        </div>
      </div>

      {/* Center: Model Status & Scenario Switcher */}
      <div className="hidden xl:flex items-center gap-space-md shrink-0">
        <div className="flex items-center gap-space-xs px-space-sm py-1 rounded bg-surface-container-low border border-surface-container">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
          <span className="font-label-sm text-label-sm text-on-surface font-medium">Model: Combination C</span>
          <span className="font-code-sm text-code-sm text-primary font-semibold">Configured • Combination C</span>
        </div>

        {/* Real Cohort Patient Switcher */}
        <div className="flex items-center gap-1 bg-surface-container-low p-1 rounded-lg border border-surface-container">
          <span className="text-on-surface-variant px-2 font-mono text-[10px] flex items-center gap-1 font-semibold uppercase">
            <UserIcon className="w-3 h-3 text-primary" />
            Patient:
          </span>
          <button
            onClick={() => onSelectPatient && onSelectPatient("PATIENT_A")}
            data-testid="header-patient-a-btn"
            className={`px-2.5 py-1 rounded font-mono text-[11px] transition-all flex items-center gap-1.5 ${
              activePatientId === "PATIENT_A"
                ? "bg-teal-700 text-white font-bold shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400"></span>
            <span>Patient A (Stable)</span>
          </button>
          <button
            onClick={() => onSelectPatient && onSelectPatient("PATIENT_B")}
            data-testid="header-patient-b-btn"
            className={`px-2.5 py-1 rounded font-mono text-[11px] transition-all flex items-center gap-1.5 ${
              activePatientId === "PATIENT_B"
                ? "bg-amber-600 text-white font-bold shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-300"></span>
            <span>Patient B (Hyperglycemic 24h)</span>
          </button>
        </div>

        {/* Scenario Switcher */}
        <div className="flex items-center gap-1 bg-surface-container-low p-1 rounded-lg border border-surface-container">
          <span className="text-on-surface-variant px-2 font-mono text-[10px] hidden xl:flex items-center gap-1 font-semibold uppercase">
            <Layers className="w-3 h-3 text-primary" />
            Scenario:
          </span>
          {[
            { id: "stable", label: "Stable Baseline" },
            { id: "postprandial", label: "Postprandial Spike" },
            { id: "hypo_risk", label: "Hypo Risk" }
          ].map((scen) => (
            <button
              key={scen.id}
              onClick={() => setCurrentScenario(scen.id)}
              className={`px-2.5 py-1 rounded font-mono text-[11px] transition-all ${
                currentScenario === scen.id
                  ? "bg-primary text-on-primary font-bold shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {scen.label}
            </button>
          ))}
        </div>
      </div>

      {/* Right: Actions, Live/Demo & Auth */}
      <div className="flex items-center gap-space-sm shrink-0">
        {/* Guided Onboarding / CGM Ingestion */}
        {onOpenOnboarding && (
          <button
            onClick={onOpenOnboarding}
            data-testid="header-import-cgm-btn"
            title="Import CGM data from CSV"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-teal-50 hover:bg-teal-100 text-teal-800 text-xs font-semibold border border-teal-200 transition-colors shadow-2xs"
          >
            <span className="material-symbols-outlined text-[16px] text-teal-700">cloud_upload</span>
            <span className="hidden sm:inline">Import CGM</span>
          </button>
        )}

        {/* Recalculate / Refresh */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          title="Recalculate Run"
          className="flex items-center gap-1 px-space-sm py-1.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-semibold border border-surface-container transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-primary" : "text-primary"}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>

        {/* Live / Demo Mode Toggle */}
        <div className="hidden sm:flex items-center gap-0.5 bg-surface-container-low p-0.5 rounded border border-surface-container">
          <button
            onClick={() => setIsDemoMode(false)}
            data-testid="header-live-btn"
            className={`flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded transition-colors ${
              !isDemoMode
                ? "bg-primary text-on-primary font-bold shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            <Wifi className="w-3 h-3" />
            API Connected
          </button>
          <button
            onClick={() => setIsDemoMode(true)}
            data-testid="header-demo-btn"
            className={`flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded transition-colors ${
              isDemoMode
                ? "bg-secondary text-on-secondary font-bold shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            Demo
          </button>
        </div>

        {/* Demo Mode Isolation Disclaimer */}
        {isSynthetic && (
          <div className="hidden 2xl:flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 font-mono text-[10px] font-semibold tracking-wide">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            SYNTHETIC DEMONSTRATION DATA • SYSTEM VALIDATION ONLY • NOT CLINICAL EVIDENCE
          </div>
        )}

        {/* Auth / Account */}
        {isAuthenticated ? (
          <div className="flex items-center gap-space-xs bg-surface-container px-space-sm py-1 rounded border border-surface-container">
            <div className="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-xs">
              <UserIcon className="w-3.5 h-3.5" />
            </div>
            <span className="hidden md:inline text-xs font-semibold text-on-surface truncate max-w-[100px]">
              {user?.full_name || user?.email?.split("@")[0]}
            </span>
            <button
              onClick={onLogout}
              title="Sign out"
              className="text-on-surface-variant hover:text-error p-1 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuthModal}
            className="flex items-center gap-1 bg-primary text-on-primary px-space-sm py-1.5 rounded font-label-sm text-label-sm font-semibold shadow-sm hover:bg-primary-container transition-colors"
          >
            <Lock className="w-3 h-3" />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
}
