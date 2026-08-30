import React from "react";
import { Sparkles, Brain, Cpu, CheckCircle2 } from "lucide-react";

export function ExplanationCard({ explanations, hybridComponents }) {
  const summary = explanations?.natural_language_summary ||
    "Continuous glucose sequence indicates stable metabolic equilibrium under active basal insulin coverage.";
  const metabolicDrivers = explanations?.metabolic_drivers || [
    "Hepatic EGP balance (Gb = 108 mg/dL)",
    "Active basal insulin depot clearance (IOB = 1.4U)",
    "Residual gut absorption flux (COB = 24g)"
  ];
  const neuralPct = hybridComponents?.mean_neural_weight_pct ?? 72;
  const odePct = 100 - neuralPct;

  return (
    <div className="glass-panel instrument-border rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <span className="font-mono text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Brain className="w-4 h-4 text-[#00daf3]" />
          Interpretable AI Decision Explanation
        </span>
        <span className="font-mono text-[10px] text-[#bac9cc] bg-[#070d1f] border border-white/10 px-2.5 py-0.5 rounded">
          MC-Dropout Uncertainty Calibrated
        </span>
      </div>

      {/* Summary Box */}
      <div className="p-3.5 rounded-lg bg-[#070d1f]/80 border-l-2 border-l-[#00daf3] text-xs text-white leading-relaxed">
        {summary}
      </div>

      {/* Metabolic Drivers List */}
      <div>
        <span className="font-mono text-[10px] text-[#bac9cc] uppercase tracking-wider block mb-2">
          Primary Physiological Drivers
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {metabolicDrivers.map((driver, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-lg bg-[#070d1f]/60 border border-white/10 text-xs font-mono text-[#bac9cc] flex items-center gap-2"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-[#00daf3]"></span>
              <span className="truncate">{driver}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Hybrid Model Attribution Breakdown */}
      <div className="pt-2 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono text-xs">
        <span className="text-[#bac9cc]">Hybrid Model Attribution:</span>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#d0bcff]"></span>
            <span className="text-white font-bold">{neuralPct}% Neural Forecaster (GRU-128)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00daf3]"></span>
            <span className="text-white font-bold">{odePct}% Hovorka Physics ODE Twin</span>
          </div>
        </div>
      </div>
    </div>
  );
}
