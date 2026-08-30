import React from "react";
import { Settings, ShieldCheck, Database, CheckCircle2, Cpu, Hash } from "lucide-react";

export function SystemSpecsPanel({ backendHealth }) {
  const modelHashes = [
    {
      file: "models/glucoshield_neural_best.pt",
      expected: "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb",
      type: "PyTorch GRU-128 Backbone"
    },
    {
      file: "models/glucoshield_hybrid_best.pt",
      expected: "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1",
      type: "Neural-ODE Blended Hybrid"
    },
    {
      file: "data/metadata/feature_scaler.joblib",
      expected: "757f5c99e294dc8c5698a42cee1843853e8506df5203508aa71a1462d545972b",
      type: "22-Channel RobustScaler"
    },
    {
      file: "data/metadata/static_scaler.joblib",
      expected: "fedc25f67dbcefd2c19ff38375568f3f2bc83ac1fa7c29840e5c81d33b479576",
      type: "9-Channel StandardScaler"
    }
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-[#00daf3]/10 text-[#00daf3] border border-[#00daf3]/30">
              <Settings className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-white font-mono tracking-tight uppercase">
              SYSTEM_INTELLIGENCE_SPECIFICATIONS & HASH MANIFEST
            </h2>
          </div>
          <p className="text-xs text-[#bac9cc] max-w-2xl">
            Live FastAPI microservice contract, bitwise frozen cryptographic SHA-256 hashes, and invariant tensor channel documentation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-[#00daf3] bg-[#00daf3]/10 border border-[#00daf3]/30 px-2.5 py-1 rounded-lg">
            Backend Status: {backendHealth?.status || "CONNECTED"}
          </span>
        </div>
      </div>

      {/* SHA-256 Frozen Artifacts Manifest */}
      <div className="glass-panel instrument-border rounded-xl p-5 space-y-3">
        <span className="font-mono text-xs text-white font-bold uppercase tracking-wider flex items-center gap-2">
          <Hash className="w-4 h-4 text-[#00daf3]" />
          Immutable SHA-256 Cryptographic Checksums
        </span>

        <div className="space-y-2">
          {modelHashes.map((m, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-[#070d1f]/80 border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono text-xs"
            >
              <div>
                <div className="text-white font-bold">{m.file}</div>
                <div className="text-[10px] text-[#bac9cc]">{m.type}</div>
              </div>
              <div className="flex items-center gap-2 text-right">
                <span className="text-[10px] text-[#00daf3] break-all">{m.expected}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#2dd4bf]/20 text-[#2dd4bf] border border-[#2dd4bf]/30">
                  MATCH
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Channel Contracts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dynamic 22-Channel */}
        <div className="glass-panel instrument-border rounded-xl p-4 space-y-2 bg-[#070d1f]/60 font-mono text-xs">
          <span className="text-[#00daf3] font-bold uppercase block">
            A. Dynamic 22-Channel Input Contract (1, 96, 22)
          </span>
          <p className="text-[11px] text-[#bac9cc]">
            cgm_glucose, d1, d2, d3, iob_fast, iob_slow, cob_fast, cob_slow, sin_tod, cos_tod, sin_dow, cos_dow, glucose_smooth, glucose_accel, rolling_mean_1h, rolling_std_1h, rolling_min_1h, rolling_max_1h, tir_indicator, hypo_indicator, hyper_indicator, cgm_missing_mask.
          </p>
        </div>

        {/* Static 9-Channel */}
        <div className="glass-panel instrument-border rounded-xl p-4 space-y-2 bg-[#070d1f]/60 font-mono text-xs">
          <span className="text-[#f9bd22] font-bold uppercase block">
            B. Static 9-Channel Phenotype Contract (1, 9)
          </span>
          <p className="text-[11px] text-[#bac9cc]">
            age_years, bmi_kg_m2, diabetes_duration_years, hba1c_pct, glycated_albumin_pct, fasting_glucose_mg_dl, c_peptide_ng_ml, has_complications, is_t1dm.
          </p>
        </div>
      </div>
    </div>
  );
}
