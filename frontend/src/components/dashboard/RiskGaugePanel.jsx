import React from "react";
import { AlertTriangle, ShieldCheck, TrendingDown, TrendingUp, AlertCircle } from "lucide-react";
import { ALERT_LEVELS } from "../../api/types.js";

export function RiskGaugePanel({ riskAssessment }) {
  const alertLevel = riskAssessment?.alert_level || "NORMAL";
  const hypoProb1h = (riskAssessment?.hypo_probability_1h ?? 0.04) * 100;
  const hypoProb2h = (riskAssessment?.hypo_probability_2h ?? 0.08) * 100;
  const hypoProb4h = (riskAssessment?.hypo_probability_4h ?? 0.12) * 100;

  const hyperProb2h = (riskAssessment?.hyper_probability_2h ?? 0.15) * 100;
  const hyperProb4h = (riskAssessment?.hyper_probability_4h ?? 0.22) * 100;

  const nadir = riskAssessment?.projected_nadir_mg_dl ?? 95.0;
  const nadirTime = riskAssessment?.projected_nadir_time_minutes ?? 120;
  const peak = riskAssessment?.projected_peak_mg_dl ?? 142.0;
  const peakTime = riskAssessment?.projected_peak_time_minutes ?? 45;

  const alertConfig = ALERT_LEVELS[alertLevel] || ALERT_LEVELS.NORMAL;

  return (
    <div className="glass-panel instrument-border rounded-xl p-5 space-y-4">
      {/* Header with Risk Pill */}
      <div className="flex justify-between items-center">
        <span className="font-mono text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#00daf3]" />
          Multi-Horizon Clinical Risk Evaluation
        </span>
        <span className={`font-mono text-[10px] px-2.5 py-0.5 rounded-full uppercase font-bold border ${
          alertLevel === "CRITICAL"
            ? "bg-[#ef4444]/20 text-[#ef4444] border-[#ef4444]/40"
            : alertLevel === "WARNING"
            ? "bg-[#f9bd22]/20 text-[#f9bd22] border-[#f9bd22]/40"
            : "bg-[#2dd4bf]/20 text-[#2dd4bf] border-[#2dd4bf]/40"
        }`}>
          {alertLevel} RISK STATUS
        </span>
      </div>

      {/* 2-Column Risk Indicators: Hypo Left, Hyper Right */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Hypoglycemia Risk */}
        <div className="p-3.5 rounded-lg bg-[#070d1f]/70 border border-white/10 space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-mono text-[11px] text-[#00daf3] font-bold flex items-center gap-1.5">
              <TrendingDown className="w-3.5 h-3.5 text-[#00daf3]" />
              Hypoglycemia Risk (&lt; 70 mg/dL)
            </span>
            <span className="font-mono text-xs text-white font-bold">{Math.round(hypoProb1h)}% (1h)</span>
          </div>

          <div className="space-y-1.5 font-mono text-[10px] text-[#bac9cc]">
            <div>
              <div className="flex justify-between mb-0.5"><span>1-Hour:</span><span>{Math.round(hypoProb1h)}%</span></div>
              <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-[#00daf3]" style={{ width: `${Math.min(100, hypoProb1h)}%` }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-0.5"><span>2-Hour:</span><span>{Math.round(hypoProb2h)}%</span></div>
              <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-[#00daf3]" style={{ width: `${Math.min(100, hypoProb2h)}%` }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-0.5"><span>4-Hour:</span><span>{Math.round(hypoProb4h)}%</span></div>
              <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-[#00daf3]" style={{ width: `${Math.min(100, hypoProb4h)}%` }}></div>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-white/10 flex justify-between items-center font-mono text-[10px]">
            <span className="text-[#bac9cc]">Projected Nadir:</span>
            <span className="text-white font-bold">{Math.round(nadir)} mg/dL @ +{nadirTime}m</span>
          </div>
        </div>

        {/* Hyperglycemia Risk */}
        <div className="p-3.5 rounded-lg bg-[#070d1f]/70 border border-white/10 space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-mono text-[11px] text-[#f9bd22] font-bold flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-[#f9bd22]" />
              Hyperglycemia Risk (&gt; 180 mg/dL)
            </span>
            <span className="font-mono text-xs text-white font-bold">{Math.round(hyperProb2h)}% (2h)</span>
          </div>

          <div className="space-y-1.5 font-mono text-[10px] text-[#bac9cc]">
            <div>
              <div className="flex justify-between mb-0.5"><span>2-Hour:</span><span>{Math.round(hyperProb2h)}%</span></div>
              <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-[#f9bd22]" style={{ width: `${Math.min(100, hyperProb2h)}%` }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-0.5"><span>4-Hour:</span><span>{Math.round(hyperProb4h)}%</span></div>
              <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-[#f9bd22]" style={{ width: `${Math.min(100, hyperProb4h)}%` }}></div>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-white/10 flex justify-between items-center font-mono text-[10px]">
            <span className="text-[#bac9cc]">Projected Peak:</span>
            <span className="text-white font-bold">{Math.round(peak)} mg/dL @ +{peakTime}m</span>
          </div>
        </div>
      </div>
    </div>
  );
}
