import React, { useState, useEffect } from "react";
import {
  User,
  ShieldCheck,
  Save,
  RefreshCw,
  Sliders,
  CheckCircle,
  Activity,
  HeartPulse,
  Info,
  Calendar,
  Users,
  PhoneCall,
  Lock
} from "lucide-react";

export function PatientProfilePanel({ staticProfile, onUpdateProfile, user, patientProfile, onOpenOnboarding }) {
  // Helper to resolve genuine stored values without fabricating synthetic numbers
  const resolveInitialValue = (field) => {
    if (patientProfile && patientProfile[field] !== undefined && patientProfile[field] !== null) {
      return patientProfile[field];
    }
    if (staticProfile && staticProfile[field] !== undefined && staticProfile[field] !== null) {
      return staticProfile[field];
    }
    return null;
  };

  const [profile, setProfile] = useState(() => ({
    age: resolveInitialValue("age"),
    bmi: resolveInitialValue("bmi"),
    diabetes_duration_years: resolveInitialValue("diabetes_duration_years"),
    hba1c: resolveInitialValue("hba1c"),
    glycated_albumin: resolveInitialValue("glycated_albumin"),
    fasting_glucose: resolveInitialValue("fasting_glucose"),
    fasting_c_peptide: resolveInitialValue("fasting_c_peptide"),
    macrovascular_comp_count: resolveInitialValue("macrovascular_comp_count"),
    microvascular_comp_count: resolveInitialValue("microvascular_comp_count"),
    is_t1dm: resolveInitialValue("is_t1dm")
  }));

  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [statusType, setStatusType] = useState(null);

  useEffect(() => {
    const source = patientProfile || staticProfile;
    if (source) {
      setProfile({
        age: source.age ?? null,
        bmi: source.bmi ?? null,
        diabetes_duration_years: source.diabetes_duration_years ?? null,
        hba1c: source.hba1c ?? null,
        glycated_albumin: source.glycated_albumin ?? null,
        fasting_glucose: source.fasting_glucose ?? null,
        fasting_c_peptide: source.fasting_c_peptide ?? null,
        macrovascular_comp_count: source.macrovascular_comp_count ?? null,
        microvascular_comp_count: source.microvascular_comp_count ?? null,
        is_t1dm: source.is_t1dm ?? null
      });
    }
  }, [staticProfile, patientProfile]);

  const handleChange = (field, val) => {
    if (val === "" || val === null || val === undefined) {
      setProfile((prev) => ({ ...prev, [field]: null }));
    } else {
      const parsed = parseFloat(val);
      setProfile((prev) => ({ ...prev, [field]: isNaN(parsed) ? null : parsed }));
    }
    setStatusMessage(null);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!onUpdateProfile) return;
    setIsSaving(true);
    setStatusMessage(null);
    try {
      await onUpdateProfile(profile);
      setStatusType("success");
      setStatusMessage("Profile covariates saved successfully.");
    } catch (err) {
      setStatusType("error");
      setStatusMessage(`Save failed: ${err.message || "Unknown error"}`);
    } finally {
      setIsSaving(false);
    }
  };

  const displayName = user?.full_name || user?.name || patientProfile?.patient_display_id || "—";
  const displayId = patientProfile?.patient_display_id || (patientProfile?.id ? `PT-${patientProfile.id.slice(0, 8).toUpperCase()}` : "—");

  const formatVal = (val, suffix = "") => {
    if (val === null || val === undefined || val === "" || isNaN(val)) {
      return "Not provided";
    }
    return `${val}${suffix}`;
  };

  const diagnosis = profile.is_t1dm === 1.0 || profile.is_t1dm === 1
    ? "Type 1 Diabetes Mellitus"
    : profile.is_t1dm === 0.0 || profile.is_t1dm === 0
    ? "Type 2 Diabetes Mellitus"
    : "Not provided";

  return (
    <div className="flex flex-col w-full space-y-6">
      {/* Header Banner with Clinical Identity Strip */}
      <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-col gap-space-xs">
          <div className="flex items-center gap-space-xs">
            <span className="font-code-sm text-code-sm text-primary uppercase font-semibold">
              Patient Record File
            </span>
            <span className="text-outline-variant">•</span>
            <span className="font-label-sm text-label-sm text-on-surface-variant">
              Validated Electronic Health Record
            </span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface font-semibold">
            Patient Clinical Profile &amp; Physiological Phenotype
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Demographics, therapeutic configuration, sensor calibration, and model adaptation status
          </p>
        </div>

        <div className="bg-surface-container-low px-space-md py-space-sm rounded-lg flex flex-col sm:flex-row items-start sm:items-center gap-space-md self-start lg:self-auto border border-surface-container">
          <div className="flex items-center gap-space-sm">
            <div className="w-10 h-10 rounded-full bg-surface-container text-on-surface flex items-center justify-center font-headline-sm">
              <User className="w-5 h-5 text-primary" />
            </div>
            <div className="flex flex-col">
              <span className="font-label-md text-label-md text-on-surface font-semibold">
                Patient: {displayName}
              </span>
              <span className="font-code-sm text-code-sm text-on-surface-variant">
                Record ID: {displayId}
              </span>
            </div>
          </div>
          <div className="hidden sm:block w-px h-8 bg-surface-container-high"></div>
          <div className="flex flex-col">
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Diagnosis: {diagnosis}
            </span>
            <div className="flex items-center gap-space-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
              <span className="font-label-sm text-label-sm text-primary font-semibold">
                Profile: {patientProfile?.id ? "Persisted Record" : "Covariate Baseline"}
              </span>
            </div>
          </div>
          {onOpenOnboarding && (
            <button
              type="button"
              onClick={onOpenOnboarding}
              className="px-3 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-colors shrink-0"
            >
              <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
              <span>Import CGM Data</span>
            </button>
          )}
        </div>
      </div>

      {/* Status banner if saving */}
      {statusMessage && (
        <div
          className={`p-space-sm rounded-lg font-mono text-xs flex items-center gap-2 border ${
            statusType === "success"
              ? "bg-[#22c55e]/10 border-[#22c55e]/30 text-[#16a34a]"
              : "bg-error/10 border-error/30 text-error"
          }`}
        >
          {statusType === "success" ? <CheckCircle className="w-4 h-4" /> : <Info className="w-4 h-4" />}
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Top Row: 3 Structured Cards (Asymmetric Bento Grid) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        {/* Card 1: Clinical Demographics & Metabolic Phenotype (4 cols) */}
        <div className="lg:col-span-4 bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-space-sm mb-space-md border-b border-surface-container">
              <div className="flex items-center gap-space-xs">
                <Activity className="w-4 h-4 text-primary" />
                <h2 className="font-headline-sm text-headline-sm text-on-surface">Metabolic Phenotype</h2>
              </div>
              <span className="px-space-xs py-0.5 rounded bg-surface-container font-code-sm text-code-sm text-primary font-semibold">
                {patientProfile?.id ? "Persisted Record" : "Covariate Profile"}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-space-xs bg-surface-container-low p-space-sm rounded-lg mb-space-md border border-surface-container">
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Age</span>
                <span className="font-label-md text-label-md text-on-surface font-semibold mt-1">
                  {formatVal(profile.age, " yrs")}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm text-on-surface-variant">BMI</span>
                <span className="font-label-md text-label-md text-on-surface font-semibold mt-1">
                  {formatVal(profile.bmi)}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Duration</span>
                <span className="font-label-md text-label-md text-on-surface font-semibold mt-1">
                  {formatVal(profile.diabetes_duration_years, " yrs")}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-space-sm rounded-lg bg-surface-container-low mb-space-md border border-surface-container">
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm text-on-surface-variant">
                  Glycated Hemoglobin (HbA1c)
                </span>
                <span className="font-body-sm text-body-sm text-outline">
                  {profile.hba1c != null ? "Laboratory record" : "Unspecified"}
                </span>
              </div>
              <div className="flex items-baseline gap-space-xs">
                <span className="font-telemetry-metric text-telemetry-metric text-primary font-bold">
                  {formatVal(profile.hba1c, " mmol/mol")}
                </span>
              </div>
            </div>

            <div className="space-y-space-xs">
              <div className="flex justify-between items-center py-space-xs text-sm">
                <span className="text-on-surface-variant font-medium">Fasting Glucose</span>
                <span className="font-code-sm text-code-sm text-on-surface font-semibold">
                  {formatVal(profile.fasting_glucose, " mg/dL")}
                </span>
              </div>
              <div className="flex justify-between items-center py-space-xs text-sm">
                <span className="text-on-surface-variant font-medium">C-Peptide</span>
                <span className="font-code-sm text-code-sm text-on-surface font-semibold">
                  {formatVal(profile.fasting_c_peptide, " ng/mL")}
                </span>
              </div>
              <div className="flex justify-between items-center py-space-xs text-sm">
                <span className="text-on-surface-variant font-medium">Glycated Albumin</span>
                <span className="font-code-sm text-code-sm text-on-surface font-semibold">
                  {formatVal(profile.glycated_albumin, "%")}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-space-md pt-space-sm bg-surface-container-low p-space-sm rounded-lg flex items-center justify-between border border-surface-container">
            <span className="font-body-sm text-body-sm text-on-surface-variant">Circadian ISF Drift Variance</span>
            <span className="font-code-sm text-code-sm text-tertiary font-semibold">Baseline Active</span>
          </div>
        </div>

        {/* Card 2: Telemetry & Ingestion Contract (4 cols) */}
        <div className="lg:col-span-4 bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-space-sm mb-space-md border-b border-surface-container">
              <div className="flex items-center gap-space-xs">
                <Activity className="w-4 h-4 text-secondary" />
                <h2 className="font-headline-sm text-headline-sm text-on-surface">Telemetry &amp; Model Contract</h2>
              </div>
              <div className="flex items-center gap-1.5 px-space-xs py-0.5 rounded bg-surface-container">
                <span className="w-2 h-2 rounded-full bg-outline"></span>
                <span className="font-code-sm text-code-sm text-on-surface-variant font-medium">Database Ingestion (REST)</span>
              </div>
            </div>

            <div className="bg-surface-container-low p-space-sm rounded-lg mb-space-md flex flex-col gap-space-xs border border-surface-container">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <HeartPulse className="w-4 h-4 text-primary" />
                  <span className="font-label-md text-label-md text-on-surface font-semibold">
                    Continuous Glucose Monitor
                  </span>
                </div>
                <span className="font-code-sm text-code-sm text-tertiary font-semibold">Persisted Stream</span>
              </div>
              <div className="flex items-center justify-between mt-space-xs">
                <span className="font-body-sm text-body-sm text-on-surface-variant">Source Telemetry Sampling</span>
                <span className="font-code-sm text-code-sm text-on-surface font-semibold">
                  5-min raw &rarr; 15-min resampled
                </span>
              </div>
              <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                <div className="bg-primary h-full w-full"></div>
              </div>
              <div className="grid grid-cols-2 gap-space-xs pt-space-xs mt-space-xs">
                <div className="flex flex-col">
                  <span className="font-body-sm text-body-sm text-outline block">Model Input Window</span>
                  <span className="font-label-sm text-label-sm text-primary font-semibold">96 steps (24h @ 15m)</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-body-sm text-body-sm text-outline block">Forecast Horizon</span>
                  <span className="font-label-sm text-label-sm text-on-surface font-semibold">20 steps (5h @ 15m)</span>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-space-xs border border-surface-container">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <Sliders className="w-4 h-4 text-secondary" />
                  <span className="font-label-md text-label-md text-on-surface font-semibold">
                    Dynamic Tensor Schema
                  </span>
                </div>
                <span className="font-code-sm text-code-sm text-on-surface-variant font-semibold">
                  22 Channels
                </span>
              </div>
              <div className="flex items-center justify-between mt-space-xs">
                <span className="font-body-sm text-body-sm text-on-surface-variant">Pump Interface Status</span>
                <span className="font-code-sm text-code-sm text-on-surface-variant font-medium">Not Connected</span>
              </div>
              <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                <div className="bg-secondary/40 h-full w-full"></div>
              </div>
              <div className="flex items-start gap-space-xs mt-space-xs pt-space-xs">
                <Info className="w-4 h-4 text-outline mt-0.5 shrink-0" />
                <div className="flex flex-col">
                  <span className="font-label-sm text-label-sm text-on-surface">Insulin Delivery Data</span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Self-reported bolus events
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-space-md flex items-center justify-between p-space-sm rounded-lg bg-surface-container-low border border-surface-container">
            <span className="font-body-sm text-body-sm text-on-surface-variant">Hardware Connectivity</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant font-medium">No Direct Live Stream (REST Sync)</span>
          </div>
        </div>

        {/* Card 3: Model Personalization & Calibration (4 cols) */}
        <div className="lg:col-span-4 bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-space-sm mb-space-md border-b border-surface-container">
              <div className="flex items-center gap-space-xs">
                <Sliders className="w-4 h-4 text-primary" />
                <h2 className="font-headline-sm text-headline-sm text-on-surface">Model Personalization</h2>
              </div>
              <span className="px-space-xs py-0.5 rounded bg-primary/10 font-code-sm text-code-sm text-primary font-semibold border border-primary/20">
                Combination C Active
              </span>
            </div>

            <div className="p-space-sm rounded-lg bg-surface-container-low mb-space-md border border-surface-container">
              <div className="flex items-center justify-between">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Model Parameterization</span>
                <span className="font-code-sm text-code-sm text-primary font-semibold">Active</span>
              </div>
              <div className="flex items-baseline gap-space-xs my-space-xs">
                <span className="font-headline-sm text-headline-sm text-on-surface">
                  V1 Frozen Neural + ODE
                </span>
              </div>
              <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                <div className="bg-primary h-full w-full"></div>
              </div>
            </div>

            <div className="space-y-space-xs">
              <div className="p-space-xs rounded bg-surface-container-low flex flex-col border border-surface-container">
                <span className="font-body-sm text-body-sm text-outline">Configuration Status</span>
                <span className="font-label-md text-label-md text-primary font-semibold">
                  Standard Baseline Profile
                </span>
              </div>
              <div className="p-space-xs rounded bg-surface-container-low flex items-center justify-between border border-surface-container">
                <span className="font-body-sm text-body-sm text-on-surface-variant">Uncertainty Engine</span>
                <span className="font-code-sm text-code-sm text-on-surface font-medium">
                  Phase-13 Regime Disagreement
                </span>
              </div>
              <div className="p-space-xs rounded bg-surface-container-low flex items-center justify-between border border-surface-container">
                <span className="font-body-sm text-body-sm text-on-surface-variant">Missing Factors</span>
                <span className="font-code-sm text-code-sm text-outline font-semibold">
                  Production Decoupled (0)
                </span>
              </div>
            </div>
          </div>

          <div className="mt-space-md pt-space-sm flex flex-col gap-space-xs border-t border-surface-container">
            <button
              type="button"
              disabled
              className="w-full h-8 rounded bg-surface-container/50 text-on-surface-variant font-label-sm text-label-sm font-medium flex items-center justify-center gap-space-xs border border-surface-container cursor-not-allowed opacity-75"
              title="Model calibration parameters are frozen in V1 production (weights and ODE adaptation parameters immutable)."
            >
              <Lock className="w-3.5 h-3.5 text-outline" />
              <span>Model Calibration Cycle: Frozen V1 Invariant</span>
            </button>
            <span className="font-body-sm text-body-sm text-outline text-center">
              Runtime recalibration is disabled. V1 weights and ODE parameters (&eta;<sub>S<sub>I</sub></sub> = 0.04, &beta; = 0.7) are frozen.
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Row: Split Strategic Modules (7 cols / 5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        {/* Left: Covariate Calibration Form (7 cols) */}
        <div className="lg:col-span-7 bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-space-sm mb-space-md border-b border-surface-container">
              <div className="flex items-center gap-space-xs">
                <Sliders className="w-4 h-4 text-primary" />
                <h2 className="font-headline-sm text-headline-sm text-on-surface">
                  Clinical Covariates Configuration
                </h2>
              </div>
              <span className="px-space-xs py-0.5 rounded bg-surface-container font-code-sm text-code-sm text-on-surface-variant font-medium">
                StandardScaler Scaled
              </span>
            </div>

            <form onSubmit={handleSave} className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Age (years)</label>
                <input
                  type="number"
                  step="1"
                  placeholder="Not provided"
                  value={profile.age ?? ""}
                  onChange={(e) => handleChange("age", e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Body Mass Index (BMI)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="Not provided"
                  value={profile.bmi ?? ""}
                  onChange={(e) => handleChange("bmi", e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Diabetes Duration (years)</label>
                <input
                  type="number"
                  step="0.5"
                  placeholder="Not provided"
                  value={profile.diabetes_duration_years ?? ""}
                  onChange={(e) => handleChange("diabetes_duration_years", e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">HbA1c (mmol/mol)</label>
                <input
                  type="number"
                  step="0.5"
                  placeholder="Not provided"
                  value={profile.hba1c ?? ""}
                  onChange={(e) => handleChange("hba1c", e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Glycated Albumin (%)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="Not provided"
                  value={profile.glycated_albumin ?? ""}
                  onChange={(e) => handleChange("glycated_albumin", e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Fasting Glucose (mg/dL)</label>
                <input
                  type="number"
                  step="1"
                  placeholder="Not provided"
                  value={profile.fasting_glucose ?? ""}
                  onChange={(e) => handleChange("fasting_glucose", e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Fasting C-Peptide (ng/mL)</label>
                <input
                  type="number"
                  step="0.05"
                  placeholder="Not provided"
                  value={profile.fasting_c_peptide ?? ""}
                  onChange={(e) => handleChange("fasting_c_peptide", e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Diabetes Type</label>
                <select
                  value={profile.is_t1dm !== null && profile.is_t1dm !== undefined ? profile.is_t1dm : ""}
                  onChange={(e) => handleChange("is_t1dm", e.target.value === "" ? null : parseFloat(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
                >
                  <option value="">Not provided</option>
                  <option value={1.0}>Type 1 Diabetes (T1DM)</option>
                  <option value={0.0}>Type 2 Diabetes (T2DM)</option>
                </select>
              </div>

              <div className="sm:col-span-2 pt-2">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="w-full py-2 bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md font-semibold rounded-lg flex items-center justify-center gap-2 shadow-sm transition-all"
                >
                  <Save className="w-4 h-4" />
                  <span>{isSaving ? "Saving Covariates..." : "Save Phenotypic Covariates"}</span>
                </button>
              </div>
            </form>
          </div>

          <div className="mt-space-md pt-space-sm bg-surface-container-low p-space-sm rounded-lg flex items-center justify-between border border-surface-container">
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Covariate Baseline Specification
            </span>
            <span className="font-code-sm text-code-sm text-on-surface-variant font-semibold">
              Standard Baseline Profile
            </span>
          </div>
        </div>

        {/* Right: Care Management (5 cols) */}
        <div className="lg:col-span-5 bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-space-sm mb-space-md border-b border-surface-container">
              <div className="flex items-center gap-space-xs">
                <Users className="w-4 h-4 text-primary" />
                <h2 className="font-headline-sm text-headline-sm text-on-surface">Care Management</h2>
              </div>
              <span className="px-space-xs py-0.5 rounded bg-surface-container-low font-code-sm text-code-sm text-on-surface-variant font-medium">
                Not configured
              </span>
            </div>

            <div className="space-y-space-sm">
              <div className="p-space-sm rounded-lg bg-surface-container-low flex items-center justify-between border border-surface-container">
                <div className="flex items-center gap-space-sm">
                  <div className="w-10 h-10 rounded-full bg-surface-container text-on-surface-variant flex items-center justify-center">
                    <Users className="w-5 h-5 text-on-surface-variant" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-md text-label-md text-on-surface font-semibold">
                      Care Team Assignment
                    </span>
                    <span className="font-body-sm text-body-sm text-on-surface-variant font-medium">
                      Not configured
                    </span>
                  </div>
                </div>
                <span className="px-space-xs py-0.5 rounded bg-surface-container font-code-sm text-code-sm text-on-surface-variant font-medium">
                  Not configured
                </span>
              </div>

              <div className="p-space-sm rounded-lg bg-surface-container-low flex items-center justify-between border border-surface-container">
                <div className="flex items-center gap-space-sm">
                  <div className="w-10 h-10 rounded-full bg-surface-container text-on-surface-variant flex items-center justify-center">
                    <PhoneCall className="w-5 h-5 text-on-surface-variant" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-md text-label-md text-on-surface font-semibold">
                      Support Contact
                    </span>
                    <span className="font-body-sm text-body-sm text-on-surface-variant font-medium">
                      Not configured
                    </span>
                  </div>
                </div>
                <span className="px-space-xs py-0.5 rounded bg-surface-container font-code-sm text-code-sm text-on-surface-variant font-medium">
                  Not configured
                </span>
              </div>

              <div className="p-space-sm rounded-lg bg-surface-container-low flex items-center justify-between border border-surface-container">
                <div className="flex items-center gap-space-sm">
                  <div className="w-10 h-10 rounded-full bg-surface-container text-on-surface-variant flex items-center justify-center">
                    <HeartPulse className="w-5 h-5 text-on-surface-variant" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-md text-label-md text-on-surface font-semibold">
                      Emergency Contact
                    </span>
                    <span className="font-body-sm text-body-sm text-on-surface-variant">
                      Not configured
                    </span>
                  </div>
                </div>
                <span className="px-space-xs py-0.5 rounded bg-surface-container font-code-sm text-code-sm text-on-surface-variant font-medium">
                  Not configured
                </span>
              </div>
            </div>
          </div>

          <div className="mt-space-md pt-space-sm flex items-center justify-between border-t border-surface-container text-on-surface-variant text-sm">
            <span>Follow-up Schedule: Not configured</span>
            <Calendar className="w-4 h-4 text-outline" />
          </div>
        </div>
      </div>
    </div>
  );
}
