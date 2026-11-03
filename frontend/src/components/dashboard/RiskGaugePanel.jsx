import React from "react";
import { Info } from "lucide-react";

export function RiskGaugePanel({ riskAssessment }) {
  // Support certified Combination C risk schema and legacy fallbacks
  const rawHypo = riskAssessment?.hypo_2h_prob ?? riskAssessment?.hypo_risk ?? null;
  const rawHyper = riskAssessment?.hyper_2h_prob ?? riskAssessment?.hyper_risk ?? null;

  const peak = (riskAssessment?.peak_mg_dl ?? riskAssessment?.projected_peak_mg_dl) != null
    ? Math.round(riskAssessment.peak_mg_dl ?? riskAssessment.projected_peak_mg_dl)
    : null;
  const peakTime = riskAssessment?.time_to_peak_min ?? riskAssessment?.projected_peak_time_minutes ?? null;
  const nadir = (riskAssessment?.nadir_mg_dl ?? riskAssessment?.projected_nadir_mg_dl) != null
    ? Math.round(riskAssessment.nadir_mg_dl ?? riskAssessment.projected_nadir_mg_dl)
    : null;

  // Hypoglycemia metrics
  const hypoPct = rawHypo !== null ? Math.round(Math.min(100, Math.max(0, rawHypo * 100))) : null;
  const hypoLabel = hypoPct === null
    ? "Unavailable"
    : riskAssessment?.hypo_risk_level || (hypoPct < 20 ? "Low Risk" : hypoPct < 50 ? "Moderate Risk" : "High Risk");
  const hypoDesc = hypoPct === null
    ? "Risk metric unavailable"
    : nadir ? `Projected nadir: ~${nadir} mg/dL` : "Minimal descent trajectory expected";

  // Hyperglycemia metrics
  const hyperPct = rawHyper !== null ? Math.round(Math.min(100, Math.max(0, rawHyper * 100))) : null;
  const hyperLabel = hyperPct === null
    ? "Unavailable"
    : riskAssessment?.hyper_risk_level || (hyperPct < 25 ? "Low Risk" : hyperPct < 60 ? "Moderate Risk" : "Elevated Risk");
  const hyperDesc = hyperPct === null
    ? "Risk metric unavailable"
    : peak ? `Projected peak: ${peakTime ? `+${Math.floor(peakTime / 60)}h ${peakTime % 60}m ` : ""}(~${peak} mg/dL)` : "Projected excursion within standard bounds";

  const observationText = riskAssessment?.physiological_observation ||
    (peak && peak <= 180
      ? `Projected peak within target range (~${peak} mg/dL) based on recorded meal and active pharmacodynamic insulin.`
      : peak && peak > 180
      ? `Transient postprandial peak projected near ~${peak} mg/dL before insulin clearance restores target range.`
      : rawHypo !== null
      ? "Nominal metabolic equilibrium maintained across 5-hour forward projection horizon."
      : "Risk projection pending forecast generation.");

  return (
    <div className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm flex flex-col justify-between border border-surface-container h-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-space-xs">
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
            SECTION C
          </span>
          <span className="text-outline-variant">•</span>
          <h2 className="font-label-md text-label-md font-semibold text-on-surface">
            METABOLIC RISK PROJECTION
          </h2>
        </div>
        <span className="font-code-sm text-code-sm text-outline">Trajectory: +5h • Acute Risk: +2h</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md my-space-sm">
        {/* Hypoglycemia Card */}
        <div className="bg-surface-container-low p-space-sm rounded border border-surface-container">
          <div className="flex items-center justify-between mb-1">
            <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">
              Hypoglycemia Risk (2h acute, &lt;70 mg/dL)
            </span>
            <span
              className={`font-code-sm text-code-sm font-bold ${
                hypoPct === null
                  ? "text-on-surface-variant"
                  : hypoPct > 50
                  ? "text-error"
                  : "text-tertiary"
              }`}
            >
              {hypoLabel} {hypoPct !== null && `(${hypoPct}%)`}
            </span>
          </div>
          <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                hypoPct === null ? "bg-transparent" : hypoPct > 50 ? "bg-error" : "bg-tertiary"
              }`}
              style={{ width: `${hypoPct !== null ? Math.max(5, hypoPct) : 0}%` }}
            />
          </div>
          <span className="font-body-sm text-body-sm text-on-surface-variant mt-1.5 block">
            {hypoDesc}
          </span>
        </div>

        {/* Hyperglycemia Card */}
        <div className="bg-surface-container-low p-space-sm rounded border border-surface-container">
          <div className="flex items-center justify-between mb-1">
            <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">
              Hyperglycemia Risk (2h acute, &gt;180 mg/dL)
            </span>
            <span
              className={`font-code-sm text-code-sm font-bold ${
                hyperPct === null
                  ? "text-on-surface-variant"
                  : hyperPct > 60
                  ? "text-error"
                  : "text-secondary"
              }`}
            >
              {hyperLabel} {hyperPct !== null && `(${hyperPct}%)`}
            </span>
          </div>
          <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                hyperPct === null ? "bg-transparent" : hyperPct > 60 ? "bg-error" : "bg-secondary-container"
              }`}
              style={{ width: `${hyperPct !== null ? Math.max(5, hyperPct) : 0}%` }}
            />
          </div>
          <span className="font-body-sm text-body-sm text-on-surface-variant mt-1.5 block">
            {hyperDesc}
          </span>
        </div>
      </div>

      {/* Active Clinical / Uncertainty Alerts */}
      {Array.isArray(riskAssessment?.active_alerts) && riskAssessment.active_alerts.length > 0 && (
        <div className="mb-space-xs p-2 rounded bg-amber-500/10 border border-amber-500/30 flex flex-col gap-1">
          {riskAssessment.active_alerts.map((alert, idx) => (
            <div key={idx} className="flex items-center gap-1.5 text-[11px] font-mono text-amber-700 dark:text-amber-400 font-semibold">
              <span className="text-xs">⚠️</span>
              <span>{alert}</span>
            </div>
          ))}
        </div>
      )}

      {/* Observation Box */}
      <div className="flex items-start gap-space-xs p-space-xs bg-surface-container-high/60 rounded border border-surface-container mt-auto">
        <Info className="w-4 h-4 text-primary mt-0.5 shrink-0" />
        <p className="font-body-sm text-body-sm text-on-surface">
          <strong className="font-medium text-on-surface">Physiological Observation:</strong> {observationText}
        </p>
      </div>
    </div>
  );
}
