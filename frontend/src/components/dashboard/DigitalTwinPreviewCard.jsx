import React from "react";
import { Utensils, Droplets, Activity, Scale, TrendingUp, ArrowDown, ArrowRight } from "lucide-react";

export function DigitalTwinPreviewCard({ forecastData, onNavigate }) {
  const peak = (forecastData?.risk_assessment?.projected_peak_mg_dl ?? forecastData?.risk_assessment?.peak_mg_dl) != null
    ? Math.round(forecastData.risk_assessment.projected_peak_mg_dl ?? forecastData.risk_assessment.peak_mg_dl)
    : (Array.isArray(forecastData?.forecast?.point_forecast_mg_dl) && forecastData.forecast.point_forecast_mg_dl.length > 0
        ? Math.round(Math.max(...forecastData.forecast.point_forecast_mg_dl.filter(p => typeof p === "number" && isFinite(p))))
        : null);
  const currentG = forecastData?.current_state?.glucose_mg_dl != null
    ? Math.round(forecastData.current_state.glucose_mg_dl)
    : null;
  const cob = forecastData?.current_state?.cob_grams ?? null;
  const iob = forecastData?.current_state?.iob_units ?? null;
  const hasValidForecast = Array.isArray(forecastData?.forecast?.point_forecast_mg_dl) && forecastData.forecast.point_forecast_mg_dl.length > 0;

  return (
    <div className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm flex flex-col justify-between border border-surface-container h-full">
      <div>
        <div className="flex items-center gap-space-xs">
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
            SECTION E
          </span>
          <span className="text-outline-variant">•</span>
          <h2 className="font-label-md text-label-md font-semibold text-on-surface">
            DIGITAL TWIN PREVIEW
          </h2>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5 mb-space-md">
          Real-time physiological multi-compartment state
        </p>

        {/* Vertical Metabolic Flow Diagram */}
        <div className="flex flex-col items-center gap-1.5 py-space-xs">
          {/* Node 1: Meal / CHO */}
          <div className="w-full bg-surface-container-low p-space-xs px-space-sm rounded flex items-center justify-between border border-surface-container">
            <div className="flex items-center gap-2">
              <Utensils className="w-4 h-4 text-secondary" />
              <span className="font-label-sm text-label-sm text-on-surface font-medium">
                Carbohydrate Ingestion
              </span>
            </div>
            <span className={`font-code-sm text-code-sm font-bold ${cob !== null ? "text-secondary" : "text-on-surface-variant font-medium"}`}>
              {cob !== null ? `~${Math.round(cob)}g Ingestion` : "Telemetry Pending"}
            </span>
          </div>

          <ArrowDown className="w-3.5 h-3.5 text-outline-variant" />

          {/* Node 2: Insulin */}
          <div className="w-full bg-surface-container-low p-space-xs px-space-sm rounded flex items-center justify-between border border-surface-container">
            <div className="flex items-center gap-2">
              <Droplets className="w-4 h-4 text-tertiary" />
              <span className="font-label-sm text-label-sm text-on-surface font-medium">
                Active Insulin (IOB)
              </span>
            </div>
            <span className={`font-code-sm text-code-sm font-bold ${iob !== null ? "text-tertiary" : "text-on-surface-variant font-medium"}`}>
              {iob !== null ? `~${iob.toFixed(1)} U Active` : "Telemetry Pending"}
            </span>
          </div>

          <ArrowDown className="w-3.5 h-3.5 text-outline-variant" />

          {/* Node 3: Physiological Flux */}
          <div className={`w-full p-space-xs px-space-sm rounded flex items-center justify-between border ${
            hasValidForecast ? "bg-primary/10 border-primary/20" : "bg-surface-container-low border-surface-container"
          }`}>
            <div className="flex items-center gap-2">
              <Activity className={`w-4 h-4 ${hasValidForecast ? "text-primary" : "text-on-surface-variant"}`} />
              <span className={`font-label-sm text-label-sm font-medium ${hasValidForecast ? "text-primary font-semibold" : "text-on-surface"}`}>
                Physiological Flux
              </span>
            </div>
            <span className={`font-code-sm text-code-sm font-semibold ${hasValidForecast ? "text-primary" : "text-on-surface-variant font-medium"}`}>
              {hasValidForecast ? "ODE State Sync" : "Standby Mode"}
            </span>
          </div>

          <ArrowDown className="w-3.5 h-3.5 text-outline-variant" />

          {/* Node 4: Glycemic Response */}
          <div className="w-full bg-surface-container-low p-space-xs px-space-sm rounded flex items-center justify-between border border-surface-container">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-on-surface-variant" />
              <span className="font-label-sm text-label-sm text-on-surface font-medium">
                Glycemic Response
              </span>
            </div>
            <span className={`font-code-sm text-code-sm ${currentG != null ? "text-on-surface font-bold" : "text-on-surface-variant font-medium"}`}>
              {currentG != null ? `${currentG} mg/dL (Live)` : "Unavailable"}
            </span>
          </div>

          <ArrowDown className="w-3.5 h-3.5 text-outline-variant" />

          {/* Node 5: 5-Hour Forecast */}
          <div className="w-full bg-surface-container-high p-space-xs px-space-sm rounded flex items-center justify-between border border-surface-container">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              <span className="font-label-sm text-label-sm text-on-surface font-bold">
                5-Hour Forecast
              </span>
            </div>
            <span className={`font-code-sm text-code-sm font-bold ${peak != null ? "text-primary" : "text-on-surface-variant font-medium"}`}>
              {peak != null ? `Peak ~${peak} mg/dL` : "Unavailable"}
            </span>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div className="mt-space-md">
        <button
          onClick={() => onNavigate && onNavigate("digital_twin")}
          className="w-full h-8 px-space-sm bg-primary hover:bg-primary-container text-on-primary rounded flex items-center justify-center gap-1.5 font-label-sm text-label-sm font-semibold transition-colors shadow-sm"
        >
          <span>Open Digital Twin</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
