import React, { useState } from "react";
import { UserCheck, ShieldCheck, Save, RefreshCw } from "lucide-react";

export function PatientProfilePanel({ staticProfile, onUpdateProfile }) {
  const [profile, setProfile] = useState(staticProfile || {
    age_years: 42.0,
    bmi_kg_m2: 24.8,
    diabetes_duration_years: 12.0,
    hba1c_pct: 7.2,
    glycated_albumin_pct: 18.5,
    fasting_glucose_mg_dl: 115.0,
    c_peptide_ng_ml: 0.15,
    has_complications: 0.0,
    is_t1dm: 1.0
  });

  const handleChange = (key, val) => {
    setProfile((prev) => ({ ...prev, [key]: parseFloat(val) || 0 }));
  };

  const handleSave = () => {
    if (onUpdateProfile) {
      onUpdateProfile(profile);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-[#00daf3]/10 text-[#00daf3] border border-[#00daf3]/30">
              <UserCheck className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-white font-mono tracking-tight uppercase">
              PATIENT_PHENOTYPIC_PROFILE (9 STATIC CHANNELS)
            </h2>
          </div>
          <p className="text-xs text-[#bac9cc] max-w-2xl">
            Static clinical covariates passed into the frozen static scaler (StandardScaler) and infused into the GRU-128 hidden state and Hovorka parameter matrix.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#00daf3] text-[#001f24] font-mono font-bold text-xs hover:bg-[#9cf0ff] shadow-lg shadow-[#00daf3]/20 transition-all"
        >
          <Save className="w-4 h-4" />
          SAVE PHENOTYPE
        </button>
      </div>

      {/* 9 Features Input Grid */}
      <div className="glass-panel instrument-border rounded-xl p-5 space-y-4">
        <span className="font-mono text-xs text-white font-bold uppercase tracking-wider block">
          Clinical Covariate Matrix (Frozen static_scaler.joblib Contract)
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
          <div>
            <label className="text-[#bac9cc] block mb-1">1. Age (years):</label>
            <input
              type="number"
              value={profile.age_years}
              onChange={(e) => handleChange("age_years", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">2. Body Mass Index (kg/m²):</label>
            <input
              type="number"
              step="0.1"
              value={profile.bmi_kg_m2}
              onChange={(e) => handleChange("bmi_kg_m2", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">3. Diabetes Duration (years):</label>
            <input
              type="number"
              value={profile.diabetes_duration_years}
              onChange={(e) => handleChange("diabetes_duration_years", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">4. Baseline HbA1c (%):</label>
            <input
              type="number"
              step="0.1"
              value={profile.hba1c_pct}
              onChange={(e) => handleChange("hba1c_pct", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">5. Glycated Albumin (%):</label>
            <input
              type="number"
              step="0.1"
              value={profile.glycated_albumin_pct}
              onChange={(e) => handleChange("glycated_albumin_pct", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">6. Fasting Glucose (mg/dL):</label>
            <input
              type="number"
              value={profile.fasting_glucose_mg_dl}
              onChange={(e) => handleChange("fasting_glucose_mg_dl", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">7. C-Peptide (ng/mL):</label>
            <input
              type="number"
              step="0.01"
              value={profile.c_peptide_ng_ml}
              onChange={(e) => handleChange("c_peptide_ng_ml", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">8. Complications (0/1):</label>
            <select
              value={profile.has_complications}
              onChange={(e) => handleChange("has_complications", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            >
              <option value="0">0 - None / Controlled</option>
              <option value="1">1 - Present (Microvascular / Neuropathy)</option>
            </select>
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">9. Diabetes Classification:</label>
            <select
              value={profile.is_t1dm}
              onChange={(e) => handleChange("is_t1dm", e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            >
              <option value="1">1 - Type 1 Diabetes Mellitus (T1DM)</option>
              <option value="0">0 - Type 2 Diabetes Mellitus (T2DM)</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
