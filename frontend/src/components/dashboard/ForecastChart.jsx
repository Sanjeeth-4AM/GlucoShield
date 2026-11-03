import React, { useMemo, useCallback } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea
} from "recharts";
import { Loader2, TrendingUp, AlertCircle, CheckCircle2 } from "lucide-react";
import { GLUCOSE_THRESHOLDS } from "../../api/types.js";

// Memoized Custom Clinical Tooltip (stable reference outside component)
function CustomTooltipContent({ active, payload, horizonFilter }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  return (
    <div className="bg-surface-container-lowest border border-surface-container p-3 rounded-lg shadow-lg font-code-sm text-xs min-w-[190px] select-none">
      <div className="flex items-center justify-between border-b border-surface-container pb-1.5 mb-2">
        <span className="font-semibold text-on-surface">{d.timeLabel}</span>
        <span className="text-[10px] text-outline font-sans">
          {d.isHistory ? "Observed CGM" : "Combination C"}
        </span>
      </div>

      {d.historicalGlucose !== null && (
        <div className="flex justify-between items-center text-on-surface py-0.5">
          <span className="text-on-surface-variant">Observed:</span>
          <span className="font-bold">{Math.round(d.historicalGlucose)} mg/dL</span>
        </div>
      )}

      {d.forecastGlucose !== null && (
        <div className="flex justify-between items-center text-primary py-0.5">
          <span className="text-primary font-medium">Forecast Mean:</span>
          <span className="font-bold">{Math.round(d.forecastGlucose)} mg/dL</span>
        </div>
      )}

      {d.band80Lower !== null && horizonFilter !== "mean_only" && (
        <div className="flex justify-between items-center text-on-surface-variant text-[11px] py-0.5">
          <span>80% Interval:</span>
          <span>{Math.round(d.band80Lower)} – {Math.round(d.band80Upper)}</span>
        </div>
      )}

      {d.band95Lower !== null && horizonFilter === "all" && (
        <div className="flex justify-between items-center text-on-surface-variant text-[11px] py-0.5">
          <span>95% Interval:</span>
          <span>{Math.round(d.band95Lower)} – {Math.round(d.band95Upper)}</span>
        </div>
      )}

      {d.whatIfGlucose !== null && (
        <div className="flex justify-between items-center text-secondary py-0.5 border-t border-surface-container mt-1 pt-1">
          <span className="font-medium">What-If:</span>
          <span className="font-bold">{Math.round(d.whatIfGlucose)} mg/dL</span>
        </div>
      )}
    </div>
  );
}
const CustomTooltip = React.memo(CustomTooltipContent);

export function ForecastChart({
  historyReadings = [],
  forecastData,
  whatIfTrajectory,
  isLoading = false,
  showTitle = true,
  horizonFilter = "all", // "all", "80_only", "mean_only"
  isDemoMode = false,
  errorMessage = null,
  onRetry = null
}) {
  const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
  const lower80 = forecastData?.forecast?.lower_80_mg_dl || [];
  const upper80 = forecastData?.forecast?.upper_80_mg_dl || [];
  const lower95 = forecastData?.forecast?.lower_95_mg_dl || [];
  const upper95 = forecastData?.forecast?.upper_95_mg_dl || [];

  // Memoized Chart Dataset: Strictly stable reference preventing ChartDataContextProvider infinite update loops
  const chartData = useMemo(() => {
    const recentHistory = (historyReadings || []).slice(-16);
    const data = [];

    // Current anchor point (NOW) strictly from genuine API response current_state or latest historical reading
    const originGlucose = forecastData?.current_state?.glucose_mg_dl ?? (recentHistory.length > 0 ? recentHistory[recentHistory.length - 1]?.cgm_glucose : null);

    // 1. Historical Points
    recentHistory.forEach((r, idx) => {
      const minsAgo = (recentHistory.length - 1 - idx) * 15;
      const hrs = Math.floor(minsAgo / 60);
      const remMins = minsAgo % 60;
      const label = minsAgo === 0 ? "NOW" : `-${hrs > 0 ? `${hrs}h` : ""}${remMins > 0 ? `${remMins}m` : ""}`;

      const isNow = minsAgo === 0;
      const nowGlucose = isNow ? (originGlucose ?? r.cgm_glucose) : null;

      data.push({
        timeLabel: label,
        minuteOffset: -minsAgo,
        isHistory: true,
        historicalGlucose: r.cgm_glucose,
        forecastGlucose: nowGlucose,
        band80Range: isNow && nowGlucose !== null ? [nowGlucose, nowGlucose] : null,
        band95Range: isNow && nowGlucose !== null ? [nowGlucose, nowGlucose] : null,
        band80Lower: nowGlucose,
        band80Upper: nowGlucose,
        band95Lower: nowGlucose,
        band95Upper: nowGlucose,
        band80Width: isNow ? 0 : null,
        band95Width: isNow ? 0 : null,
        whatIfGlucose: nowGlucose
      });
    });

    // Anchor NOW origin if recentHistory is empty but originGlucose is known
    if (recentHistory.length === 0 && typeof originGlucose === "number" && !isNaN(originGlucose) && isFinite(originGlucose)) {
      data.push({
        timeLabel: "NOW",
        minuteOffset: 0,
        isHistory: true,
        historicalGlucose: originGlucose,
        forecastGlucose: originGlucose,
        band80Range: [originGlucose, originGlucose],
        band95Range: [originGlucose, originGlucose],
        band80Lower: originGlucose,
        band80Upper: originGlucose,
        band95Lower: originGlucose,
        band95Upper: originGlucose,
        band80Width: 0,
        band95Width: 0,
        whatIfGlucose: originGlucose
      });
    }

    if (pointForecast.length > 0) {
      pointForecast.forEach((val, i) => {
        const mins = (i + 1) * 15;
        const hrs = Math.floor(mins / 60);
        const remMins = mins % 60;
        const label = `+${hrs > 0 ? `${hrs}h` : ""}${remMins > 0 ? `${remMins}m` : ""}`;

        const cleanForecast = (typeof val === "number" && !isNaN(val) && isFinite(val)) ? val : null;

        // Strictly map genuine bounds without synthetic offset fallbacks
        const l80 = (typeof lower80[i] === "number" && !isNaN(lower80[i]) && isFinite(lower80[i])) ? lower80[i] : null;
        const u80 = (typeof upper80[i] === "number" && !isNaN(upper80[i]) && isFinite(upper80[i])) ? upper80[i] : null;
        const l95 = (typeof lower95[i] === "number" && !isNaN(lower95[i]) && isFinite(lower95[i])) ? lower95[i] : null;
        const u95 = (typeof upper95[i] === "number" && !isNaN(upper95[i]) && isFinite(upper95[i])) ? upper95[i] : null;

        const valid80 = l80 !== null && u80 !== null && u80 >= l80;
        const valid95 = l95 !== null && u95 !== null && u95 >= l95;

        const whatIfVal = (whatIfTrajectory && typeof whatIfTrajectory[i] === "number" && !isNaN(whatIfTrajectory[i]) && isFinite(whatIfTrajectory[i]))
          ? whatIfTrajectory[i]
          : null;

        data.push({
          timeLabel: label,
          minuteOffset: mins,
          isHistory: false,
          historicalGlucose: null,
          forecastGlucose: cleanForecast,
          band80Range: valid80 ? [l80, u80] : null,
          band95Range: valid95 ? [l95, u95] : null,
          band80Lower: l80,
          band80Upper: u80,
          band80Width: valid80 ? Math.max(0, u80 - l80) : null,
          band95Lower: l95,
          band95Upper: u95,
          band95Width: valid95 ? Math.max(0, u95 - l95) : null,
          whatIfGlucose: whatIfVal
        });
      });
    }

    return data;
  }, [historyReadings, forecastData, whatIfTrajectory]);

  // Derive projected peak and timing from risk assessment or point forecast
  const { peakGlucose, peakMinute } = useMemo(() => {
    let peakG = null;
    let peakM = null;

    if (forecastData?.risk_assessment?.peak_mg_dl != null && forecastData?.risk_assessment?.time_to_peak_min != null) {
      peakG = Number(forecastData.risk_assessment.peak_mg_dl);
      peakM = Number(forecastData.risk_assessment.time_to_peak_min);
    } else if (Array.isArray(forecastData?.forecast?.point_forecast_mg_dl) && forecastData.forecast.point_forecast_mg_dl.length > 0) {
      let maxVal = -Infinity;
      let maxMins = 0;
      forecastData.forecast.point_forecast_mg_dl.forEach((val, i) => {
        if (typeof val === "number" && val > maxVal) {
          maxVal = val;
          maxMins = (i + 1) * 15;
        }
      });
      if (maxVal !== -Infinity) {
        peakG = maxVal;
        peakM = maxMins;
      }
    }
    return { peakGlucose: peakG, peakMinute: peakM };
  }, [forecastData]);

  // Memoized Observed & Projected Time-in-Range (TIR) metrics
  const { historicalTirPct, projectedTirPct } = useMemo(() => {
    const validHistory = (historyReadings || []).filter(
      (r) => r && typeof r.cgm_glucose === "number" && !isNaN(r.cgm_glucose)
    );
    const hTir = validHistory.length > 0
      ? Math.round(
          (validHistory.filter((r) => r.cgm_glucose >= 70 && r.cgm_glucose <= 180).length /
            validHistory.length) * 100
        )
      : null;

    const validPoints = (pointForecast || []).filter(
      (g) => typeof g === "number" && !isNaN(g)
    );
    const pTir = validPoints.length > 0
      ? Math.round(
          (validPoints.filter((g) => g >= 70 && g <= 180).length /
            validPoints.length) * 100
        )
      : null;

    return { historicalTirPct: hTir, projectedTirPct: pTir };
  }, [historyReadings, pointForecast]);

  // Tooltip renderer with stable callback
  const renderTooltip = useCallback(
    (props) => <CustomTooltip {...props} horizonFilter={horizonFilter} />,
    [horizonFilter]
  );

  // Stable forecast dot renderer
  const renderForecastDot = useCallback((props) => {
    if (props?.payload?.timeLabel === "NOW") {
      return (
        <circle
          key="current-now-dot"
          cx={props.cx}
          cy={props.cy}
          r={5}
          fill="#00685f"
          stroke="#ffffff"
          strokeWidth={2}
        />
      );
    }
    return false;
  }, []);

  return (
    <section className="bg-surface-container-lowest p-4 sm:p-5 lg:p-6 rounded-xl shadow-sm flex flex-col gap-space-md border border-surface-container relative">
      {/* Header & Badges */}
      {showTitle && (
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-xs">
          <div>
            <div className="flex items-center gap-space-xs">
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
                SECTION B
              </span>
              <span className="text-outline-variant">•</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">
                5-HOUR GLUCOSE FORECAST
              </h2>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              Production Combination C Serving • 20-step / 15-minute horizon ensemble
            </p>
          </div>

          {/* Chart Legend Badges */}
          <div className="flex flex-wrap items-center gap-space-xs">
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container text-on-surface font-label-sm text-label-sm">
              <span className="w-2.5 h-0.5 bg-on-surface rounded-full"></span>
              Observed CGM
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container text-on-surface font-label-sm text-label-sm">
              <span className="w-2 h-2 rounded-full bg-primary ring-2 ring-primary-fixed"></span>
              Current (NOW)
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container text-primary font-label-sm text-label-sm font-semibold">
              <span className="w-3 h-0.5 border-t border-dashed border-primary"></span>
              Forecast Mean
            </span>
            {horizonFilter !== "mean_only" && (
              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container text-on-surface-variant font-label-sm text-label-sm">
                <span className="w-2.5 h-2.5 bg-primary/25 rounded-sm"></span>
                80% Uncertainty
              </span>
            )}
            {horizonFilter === "all" && (
              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container text-on-surface-variant font-label-sm text-label-sm">
                <span className="w-2.5 h-2.5 bg-primary/10 rounded-sm"></span>
                95% Uncertainty
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container-high text-tertiary font-label-sm text-label-sm font-medium">
              <span className="w-2.5 h-2 bg-tertiary-fixed rounded-sm"></span>
              Target 70–180
            </span>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-surface/70 backdrop-blur-xs flex items-center justify-center z-20 rounded-xl">
          <div className="flex items-center gap-2 bg-surface-container-lowest px-4 py-2 rounded-lg shadow-md border border-surface-container">
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <span className="font-code-sm text-xs text-on-surface font-semibold">
              Evaluating Combination C Ensemble...
            </span>
          </div>
        </div>
      )}

      {/* Chart Canvas */}
      <div className="w-full overflow-x-auto">
        <div className="w-full min-w-[650px] h-80 sm:h-96 lg:h-[400px] relative">
        {/* CASE 1 & Error Informative Overlay when forecast is not available */}
        {!forecastData && !isLoading && !isDemoMode && (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 bg-surface-container-lowest/85 backdrop-blur-xs rounded-lg select-none">
            {errorMessage ? (
              <>
                <div className="p-2.5 rounded-full bg-error-container/40 mb-2 text-error">
                  <AlertCircle className="w-6 h-6 text-error" />
                </div>
                <h3 className="font-headline-sm text-sm font-semibold text-on-surface mb-1">
                  Forecast Request Unavailable
                </h3>
                <p className="font-body-sm text-xs text-on-surface-variant max-w-md mb-3 leading-relaxed">
                  {errorMessage}
                </p>
                {onRetry && (
                  <button
                    type="button"
                    onClick={onRetry}
                    className="px-3 py-1.5 bg-primary text-on-primary rounded text-xs font-semibold hover:bg-primary-container transition-colors shadow-sm"
                  >
                    Retry Forecast
                  </button>
                )}
              </>
            ) : (
              <>
                <div className="p-2.5 rounded-full bg-surface-container mb-2 text-primary">
                  <TrendingUp className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-headline-sm text-sm font-semibold text-on-surface mb-1">
                  Awaiting 24-Hour Telemetry for Multi-Horizon Forecast
                </h3>
                <p className="font-body-sm text-xs text-on-surface-variant max-w-md mb-3 leading-relaxed">
                  {historyReadings.length === 0
                    ? "No continuous glucose monitoring readings have been logged yet for this patient profile. In Live API mode, GlucoShield V1 Combination C requires 96 continuous 15-minute observations (24 hours of telemetry) before generating 5-hour predictive trajectories."
                    : `Currently ${historyReadings.length} of 96 continuous 15-minute observations are available. Combination C requires a full 24-hour baseline (96 steps) before computing multi-horizon forecasts.`}
                </p>
                <div className="flex items-center gap-2">
                  <span className="font-code-sm text-xs px-2.5 py-1 rounded-full bg-surface-container text-on-surface-variant border border-surface-container">
                    Buffer: {historyReadings.length} / 96 steps
                  </span>
                  <span className="font-code-sm text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
                    Live API Mode Active
                  </span>
                </div>
              </>
            )}
          </div>
        )}

        <ResponsiveContainer width="100%" height="100%" minWidth={700} minHeight={288} debounce={50}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="band95Gradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00685f" stopOpacity={0.16} />
                <stop offset="100%" stopColor="#00685f" stopOpacity={0.04} />
              </linearGradient>
              <linearGradient id="band80Gradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00685f" stopOpacity={0.30} />
                <stop offset="100%" stopColor="#00685f" stopOpacity={0.10} />
              </linearGradient>
            </defs>

            {/* Target Glycemic Band: 70 – 180 mg/dL */}
            <ReferenceArea
              y1={GLUCOSE_THRESHOLDS.TARGET_MIN}
              y2={GLUCOSE_THRESHOLDS.TARGET_MAX}
              fill="#f0fdf4"
              fillOpacity={0.7}
            />

            {/* Critical Threshold Lines */}
            <ReferenceLine
              y={GLUCOSE_THRESHOLDS.TARGET_MAX}
              stroke="#006948"
              strokeDasharray="4 2"
              strokeWidth={1.2}
              label={{ value: "180 Upper Target", position: "right", fill: "#006948", fontSize: 10, fontFamily: "JetBrains Mono" }}
            />
            <ReferenceLine
              y={GLUCOSE_THRESHOLDS.TARGET_MIN}
              stroke="#ba1a1a"
              strokeDasharray="4 2"
              strokeWidth={1.2}
              label={{ value: "70 Hypo Threshold", position: "right", fill: "#ba1a1a", fontSize: 10, fontFamily: "JetBrains Mono" }}
            />
            <ReferenceLine
              y={GLUCOSE_THRESHOLDS.VERY_LOW}
              stroke="#ba1a1a"
              strokeDasharray="2 2"
              strokeWidth={0.75}
              strokeOpacity={0.6}
            />

            {/* Vertical NOW Divider */}
            <ReferenceLine
              x="NOW"
              stroke="#00685f"
              strokeDasharray="2 2"
              strokeWidth={1.75}
              label={{ value: "NOW", position: "top", fill: "#00685f", fontSize: 10, fontWeight: "bold", fontFamily: "JetBrains Mono" }}
            />

            <XAxis
              dataKey="timeLabel"
              stroke="#6d7a77"
              tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
              tickLine={false}
              axisLine={{ stroke: "#eaedff" }}
            />
            <YAxis
              domain={[40, 260]}
              ticks={[40, 70, 120, 180, 240]}
              stroke="#6d7a77"
              tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
              tickLine={false}
              axisLine={{ stroke: "#eaedff" }}
              unit=" mg/dL"
            />

            <Tooltip content={renderTooltip} />

            {/* 95% Confidence Interval Area (Native [min, max] range) */}
            {horizonFilter === "all" && (
              <Area
                type="monotone"
                dataKey="band95Range"
                stroke="none"
                fill="url(#band95Gradient)"
                connectNulls={false}
                isAnimationActive={false}
              />
            )}

            {/* 80% Confidence Interval Area (Native [min, max] range) */}
            {horizonFilter !== "mean_only" && (
              <Area
                type="monotone"
                dataKey="band80Range"
                stroke="none"
                fill="url(#band80Gradient)"
                connectNulls={false}
                isAnimationActive={false}
              />
            )}

            {/* Historical CGM line (Dark solid) */}
            <Line
              type="monotone"
              dataKey="historicalGlucose"
              stroke="#131b2e"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#131b2e" }}
              activeDot={{ r: 5, fill: "#00685f" }}
              connectNulls={false}
              isAnimationActive={false}
            />

            {/* Forecast Mean Trajectory line (Primary teal dashed) */}
            <Line
              type="monotone"
              dataKey="forecastGlucose"
              stroke="#00685f"
              strokeWidth={2.5}
              strokeDasharray="4 3"
              dot={renderForecastDot}
              activeDot={{ r: 5, fill: "#00685f" }}
              connectNulls={false}
              isAnimationActive={false}
            />

            {/* What-If Alternative Trajectory (if active) */}
            {whatIfTrajectory && (
              <Line
                type="monotone"
                dataKey="whatIfGlucose"
                stroke="#006398"
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={{ r: 2.5, fill: "#006398" }}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
        </div>
      </div>

      {/* Chart Footer Strip: Explicitly distinguishing Historical In-Range from 5-Hour Projected In-Range */}
      <div className="pt-space-xs border-t border-surface-container flex flex-wrap items-center justify-between text-on-surface-variant font-code-sm text-code-sm gap-y-2">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
          <div>
            <span className="text-on-surface font-semibold">Observed Buffer In-Range:</span>{" "}
            <span className="text-tertiary font-bold">
              {historicalTirPct !== null ? `${historicalTirPct}%` : "—"}
            </span>
            {historicalTirPct === null && (
              <span className="text-[11px] text-outline font-normal ml-1">
                (No eligible historical readings)
              </span>
            )}
          </div>
          <div>
            <span className="text-on-surface font-semibold">5-Hour Projected In-Range:</span>{" "}
            <span className="text-primary font-bold">
              {projectedTirPct !== null ? `${projectedTirPct}%` : "—"}
            </span>
          </div>
          <div>
            <span className="text-on-surface font-semibold">Projected Peak:</span>{" "}
            <span className="text-secondary font-bold">
              {peakGlucose !== null && peakMinute !== null
                ? `~${Math.round(peakGlucose)} mg/dL (${peakMinute < 60 ? `+${peakMinute}m` : `+${Math.floor(peakMinute / 60)}h${peakMinute % 60 > 0 ? ` ${peakMinute % 60}m` : ""}`})`
                : "—"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-on-surface-variant">
          <span className="w-2 h-2 rounded-full bg-primary"></span>
          <span>Model Serving: Combination C</span>
        </div>
      </div>
    </section>
  );
}
