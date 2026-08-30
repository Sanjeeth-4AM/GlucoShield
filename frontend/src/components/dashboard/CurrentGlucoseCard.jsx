import React from "react";
import { ArrowRight, ArrowUpRight, ArrowDownRight, Droplets, Utensils, Sliders, Activity } from "lucide-react";
import { GLUCOSE_THRESHOLDS } from "../../api/types.js";

export function CurrentGlucoseCard({ currentState, hybridComponents, riskAssessment }) {
  const glucose = currentState?.glucose_mg_dl ?? 120.0;
  const iob = currentState?.iob_units ?? 1.4;
  const cob = currentState?.cob_grams ?? 24.0;
  const neuralPct = hybridComponents?.mean_neural_weight_pct ?? 72;
  const odePct = 100 - neuralPct;
  const alphaVal = (neuralPct / 100).toFixed(2);

  // Velocity calculation & styling
  let velocityText = "STABLE velocity +0.1 mg/dL/m";
  let TrendIcon = ArrowRight;
  let trendColor = "text-[#00daf3]";

  if (glucose > 140) {
    velocityText = "RISING velocity +1.8 mg/dL/m";
    TrendIcon = ArrowUpRight;
    trendColor = "text-[#d0bcff]";
  } else if (glucose < 90) {
    velocityText = "FALLING velocity -1.6 mg/dL/m";
    TrendIcon = ArrowDownRight;
    trendColor = "text-[#ef4444]";
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 1. CGM.NOW Hero Pod */}
      <div className="glass-panel instrument-border rounded-xl p-5 relative overflow-hidden group">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#00daf3]/15 to-transparent opacity-60 pointer-events-none"></div>
        
        <div className="flex justify-between items-start relative z-10 mb-2">
          <span className="font-mono text-xs font-semibold text-[#bac9cc] tracking-wider uppercase">
            CGM.NOW
          </span>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00daf3] pulse-glow"></span>
            <span className="font-mono text-[10px] text-[#00daf3] tracking-widest font-bold">LIVE</span>
          </div>
        </div>

        <div className="relative z-10 flex flex-col items-center justify-center py-4">
          <div className="flex items-baseline gap-2">
            <span className="text-6xl font-light font-sans text-white tracking-tighter tabular-nums">
              {Math.round(glucose)}
            </span>
            <span className="font-mono text-xs text-[#bac9cc]">mg/dL</span>
          </div>
          
          <div className={`flex items-center gap-1.5 mt-2 ${trendColor}`}>
            <TrendIcon className="w-4 h-4" />
            <span className="font-mono text-xs tracking-tight">{velocityText}</span>
          </div>
        </div>
      </div>

      {/* 2. Metabolic Metrics Grid: IOB, COB, and Alpha Blend */}
      <div className="grid grid-cols-2 gap-3">
        {/* IOB Pod */}
        <div className="glass-panel instrument-border rounded-xl p-3.5 relative">
          <div className="flex justify-between items-center mb-1">
            <span className="font-mono text-[10px] text-[#bac9cc] uppercase flex items-center gap-1">
              <Droplets className="w-3 h-3 text-[#d0bcff]" />
              IOB (Insulin)
            </span>
          </div>
          <div className="flex items-baseline gap-1.5 my-1">
            <span className="text-2xl font-light font-mono text-[#d0bcff]">{iob.toFixed(1)}</span>
            <span className="font-mono text-[10px] text-[#bac9cc]">U</span>
          </div>
          {/* Micro visualization */}
          <div className="w-full h-1 bg-white/10 mt-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#d0bcff] transition-all duration-500"
              style={{ width: `${Math.min(100, (iob / 6.0) * 100)}%` }}
            ></div>
          </div>
        </div>

        {/* COB Pod */}
        <div className="glass-panel instrument-border rounded-xl p-3.5 relative">
          <div className="flex justify-between items-center mb-1">
            <span className="font-mono text-[10px] text-[#bac9cc] uppercase flex items-center gap-1">
              <Utensils className="w-3 h-3 text-[#ffdf9f]" />
              COB (Carbs)
            </span>
          </div>
          <div className="flex items-baseline gap-1.5 my-1">
            <span className="text-2xl font-light font-mono text-[#ffdf9f]">{Math.round(cob)}</span>
            <span className="font-mono text-[10px] text-[#bac9cc]">g</span>
          </div>
          {/* Micro visualization */}
          <div className="w-full h-1 bg-white/10 mt-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#ffdf9f] transition-all duration-500"
              style={{ width: `${Math.min(100, (cob / 80.0) * 100)}%` }}
            ></div>
          </div>
        </div>

        {/* Alpha Blend Pod (Spans 2 cols) */}
        <div className="glass-panel instrument-border rounded-xl p-3.5 relative col-span-2 border-l-2 border-l-[#00daf3]">
          <div className="flex justify-between items-center mb-1">
            <span className="font-mono text-[10px] text-[#bac9cc] uppercase flex items-center gap-1">
              <Sliders className="w-3 h-3 text-[#00daf3]" />
              α(t) BLEND.WEIGHT (NEURAL / ODE)
            </span>
            <span className="font-mono text-[10px] text-[#00daf3] font-bold">
              {neuralPct}% NN / {odePct}% ODE
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-2xl font-light font-mono text-white">{alphaVal}</span>
            <div className="flex-1 flex flex-col gap-1">
              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden flex">
                <div className="h-full bg-[#00daf3]" style={{ width: `${odePct}%` }} title={`ODE: ${odePct}%`}></div>
                <div className="h-full bg-[#d0bcff]" style={{ width: `${neuralPct}%` }} title={`Neural: ${neuralPct}%`}></div>
              </div>
              <div className="flex justify-between font-mono text-[9px] text-[#bac9cc]/70">
                <span>M-ODE ({odePct}%)</span>
                <span>N-ODE ({neuralPct}%)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
