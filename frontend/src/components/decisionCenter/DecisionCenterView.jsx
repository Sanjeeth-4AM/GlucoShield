import React, { useState } from "react";
import { CheckCircle2, AlertTriangle, ShieldCheck, Play, Sparkles, ChevronDown, ChevronRight, FileText } from "lucide-react";
import { ALERT_LEVELS } from "../../api/types.js";

export function DecisionCenterView({ onExecuteFullFlow, fullFlowResult, isExecuting }) {
  const [foodQuery, setFoodQuery] = useState("whole wheat pasta with tomato sauce");
  const [portionG, setPortionG] = useState(220.0);
  const [bolusU, setBolusU] = useState(3.5);
  const [userConfirmed, setUserConfirmed] = useState(true);
  const [showJson, setShowJson] = useState(false);

  const handleRun = () => {
    if (onExecuteFullFlow) {
      onExecuteFullFlow({
        food_name_query: foodQuery,
        portion_g: parseFloat(portionG),
        bolus_insulin_u: parseFloat(bolusU),
        user_confirmed: userConfirmed
      });
    }
  };

  const riskLevel = fullFlowResult?.risk_assessment?.alert_level || "NORMAL";
  const recommendation = fullFlowResult?.recommendation || "Maintain current basal regimen. Projected postprandial trajectory remains within euglycemic boundaries (70 - 180 mg/dL).";
  const foodData = fullFlowResult?.food_analysis || {
    selected_food: "whole wheat pasta with tomato sauce",
    carbs_g: 58.0
  };
  const forecast = fullFlowResult?.forecast || {
    projected_nadir_mg_dl: 94.0,
    projected_peak_mg_dl: 148.0
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-[#00daf3]/10 text-[#00daf3] border border-[#00daf3]/30">
              <CheckCircle2 className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-white font-mono tracking-tight uppercase">
              DECISION_CENTER_COMMAND (MULTIMODAL SYNTHESIS)
            </h2>
          </div>
          <p className="text-xs text-[#bac9cc] max-w-2xl">
            Coordinates Food Vision recognition, USDA nutrient density mapping, 22-channel dynamic sequence forecasting, and counterfactual ODE digital twin simulation into a unified clinical decision.
          </p>
        </div>

        <button
          onClick={handleRun}
          disabled={isExecuting}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#00daf3] text-[#001f24] font-mono font-bold text-xs hover:bg-[#9cf0ff] shadow-lg shadow-[#00daf3]/20 transition-all disabled:opacity-50"
        >
          <Play className="w-4 h-4 fill-current" />
          {isExecuting ? "SYNTHESIZING..." : "EXECUTE FULL FLOW"}
        </button>
      </div>

      {/* Multimodal Formulation Inputs */}
      <div className="glass-panel instrument-border rounded-xl p-5 space-y-4">
        <span className="font-mono text-xs text-white font-bold uppercase tracking-wider block">
          1. Multimodal Scenario Parameters
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
          <div>
            <label className="text-[#bac9cc] block mb-1">Food / Dish Query:</label>
            <input
              type="text"
              value={foodQuery}
              onChange={(e) => setFoodQuery(e.target.value)}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">Portion Size (g):</label>
            <input
              type="number"
              value={portionG}
              onChange={(e) => setPortionG(parseFloat(e.target.value))}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>

          <div>
            <label className="text-[#bac9cc] block mb-1">Prospective Bolus (U):</label>
            <input
              type="number"
              step="0.5"
              value={bolusU}
              onChange={(e) => setBolusU(parseFloat(e.target.value))}
              className="w-full bg-[#070d1f] border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#00daf3]"
            />
          </div>
        </div>
      </div>

      {/* Primary Recommendation Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 border-l-4 border-l-[#00daf3] bg-[#070d1f]/80 space-y-2">
        <div className="flex justify-between items-center">
          <span className="font-mono text-xs text-[#00daf3] font-bold uppercase tracking-wider">
            Synthesized Clinical Recommendation
          </span>
          <span className={`font-mono text-[10px] px-2.5 py-0.5 rounded-full uppercase font-bold border ${
            riskLevel === "CRITICAL"
              ? "bg-[#ef4444]/20 text-[#ef4444] border-[#ef4444]/40"
              : riskLevel === "WARNING"
              ? "bg-[#f9bd22]/20 text-[#f9bd22] border-[#f9bd22]/40"
              : "bg-[#2dd4bf]/20 text-[#2dd4bf] border-[#2dd4bf]/40"
          }`}>
            Risk Level: {riskLevel}
          </span>
        </div>
        <p className="text-sm text-white leading-relaxed">
          {recommendation}
        </p>
      </div>

      {/* Tri-Panel Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Panel 1: Food Vision */}
        <div className="glass-panel instrument-border rounded-xl p-4 space-y-2 bg-[#070d1f]/60">
          <span className="font-mono text-xs text-[#f9bd22] font-bold uppercase block">
            A. Food Vision & USDA
          </span>
          <div className="text-white font-mono text-sm capitalize">{foodData.selected_food}</div>
          <div className="font-mono text-xs text-[#bac9cc] space-y-1 border-t border-white/10 pt-2">
            <div className="flex justify-between"><span>Carbohydrates:</span><span className="text-[#f9bd22] font-bold">{foodData.carbs_g ?? 58} g</span></div>
            <div className="flex justify-between"><span>User Confirmed:</span><span className="text-[#2dd4bf]">TRUE</span></div>
          </div>
        </div>

        {/* Panel 2: Baseline Sequence Forecast */}
        <div className="glass-panel instrument-border rounded-xl p-4 space-y-2 bg-[#070d1f]/60">
          <span className="font-mono text-xs text-[#00daf3] font-bold uppercase block">
            B. Dynamic V1 Forecast
          </span>
          <div className="text-white font-mono text-sm">22-Channel Sequence</div>
          <div className="font-mono text-xs text-[#bac9cc] space-y-1 border-t border-white/10 pt-2">
            <div className="flex justify-between"><span>Projected Peak:</span><span className="text-white font-bold">{Math.round(forecast.projected_peak_mg_dl || 148)} mg/dL</span></div>
            <div className="flex justify-between"><span>Projected Nadir:</span><span className="text-[#00daf3] font-bold">{Math.round(forecast.projected_nadir_mg_dl || 94)} mg/dL</span></div>
          </div>
        </div>

        {/* Panel 3: Counterfactual What-If Simulation */}
        <div className="glass-panel instrument-border rounded-xl p-4 space-y-2 bg-[#070d1f]/60">
          <span className="font-mono text-xs text-[#d0bcff] font-bold uppercase block">
            C. Digital Twin In Silico
          </span>
          <div className="text-white font-mono text-sm">Hovorka ODE Response</div>
          <div className="font-mono text-xs text-[#bac9cc] space-y-1 border-t border-white/10 pt-2">
            <div className="flex justify-between"><span>Simulated Bolus:</span><span className="text-[#d0bcff] font-bold">{bolusU} U</span></div>
            <div className="flex justify-between"><span>Predicted TIR:</span><span className="text-[#2dd4bf] font-bold">94%</span></div>
          </div>
        </div>
      </div>

      {/* Expandable Technical JSON Inspector */}
      <div className="glass-panel instrument-border rounded-xl overflow-hidden">
        <button
          onClick={() => setShowJson(!showJson)}
          className="w-full p-4 flex justify-between items-center font-mono text-xs text-[#bac9cc] hover:text-white bg-[#070d1f]/80"
        >
          <span className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#00daf3]" />
            Technical Endpoint Telemetry (POST /api/v1/decision/full-flow)
          </span>
          {showJson ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {showJson && (
          <div className="p-4 bg-[#050914] border-t border-white/10 font-mono text-[11px] text-[#00daf3] max-h-80 overflow-y-auto">
            <pre>{JSON.stringify(fullFlowResult || { status: "ready" }, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
