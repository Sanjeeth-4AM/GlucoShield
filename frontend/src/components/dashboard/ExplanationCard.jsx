import React from "react";
import { Info, Sparkles } from "lucide-react";

export function ExplanationCard({ explanation, explanations, hybridComponents }) {
  const exp = explanation || explanations;

  // Extract genuine drivers or metabolic factors from backend explanation
  const rawDrivers = exp?.forecast_drivers || [];
  const metabolicFactors = exp?.metabolic_factors || [];

  let displayDrivers = [];

  if (rawDrivers.length > 0) {
    displayDrivers = rawDrivers.map((d, idx) => ({
      title: `${idx + 1}. ${d.name || d.driver_name || "Metabolic Parameter"}`,
      subtitle: d.value_text || null,
      vector: d.direction === "up" ? "↑" : d.direction === "down" ? "↓" : "→",
      vectorColor: d.direction === "up" ? "text-secondary" : d.direction === "down" ? "text-tertiary" : "text-primary",
      impactTag: d.impact_level || "Active Factor",
      description: d.explanation || d.clinical_rationale || "Physiological contribution to 5-hour forward projection."
    }));
  } else if (metabolicFactors.length > 0) {
    displayDrivers = metabolicFactors.map((factor, idx) => {
      const isCarb = factor.toLowerCase().includes("carbohydrate");
      const isInsulin = factor.toLowerCase().includes("insulin");
      const isDown = isInsulin && !factor.toLowerCase().includes("low insulin");
      const isUp = isCarb && !factor.toLowerCase().includes("minimal");

      return {
        title: `${idx + 1}. ${isCarb ? "Carbohydrate Influx" : isInsulin ? "Insulin Pharmacodynamics" : "Physiological Momentum"}`,
        subtitle: null,
        vector: isUp ? "↑" : isDown ? "↓" : "→",
        vectorColor: isUp ? "text-secondary" : isDown ? "text-tertiary" : "text-primary",
        impactTag: isUp ? "Absorption" : isDown ? "Clearance" : "Equilibrium",
        description: factor
      };
    });
  }

  const hasExplanation = displayDrivers.length > 0 || Boolean(exp?.trend_summary);

  return (
    <div className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm flex flex-col justify-between border border-surface-container h-full">
      <div>
        <div className="flex items-center gap-space-xs">
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
            SECTION D
          </span>
          <span className="text-outline-variant">•</span>
          <h2 className="font-label-md text-label-md font-semibold text-on-surface">
            Why is the model predicting this?
          </h2>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5 mb-space-md">
          Primary verified production drivers in Combination C architecture
        </p>

        {exp?.trend_summary && (
          <div className="mb-space-sm p-space-sm rounded bg-surface-container-low border border-surface-container">
            <span className="font-label-sm text-label-sm font-semibold text-on-surface block mb-0.5">
              Trajectory Summary
            </span>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              {exp.trend_summary}
            </p>
          </div>
        )}

        {hasExplanation ? (
          <div className="space-y-space-sm">
            {displayDrivers.map((driver, idx) => (
              <div key={idx} className="bg-surface-container-low p-space-sm rounded border border-surface-container">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="font-label-md text-label-md font-semibold text-on-surface">
                      {driver.title}
                    </span>
                    {driver.subtitle && (
                      <span className="font-code-sm text-code-sm text-secondary font-medium">
                        ({driver.subtitle})
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`font-bold text-sm ${driver.vectorColor}`}>{driver.vector}</span>
                    <span className="px-1.5 py-0.5 rounded bg-surface-container-high font-code-sm text-code-sm font-semibold text-on-surface">
                      {driver.impactTag}
                    </span>
                  </div>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                  {driver.description}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-space-lg rounded-lg bg-surface-container-low text-center border border-surface-container">
            <Info className="w-5 h-5 text-outline mx-auto mb-1.5" />
            <span className="font-label-md text-label-md text-on-surface font-semibold block">
              Model attribution unavailable
            </span>
            <span className="font-body-sm text-body-sm text-on-surface-variant mt-1 block">
              Generate a forecast to view verified physiological attribution drivers.
            </span>
          </div>
        )}

        {exp?.uncertainty_rationale && (
          <div className="mt-space-sm p-space-sm rounded bg-surface-container-low border border-surface-container">
            <span className="font-label-sm text-label-sm font-semibold text-on-surface block mb-0.5">
              Uncertainty &amp; Downside Dispersion Analysis
            </span>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              {exp.uncertainty_rationale}
            </p>
          </div>
        )}
      </div>

      <div className="mt-space-md pt-space-xs text-right">
        <span className="font-code-sm text-code-sm text-outline">
          {exp?.hybrid_attribution || "Attribution: Production Model Combination C"}
        </span>
      </div>
    </div>
  );
}
