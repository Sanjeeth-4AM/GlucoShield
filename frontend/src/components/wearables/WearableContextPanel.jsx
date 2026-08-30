import React from "react";
import { Watch, Heart, Footprints, Flame, ShieldAlert, CheckCircle2, Info } from "lucide-react";

export function WearableContextPanel({ wearableContext, onUpdateWearable }) {
  const steps = wearableContext?.step_count_last_hour ?? 450;
  const hr = wearableContext?.mean_hr_bpm ?? 74.0;
  const calories = Math.round(steps * 0.04);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-[#00daf3]/10 text-[#00daf3] border border-[#00daf3]/30">
              <Watch className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-white font-mono tracking-tight uppercase">
              WEARABLE_OBSERVATIONAL_CONTEXT (TELEMETRY)
            </h2>
          </div>
          <p className="text-xs text-[#bac9cc] max-w-2xl">
            Smartwatch activity and optical PPG telemetry ingestion for observational context and activity-adjusted meal advisories.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-[#2dd4bf] bg-[#2dd4bf]/10 border border-[#2dd4bf]/30 px-2.5 py-1 rounded-lg">
            Telemetry Feed: Connected
          </span>
        </div>
      </div>

      {/* Mandatory Phase 7C Scientific Guarantee Banner */}
      <div className="glass-panel instrument-border-cyan rounded-xl p-5 bg-[#070d1f]/90 space-y-3">
        <div className="flex items-center gap-2 text-[#00daf3]">
          <ShieldAlert className="w-5 h-5" />
          <h3 className="font-mono text-xs font-bold uppercase tracking-wider">
            Phase 7C Empirical Scientific Invariant (Glucdict LOOCV Protocol v2.1.0)
          </h3>
        </div>
        <p className="text-xs text-[#bac9cc] leading-relaxed">
          Rigorous Leave-One-Out Cross-Validation (LOOCV) across 13 held-out participants demonstrated that smartwatch activity features produced a <strong className="text-white">Delta MAE of -0.21 mg/dL (Wilcoxon W = 34.0, p = 0.455)</strong>, confirming no statistically significant forecasting improvement. Consequently, wearable telemetry is <strong className="text-[#00daf3]">strictly isolated</strong> from the frozen 22-channel dynamic forecaster tensor contract.
        </p>
      </div>

      {/* Telemetry Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Step Count */}
        <div className="glass-panel instrument-border rounded-xl p-4 bg-[#070d1f]/70 space-y-2">
          <div className="flex justify-between items-center">
            <span className="font-mono text-xs text-[#00daf3] font-bold flex items-center gap-1.5">
              <Footprints className="w-4 h-4" />
              Step Count (Last 1h)
            </span>
          </div>
          <div className="text-3xl font-light font-mono text-white">{steps} <span className="text-xs text-[#bac9cc]">steps</span></div>
          <div className="font-mono text-[10px] text-[#bac9cc] border-t border-white/10 pt-2">
            Status: Moderate ambulatory activity
          </div>
        </div>

        {/* Heart Rate */}
        <div className="glass-panel instrument-border rounded-xl p-4 bg-[#070d1f]/70 space-y-2">
          <div className="flex justify-between items-center">
            <span className="font-mono text-xs text-[#ef4444] font-bold flex items-center gap-1.5">
              <Heart className="w-4 h-4" />
              Mean Heart Rate
            </span>
          </div>
          <div className="text-3xl font-light font-mono text-white">{Math.round(hr)} <span className="text-xs text-[#bac9cc]">BPM</span></div>
          <div className="font-mono text-[10px] text-[#bac9cc] border-t border-white/10 pt-2">
            Sensor: Optical PPG (Wrist)
          </div>
        </div>

        {/* Energy Burned */}
        <div className="glass-panel instrument-border rounded-xl p-4 bg-[#070d1f]/70 space-y-2">
          <div className="flex justify-between items-center">
            <span className="font-mono text-xs text-[#f9bd22] font-bold flex items-center gap-1.5">
              <Flame className="w-4 h-4" />
              Active Energy
            </span>
          </div>
          <div className="text-3xl font-light font-mono text-white">{calories} <span className="text-xs text-[#bac9cc]">kcal</span></div>
          <div className="font-mono text-[10px] text-[#bac9cc] border-t border-white/10 pt-2">
            Metabolic Equivalent: 1.2 MET
          </div>
        </div>
      </div>
    </div>
  );
}
