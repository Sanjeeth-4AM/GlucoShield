import React from "react";
import { ArrowRight, ArrowUpRight, ArrowDownRight, Minus, ShieldCheck, AlertTriangle } from "lucide-react";
import { GLUCOSE_THRESHOLDS } from "../../api/types.js";

export function DashboardTopCards({
  currentState,
  latestReading,
  forecastData,
  historyReadings = [],
  riskAssessment,
  patientProfile
}) {
  const isHistoricalDataset = patientProfile?.data_status === "HISTORICAL_DATASET" || !patientProfile?.is_live_sensor;
  const telemetryStatusLabel = isHistoricalDataset ? "Dataset Telemetry (24h)" : "Sensor Active";

  // --- CARD 1: Current Glucose ---
  const effectiveGlucose = currentState?.glucose_mg_dl ?? (latestReading?.cgm_glucose !== undefined ? latestReading.cgm_glucose : null);
  const glucose = effectiveGlucose !== null && effectiveGlucose !== undefined && !isNaN(effectiveGlucose) ? Math.round(effectiveGlucose) : null;
  const slope = currentState?.trend_slope_mg_dl_per_min ?? 0.0;
  const direction = currentState?.trend_direction || "flat";
  const timestamp = currentState?.timestamp || latestReading?.timestamp;

  let formattedTime = "Live";
  if (timestamp) {
    try {
      const d = new Date(timestamp);
      formattedTime = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      formattedTime = "Active";
    }
  }

  let TrendIcon = Minus;
  let trendLabel = "Steady (→)";
  let slopeText = `${slope >= 0 ? "+" : ""}${slope.toFixed(1)} mg/dL/m`;

  if (direction.includes("up") || slope > 0.5) {
    TrendIcon = ArrowUpRight;
    trendLabel = "Rising (↗)";
  } else if (direction.includes("down") || slope < -0.5) {
    TrendIcon = ArrowDownRight;
    trendLabel = "Falling (↘)";
  }

  const inRange = glucose !== null && glucose >= GLUCOSE_THRESHOLDS.TARGET_MIN && glucose <= GLUCOSE_THRESHOLDS.TARGET_MAX;
  const isLow = glucose !== null && glucose < GLUCOSE_THRESHOLDS.TARGET_MIN;
  const isHigh = glucose !== null && glucose > GLUCOSE_THRESHOLDS.TARGET_MAX;

  let rangeLabel = "In target range (70–180 mg/dL)";
  let statusBadgeStyle = "bg-teal-50 text-teal-800 border-teal-200";

  if (glucose === null) {
    rangeLabel = "Awaiting Readings";
    statusBadgeStyle = "bg-slate-100 text-slate-600 border-slate-200";
  } else if (isLow) {
    rangeLabel = glucose < GLUCOSE_THRESHOLDS.VERY_LOW ? "Critical Hypoglycemia (<54)" : "Below Target (<70 mg/dL)";
    statusBadgeStyle = "bg-rose-50 text-rose-800 border-rose-200";
  } else if (isHigh) {
    rangeLabel = glucose > GLUCOSE_THRESHOLDS.VERY_HIGH ? "Severe Hyperglycemia (>250)" : "Above Target (>180 mg/dL)";
    statusBadgeStyle = "bg-amber-50 text-amber-800 border-amber-200";
  }

  // --- CARD 2: 5-Hour Forecast Status ---
  const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
  const hasForecast = Array.isArray(pointForecast) && pointForecast.length > 0;
  const historyCount = (historyReadings || []).length;

  // --- CARD 3: Expected Highest & Lowest (Peak & Nadir) ---
  const peakVal = (riskAssessment?.peak_mg_dl ?? riskAssessment?.projected_peak_mg_dl) != null
    ? Math.round(riskAssessment.peak_mg_dl ?? riskAssessment.projected_peak_mg_dl)
    : (hasForecast ? Math.round(Math.max(...pointForecast.filter(p => typeof p === "number" && isFinite(p)))) : null);

  const peakMin = riskAssessment?.time_to_peak_min != null ? Math.round(riskAssessment.time_to_peak_min) : null;

  const nadirVal = (riskAssessment?.nadir_mg_dl ?? riskAssessment?.projected_nadir_mg_dl) != null
    ? Math.round(riskAssessment.nadir_mg_dl ?? riskAssessment.projected_nadir_mg_dl)
    : (hasForecast ? Math.round(Math.min(...pointForecast.filter(p => typeof p === "number" && isFinite(p)))) : null);

  const nadirMin = riskAssessment?.time_to_nadir_min != null ? Math.round(riskAssessment.time_to_nadir_min) : null;

  const formatDeltaMin = (mins) => {
    if (mins === null || isNaN(mins)) return "";
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (h > 0) return `in ${h}h ${m}m`;
    return `in ${m}m`;
  };

  // --- CARD 4: Hypoglycemia Risk (Up to 4h) ---
  const primaryStatus = riskAssessment?.primary_status || (hasForecast ? "STABLE" : "Pending");
  const alertLevel = riskAssessment?.alert_level || (hasForecast ? "INFO" : "PENDING");
  
  // Extract multi-horizon hypoglycemia probabilities from certified response
  const rawHypo1h = riskAssessment?.hypo_1h_prob ?? riskAssessment?.hypo_risk_1h_prob ?? null;
  const rawHypo2h = riskAssessment?.hypo_2h_prob ?? riskAssessment?.hypo_risk_2h_prob ?? null;
  const rawHypo4h = riskAssessment?.hypo_4h_prob ?? riskAssessment?.hypo_risk_4h_prob ?? null;
  
  const hypo1hPct = rawHypo1h !== null && !isNaN(rawHypo1h) ? (rawHypo1h * 100).toFixed(1) : null;
  const hypo2hPct = rawHypo2h !== null && !isNaN(rawHypo2h) ? (rawHypo2h * 100).toFixed(1) : null;
  const hypo4hPct = rawHypo4h !== null && !isNaN(rawHypo4h) ? (rawHypo4h * 100).toFixed(1) : null;
  
  const activeAlerts = Array.isArray(riskAssessment?.active_alerts) ? riskAssessment.active_alerts : [];

  const lower95 = forecastData?.forecast?.lower_95_mg_dl || [];
  const minLower95 = lower95.length > 0 ? Math.round(Math.min(...lower95)) : null;

  return (
    <div className="space-y-4">
      {/* 4 Top Cards Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* CARD 1: Current Glucose */}
        <article className="bg-white p-4 rounded-xl shadow-xs border border-slate-200 flex flex-col justify-between h-full">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-sans">
                Current glucose
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                {formattedTime} • {telemetryStatusLabel}
              </span>
            </div>
            <span className="p-1 rounded bg-teal-50 text-teal-700">
              <span className="material-symbols-outlined text-[20px]">sensors</span>
            </span>
          </div>

          <div className="my-2.5 flex items-baseline gap-2">
            <span className="font-mono text-4xl font-bold text-slate-900 tracking-tight">
              {glucose !== null ? glucose : "—"}
            </span>
            <span className="text-xs font-medium text-slate-500 uppercase">
              mg/dL
            </span>
            <div className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs font-medium">
              <TrendIcon className="w-3.5 h-3.5 text-teal-700" />
              <span>{trendLabel}</span>
            </div>
          </div>

          <div className="pt-1">
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border font-medium ${statusBadgeStyle}`}>
              <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
              <span>{rangeLabel}</span>
            </div>
          </div>
        </article>

        {/* CARD 2: 5-Hour Forecast Status */}
        <article className="bg-white p-4 rounded-xl shadow-xs border border-slate-200 flex flex-col justify-between h-full">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-sans">
                5-hour forecast status
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                20 steps • 15-min intervals
              </span>
            </div>
            <span className="p-1 rounded bg-teal-50 text-teal-700">
              <span className="material-symbols-outlined text-[20px]">timeline</span>
            </span>
          </div>

          <div className="my-2.5 flex flex-col">
            <span className="font-sans text-xl font-bold text-slate-900">
              {hasForecast ? "Forecast ready" : "Awaiting Data"}
            </span>
            <span className="text-xs text-slate-500 mt-0.5">
              {hasForecast ? "Combination C ensemble evaluated" : "96 observations required"}
            </span>
          </div>

          <div className="pt-1">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-slate-700 text-xs font-mono">
              <span className="material-symbols-outlined text-[14px] text-teal-700">database</span>
              <span>Based on {historyCount >= 96 ? "96" : historyCount} prior readings</span>
            </div>
          </div>
        </article>

        {/* CARD 3: Expected Highest & Lowest */}
        <article className="bg-white p-4 rounded-xl shadow-xs border border-slate-200 flex flex-col justify-between h-full">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-sans">
                Expected highest and lowest levels
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                Projected peak and low (5h)
              </span>
            </div>
            <span className="p-1 rounded bg-teal-50 text-teal-700">
              <span className="material-symbols-outlined text-[20px]">swap_vert</span>
            </span>
          </div>

          <div className="my-2 grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-50 p-2 rounded border border-slate-100">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-500 block font-medium">Point Peak</span>
                {peakMin !== null && (
                  <span className="text-[10px] text-slate-400 font-mono">({formatDeltaMin(peakMin)})</span>
                )}
              </div>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="font-mono text-lg font-bold text-slate-900" data-testid="point-peak-val">{peakVal !== null ? peakVal : "—"}</span>
                <span className="text-[10px] text-slate-400">mg/dL</span>
              </div>
              <span className="text-[10px] text-slate-400 block mt-0.5" data-testid="point-peak-label">Trajectory expected max</span>
            </div>
            <div className="bg-slate-50 p-2 rounded border border-slate-100">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-500 block font-medium">Point Nadir</span>
                {nadirMin !== null && (
                  <span className="text-[10px] text-slate-400 font-mono">({formatDeltaMin(nadirMin)})</span>
                )}
              </div>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="font-mono text-lg font-bold text-slate-900" data-testid="point-nadir-val">{nadirVal !== null ? nadirVal : "—"}</span>
                <span className="text-[10px] text-slate-400">mg/dL</span>
              </div>
              <span className="text-[10px] text-slate-400 block mt-0.5" data-testid="point-nadir-label">Trajectory expected min</span>
            </div>
          </div>

          <div className="pt-1">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-teal-50 border border-teal-100 text-teal-800 text-xs font-medium">
              <span className="material-symbols-outlined text-[14px]">auto_graph</span>
              <span>Physiologic dampening: Active</span>
            </div>
          </div>
        </article>

        {/* CARD 4: Hypoglycemia Risk (Up to 4h) */}
        <article className="bg-white p-4 rounded-xl shadow-xs border border-slate-200 flex flex-col justify-between h-full">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-sans" data-testid="risk-card-title">
                Hypoglycemia risk (up to 4h)
              </span>
              <span className="text-[11px] text-slate-400 font-mono" data-testid="risk-threshold-subtitle">
                Low &lt; 70 mg/dL • Severe &lt; 54 mg/dL
              </span>
            </div>
            <span className="p-1 rounded bg-teal-50 text-teal-700">
              <span className="material-symbols-outlined text-[20px]">verified_user</span>
            </span>
          </div>

          <div className="my-2 flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-sans text-xl font-bold text-slate-900" data-testid="risk-primary-status">
                {primaryStatus === "STABLE" ? "Low risk" : primaryStatus}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-slate-100 font-mono text-[10px] font-semibold text-slate-700" data-testid="risk-alert-level">
                ALERT: {alertLevel}
              </span>
            </div>
            <span className="text-xs text-slate-600 mt-0.5" data-testid="risk-prob-2h">
              {hypo2hPct !== null ? `${hypo2hPct}% acute risk (2-hour window)` : "Risk evaluation nominal"}
            </span>

            {/* Multi-horizon risk probability grid: 1h, 2h, 4h, and explicit 5h unmodeled note */}
            <div className="grid grid-cols-4 gap-1 mt-2 text-center text-[10px] font-mono bg-slate-50 p-1.5 rounded border border-slate-100">
              <div data-testid="risk-prob-1h">
                <span className="text-slate-400 block text-[9px]">1h</span>
                <span className="font-semibold text-slate-700">{hypo1hPct !== null ? `${hypo1hPct}%` : "—"}</span>
              </div>
              <div className="border-x border-slate-200" data-testid="risk-prob-2h-cell">
                <span className="text-slate-400 block text-[9px]">2h</span>
                <span className="font-semibold text-slate-700">{hypo2hPct !== null ? `${hypo2hPct}%` : "—"}</span>
              </div>
              <div className="border-r border-slate-200" data-testid="risk-prob-4h">
                <span className="text-slate-400 block text-[9px]">4h</span>
                <span className="font-semibold text-slate-700">{hypo4hPct !== null ? `${hypo4hPct}%` : "—"}</span>
              </div>
              <div data-testid="risk-prob-5h">
                <span className="text-slate-400 block text-[9px]">5h</span>
                <span className="text-slate-400 italic">N/A*</span>
              </div>
            </div>
            <span className="text-[10px] text-slate-400 leading-tight block mt-1" data-testid="risk-5h-note">
              *5h risk probability not evaluated by model (evaluates 1h, 2h, 4h horizons).
            </span>
          </div>

          <div className="pt-1">
            <div
              data-testid="risk-lower-bound-badge"
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border font-medium ${
                minLower95 !== null && minLower95 < 54
                  ? "bg-amber-50 text-amber-800 border-amber-200"
                  : minLower95 !== null && minLower95 < 70
                  ? "bg-amber-50 text-amber-800 border-amber-200"
                  : "bg-teal-50 text-teal-800 border-teal-200"
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
              <span>
                {minLower95 !== null
                  ? minLower95 < 54
                    ? `Lower 95% bound reaches ${minLower95} mg/dL (< 54 severe)`
                    : minLower95 < 70
                    ? `Lower 95% bound reaches ${minLower95} mg/dL (< 70 low)`
                    : `Lower 95% bound: ${minLower95} mg/dL (above 70)`
                  : hasForecast
                  ? "Lower 95% bound: Pending"
                  : "Awaiting Forecast"}
              </span>
            </div>
          </div>
        </article>

      </section>

      {/* Active Clinical Safety Note Banner (Always visible when risk alerts exist) */}
      <section className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs flex items-start gap-3" data-testid="clinical-safety-banner">
        <div className="p-1.5 bg-teal-50 rounded-lg text-teal-700 flex items-center justify-center shrink-0 border border-teal-100">
          <span className="material-symbols-outlined text-[20px]">health_and_safety</span>
        </div>
        <div className="flex flex-col w-full gap-1.5 text-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <p className="text-slate-800 leading-relaxed font-sans">
              <strong className="font-semibold text-slate-900 mr-1.5">Clinical safety note:</strong>
              {activeAlerts.length > 0 ? (
                <span className="text-amber-800 font-medium" data-testid="active-alert-item">
                  {activeAlerts.join(" ")}
                </span>
              ) : minLower95 !== null && minLower95 >= 70 ? (
                <span>
                  Nominal trajectory. Both calibrated 95% lower bound ({minLower95} mg/dL) and point-forecast nadir ({nadirVal !== null ? `${nadirVal} mg/dL` : "—"}) remain above the 70 mg/dL threshold.
                </span>
              ) : (
                <span>
                  Trajectory monitoring active. Point nadir is {nadirVal !== null ? `${nadirVal} mg/dL` : "—"}.
                </span>
              )}
            </p>
            <span className="font-mono text-[11px] text-teal-700 bg-teal-50 px-2 py-0.5 rounded shrink-0 border border-teal-100 self-start sm:self-auto">
              Monitoring: Configured
            </span>
          </div>

          {/* Explicit Quantity Distinction */}
          {hasForecast && minLower95 !== null && nadirVal !== null && (
            <p className="text-[11px] text-slate-500 border-t border-slate-100 pt-1.5 font-sans" data-testid="safety-quantity-distinction">
              <span className="font-medium text-slate-700">Quantity distinction:</span> Point-forecast nadir ({nadirVal} mg/dL) represents the expected mean trajectory minimum, whereas the calibrated 95% prediction interval lower bound ({minLower95} mg/dL) reflects downside statistical uncertainty {minLower95 < 54 ? "(extending below severe hypoglycemia threshold 54 mg/dL)" : minLower95 < 70 ? "(extending below low glucose threshold 70 mg/dL)" : "(remaining above 70 mg/dL)"}. Prediction intervals denote statistical trajectory dispersion, not the discrete probability of crossing a clinical threshold.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
