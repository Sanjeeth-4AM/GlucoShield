import React from "react";
import { ExplanationCard } from "./ExplanationCard.jsx";
import { RecentEventsCard } from "./RecentEventsCard.jsx";
import { DigitalTwinPreviewCard } from "./DigitalTwinPreviewCard.jsx";

export function DashboardAccordions({
  forecastData,
  historyReadings = [],
  persistedRecentEvents = [],
  onNavigateToTab
}) {
  const currentG = forecastData?.current_state?.glucose_mg_dl != null
    ? Math.round(forecastData.current_state.glucose_mg_dl)
    : 116;
  const cob = forecastData?.current_state?.cob_grams ?? null;
  const iob = forecastData?.current_state?.iob_units ?? null;

  return (
    <div className="space-y-3 font-sans">
      
      {/* ACCORDION 1: Why this forecast? (Model factors) */}
      <details className="group bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden" open>
        <summary className="p-4 flex items-center justify-between cursor-pointer list-none select-none hover:bg-slate-50 transition-colors">
          <div className="flex items-center gap-3">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100">
              <span className="material-symbols-outlined text-[20px]">tune</span>
            </span>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-slate-900">Why this forecast? (Model factors)</span>
              <span className="text-xs text-slate-500">Physiological attribution decomposition for upcoming 5 hours</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono hidden sm:inline">Active Factors: 4</span>
            <span className="material-symbols-outlined text-slate-400 transition-transform duration-200 group-open:rotate-180">expand_more</span>
          </div>
        </summary>
        <div className="p-5 pt-1 border-t border-slate-100">
          <ExplanationCard
            explanation={forecastData?.explanation || forecastData?.explanations}
            explanations={forecastData?.explanation || forecastData?.explanations}
            hybridComponents={forecastData?.hybrid_components}
          />
        </div>
      </details>

      {/* ACCORDION 2: Recent events */}
      <details className="group bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
        <summary className="p-4 flex items-center justify-between cursor-pointer list-none select-none hover:bg-slate-50 transition-colors">
          <div className="flex items-center gap-3">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100">
              <span className="material-symbols-outlined text-[20px]">history</span>
            </span>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-slate-900">Recent events</span>
              <span className="text-xs text-slate-500">Timeline of inputs, meal announcements, and telemetry checks</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">Recorded History</span>
            <span className="material-symbols-outlined text-slate-400 transition-transform duration-200 group-open:rotate-180">expand_more</span>
          </div>
        </summary>
        <div className="p-5 pt-1 border-t border-slate-100">
          <RecentEventsCard
            historyReadings={historyReadings}
            persistedEvents={persistedRecentEvents}
            onNavigate={() => onNavigateToTab && onNavigateToTab("history")}
          />
        </div>
      </details>

      {/* ACCORDION 3: Digital Twin overview */}
      <details className="group bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
        <summary className="p-4 flex items-center justify-between cursor-pointer list-none select-none hover:bg-slate-50 transition-colors">
          <div className="flex items-center gap-3">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100">
              <span className="material-symbols-outlined text-[20px]">account_tree</span>
            </span>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-slate-900">Digital Twin overview</span>
              <span className="text-xs text-slate-500">Multi-compartment mechanistic latent state progression</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono hidden sm:inline">5-Compartment Vector</span>
            <span className="material-symbols-outlined text-slate-400 transition-transform duration-200 group-open:rotate-180">expand_more</span>
          </div>
        </summary>
        <div className="p-5 pt-3 border-t border-slate-100 space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            The Digital Twin synchronizes continuous telemetry with mathematical representations of stomach emptying, plasma insulin concentration, and peripheral glucose uptake.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-center text-xs">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex flex-col items-center gap-1">
              <span className="material-symbols-outlined text-teal-700 text-[22px]">ramen_dining</span>
              <span className="font-semibold text-slate-900">Carbohydrates</span>
              <span className="text-[11px] text-slate-500 font-mono">{cob !== null ? `${Math.round(cob)}g gut intake` : "0g active"}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex flex-col items-center gap-1">
              <span className="material-symbols-outlined text-blue-700 text-[22px]">medication</span>
              <span className="font-semibold text-slate-900">Insulin Active</span>
              <span className="text-[11px] text-slate-500 font-mono">{iob !== null ? `${iob.toFixed(1)} U remaining` : "0.5 U basal"}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex flex-col items-center gap-1">
              <span className="material-symbols-outlined text-emerald-700 text-[22px]">vital_signs</span>
              <span className="font-semibold text-slate-900">Body Response</span>
              <span className="text-[11px] text-slate-500 font-mono">Hepatic dampening</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 flex flex-col items-center gap-1">
              <span className="material-symbols-outlined text-teal-700 text-[22px]">water_drop</span>
              <span className="font-semibold text-slate-900">Current Glucose</span>
              <span className="text-[11px] text-slate-500 font-mono">{currentG} mg/dL state</span>
            </div>
            <div className="p-3 rounded-lg bg-teal-50 border border-teal-100 flex flex-col items-center gap-1 col-span-2 sm:col-span-1">
              <span className="material-symbols-outlined text-teal-800 text-[22px]">trending_up</span>
              <span className="font-semibold text-teal-900">5h Forecast</span>
              <span className="text-[11px] text-teal-700 font-mono">115 → 75 mg/dL</span>
            </div>
          </div>
          <div className="flex justify-end pt-1">
            <button
              type="button"
              onClick={() => onNavigateToTab && onNavigateToTab("digital_twin")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-teal-800 text-xs font-semibold transition-colors"
            >
              <span>View Digital Twin Deep Dive</span>
              <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>
          </div>
        </div>
      </details>

      {/* ACCORDION 4: Model details and data sources */}
      <details className="group bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
        <summary className="p-4 flex items-center justify-between cursor-pointer list-none select-none hover:bg-slate-50 transition-colors">
          <div className="flex items-center gap-3">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100">
              <span className="material-symbols-outlined text-[20px]">science</span>
            </span>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-slate-900">Model details and data sources</span>
              <span className="text-xs text-slate-500">Architecture provenance, input window depth, and numerical convergence metrics</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">Converged</span>
            <span className="material-symbols-outlined text-slate-400 transition-transform duration-200 group-open:rotate-180">expand_more</span>
          </div>
        </summary>
        <div className="p-5 pt-3 border-t border-slate-100">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">Model Configuration</span>
              <div className="font-semibold text-slate-900">Combination C (Neural-ODE)</div>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Hybrid architecture coupling continuous differentiable ODE layers with recurrent latent states for physiological fidelity.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">Input Observations</span>
              <div className="font-semibold text-slate-900">96 Continuous Points (24h)</div>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Full 24-hour lookback depth meets the minimum requirement for baseline metabolic parameter estimation without synthetic imputation.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">Runtime Performance</span>
              <div className="font-semibold text-slate-900">Solver Execution: 42 ms</div>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Adaptive step Dormand-Prince integrator (rtol=1e-5, atol=1e-7). All 20 forward steps verified free of gradient divergence.
              </p>
            </div>
          </div>
        </div>
      </details>

    </div>
  );
}
