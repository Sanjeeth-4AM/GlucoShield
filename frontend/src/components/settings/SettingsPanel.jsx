import React, { useState } from "react";
import {
  Sliders,
  Cpu,
  Bell,
  Database,
  Shield,
  Save,
  RotateCcw,
  CheckCircle,
  Lock,
  Info
} from "lucide-react";

export function SettingsPanel({ backendHealth }) {
  const [activeDomain, setActiveDomain] = useState("clinical");
  const [tirLow, setTirLow] = useState(70);
  const [tirHigh, setTirHigh] = useState(180);
  const [urgentHypo, setUrgentHypo] = useState(54);
  const [urgentHyper, setUrgentHyper] = useState(200);
  const [confidenceCorridor, setConfidenceCorridor] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleReset = () => {
    setTirLow(70);
    setTirHigh(180);
    setUrgentHypo(54);
    setUrgentHyper(200);
    setConfidenceCorridor(true);
  };

  return (
    <div className="flex flex-col w-full space-y-6">
      {/* Top Banner / Clinical Context Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col gap-space-xs">
          <div className="flex items-center gap-space-sm">
            <h1 className="font-headline-xl text-headline-xl text-on-surface tracking-tight">
              System & Clinical Configuration
            </h1>
            <span className="px-space-sm py-0.5 rounded bg-surface-container-high text-primary font-code-sm text-code-sm font-semibold border border-surface-container">
              System Configuration
            </span>
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
            Manage model serving parameters, alert thresholds, system permissions, and monitoring configuration.
          </p>
        </div>

        {/* Metadata Badges */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-space-sm self-start md:self-center">
          <div className="bg-surface-container-lowest px-space-md py-space-sm rounded-lg shadow-sm border border-surface-container flex items-center gap-space-sm">
            <Shield className="w-5 h-5 text-primary" />
            <div className="flex flex-col text-left">
              <span className="font-label-sm text-label-sm text-on-surface font-semibold">
                GlucoShield System Configuration
              </span>
              <span className="font-code-sm text-code-sm text-on-surface-variant">
                Combination C Production
              </span>
            </div>
          </div>
        </div>
      </div>

      {saveSuccess && (
        <div className="mb-space-md p-space-sm rounded-lg bg-[#22c55e]/10 border border-[#22c55e]/30 text-[#16a34a] font-mono text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />
          <span>Configuration saved successfully and updated in clinical runtime.</span>
        </div>
      )}

      {/* Main 12-Column Responsive Workspace */}
      <div className="grid grid-cols-12 gap-4 sm:gap-6 items-start">
        {/* Sub-Navigation Navigation Rail (3 Cols) */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-space-sm">
          <div className="bg-surface-container-lowest p-space-sm rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-xs">
            <span className="px-space-sm py-space-xs font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
              Configuration Domains
            </span>

            {[
              { id: "clinical", label: "Clinical Parameters", icon: Sliders },
              { id: "serving", label: "Model & Algorithmic Serving", icon: Cpu, badge: "Combination C" },
              { id: "alerts", label: "Alert & Escalation Protocols", icon: Bell },
              { id: "connections", label: "Data Connections", icon: Database, badge: "Available" },
              { id: "security", label: "Security & Access Control", icon: Shield }
            ].map((domain) => {
              const Icon = domain.icon;
              const isActive = activeDomain === domain.id;
              return (
                <button
                  key={domain.id}
                  onClick={() => setActiveDomain(domain.id)}
                  className={`w-full flex items-center justify-between px-space-md py-space-sm rounded-lg font-label-md text-label-md transition-all text-left ${
                    isActive
                      ? "bg-primary-container text-on-primary-container font-semibold shadow-sm"
                      : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                  }`}
                >
                  <div className="flex items-center gap-space-sm">
                    <Icon className="w-4 h-4" />
                    <span>{domain.label}</span>
                  </div>
                  {domain.badge && (
                    <span className="font-code-sm text-[10px] px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface-variant">
                      {domain.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Quick Institutional Presets / Audit Card */}
          <div className="bg-surface-container-low p-space-md rounded-xl flex flex-col gap-space-sm border border-surface-container">
            <div className="flex items-center gap-space-xs text-on-surface font-label-sm text-label-sm font-semibold">
              <Sliders className="w-4 h-4 text-secondary" />
              <span>Glycemic Target Configuration</span>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Adjust standard clinical boundaries for in-range telemetry tracking.
            </p>
            <div className="pt-space-xs flex items-center justify-between font-mono text-xs">
              <span className="text-on-surface-variant">Combination C Production</span>
              <span className="text-primary font-semibold">ADA 2026 Standards</span>
            </div>
          </div>
        </div>

        {/* Main Settings Canvas (9 Cols) */}
        <div className="col-span-12 lg:col-span-9 flex flex-col gap-space-lg">
          {/* SECTION 1: Clinical Target Ranges & Glycemic Thresholds */}
          <section className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-lg">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-space-sm">
                <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
                  <Sliders className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">
                    Clinical Target Ranges &amp; Glycemic Thresholds
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Physiological boundary states and predictive boundary detection settings
                  </p>
                </div>
              </div>
              <span className="px-space-sm py-space-xs rounded bg-surface-container font-code-sm text-code-sm text-on-surface-variant">
                Standard Protocol
              </span>
            </div>

            {/* Target Visual Band Representation */}
            <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col gap-space-md border border-surface-container">
              <div className="flex items-center justify-between text-on-surface">
                <span className="font-label-md text-label-md font-semibold">
                  Standard Clinical In-Range Envelope (TIR)
                </span>
                <div className="flex items-center gap-space-xs">
                  <span className="font-telemetry-metric text-telemetry-metric text-primary font-bold">
                    {tirLow} – {tirHigh}
                  </span>
                  <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">mg/dL</span>
                </div>
              </div>

              {/* Glycemic Strip Visualizer */}
              <div className="relative w-full h-8 bg-surface-container-high rounded overflow-hidden flex text-xs select-none">
                <div className="h-full bg-error-container/60 flex items-center justify-center font-bold text-on-error-container" style={{ width: "15%" }}>
                  &lt;54
                </div>
                <div className="h-full bg-amber-100 flex items-center justify-center text-amber-800 font-medium" style={{ width: "10%" }}>
                  54–70
                </div>
                <div className="h-full bg-tertiary-container flex items-center justify-center font-bold text-on-tertiary-container uppercase tracking-wider text-[11px]" style={{ width: "50%" }}>
                  Target Zone (70–180 mg/dL)
                </div>
                <div className="h-full bg-amber-100 flex items-center justify-center text-amber-800 font-medium" style={{ width: "10%" }}>
                  180–200
                </div>
                <div className="h-full bg-error-container/40 flex items-center justify-center font-bold text-on-error-container" style={{ width: "15%" }}>
                  &gt;200
                </div>
              </div>

              <div className="flex justify-between font-code-sm text-code-sm text-on-surface-variant">
                <span>Severe Hypo: &lt;54</span>
                <span>Euglycemic Range: 70–180</span>
                <span>Severe Hyper: &gt;200</span>
              </div>
            </div>

            {/* Metric Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
              <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col justify-between border border-surface-container">
                <div>
                  <span className="font-label-sm text-label-sm text-on-surface-variant uppercase">
                    Critical Hypoglycemia Alert
                  </span>
                  <div className="flex items-baseline gap-space-xs mt-space-xs">
                    <span className="font-telemetry-display text-telemetry-display text-error font-bold">
                      {urgentHypo}
                    </span>
                    <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">mg/dL</span>
                  </div>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-sm">
                  Urgent alert tier triggers telemetry push to care dashboard.
                </p>
              </div>

              <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col justify-between border border-surface-container">
                <div>
                  <span className="font-label-sm text-label-sm text-on-surface-variant uppercase">
                    Hyperglycemia Sustained
                  </span>
                  <div className="flex items-baseline gap-space-xs mt-space-xs">
                    <span className="font-telemetry-display text-telemetry-display text-on-surface font-bold">
                      {urgentHyper}
                    </span>
                    <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">mg/dL</span>
                  </div>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-sm">
                  Flagged after continuous duration exceeding 45 minutes.
                </p>
              </div>

              <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col justify-between border border-surface-container">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-label-sm text-label-sm text-on-surface-variant uppercase">
                      Projection Horizon
                    </span>
                    <Lock className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <div className="flex items-baseline gap-space-xs mt-space-xs">
                    <span className="font-telemetry-display text-telemetry-display text-primary font-bold">5.0</span>
                    <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">Hours</span>
                  </div>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-sm">
                  20 steps / 15-min intervals. Clinically frozen.
                </p>
              </div>
            </div>
          </section>

          {/* SECTION 2: Model Serving & Personalization Configuration */}
          <section className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-lg">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-space-sm">
                <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">
                    Model Serving &amp; Personalization Configuration
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Multi-compartmental ODE kinetics and neural forecaster inference orchestrator
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-space-xs px-space-sm py-space-xs rounded bg-surface-container-high border border-surface-container">
                <span className={`w-2 h-2 rounded-full ${backendHealth?.healthy !== false ? "bg-tertiary" : "bg-warning"}`}></span>
                <span className="font-code-sm text-code-sm text-on-surface font-semibold">
                  {backendHealth?.healthy !== false ? (backendHealth?.model || "Combination C Serving Online") : "Offline / Standby"}
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-space-md">
              {/* Architecture Selection Line */}
              <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col md:flex-row md:items-center justify-between gap-space-md border border-surface-container">
                <div className="flex flex-col">
                  <span className="font-label-md text-label-md text-on-surface font-semibold">
                    Production Serving Architecture
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Combination C physiological inference architecture (V1 Neural + Phase-13 Uncertainty)
                  </span>
                </div>
                <div className="flex items-center gap-space-sm">
                  <span className="px-space-sm py-space-xs rounded bg-surface-container-lowest font-code-sm text-code-sm text-primary font-semibold shadow-sm border border-surface-container">
                    Combination C (Active)
                  </span>
                </div>
              </div>

              {/* Parameter Calibration Policy */}
              <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col md:flex-row md:items-center justify-between gap-space-md border border-surface-container">
                <div className="flex flex-col">
                  <span className="font-label-md text-label-md text-on-surface font-semibold">
                    Parameter Calibration Policy
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Model weights and Hovorka ODE physiological parameters are frozen in Combination C serving; runtime online retraining is disabled.
                  </span>
                </div>
                <div className="flex items-center gap-space-sm">
                  <span className="px-space-sm py-space-xs rounded bg-surface-container-lowest font-code-sm text-code-sm text-primary font-semibold border border-surface-container">
                    Configured (Frozen Model)
                  </span>
                </div>
              </div>

              {/* Strict Science Policy Switch (Locked) */}
              <div className="p-space-md rounded-lg bg-surface-container-low flex items-center justify-between border border-surface-container">
                <div className="flex flex-col pr-space-md">
                  <div className="flex items-center gap-space-xs">
                    <span className="font-label-md text-label-md text-on-surface font-semibold">
                      Consumer Biometric Exclusion
                    </span>
                    <Lock className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Exclude uncalibrated consumer wearables from physiological inference pipeline.
                  </span>
                </div>
                <div className="flex items-center gap-space-sm">
                  <span className="font-code-sm text-code-sm text-primary font-semibold uppercase">
                    Enforced (Locked)
                  </span>
                  <div className="w-10 h-6 bg-primary rounded-full relative flex items-center px-0.5">
                    <div className="w-5 h-5 rounded-full bg-white ml-auto shadow-sm"></div>
                  </div>
                </div>
              </div>

              {/* Confidence Interval Envelopes */}
              <div className="p-space-md rounded-lg bg-surface-container-low flex items-center justify-between border border-surface-container">
                <div className="flex flex-col pr-space-md">
                  <span className="font-label-md text-label-md text-on-surface font-semibold">
                    Confidence Corridor Representation
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Phase-13 / regime-conditioned uncertainty bounds across all multi-horizon forecasting projections.
                  </span>
                </div>
                <div className="flex items-center gap-space-sm">
                  <span className="font-code-sm text-code-sm text-on-surface-variant">
                    {confidenceCorridor ? "Enabled" : "Disabled"}
                  </span>
                  <button
                    onClick={() => setConfidenceCorridor(!confidenceCorridor)}
                    className={`w-10 h-6 rounded-full relative flex items-center px-0.5 transition-colors ${
                      confidenceCorridor ? "bg-primary" : "bg-surface-container-high"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${
                        confidenceCorridor ? "ml-auto" : "mr-auto"
                      }`}
                    ></div>
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 3: Clinical Notification & Escalation Protocols */}
          <section className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-lg">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-space-sm">
                <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
                  <Bell className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">
                    Clinical Notification &amp; Escalation Protocols
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Automated system response routing and urgent hypoglycemia threshold notifications
                  </p>
                </div>
              </div>
              <span className="px-space-sm py-space-xs rounded bg-surface-container font-code-sm text-code-sm text-on-surface-variant">
                Active Protocol
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
              <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col justify-between gap-space-md border border-surface-container">
                <div>
                  <div className="flex items-center justify-between mb-space-xs">
                    <span className="font-label-md text-label-md text-on-surface font-semibold">
                      Urgent Hypo Prediction (&lt;70 mg/dL in 60m)
                    </span>
                    <span className="w-2 h-2 rounded-full bg-error animate-pulse"></span>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Triggers in-app banner alert and triage indicator when predicted glucose drops below threshold.
                  </p>
                </div>
                <div className="flex items-center justify-between pt-space-xs border-t border-surface-container">
                  <span className="font-code-sm text-code-sm text-primary font-semibold">In-App Alert Active</span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant font-medium">Synchronous Evaluation</span>
                </div>
              </div>

              <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col justify-between gap-space-md border border-surface-container">
                <div>
                  <div className="flex items-center justify-between mb-space-xs">
                    <span className="font-label-md text-label-md text-on-surface font-semibold">
                      Postprandial Variance Divergence
                    </span>
                    <span className="w-2 h-2 rounded-full bg-secondary"></span>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Alerts care team if postprandial glucose trajectory diverges &gt;25 mg/dL from simulated carbohydrate absorption curve within 90 minutes.
                  </p>
                </div>
                <div className="flex items-center justify-between pt-space-xs border-t border-surface-container">
                  <span className="font-code-sm text-code-sm text-on-surface font-semibold">Dashboard Flag Enabled</span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant font-medium">Silent In-App</span>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 4: System Access Control & Session Governance */}
          <section className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-lg">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-space-sm">
                <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">
                    System Access Control &amp; Session Governance
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    System security policies, session management, and user permissions
                  </p>
                </div>
              </div>
              <span className="px-space-sm py-space-xs rounded bg-surface-container-low text-tertiary font-code-sm text-code-sm font-semibold border border-surface-container">
                Active
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
              <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col gap-space-xs border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant uppercase">Session Timeout</span>
                <span className="font-telemetry-metric text-telemetry-metric text-on-surface font-bold">15 Minutes</span>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                  Automatic workstation session lock following idle duration threshold.
                </p>
              </div>

              <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col gap-space-xs border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant uppercase">Local Audit Trail</span>
                <span className="font-telemetry-metric text-telemetry-metric text-on-surface font-bold">System Audit Log</span>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                  Operational logging of all threshold updates and parameter modifications.
                </p>
              </div>

              <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col gap-space-xs border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant uppercase">Access Control</span>
                <span className="font-label-md text-label-md text-primary font-semibold">Role-Based Access</span>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                  Role-based privilege model active for standard application configuration scope.
                </p>
              </div>
            </div>
          </section>

          {/* SECTION 5: Form Action Bar */}
          <div className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border border-surface-container flex flex-col sm:flex-row items-center justify-between gap-space-md">
            <div className="flex items-center gap-space-sm text-on-surface-variant">
              <Info className="w-4 h-4 text-primary" />
              <span className="font-body-sm text-body-sm">
                All changes to physiological thresholds are committed to the system configuration log.
              </span>
            </div>
            <div className="flex items-center gap-space-sm w-full sm:w-auto">
              <button
                type="button"
                onClick={handleReset}
                className="w-full sm:w-auto px-space-md py-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm transition-colors border border-surface-container flex items-center justify-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5 text-on-surface-variant" />
                <span>Revert to Defaults</span>
              </button>
              <button
                type="button"
                onClick={handleSave}
                className="w-full sm:w-auto px-space-lg py-space-sm rounded-lg bg-primary hover:bg-primary-container text-on-primary font-label-sm text-label-sm font-semibold transition-all shadow-sm flex items-center justify-center gap-space-xs"
              >
                <Save className="w-4 h-4" />
                <span>Save Configuration Changes</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
