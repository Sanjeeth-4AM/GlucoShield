import React, { useState } from "react";
import { FlaskConical, Play, Sparkles, AlertTriangle, ArrowRight, ShieldCheck, Zap } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine } from "recharts";

export function WhatIfSimulator({ onSimulate, whatIfResult, isSimulating, onTransferToDecision }) {
  const [mealCarbs, setMealCarbs] = useState(60.0);
  const [bolusInsulin, setBolusInsulin] = useState(4.5);
  const [exerciseMins, setExerciseMins] = useState(0);

  const handleRun = () => {
    if (onSimulate) {
      onSimulate({
        meal_carbs_g: parseFloat(mealCarbs),
        bolus_insulin_u: parseFloat(bolusInsulin),
        exercise_intensity_factor: exerciseMins > 0 ? 1.5 : 1.0
      });
    }
  };

  // Trajectory chart points
  const trajectory = whatIfResult?.simulated_trajectory || [];
  const chartPoints = trajectory.map((g, idx) => ({
    minute: (idx + 1) * 15,
    label: `+${Math.floor(((idx + 1) * 15) / 60)}h${((idx + 1) * 15) % 60 ? `${((idx + 1) * 15) % 60}m` : ""}`,
    simulatedGlucose: Math.round(g)
  }));

  const peak = whatIfResult?.peak_glucose ?? (120 + mealCarbs * 0.9 - bolusInsulin * 12);
  const nadir = whatIfResult?.nadir_glucose ?? Math.max(55, 120 + mealCarbs * 0.3 - bolusInsulin * 16);
  const tir = whatIfResult?.time_in_range_pct ?? (nadir >= 70 && peak <= 180 ? 92 : 68);
  const timeToNadir = whatIfResult?.time_to_nadir_minutes ?? 180;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-[#f9bd22]/10 text-[#f9bd22] border border-[#f9bd22]/30">
              <FlaskConical className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-white font-mono tracking-tight uppercase">
              PHYSIOLOGY_SIMULATION_LAB (IN SILICO COUNTERFACTUALS)
            </h2>
          </div>
          <p className="text-xs text-[#bac9cc] max-w-2xl">
            Simulate prospective carbohydrate ingestion and insulin bolus administration against the patient's calibrated Hovorka ODE digital twin before physical execution.
          </p>
        </div>

        <button
          onClick={handleRun}
          disabled={isSimulating}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#00daf3] text-[#001f24] font-mono font-bold text-xs hover:bg-[#9cf0ff] shadow-lg shadow-[#00daf3]/20 transition-all disabled:opacity-50"
        >
          <Play className="w-4 h-4 fill-current" />
          {isSimulating ? "COMPUTING ODE..." : "EXECUTE IN SILICO"}
        </button>
      </div>

      {/* Main Grid: Sliders on Left, Simulation Results on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Sliders */}
        <div className="lg:col-span-5 space-y-4">
          {/* Meal Carbs Slider */}
          <div className="glass-panel instrument-border rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs text-[#f9bd22] font-bold uppercase tracking-wider">
                1. Prospective Meal Carbs
              </span>
              <span className="font-mono text-sm text-white font-bold bg-[#070d1f] px-2 py-0.5 rounded border border-white/10">
                {mealCarbs} g
              </span>
            </div>

            <input
              type="range"
              min="0"
              max="150"
              step="5"
              value={mealCarbs}
              onChange={(e) => setMealCarbs(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-[#f9bd22]"
            />

            <div className="flex gap-2">
              {[
                { label: "Snack (25g)", val: 25 },
                { label: "Standard Meal (60g)", val: 60 },
                { label: "High Carb (110g)", val: 110 }
              ].map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => setMealCarbs(preset.val)}
                  className="font-mono text-[10px] px-2 py-1 rounded bg-[#070d1f] border border-white/10 text-[#bac9cc] hover:text-white hover:border-[#f9bd22]/50 transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Bolus Insulin Slider */}
          <div className="glass-panel instrument-border rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs text-[#d0bcff] font-bold uppercase tracking-wider">
                2. Prospective Bolus Insulin
              </span>
              <span className="font-mono text-sm text-white font-bold bg-[#070d1f] px-2 py-0.5 rounded border border-white/10">
                {bolusInsulin} U
              </span>
            </div>

            <input
              type="range"
              min="0"
              max="15"
              step="0.5"
              value={bolusInsulin}
              onChange={(e) => setBolusInsulin(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-[#d0bcff]"
            />

            <div className="flex gap-2">
              {[
                { label: "Micro (1.5U)", val: 1.5 },
                { label: "Standard (4.5U)", val: 4.5 },
                { label: "Correction (8.0U)", val: 8.0 }
              ].map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => setBolusInsulin(preset.val)}
                  className="font-mono text-[10px] px-2 py-1 rounded bg-[#070d1f] border border-white/10 text-[#bac9cc] hover:text-white hover:border-[#d0bcff]/50 transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Optional Action Buttons */}
          {onTransferToDecision && (
            <button
              onClick={() => onTransferToDecision({ mealCarbs, bolusInsulin, whatIfResult })}
              className="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-[#070d1f] border border-[#00daf3]/40 text-[#00daf3] hover:bg-[#00daf3]/10 font-mono text-xs font-bold transition-all shadow-md"
            >
              <span>Transfer Formulation to Decision Center</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Right Column: Simulation Outcomes */}
        <div className="lg:col-span-7 space-y-4">
          {/* KPI Output Matrix */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Peak */}
            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/60">
              <span className="font-mono text-[10px] text-[#bac9cc] uppercase block mb-1">Projected Peak</span>
              <span className={`text-xl font-mono font-bold ${peak > 180 ? "text-[#ef4444]" : "text-white"}`}>
                {Math.round(peak)} <span className="text-[10px] font-normal text-[#bac9cc]">mg/dL</span>
              </span>
            </div>

            {/* Nadir */}
            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/60">
              <span className="font-mono text-[10px] text-[#bac9cc] uppercase block mb-1">Projected Nadir</span>
              <span className={`text-xl font-mono font-bold ${nadir < 70 ? "text-[#ef4444]" : "text-[#00daf3]"}`}>
                {Math.round(nadir)} <span className="text-[10px] font-normal text-[#bac9cc]">mg/dL</span>
              </span>
            </div>

            {/* Time to Nadir */}
            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/60">
              <span className="font-mono text-[10px] text-[#bac9cc] uppercase block mb-1">Time to Nadir</span>
              <span className="text-xl font-mono font-bold text-[#d0bcff]">
                {timeToNadir} <span className="text-[10px] font-normal text-[#bac9cc]">min</span>
              </span>
            </div>

            {/* TIR */}
            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/60">
              <span className="font-mono text-[10px] text-[#bac9cc] uppercase block mb-1">Predicted TIR</span>
              <span className={`text-xl font-mono font-bold ${tir >= 70 ? "text-[#2dd4bf]" : "text-[#f9bd22]"}`}>
                {Math.round(tir)}%
              </span>
            </div>
          </div>

          {/* Simulated Trajectory Curve Chart */}
          <div className="glass-panel instrument-border rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
              <span className="font-mono text-xs text-white font-bold uppercase tracking-wider">
                Simulated 5-Hour ODE Postprandial Curve
              </span>
              <span className="font-mono text-[10px] text-[#00daf3]">
                {mealCarbs}g Carbs / {bolusInsulin}U Bolus
              </span>
            </div>

            <div className="w-full h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartPoints} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                  <ReferenceLine y={180} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
                  <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
                  <XAxis dataKey="label" stroke="#64748B" fontSize={10} fontFamily="JetBrains Mono" />
                  <YAxis domain={[40, 240]} stroke="#64748B" fontSize={10} fontFamily="JetBrains Mono" unit=" mg" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(7, 13, 31, 0.95)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                      borderRadius: "8px",
                      fontSize: "12px",
                      fontFamily: "JetBrains Mono"
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="simulatedGlucose"
                    stroke="#ec4899"
                    strokeWidth={2.5}
                    dot={{ fill: "#ec4899", r: 3 }}
                    activeDot={{ r: 5 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
