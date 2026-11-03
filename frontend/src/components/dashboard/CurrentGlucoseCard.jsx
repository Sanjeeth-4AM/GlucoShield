import React from "react";
import { ArrowRight, ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { GLUCOSE_THRESHOLDS } from "../../api/types.js";

export function CurrentGlucoseCard({ currentState, latestReading, hybridComponents, riskAssessment }) {
  const effectiveGlucose = currentState?.glucose_mg_dl ?? (latestReading?.cgm_glucose !== undefined ? latestReading.cgm_glucose : null);
  const glucose = effectiveGlucose !== null && effectiveGlucose !== undefined && !isNaN(effectiveGlucose) ? Math.round(effectiveGlucose) : null;
  const slope = currentState?.trend_slope_mg_dl_per_min ?? 0.0;
  const direction = currentState?.trend_direction || "flat";
  const timestamp = currentState?.timestamp || latestReading?.timestamp;

  // Format time
  let formattedTime = "Live Telemetry";
  if (timestamp) {
    try {
      const d = new Date(timestamp);
      formattedTime = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      formattedTime = "Telemetry Active";
    }
  }

  // Determine trend icon and text
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

  // Bounds and range status
  const inRange = glucose !== null && glucose >= GLUCOSE_THRESHOLDS.TARGET_MIN && glucose <= GLUCOSE_THRESHOLDS.TARGET_MAX;
  const isLow = glucose !== null && glucose < GLUCOSE_THRESHOLDS.TARGET_MIN;
  const isHigh = glucose !== null && glucose > GLUCOSE_THRESHOLDS.TARGET_MAX;

  let rangeLabel = "Target In-Range (70–180 mg/dL)";
  let boundsStatus = "Within Clinical Bounds";
  let statusDotColor = "bg-tertiary";

  if (glucose === null) {
    rangeLabel = "Sensor Connecting...";
    boundsStatus = "Awaiting Readings";
    statusDotColor = "bg-outline-variant";
  } else if (isLow) {
    rangeLabel = "Below Target (<70 mg/dL)";
    boundsStatus = glucose < GLUCOSE_THRESHOLDS.VERY_LOW ? "Critical Hypoglycemia" : "Low Glucose Alert";
    statusDotColor = "bg-error";
  } else if (isHigh) {
    rangeLabel = "Above Target (>180 mg/dL)";
    boundsStatus = glucose > GLUCOSE_THRESHOLDS.VERY_HIGH ? "Severe Hyperglycemia" : "Elevated Postprandial";
    statusDotColor = "bg-secondary";
  }

  return (
    <div className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm flex flex-col justify-between relative overflow-hidden border border-surface-container h-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-space-xs">
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
            SECTION A
          </span>
          <span className="text-outline-variant">•</span>
          <h2 className="font-label-md text-label-md font-semibold text-on-surface">
            CURRENT GLUCOSE
          </h2>
        </div>
        <span className="font-code-sm text-code-sm text-outline font-medium">
          {formattedTime}
        </span>
      </div>

      <div className="my-space-md flex items-baseline gap-space-sm">
        <span className="font-telemetry-display text-telemetry-display text-on-surface tracking-tighter text-5xl font-bold">
          {glucose !== null ? glucose : "—"}
        </span>
        <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant uppercase font-semibold">
          mg/dL
        </span>
        <div className="ml-auto inline-flex items-center gap-1 px-space-sm py-1 bg-surface-container-high rounded text-primary font-label-sm text-label-sm font-semibold">
          <TrendIcon className="w-4 h-4 text-primary" />
          <span>{trendLabel}</span>
          <span className="font-code-sm text-code-sm font-normal text-on-surface-variant pl-0.5">
            ({slopeText})
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-space-xs bg-surface-container-low px-space-sm py-space-xs rounded border border-surface-container">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${statusDotColor}`}></span>
          <span className="font-label-sm text-label-sm text-on-surface font-medium">
            {rangeLabel}
          </span>
        </div>
        <span className="font-code-sm text-code-sm text-on-surface-variant">
          {boundsStatus}
        </span>
      </div>
    </div>
  );
}
