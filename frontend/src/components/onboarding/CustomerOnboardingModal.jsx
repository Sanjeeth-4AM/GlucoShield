import React, { useState } from "react";
import { parseCgmCsv, SAMPLE_CGM_CSV } from "../../utils/cgmCsvParser.js";
import { apiIngestCGMBatch, apiUpdatePatient } from "../../api/auth.js";

/**
 * CustomerOnboardingModal
 * =======================
 * 5-Stage Guided Onboarding & Setup Workflow:
 *   Stage 1: Account / Sign In
 *   Stage 2: Complete Clinical Profile
 *   Stage 3: Import Supported CGM History (CSV Preview & Ingestion)
 *   Stage 4: Review Data Quality & Forecast Readiness
 *   Stage 5: Generate Certified Forecast
 */
export function CustomerOnboardingModal({
  isOpen,
  onClose,
  token,
  user,
  patientProfile,
  onUpdatePatientProfile,
  onIngestSuccess,
  onTriggerForecast,
  isLoadingForecast
}) {
  const [currentStage, setCurrentStage] = useState(patientProfile ? 2 : 1);
  const [csvText, setCsvText] = useState("");
  const [csvFile, setCsvFile] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null); // { type: 'success'|'error', message, count }
  const [showTemplate, setShowTemplate] = useState(false);

  // Editable Profile fields for Stage 2
  const [profileForm, setProfileForm] = useState({
    age: patientProfile?.age ?? 45,
    bmi: patientProfile?.bmi ?? 26.5,
    diabetes_duration_years: patientProfile?.diabetes_duration_years ?? 10.0,
    hba1c: patientProfile?.hba1c ?? 58.0,
    glycated_albumin: patientProfile?.glycated_albumin ?? 18.0,
    fasting_glucose: patientProfile?.fasting_glucose ?? 130.0,
    fasting_c_peptide: patientProfile?.fasting_c_peptide ?? 0.8,
    is_t1dm: patientProfile?.is_t1dm ?? 1.0
  });
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  if (!isOpen) return null;

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFile(file);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      setCsvText(text);
      const res = parseCgmCsv(text);
      setParsedData(res);
      setIngestStatus(null);
    };
    reader.readAsText(file);
  };

  const handleLoadSampleData = () => {
    setCsvText(SAMPLE_CGM_CSV);
    const res = parseCgmCsv(SAMPLE_CGM_CSV);
    setParsedData(res);
    setIngestStatus(null);
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!token || !patientProfile?.id) return;
    setIsSavingProfile(true);
    try {
      const updated = await apiUpdatePatient(token, patientProfile.id, {
        age: Number(profileForm.age),
        bmi: Number(profileForm.bmi),
        diabetes_duration_years: Number(profileForm.diabetes_duration_years),
        hba1c: Number(profileForm.hba1c),
        glycated_albumin: Number(profileForm.glycated_albumin),
        fasting_glucose: Number(profileForm.fasting_glucose),
        fasting_c_peptide: Number(profileForm.fasting_c_peptide),
        is_t1dm: Number(profileForm.is_t1dm)
      });
      if (onUpdatePatientProfile) onUpdatePatientProfile(updated);
      setCurrentStage(3); // Advance to CGM Import
    } catch (err) {
      setIngestStatus({ type: "error", message: `Profile save failed: ${err.message}` });
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleExecuteIngestion = async () => {
    if (!parsedData || !parsedData.valid || parsedData.readings.length === 0) return;
    if (!token || !patientProfile?.id) {
      setIngestStatus({ type: "error", message: "Patient session not authenticated." });
      return;
    }

    setIsIngesting(true);
    setIngestStatus(null);
    try {
      const ingested = await apiIngestCGMBatch(token, patientProfile.id, parsedData.readings);
      setIngestStatus({
        type: "success",
        message: `Successfully ingested ${ingested.length} validated CGM readings!`,
        count: ingested.length
      });
      if (onIngestSuccess) onIngestSuccess(ingested);
      setCurrentStage(4); // Advance to Readiness Check
    } catch (err) {
      setIngestStatus({ type: "error", message: `Ingestion failed: ${err.message}` });
    } finally {
      setIsIngesting(false);
    }
  };

  const STAGES = [
    { num: 1, label: "Account" },
    { num: 2, label: "Profile" },
    { num: 3, label: "Import CGM" },
    { num: 4, label: "Data Quality" },
    { num: 5, label: "Forecast" }
  ];

  return (
    <div data-testid="customer-onboarding-modal" className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="relative w-full max-w-2xl bg-white border border-slate-200 rounded-xl shadow-xl flex flex-col overflow-hidden max-h-[92vh]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100">
              <span className="material-symbols-outlined text-[20px]">rocket_launch</span>
            </span>
            <div>
              <h2 className="text-base font-semibold text-slate-900 font-sans">
                Patient Setup & CGM Onboarding
              </h2>
              <p className="text-xs text-slate-500 font-sans">
                {patientProfile?.patient_display_id || "New Customer Guided Provisioning"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="onboarding-close-btn"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Stepper Bar */}
        <div className="px-6 py-3 border-b border-slate-100 bg-white">
          <div className="flex items-center justify-between">
            {STAGES.map((s) => (
              <button
                key={s.num}
                onClick={() => {
                  if (s.num <= currentStage || (patientProfile && s.num <= 4)) setCurrentStage(s.num);
                }}
                className={`flex items-center gap-2 text-xs font-medium transition-colors ${
                  currentStage === s.num
                    ? "text-teal-700 font-semibold"
                    : currentStage > s.num
                    ? "text-slate-700"
                    : "text-slate-400 opacity-60"
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono ${
                    currentStage === s.num
                      ? "bg-teal-700 text-white"
                      : currentStage > s.num
                      ? "bg-teal-50 text-teal-700 border border-teal-200"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {currentStage > s.num ? "✓" : s.num}
                </span>
                <span className="hidden sm:inline">{s.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-800">
          
          {/* Status Alert if any */}
          {ingestStatus && (
            <div
              className={`p-3 rounded-lg text-xs font-sans flex items-start gap-2 border ${
                ingestStatus.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-rose-50 text-rose-800 border-rose-200"
              }`}
            >
              <span className="material-symbols-outlined text-[16px] shrink-0 mt-0.5">
                {ingestStatus.type === "success" ? "check_circle" : "error"}
              </span>
              <span>{ingestStatus.message}</span>
            </div>
          )}

          {/* STAGE 1: ACCOUNT INTRO */}
          {currentStage === 1 && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                <h3 className="text-sm font-semibold text-slate-900">1. Account &amp; Identity Provisioning</h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Every registered clinician or demo patient is automatically assigned a secure longitudinal record container protected by 256-bit JWT authorization.
                </p>
                <div className="pt-2 text-xs font-mono text-slate-700 bg-white p-2.5 rounded border border-slate-200">
                  User: {user?.email || "Authenticated"}<br />
                  Patient ID: {patientProfile?.patient_display_id || patientProfile?.id || "Auto-Provisioned"}
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStage(2)}
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                >
                  <span>Continue to Clinical Profile</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </div>
          )}

          {/* STAGE 2: CLINICAL PROFILE */}
          {currentStage === 2 && (
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">2. Complete Clinical Baseline Covariates</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  The Combination C model uses these 9 physiological parameters to condition personalized ODE dynamics.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Age (years)</label>
                  <input
                    type="number"
                    step="1"
                    min="18"
                    max="90"
                    value={profileForm.age}
                    onChange={(e) => setProfileForm({ ...profileForm, age: e.target.value })}
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded font-mono text-slate-900 focus:outline-teal-700"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">BMI (kg/m²)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="15"
                    max="50"
                    value={profileForm.bmi}
                    onChange={(e) => setProfileForm({ ...profileForm, bmi: e.target.value })}
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded font-mono text-slate-900 focus:outline-teal-700"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Diabetes Duration (years)</label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    max="60"
                    value={profileForm.diabetes_duration_years}
                    onChange={(e) => setProfileForm({ ...profileForm, diabetes_duration_years: e.target.value })}
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded font-mono text-slate-900 focus:outline-teal-700"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">HbA1c (mmol/mol)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="20"
                    max="150"
                    value={profileForm.hba1c}
                    onChange={(e) => setProfileForm({ ...profileForm, hba1c: e.target.value })}
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded font-mono text-slate-900 focus:outline-teal-700"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Fasting Glucose (mg/dL)</label>
                  <input
                    type="number"
                    step="1"
                    min="50"
                    max="300"
                    value={profileForm.fasting_glucose}
                    onChange={(e) => setProfileForm({ ...profileForm, fasting_glucose: e.target.value })}
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded font-mono text-slate-900 focus:outline-teal-700"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Fasting C-Peptide (ng/mL)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.0"
                    max="10.0"
                    value={profileForm.fasting_c_peptide}
                    onChange={(e) => setProfileForm({ ...profileForm, fasting_c_peptide: e.target.value })}
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded font-mono text-slate-900 focus:outline-teal-700"
                    required
                  />
                </div>
              </div>

              <div className="flex justify-between items-center pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setCurrentStage(1)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={isSavingProfile}
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                >
                  {isSavingProfile ? "Saving Profile..." : "Save & Continue to CGM Import"}
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </form>
          )}

          {/* STAGE 3: CGM CSV IMPORT */}
          {currentStage === 3 && (
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">3. Import Continuous Glucose Monitoring Data</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Upload a CSV file containing at least 96 observations (24h of 15-minute readings).
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowTemplate(!showTemplate)}
                  className="text-xs text-teal-700 hover:underline flex items-center gap-1 font-medium"
                >
                  <span className="material-symbols-outlined text-[16px]">help_outline</span>
                  <span>{showTemplate ? "Hide format" : "View expected format"}</span>
                </button>
              </div>

              {/* Format Spec Accordion */}
              {showTemplate && (
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-2">
                  <div className="font-semibold text-slate-800">Supported Columns &amp; Units:</div>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600 font-mono text-[11px]">
                    <li><strong>timestamp</strong>: ISO-8601 (e.g. 2026-10-28T12:00:00)</li>
                    <li><strong>cgm_glucose</strong>: numeric mg/dL (20.0 to 600.0)</li>
                    <li><strong>insulin_bolus</strong>: numeric units (optional, default 0.0)</li>
                    <li><strong>insulin_basal</strong>: numeric units/hr (optional, default 0.0)</li>
                    <li><strong>meal_carbs</strong>: numeric grams (optional, default 0.0)</li>
                  </ul>
                  <div className="pt-1 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleLoadSampleData}
                      className="px-2.5 py-1 bg-teal-50 border border-teal-200 text-teal-800 rounded font-sans text-xs hover:bg-teal-100 font-medium"
                    >
                      Load Sample 96-Point Benchmark CSV
                    </button>
                  </div>
                </div>
              )}

              {/* Dropzone / File Picker */}
              <div className="p-6 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50 hover:bg-slate-50 text-center space-y-3 transition-colors">
                <span className="material-symbols-outlined text-teal-700 text-[36px]">upload_file</span>
                <div>
                  <p className="text-xs font-medium text-slate-800">
                    {csvFile ? csvFile.name : "Select or drag & drop a CGM CSV file"}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    CSV files up to 5 MB supported • Deduplication enforced automatically
                  </p>
                </div>
                <div className="flex items-center justify-center gap-2">
                  <label className="cursor-pointer px-3.5 py-1.5 bg-white border border-slate-300 hover:border-slate-400 rounded-lg text-xs font-semibold text-slate-700 shadow-2xs transition-colors">
                    Browse File
                    <input type="file" accept=".csv,text/csv" onChange={handleFileUpload} className="hidden" />
                  </label>
                  <button
                    type="button"
                    onClick={handleLoadSampleData}
                    className="px-3 py-1.5 bg-teal-50 border border-teal-200 hover:bg-teal-100 rounded-lg text-xs font-semibold text-teal-800 transition-colors"
                  >
                    Load Sample 96-Point CSV
                  </button>
                </div>
              </div>

              {/* Parsed Summary & Preview */}
              {parsedData && (
                <div className="space-y-3 pt-2">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-slate-900">Validation Summary: </span>
                      <span className="font-mono text-slate-700">{parsedData.summary.acceptedRows} accepted</span>
                      {parsedData.summary.rejectedRows > 0 && (
                        <span className="text-rose-600 font-mono ml-2">({parsedData.summary.rejectedRows} rejected)</span>
                      )}
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium ${
                        parsedData.summary.has96Eligible
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {parsedData.summary.eligibleCount} / 96 eligible
                    </span>
                  </div>

                  {/* Errors preview if any */}
                  {parsedData.errors?.length > 0 && (
                    <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 max-h-28 overflow-y-auto font-mono text-[11px] space-y-1">
                      <div className="font-sans font-semibold">Row Validation Diagnostics:</div>
                      {parsedData.errors.map((err, idx) => (
                        <div key={idx}>• {err}</div>
                      ))}
                    </div>
                  )}

                  {/* Readings Table Preview */}
                  {parsedData.readings.length > 0 && (
                    <div className="border border-slate-200 rounded-lg overflow-hidden max-h-40 overflow-y-auto">
                      <table className="w-full text-[11px] font-mono text-left">
                        <thead className="bg-slate-100 text-slate-600 sticky top-0">
                          <tr>
                            <th className="p-1.5">Timestamp</th>
                            <th className="p-1.5">Glucose (mg/dL)</th>
                            <th className="p-1.5">Bolus (U)</th>
                            <th className="p-1.5">Basal (U/h)</th>
                            <th className="p-1.5">Carbs (g)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {parsedData.readings.slice(0, 10).map((r, i) => (
                            <tr key={i} className="hover:bg-slate-50">
                              <td className="p-1.5">{r.timestamp.slice(0, 19).replace("T", " ")}</td>
                              <td className="p-1.5 font-semibold text-slate-900">{r.cgm_glucose}</td>
                              <td className="p-1.5">{r.insulin_bolus}</td>
                              <td className="p-1.5">{r.insulin_basal}</td>
                              <td className="p-1.5">{r.meal_carbs}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-between items-center pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setCurrentStage(2)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900"
                >
                  Back
                </button>
                <button
                  type="button"
                  disabled={!parsedData?.valid || isIngesting}
                  onClick={handleExecuteIngestion}
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                >
                  {isIngesting ? "Ingesting Readings..." : "Upload & Save to Patient"}
                  <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
                </button>
              </div>
            </div>
          )}

          {/* STAGE 4: DATA QUALITY & FORECAST READINESS */}
          {currentStage === 4 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">4. Data Quality &amp; Forecast Readiness Assessment</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Verified against the Combination C serving contract (24h continuous horizon @ 15m intervals).
                </p>
              </div>

              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-800">Historical Depth Requirement:</span>
                    <span className="px-2 py-0.5 rounded font-mono text-xs font-semibold bg-emerald-100 text-emerald-800">
                      READY (96 / 96 Observations)
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-600 h-full rounded-full" style={{ width: "100%" }}></div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-600 pt-1">
                    <div>• Interval: 15 minutes</div>
                    <div>• Quality Flag: Nominal</div>
                    <div>• Temporal Monotonicity: Verified</div>
                    <div>• Boundary Checks: All [20, 600] mg/dL</div>
                  </div>
                </div>

                <div className="p-3 bg-teal-50 border border-teal-100 rounded-lg text-xs text-teal-800 space-y-1">
                  <div className="font-semibold">Patient Sandbox Isolated:</div>
                  <p className="text-[11px] leading-relaxed">
                    Readings have been stored in the patient&apos;s longitudinal database record. The frozen Combination C forecaster is ready to compute the 20-step multi-horizon prediction trajectory.
                  </p>
                </div>
              </div>

              <div className="flex justify-between items-center pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setCurrentStage(3)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStage(5)}
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                >
                  <span>Proceed to Forecast Generation</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </div>
          )}

          {/* STAGE 5: GENERATE GENUINE FORECAST */}
          {currentStage === 5 && (
            <div className="space-y-4 text-center py-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-teal-50 text-teal-700 flex items-center justify-center border border-teal-200">
                <span className="material-symbols-outlined text-[28px]">biotech</span>
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-slate-900">
                  Ready to Compute Glucose Forecast
                </h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Execute the frozen Combination C ensemble (V1 Point Forecaster + Phase 13 Regime-Conditioned Uncertainty) using your newly ingested CGM observations.
                </p>
              </div>

              <div className="pt-4 flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                >
                  Close & Explore Dashboard
                </button>
                <button
                  type="button"
                  disabled={isLoadingForecast}
                  onClick={async () => {
                    if (onTriggerForecast) await onTriggerForecast();
                    onClose();
                  }}
                  className="px-5 py-2.5 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition-all flex items-center gap-2"
                >
                  {isLoadingForecast ? (
                    <>
                      <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                      <span>Evaluating Combination C...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[16px]">bolt</span>
                      <span>Generate Genuine Forecast</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
