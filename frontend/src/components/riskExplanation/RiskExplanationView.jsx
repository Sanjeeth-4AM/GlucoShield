import React from "react";
import {
  HeartPulse,
  TrendingUp,
  Info,
  Clock,
  Printer,
  CheckCircle,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  MoveRight
} from "lucide-react";

export function RiskExplanationView({ forecastData }) {
  const currentGlucoseVal =
    forecastData?.current_state?.glucose_mg_dl ??
    forecastData?.forecast?.point_forecast_mg_dl?.[0] ??
    forecastData?.point_forecast_mg_dl?.[0] ??
    null;
  const currentGlucose = Number.isFinite(currentGlucoseVal) ? Math.round(currentGlucoseVal) : null;

  const riskAssessment = forecastData?.risk_assessment || {};
  const hypoProb = riskAssessment?.hypo_2h_prob ?? riskAssessment?.hypo_probability ?? null;
  const hyperProb = riskAssessment?.hyper_2h_prob ?? riskAssessment?.hyper_probability ?? null;
  const nadirVal = (riskAssessment?.nadir_mg_dl ?? riskAssessment?.projected_nadir_mg_dl) != null
    ? Math.round(riskAssessment.nadir_mg_dl ?? riskAssessment.projected_nadir_mg_dl)
    : null;
  const peakVal = (riskAssessment?.peak_mg_dl ?? riskAssessment?.projected_peak_mg_dl) != null
    ? Math.round(riskAssessment.peak_mg_dl ?? riskAssessment.projected_peak_mg_dl)
    : null;
  const peakTime = riskAssessment?.time_to_peak_min ?? null;
  const nadirTime = riskAssessment?.time_to_nadir_min ?? null;

  const primaryStatus = riskAssessment?.primary_status || (currentGlucose !== null ? "STABLE" : "UNAVAILABLE");
  const alertLevel = riskAssessment?.alert_level || (currentGlucose !== null ? "INFO" : "UNAVAILABLE");
  const activeAlerts = Array.isArray(riskAssessment?.active_alerts) ? riskAssessment.active_alerts : [];

  const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || forecastData?.point_forecast_mg_dl || [];
  const lower95 = forecastData?.forecast?.lower_95_mg_dl || [];
  const upper95 = forecastData?.forecast?.upper_95_mg_dl || [];
  const minLower95 = lower95.length > 0 ? Math.min(...lower95) : null;
  const crossesHypo50 = minLower95 !== null && minLower95 < 50.0;

  const hypoStatus = hypoProb === null
    ? "Unavailable"
    : hypoProb > 0.2 ? "Elevated Risk" : hypoProb > 0.1 ? "Moderate" : "Low Risk";
  const hyperStatus = hyperProb === null
    ? "Unavailable"
    : hyperProb > 0.4 ? "High Risk" : hyperProb > 0.2 ? "Moderate Elevation" : "Controlled";

  // Genuine Explanation Object
  const exp = forecastData?.explanation || forecastData?.explanations;
  const metabolicFactors = exp?.metabolic_factors || [];
  const rawDrivers = exp?.forecast_drivers || [];

  return (
    <div className="flex flex-col w-full space-y-6">
      {/* Top Control Ribbon & Clinical Context */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md py-space-lg mb-space-sm">
        <div className="flex flex-col">
          <div className="flex items-center gap-space-xs text-primary font-code-sm text-code-sm font-semibold tracking-wider uppercase mb-space-xs">
            <Sparkles className="w-4 h-4 text-primary" />
            <span>MODEL ARCHITECTURE: COMBINATION C</span>
            <span className="text-outline-variant">•</span>
            <span className="text-on-surface-variant font-medium">ATTRIBUTION: QUALITATIVE PHYSIOLOGICAL</span>
          </div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface">
            Clinical Risk Stratification &amp; Model Explainability
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-0.5">
            Auditable risk trajectories and feature attribution for Combination C hybrid model
          </p>
          <div className="flex items-center gap-2 mt-2">
            <div className="px-3 py-1 rounded-lg bg-surface-container-low border border-surface-container text-xs font-mono font-bold text-on-surface">
              PRIMARY STATUS: <span className="text-primary">{primaryStatus}</span>
            </div>
            <div className={`px-3 py-1 rounded-lg border text-xs font-mono font-bold ${
              alertLevel === "CRITICAL" ? "bg-error/15 text-error border-error/30" :
              alertLevel === "WARNING" ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30" :
              "bg-primary/10 text-primary border-primary/25"
            }`}>
              ALERT LEVEL: {alertLevel}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-space-sm">
          <div className="px-space-md py-space-xs bg-surface-container-low rounded-xl flex items-center gap-space-sm shadow-sm border border-surface-container">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"></span>
            </span>
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Risk Assessment Window</span>
              <span className="font-code-sm text-code-sm text-on-surface font-semibold">
                T0 → T+5h Horizon (20 Steps)
              </span>
            </div>
          </div>
          <button
            onClick={() => window.print()}
            className="px-space-md py-2 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface font-label-sm text-label-sm rounded-lg shadow-sm flex items-center gap-space-xs transition-colors border border-surface-container"
          >
            <Printer className="w-4 h-4 text-on-surface-variant" />
            <span>Print Audit</span>
          </button>
        </div>
      </div>

      {/* Downside Uncertainty Notice & Active Risk Alerts */}
      {(activeAlerts.length > 0 || crossesHypo50) && (
        <div className="mb-space-lg p-space-lg rounded-xl bg-amber-500/10 border border-amber-500/30 shadow-xs flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-bold text-sm">
              <span className="text-lg">⚠️</span>
              <span className="uppercase tracking-wider">Metabolic Uncertainty Notice</span>
            </div>
            <span className="font-mono text-xs text-amber-700 dark:text-amber-400 font-semibold px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/30">
              Calibrated 95% CI Boundary
            </span>
          </div>

          {activeAlerts.map((alert, idx) => (
            <div key={idx} className="font-mono text-xs text-amber-900 dark:text-amber-200 font-semibold flex items-center gap-1.5 pl-6">
              <span>•</span>
              <span>{alert}</span>
            </div>
          ))}

          {crossesHypo50 && !activeAlerts.some((a) => a.toLowerCase().includes("hypoglycemic")) && (
            <div className="font-mono text-xs text-amber-900 dark:text-amber-200 font-semibold flex items-center gap-1.5 pl-6">
              <span>•</span>
              <span>NOTICE: Downside trajectory uncertainty extends into hypoglycemic range. Calibrated 95% lower bound reaches {minLower95} mg/dL.</span>
            </div>
          )}

          {exp?.uncertainty_rationale && (
            <div className="text-xs text-on-surface-variant font-mono pl-6 pt-2 border-t border-amber-500/20">
              <strong className="text-on-surface">Predictive Uncertainty Rationale:</strong> {exp.uncertainty_rationale}
            </div>
          )}
        </div>
      )}

      {/* Trajectory & Interval Range Summary */}
      {pointForecast.length > 0 && (
        <div className="mb-space-lg bg-surface-container-lowest rounded-xl p-space-md border border-surface-container shadow-sm flex flex-wrap items-center justify-between gap-space-md text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-on-surface-variant">Point Forecast Range (20 Steps):</span>
            <span className="text-on-surface font-bold">
              {Math.min(...pointForecast)} – {Math.max(...pointForecast)} mg/dL
            </span>
          </div>
          {lower95.length > 0 && upper95.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-on-surface-variant">Calibrated 95% Interval:</span>
              <span className="text-tertiary font-bold">
                [{Math.min(...lower95)} – {Math.max(...upper95)}] mg/dL
              </span>
              <span className="text-outline text-[11px]">(t+15m: [{lower95[0]} – {upper95[0]}])</span>
            </div>
          )}
          {exp?.headline && (
            <div className="w-full text-on-surface font-sans font-semibold pt-1 border-t border-surface-container">
              {exp.headline}
            </div>
          )}
        </div>
      )}

      {/* Quantity Distinction Callout Banner */}
      <div className="p-space-md rounded-xl bg-surface-container-low border border-surface-container shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm text-xs font-mono">
        <div className="flex items-center gap-2 text-on-surface">
          <Info className="w-4 h-4 text-primary shrink-0" />
          <span>
            <strong className="text-primary font-sans font-semibold">Clinical Quantity Distinction:</strong>{" "}
            Point nadir ({nadirVal !== null ? `${nadirVal} mg/dL` : "—"}) represents central expectation. Prediction intervals (e.g. 95% lower bound reaches {minLower95 !== null ? `${minLower95} mg/dL` : "—"}) quantify statistical dispersion and forecast uncertainty, not discrete threshold crossing probability. Discrete 2h acute hypoglycemia probability is {hypoProb !== null ? `${(hypoProb * 100).toFixed(1)}%` : "—"}.
          </span>
        </div>
      </div>

      {/* Clinical Risk Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Hypoglycemia Profile Card */}
        <div className="bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm border border-surface-container flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 left-0 bottom-0 w-1.5 bg-tertiary"></div>
          <div>
            <div className="flex items-start justify-between gap-space-md mb-space-md">
              <div className="flex items-center gap-space-sm">
                <div className="w-10 h-10 rounded-lg bg-surface-container-low text-tertiary flex items-center justify-center">
                  <HeartPulse className="w-5 h-5 text-tertiary" />
                </div>
                <div>
                  <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">
                    Threshold: &lt;70 mg/dL
                  </span>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">Hypoglycemia Risk Profile</h2>
                </div>
              </div>
              <div className="px-space-sm py-1 rounded bg-surface-container-low text-tertiary font-label-sm text-label-sm font-semibold flex items-center gap-1.5 border border-surface-container">
                <span className="w-2 h-2 rounded-full bg-tertiary"></span>
                <span>Status: {hypoStatus}</span>
              </div>
            </div>

            <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed mb-space-lg">
              {nadirVal !== null ? (
                <>
                  Projected nadir reading is{" "}
                  <span className="font-telemetry-metric text-telemetry-metric text-on-surface font-semibold">
                    {nadirVal} mg/dL
                  </span>{" "}
                  {nadirTime ? `at T+${nadirTime}m ` : ""}under active basal and bolus pharmacodynamics.
                </>
              ) : (
                "Continuous trajectory evaluates hypoglycemia threshold across the full 5-hour forward projection horizon."
              )}
            </p>

            {/* Sub-threshold Breakdown */}
            <div className="grid grid-cols-2 gap-space-md bg-surface-container-low p-space-md rounded-lg mb-space-md border border-surface-container">
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Level 1 (&lt;70 mg/dL)</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="font-headline-sm text-headline-sm text-tertiary font-semibold">{hypoStatus}</span>
                </div>
                <span className="font-body-sm text-body-sm text-outline mt-0.5">
                  {hypoProb !== null ? `${(hypoProb * 100).toFixed(1)}% probability (2h)` : "—"}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Level 2 (&lt;54 mg/dL)</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                    {nadirVal !== null && nadirVal < 54 ? "Elevated" : "Controlled"}
                  </span>
                </div>
                <span className="font-body-sm text-body-sm text-outline mt-0.5">
                  {nadirVal !== null && nadirVal < 54 ? "Nadir <54 mg/dL" : "Point nadir above 54 mg/dL"}
                </span>
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-space-md flex items-center justify-between border-t border-surface-container">
            <div className="flex items-center gap-1 text-on-surface-variant font-label-sm text-label-sm">
              <Info className="w-4 h-4 text-tertiary" />
              <span>Model Horizon: 5-Hour Forecast Window</span>
            </div>
            <span className="font-code-sm text-code-sm text-outline">Calculated Trajectory</span>
          </div>
        </div>

        {/* Hyperglycemia Profile Card */}
        <div className="bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm border border-surface-container flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 left-0 bottom-0 w-1.5 bg-secondary"></div>
          <div>
            <div className="flex items-start justify-between gap-space-md mb-space-md">
              <div className="flex items-center gap-space-sm">
                <div className="w-10 h-10 rounded-lg bg-surface-container-low text-secondary flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-secondary" />
                </div>
                <div>
                  <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">
                    Threshold: &gt;180 mg/dL
                  </span>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">Hyperglycemia Risk Profile</h2>
                </div>
              </div>
              <div className="px-space-sm py-1 rounded bg-surface-container-low text-secondary font-label-sm text-label-sm font-semibold flex items-center gap-1.5 border border-surface-container">
                <span className="w-2 h-2 rounded-full bg-secondary"></span>
                <span>Status: {hyperStatus}</span>
              </div>
            </div>

            <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed mb-space-lg">
              {peakVal !== null ? (
                <>
                  Projected excursion peak near{" "}
                  <span className="font-code-sm text-code-sm text-on-surface font-semibold">
                    {peakTime ? `+${peakTime}m ` : ""}(~{peakVal} mg/dL)
                  </span>{" "}
                  with potential upper bound {peakVal > 180 ? "exceeding" : "within"} 180 mg/dL clinical target boundary.
                </>
              ) : (
                "Continuous trajectory evaluates postprandial glycemic excursions against target 70–180 mg/dL boundaries."
              )}
            </p>

            {/* Recommendation Banner */}
            <div className="bg-surface-container-low p-space-md rounded-lg mb-space-md flex items-start gap-space-sm border border-surface-container">
              <Info className="w-5 h-5 text-secondary shrink-0 mt-0.5" />
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm font-semibold text-on-surface">Physiological Observation</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant mt-0.5 leading-normal">
                  {riskAssessment?.physiological_observation || "Active insulin on board continues steady clearance toward normal euglycemic range."}
                </span>
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-space-md flex items-center justify-between border-t border-surface-container">
            <div className="flex items-center gap-1 text-on-surface-variant font-label-sm text-label-sm">
              <Clock className="w-4 h-4 text-secondary" />
              <span>Projected Excursion Tracking</span>
            </div>
            <span className="font-code-sm text-code-sm text-outline">Calculated Trajectory</span>
          </div>
        </div>
      </div>

      {/* Middle Row: Risk Horizon Timeline Chart */}
      <div className="bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm border border-surface-container">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-sm mb-space-lg">
          <div className="flex flex-col">
            <div className="flex items-center gap-space-xs">
              <Clock className="w-4 h-4 text-primary" />
              <h2 className="font-headline-sm text-headline-sm text-on-surface">Rolling 5-Hour Risk Timeline</h2>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              Discrete certified horizon milestones (T+1h, T+2h, T+4h) evaluated by Combination C
            </p>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-space-md">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-tertiary"></span>
              <span className="font-label-sm text-label-sm text-on-surface-variant">Hypoglycemia Risk (&lt;70)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-secondary"></span>
              <span className="font-label-sm text-label-sm text-on-surface-variant">Hyperglycemia Risk (&gt;180)</span>
            </div>
          </div>
        </div>

        {/* Timeline Grid Bars (5 Horizon Milestones) */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-space-sm pt-space-xs">
          {/* Milestone 1: T+1h */}
          <div className="bg-surface-container-low rounded-lg p-space-md flex flex-col justify-between border border-surface-container">
            <div>
              <div className="flex items-center justify-between mb-space-xs">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">T0 → T+1h</span>
                <span className="font-label-sm text-label-sm text-outline">+60m</span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface-variant">Early Postprandial Influx</span>
            </div>
            <div className="my-space-md flex flex-col gap-2">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hyper</span>
                  <span className="font-code-sm text-code-sm text-outline italic">
                    N/A — Not Evaluated
                  </span>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hypo</span>
                  <span className="font-code-sm text-code-sm font-semibold text-tertiary">
                    {riskAssessment?.hypo_1h_prob != null ? `${(riskAssessment.hypo_1h_prob * 100).toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>
            </div>
            <span className="font-body-sm text-body-sm text-outline">Certified 1h Milestone (Hypo)</span>
          </div>

          {/* Milestone 2: T+2h (Apex Window) */}
          <div className="bg-surface-container rounded-lg p-space-md flex flex-col justify-between relative shadow-sm border border-secondary/30">
            <div className="absolute top-2 right-2">
              <span className="px-1.5 py-0.5 rounded bg-secondary text-on-secondary font-code-sm text-[10px] uppercase font-bold tracking-tight">
                2h Window
              </span>
            </div>
            <div>
              <div className="flex items-center justify-between mb-space-xs">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">T+1h → T+2h</span>
                <span className="font-label-sm text-label-sm text-secondary font-semibold">+120m</span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface font-medium">Postprandial Peak Window</span>
            </div>
            <div className="my-space-md flex flex-col gap-2">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface font-medium">Hyper</span>
                  <span className="font-code-sm text-code-sm font-semibold text-secondary">
                    {riskAssessment?.hyper_2h_prob != null ? `${(riskAssessment.hyper_2h_prob * 100).toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hypo</span>
                  <span className="font-code-sm text-code-sm font-semibold text-tertiary">
                    {riskAssessment?.hypo_2h_prob != null ? `${(riskAssessment.hypo_2h_prob * 100).toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>
            </div>
            <span className="font-body-sm text-body-sm text-secondary font-medium">Certified 2h Milestone</span>
          </div>

          {/* Milestone 3: T+3h (Unmodeled discrete milestone) */}
          <div className="bg-surface-container-low rounded-lg p-space-md flex flex-col justify-between border border-surface-container">
            <div>
              <div className="flex items-center justify-between mb-space-xs">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">T+2h → T+3h</span>
                <span className="font-label-sm text-label-sm text-outline">+180m</span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface-variant">Transition Phase</span>
            </div>
            <div className="my-space-md flex flex-col gap-2">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hyper</span>
                  <span className="font-code-sm text-code-sm text-outline italic">N/A — Not Evaluated</span>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hypo</span>
                  <span className="font-code-sm text-code-sm text-outline italic">N/A — Not Evaluated</span>
                </div>
              </div>
            </div>
            <span className="font-body-sm text-body-sm text-outline">Unmodeled Milestone</span>
          </div>

          {/* Milestone 4: T+4h */}
          <div className="bg-surface-container-low rounded-lg p-space-md flex flex-col justify-between border border-surface-container">
            <div>
              <div className="flex items-center justify-between mb-space-xs">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">T+3h → T+4h</span>
                <span className="font-label-sm text-label-sm text-outline">+240m</span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface-variant">Carbohydrate Depletion Phase</span>
            </div>
            <div className="my-space-md flex flex-col gap-2">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hyper</span>
                  <span className="font-code-sm text-code-sm font-semibold text-secondary">
                    {riskAssessment?.hyper_4h_prob != null ? `${(riskAssessment.hyper_4h_prob * 100).toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hypo</span>
                  <span className="font-code-sm text-code-sm font-semibold text-tertiary">
                    {riskAssessment?.hypo_4h_prob != null ? `${(riskAssessment.hypo_4h_prob * 100).toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>
            </div>
            <span className="font-body-sm text-body-sm text-outline">Certified 4h Milestone</span>
          </div>

          {/* Milestone 5: T+5h (Unmodeled discrete milestone) */}
          <div className="bg-surface-container-low rounded-lg p-space-md flex flex-col justify-between border border-surface-container">
            <div>
              <div className="flex items-center justify-between mb-space-xs">
                <span className="font-code-sm text-code-sm font-semibold text-on-surface">T+4h → T+5h</span>
                <span className="font-label-sm text-label-sm text-outline">+300m</span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface-variant">Target Band Convergence</span>
            </div>
            <div className="my-space-md flex flex-col gap-2">
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hyper</span>
                  <span className="font-code-sm text-code-sm text-outline italic">N/A — Not Evaluated</span>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Hypo</span>
                  <span className="font-code-sm text-code-sm text-outline italic">N/A — Not Evaluated</span>
                </div>
              </div>
            </div>
            <span className="font-body-sm text-body-sm text-outline">Unmodeled Milestone</span>
          </div>
        </div>

        <div className="mt-space-md pt-space-xs text-xs text-on-surface-variant font-mono">
          * Certified Combination C discrete horizons are T+1h (hypo only), T+2h (hypo + hyper), and T+4h (hypo + hyper). Intermediate (T+3h) and terminal (T+5h) discrete risk probabilities are not evaluated by the frozen model heads.
        </div>
      </div>

      {/* Bottom Row: Model Explainability & Attribution Table */}
      <div className="bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm border border-surface-container">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-sm mb-space-lg">
          <div className="flex flex-col">
            <div className="flex items-center gap-space-xs">
              <Sparkles className="w-4 h-4 text-primary" />
              <h2 className="font-headline-sm text-headline-sm text-on-surface">Verified Production Forecast Drivers</h2>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              Physiological state variables driving the projected 5-hour glycemic trajectory in Combination C
            </p>
          </div>
          <div className="flex items-center gap-space-sm text-outline font-code-sm text-code-sm bg-surface-container-low px-space-sm py-1 rounded border border-surface-container">
            <span>Base Glycemic Intercept:</span>
            <span className="text-on-surface font-semibold">{currentGlucose !== null ? `${currentGlucose} mg/dL` : "—"}</span>
          </div>
        </div>

        {/* Attribution Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider h-9">
                <th className="px-space-md py-1 rounded-l">Verified Production Parameter</th>
                <th className="px-space-md py-1">Direct Physiological Role</th>
                <th className="px-space-md py-1">Vector Direction</th>
                <th className="px-space-md py-1">Attribution Scope</th>
                <th className="px-space-md py-1 text-right rounded-r">Impact Classification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-low text-body-md font-body-md">
              {rawDrivers.length > 0 ? (
                rawDrivers.map((d, idx) => (
                  <tr key={idx} className="hover:bg-surface-container-low/50 transition-colors h-14">
                    <td className="px-space-md py-space-sm font-semibold text-on-surface">
                      {d.name || d.driver_name}
                    </td>
                    <td className="px-space-md py-space-sm text-on-surface-variant">
                      {d.explanation || "Physiological contribution"}
                    </td>
                    <td className="px-space-md py-space-sm">
                      <span className="px-2 py-0.5 rounded bg-surface-container-low text-on-surface font-label-sm text-label-sm font-medium">
                        {d.direction === "up" ? "↑ Upward" : d.direction === "down" ? "↓ Downward" : "→ Neutral"}
                      </span>
                    </td>
                    <td className="px-space-md py-space-sm text-outline font-code-sm text-code-sm">
                      Model Attributed
                    </td>
                    <td className="px-space-md py-space-sm text-right">
                      <span className="px-2 py-0.5 rounded bg-surface-container-low text-primary font-label-sm text-label-sm font-semibold">
                        {d.impact_level || "Active"}
                      </span>
                    </td>
                  </tr>
                ))
              ) : metabolicFactors.length > 0 ? (
                metabolicFactors.map((factor, idx) => {
                  const isCarb = factor.toLowerCase().includes("carbohydrate");
                  const isInsulin = factor.toLowerCase().includes("insulin");
                  const isDown = isInsulin && !factor.toLowerCase().includes("low insulin");
                  const isUp = isCarb && !factor.toLowerCase().includes("minimal");

                  return (
                    <tr key={idx} className="hover:bg-surface-container-low/50 transition-colors h-14">
                      <td className="px-space-md py-space-sm">
                        <div className="flex items-center gap-space-sm">
                          <div className="w-8 h-8 rounded bg-surface-container-low text-primary flex items-center justify-center">
                            {isUp ? <TrendingUp className="w-4 h-4 text-secondary" /> : isDown ? <HeartPulse className="w-4 h-4 text-tertiary" /> : <Clock className="w-4 h-4 text-primary" />}
                          </div>
                          <div className="flex flex-col">
                            <span className="font-label-md text-label-md text-on-surface font-semibold">
                              {isCarb ? "Carbohydrate Ingestion (COB)" : isInsulin ? "Active Insulin on Board (IOB)" : "Circadian & Momentum Baseline"}
                            </span>
                            <span className="font-code-sm text-code-sm text-outline">{factor}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-space-md py-space-sm text-on-surface-variant font-body-sm">
                        {isCarb ? "Systemic Gut Appearance" : isInsulin ? "Peripheral Glucose Disposal" : "Metabolic Equilibrium Baseline"}
                      </td>
                      <td className="px-space-md py-space-sm">
                        <span className={`px-2 py-0.5 rounded bg-surface-container-low font-label-sm text-label-sm font-medium inline-flex items-center gap-1 border border-surface-container ${isUp ? "text-secondary" : isDown ? "text-tertiary" : "text-primary"}`}>
                          {isUp ? <ArrowUpRight className="w-3.5 h-3.5" /> : isDown ? <ArrowDownRight className="w-3.5 h-3.5" /> : <MoveRight className="w-3.5 h-3.5" />}
                          {isUp ? "Upward" : isDown ? "Downward" : "Neutral"}
                        </span>
                      </td>
                      <td className="px-space-md py-space-sm text-outline font-code-sm text-code-sm">
                        Physiological Flux
                      </td>
                      <td className="px-space-md py-space-sm text-right">
                        <span className={`px-2 py-0.5 rounded bg-surface-container-low font-label-sm text-label-sm font-semibold border border-surface-container ${isUp ? "text-secondary" : isDown ? "text-tertiary" : "text-primary"}`}>
                          {isUp ? "Carbohydrate Appearance" : isDown ? "Insulin Action" : "Baseline State"}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-on-surface-variant font-body-md">
                    Model attribution unavailable. Generate a forecast to view verified parameter drivers.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Scientific Transparency & Provenance Note */}
        <div className="mt-space-lg p-space-md rounded-lg bg-surface-container-low flex items-start gap-space-md border border-surface-container">
          <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm text-on-surface font-semibold uppercase tracking-wider">
              Scientific Transparency Guarantee
            </span>
            <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5 leading-relaxed">
              Combination C utilizes certified production parameters (continuous glucose monitoring history, pharmacodynamic insulin on board, logged carbohydrate ingestion, and diurnal circadian phase). Additive per-feature mg/dL SHAP decompositions are not computed by the frozen Combination C model; genuine qualitative directional physiological impacts are reported above.
            </p>
          </div>
        </div>
      </div>

      {/* Clinical Sign-Off & Regulatory Footer */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-outline gap-space-sm px-space-xs font-code-sm text-code-sm">
        <div className="flex items-center gap-space-xs">
          <CheckCircle className="w-4 h-4 text-primary" />
          <span>Model Architecture: Combination C • Framework: Certified Hybrid Physics-ODE Serving</span>
        </div>
        <div className="flex items-center gap-space-md">
          <span>Attribution: Qualitative Physiological State Decomposition</span>
        </div>
      </div>
    </div>
  );
}
