import React, { useState } from "react";
import { ForecastChart } from "../dashboard/ForecastChart.jsx";
import {
  RefreshCw,
  ShieldCheck,
  Activity,
  CheckCircle2,
  Table as TableIcon
} from "lucide-react";

export function ForecastView({
  historyReadings,
  forecastData,
  whatIfTrajectory,
  isLoading,
  onRefresh
}) {
  const [ciFilter, setCiFilter] = useState("all"); // "all", "80_only", "mean_only"

  const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
  const lower80 = forecastData?.forecast?.lower_80_mg_dl || [];
  const upper80 = forecastData?.forecast?.upper_80_mg_dl || [];
  const lower95 = forecastData?.forecast?.lower_95_mg_dl || [];
  const upper95 = forecastData?.forecast?.upper_95_mg_dl || [];
  const originGlucose = forecastData?.current_state?.glucose_mg_dl ?? (historyReadings?.length > 0 ? historyReadings[historyReadings.length - 1]?.cgm_glucose : null);

  // Compute 5-Hour Horizon Projected In-Range directly from point forecast
  const hasPointForecast = Array.isArray(pointForecast) && pointForecast.length > 0;
  const projectedTir = hasPointForecast
    ? Math.round((pointForecast.filter((g) => g >= 70 && g <= 180).length / pointForecast.length) * 100)
    : null;
  const tirDisplay = projectedTir !== null ? `${projectedTir}%` : "—";

  // Compute Historical Observed In-Range (Buffer)
  const validHistory = (historyReadings || []).filter(
    (r) => r && typeof r.cgm_glucose === "number" && !isNaN(r.cgm_glucose)
  );
  const historicalTir = validHistory.length > 0
    ? Math.round((validHistory.filter((r) => r.cgm_glucose >= 70 && r.cgm_glucose <= 180).length / validHistory.length) * 100)
    : null;
  const historicalTirDisplay = historicalTir !== null ? `${historicalTir}%` : "—";

  // 5 Hourly milestone steps (+1h, +2h, +3h, +4h, +5h) -> indices 3, 7, 11, 15, 19
  const milestones = [
    { step: "T+1h", timeOffset: "+60m", idx: 3 },
    { step: "T+2h", timeOffset: "+120m", idx: 7 },
    { step: "T+3h", timeOffset: "+180m", idx: 11 },
    { step: "T+4h", timeOffset: "+240m", idx: 15 },
    { step: "T+5h", timeOffset: "+300m", idx: 19 }
  ].map((m) => {
    const hasPoint = typeof pointForecast[m.idx] === "number" && !isNaN(pointForecast[m.idx]) && isFinite(pointForecast[m.idx]);
    const val = hasPoint ? Math.round(pointForecast[m.idx]) : "—";
    const hasL80 = typeof lower80[m.idx] === "number" && !isNaN(lower80[m.idx]) && isFinite(lower80[m.idx]);
    const hasU80 = typeof upper80[m.idx] === "number" && !isNaN(upper80[m.idx]) && isFinite(upper80[m.idx]);
    const hasL95 = typeof lower95[m.idx] === "number" && !isNaN(lower95[m.idx]) && isFinite(lower95[m.idx]);
    const hasU95 = typeof upper95[m.idx] === "number" && !isNaN(upper95[m.idx]) && isFinite(upper95[m.idx]);

    const l80 = hasL80 ? Math.round(lower80[m.idx]) : "—";
    const u80 = hasU80 ? Math.round(upper80[m.idx]) : "—";
    const l95 = hasL95 ? Math.round(lower95[m.idx]) : "—";
    const u95 = hasU95 ? Math.round(upper95[m.idx]) : "—";

    const prevVal = m.idx === 3 ? originGlucose : pointForecast[m.idx - 4];
    const hasPrev = typeof prevVal === "number" && !isNaN(prevVal) && isFinite(prevVal);
    const roc = (hasPoint && hasPrev) ? ((pointForecast[m.idx] - prevVal) / 60).toFixed(1) : null;
    const rocText = roc !== null ? `${Number(roc) >= 0 ? "+" : ""}${roc} mg/dL/m` : "—";

    return {
      step: m.step,
      timeOffset: m.timeOffset,
      projected: val,
      interval80: (hasL80 && hasU80 && u80 >= l80) ? `${l80} – ${u80}` : "—",
      interval95: (hasL95 && hasU95 && u95 >= l95) ? `${l95} – ${u95}` : "—",
      rocText
    };
  });

  const hasIntervals = Array.isArray(lower80) && lower80.length > 0 && Array.isArray(upper80) && upper80.length > 0;

  // Clinical trajectory and diagnostics derived from genuine forecast telemetry
  const primaryStatus = forecastData?.risk_assessment?.primary_status || "STABLE";
  const alertLevel = forecastData?.risk_assessment?.alert_level;
  const trendSummary = forecastData?.explanation?.trend_summary || primaryStatus;
  const headline = forecastData?.explanation?.headline || (
    forecastData?.risk_assessment?.peak_mg_dl != null
      ? `Forward trajectory evaluated under Combination C. Projected peak: ~${Math.round(forecastData.risk_assessment.peak_mg_dl)} mg/dL (+${forecastData.risk_assessment.time_to_peak_min || 0}m).`
      : "Forward trajectory evaluated under continuous neural-physiological hybrid serving."
  );

  const trajectoryStatusText = forecastData?.risk_assessment?.primary_status
    ? `${forecastData.risk_assessment.primary_status} (${forecastData.risk_assessment.alert_level || "NOMINAL"})`
    : (projectedTir !== null ? `${projectedTir}% In-Range (70–180)` : "Pending Forecast");

  const ensembleStatus = alertLevel === "CRITICAL"
    ? "Critical Alert (Active)"
    : alertLevel === "WARNING"
    ? "Warning Advisory (Active)"
    : alertLevel === "INFO"
    ? "Informational Advisory"
    : forecastData?.forecast
    ? "Nominal Serving (Active)"
    : "Awaiting Forecast";

  return (
    <div className="flex flex-col w-full space-y-6">
      {/* Header Section */}
      <section className="flex flex-col gap-space-md">
        <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-space-md">
          <div>
            <div className="flex items-center gap-space-xs text-primary font-code-sm text-code-sm uppercase tracking-wider mb-space-xs font-semibold">
              <span className="material-symbols-outlined text-sm">insights</span>
              <span>FORECAST ENGINE</span>
            </div>
            <h1 className="font-headline-xl text-headline-xl text-on-surface tracking-tight text-2xl lg:text-3xl font-bold">
              5-Hour Glucose Forecast &amp; Horizon Analytics
            </h1>
            <p className="font-body-md text-body-md text-on-surface-variant mt-0.5">
              Continuous 20-step neural-physiological hybrid forecast projection (Combination C)
            </p>
          </div>

          {/* Action Toggles */}
          <div className="flex flex-wrap items-center gap-space-sm self-start xl:self-auto">
            <div className="flex items-center bg-surface-container-high rounded p-0.5 border border-surface-container">
              <button
                onClick={() => setCiFilter("all")}
                className={`px-space-sm py-1 rounded text-xs font-semibold transition-all ${
                  ciFilter === "all"
                    ? "bg-surface-container-lowest text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                Prediction Ranges
              </button>
              <button
                onClick={() => setCiFilter("80_only")}
                className={`px-space-sm py-1 rounded text-xs font-semibold transition-all ${
                  ciFilter === "80_only"
                    ? "bg-surface-container-lowest text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                80% Range Only
              </button>
              <button
                onClick={() => setCiFilter("mean_only")}
                className={`px-space-sm py-1 rounded text-xs font-semibold transition-all ${
                  ciFilter === "mean_only"
                    ? "bg-surface-container-lowest text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                Forecast Only
              </button>
            </div>

            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="flex items-center gap-space-xs px-space-md py-1.5 rounded bg-primary text-on-primary font-label-sm text-label-sm font-semibold hover:bg-primary-container shadow-sm transition-colors disabled:opacity-50 text-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Recalculate Run</span>
            </button>
          </div>
        </div>

        {/* Telemetry Triage Ribbon */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-space-sm p-space-md bg-surface-container-low rounded-xl border border-surface-container">
          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase text-[10px]">
              Model Status
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
              <span className="font-code-sm text-code-sm text-primary font-semibold text-xs">
                Active (Comb C)
              </span>
            </div>
          </div>

          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase text-[10px]">
              Inference Cadence
            </span>
            <span className="font-code-sm text-code-sm text-on-surface font-semibold text-xs mt-0.5">
              15 min steps (5h)
            </span>
          </div>

          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase text-[10px]">
              Data Continuity
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-tertiary"></span>
              <span className="font-code-sm text-code-sm text-tertiary font-semibold text-xs">
                Continuous Sync
              </span>
            </div>
          </div>

          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase text-[10px]">
              Forecast Horizon
            </span>
            <span className="font-code-sm text-code-sm text-on-surface font-semibold text-xs mt-0.5">
              NOW → +5h (20 steps)
            </span>
          </div>

          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase text-[10px]">
              Telemetry Stream
            </span>
            <span className="font-code-sm text-code-sm text-on-surface font-semibold text-xs mt-0.5 truncate">
              CGM 24h Buffer
            </span>
          </div>

          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase text-[10px]">
              Uncertainty Bounds
            </span>
            <div className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-code-sm text-[11px] font-semibold mt-0.5 w-fit ${
              hasIntervals ? "bg-surface-container text-primary" : "bg-surface-container text-on-surface-variant"
            }`}>
              {hasIntervals && <CheckCircle2 className="w-3 h-3 text-primary" />}
              <span>{hasIntervals ? "80% & 95% UI" : "Unavailable"}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Hero Chart Panel */}
      <ForecastChart
        historyReadings={historyReadings}
        forecastData={forecastData}
        whatIfTrajectory={whatIfTrajectory}
        isLoading={isLoading}
        showTitle={false}
        horizonFilter={ciFilter}
      />

      {/* Analytical Bottom Panels (3 Columns) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        {/* Card 1: Interpretation & Expected Glucose Trend */}
        <div className="lg:col-span-4 bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm flex flex-col justify-between border border-surface-container">
          <div>
            <div className="flex items-center justify-between mb-space-sm">
              <div className="flex items-center gap-space-xs text-on-surface font-headline-sm text-headline-sm font-semibold">
                <Activity className="w-5 h-5 text-primary" />
                <span>Expected Glucose Trend</span>
              </div>
              <span className="px-space-xs py-0.5 rounded bg-surface-container font-label-sm text-label-sm text-on-surface-variant font-semibold text-xs">
                {trendSummary}
              </span>
            </div>

            <div className="p-space-sm rounded bg-surface-container-low mb-space-md border border-surface-container">
              <p className="font-body-md text-body-md text-on-surface leading-relaxed text-xs">
                {headline}
              </p>
            </div>

            <div className="flex flex-col gap-space-sm">
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-on-surface-variant font-medium">5-Hour Horizon Projected In-Range:</span>
                  <span className="font-telemetry-metric text-primary font-bold text-sm">{tirDisplay}</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-primary h-full rounded-full transition-all duration-500"
                    style={{ width: `${projectedTir !== null ? projectedTir : 0}%` }}
                  />
                </div>
                <div className="flex justify-between font-label-sm text-[11px] text-on-surface-variant">
                  <span>Clinical Target: &gt;70%</span>
                  <span className={projectedTir !== null && projectedTir >= 70 ? "text-primary font-medium" : "text-on-surface-variant"}>
                    {projectedTir !== null ? (projectedTir >= 70 ? "Projected ≥70% Target Met" : "Projected <70% Target") : "Pending Forecast"}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs pt-2 border-t border-surface-container">
                <span className="text-on-surface-variant font-medium">Observed Buffer In-Range:</span>
                <span className="font-telemetry-metric text-tertiary font-bold">{historicalTirDisplay}</span>
              </div>
            </div>
          </div>

          <div className="mt-space-md pt-space-sm border-t border-surface-container flex items-center justify-between text-xs">
            <span className="text-on-surface-variant">Trajectory Status</span>
            <span className="font-code-sm text-primary font-semibold">{trajectoryStatusText}</span>
          </div>
        </div>

        {/* Card 2: Step-by-Step Horizon Projection Table */}
        <div className="lg:col-span-5 bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm flex flex-col border border-surface-container">
          <div className="flex items-center justify-between mb-space-sm">
            <div className="flex items-center gap-space-xs text-on-surface font-headline-sm text-headline-sm font-semibold">
              <TableIcon className="w-5 h-5 text-primary" />
              <span>Step-by-Step Forecast</span>
            </div>
            <span className="font-code-sm text-code-sm text-on-surface-variant text-xs">Δt = 1 Hour</span>
          </div>

          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-surface-container-low text-on-surface-variant font-label-sm uppercase tracking-wider text-[11px]">
                  <th className="py-2 px-space-sm rounded-l">Horizon Step</th>
                  <th className="py-2 px-space-sm text-right">Forecast</th>
                  {(ciFilter === "all" || ciFilter === "80_only") && (
                    <th className="py-2 px-space-sm text-center">80% Range</th>
                  )}
                  {ciFilter === "all" && (
                    <th className="py-2 px-space-sm text-center">95% Range</th>
                  )}
                  <th className="py-2 px-space-sm rounded-r text-right">Change Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container font-code-sm">
                {milestones.map((m, idx) => (
                  <tr key={idx} className="hover:bg-surface-container-low/50 transition-colors">
                    <td className="py-2 px-space-sm font-semibold text-on-surface">
                      {m.step} <span className="font-normal text-on-surface-variant">({m.timeOffset})</span>
                    </td>
                    <td className="py-2 px-space-sm text-right font-bold text-on-surface">
                      {m.projected !== "—" ? `${m.projected} mg/dL` : "—"}
                    </td>
                    {(ciFilter === "all" || ciFilter === "80_only") && (
                      <td className="py-2 px-space-sm text-center text-on-surface-variant">
                        {m.interval80}
                      </td>
                    )}
                    {ciFilter === "all" && (
                      <td className="py-2 px-space-sm text-center text-on-surface-variant">
                        {m.interval95}
                      </td>
                    )}
                    <td className="py-2 px-space-sm text-right text-primary font-semibold">
                      {m.rocText}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Card 3: Uncertainty Quantification & Diagnostics */}
        <div className="lg:col-span-3 bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm flex flex-col justify-between border border-surface-container">
          <div>
            <div className="flex items-center justify-between mb-space-sm">
              <div className="flex items-center gap-space-xs text-on-surface font-headline-sm text-headline-sm font-semibold">
                <ShieldCheck className="w-5 h-5 text-primary" />
                <span>Diagnostics</span>
              </div>
              <span className="px-space-xs py-0.5 rounded bg-surface-container font-code-sm text-primary font-semibold text-xs">
                Combination C
              </span>
            </div>

            <div className="space-y-space-sm text-xs">
              <div className="p-space-xs rounded bg-surface-container-low flex justify-between items-center border border-surface-container">
                <span className="text-on-surface-variant">Point Forecaster:</span>
                <span className="font-code-sm font-semibold text-on-surface">Frozen V1 Hybrid</span>
              </div>
              <div className="p-space-xs rounded bg-surface-container-low flex justify-between items-center border border-surface-container">
                <span className="text-on-surface-variant">Uncertainty Engine:</span>
                <span className="font-code-sm font-semibold text-primary">Phase-13 Gate</span>
              </div>
              <div className="p-space-xs rounded bg-surface-container-low flex justify-between items-center border border-surface-container">
                <span className="text-on-surface-variant">Feature Channels:</span>
                <span className="font-code-sm font-semibold text-on-surface">22 Dynamic Inputs</span>
              </div>
              <div className="p-space-xs rounded bg-surface-container-low flex justify-between items-center border border-surface-container">
                <span className="text-on-surface-variant">Regime Weight w_high:</span>
                <span className="font-code-sm font-semibold text-tertiary">0.30 Calibrated</span>
              </div>
            </div>
          </div>

          <div className="mt-space-md pt-space-xs border-t border-surface-container flex items-center justify-between text-xs">
            <span className="text-on-surface-variant">Ensemble Status</span>
            <span className={`font-code-sm font-semibold ${
              alertLevel === "CRITICAL" ? "text-error" : alertLevel === "WARNING" ? "text-amber-500" : "text-tertiary"
            }`}>
              {ensembleStatus}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
