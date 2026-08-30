import React, { useState } from "react";
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
import { GLUCOSE_THRESHOLDS } from "../../api/types.js";

export function ForecastChart({ historyReadings, forecastData, whatIfTrajectory }) {
  const [horizonView, setHorizonView] = useState("5H"); // "1H" or "5H"
  const [showSubComponents, setShowSubComponents] = useState(true);

  // Prepare chart dataset
  const recentHistory = (historyReadings || []).slice(-16);
  const chartData = [];

  recentHistory.forEach((r, idx) => {
    const minsAgo = (16 - idx) * 15;
    chartData.push({
      timeLabel: `-${Math.floor(minsAgo / 60)}h${minsAgo % 60 ? `${minsAgo % 60}m` : ""}`,
      minuteOffset: -minsAgo,
      isHistory: true,
      historicalGlucose: r.cgm_glucose,
      forecastGlucose: null,
      band80: null,
      band95: null,
      odeGlucose: null,
      neuralGlucose: null,
      whatIfGlucose: null
    });
  });

  // Current anchor point (t=0, NOW)
  const currentG = recentHistory.length > 0 ? recentHistory[recentHistory.length - 1].cgm_glucose : 120.0;
  chartData.push({
    timeLabel: "NOW",
    minuteOffset: 0,
    isHistory: true,
    historicalGlucose: currentG,
    forecastGlucose: currentG,
    band80: [currentG, currentG],
    band95: [currentG, currentG],
    odeGlucose: currentG,
    neuralGlucose: currentG,
    whatIfGlucose: currentG
  });

  // Add 20-step forecast points (0 to +300 minutes)
  if (forecastData?.forecast?.point_forecast_mg_dl) {
    const horizons = forecastData.forecast.horizon_minutes || [];
    const points = forecastData.forecast.point_forecast_mg_dl || [];
    const l80 = forecastData.forecast.lower_80_mg_dl || [];
    const u80 = forecastData.forecast.upper_80_mg_dl || [];
    const l95 = forecastData.forecast.lower_95_mg_dl || [];
    const u95 = forecastData.forecast.upper_95_mg_dl || [];
    const odePts = forecastData.hybrid_components?.ode_simulation_mg_dl || [];
    const neuralPts = forecastData.hybrid_components?.neural_prediction_mg_dl || [];

    const limit = horizonView === "1H" ? 4 : points.length;

    for (let i = 0; i < limit; i++) {
      const mins = horizons[i] || (i + 1) * 15;
      const hrs = Math.floor(mins / 60);
      const remMins = mins % 60;
      const label = `+${hrs > 0 ? `${hrs}h` : ""}${remMins > 0 ? `${remMins}m` : ""}`;

      chartData.push({
        timeLabel: label,
        minuteOffset: mins,
        isHistory: false,
        historicalGlucose: null,
        forecastGlucose: points[i],
        lower80: l80[i],
        upper80: u80[i],
        lower95: l95[i],
        upper95: u95[i],
        band80: [l80[i], u80[i]],
        band95: [l95[i], u95[i]],
        odeGlucose: odePts[i] || null,
        neuralGlucose: neuralPts[i] || null,
        whatIfGlucose: (whatIfTrajectory && whatIfTrajectory[i]) || null
      });
    }
  }

  // Custom Stitch-Style Tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const pt = payload[0]?.payload;
    if (!pt) return null;

    return (
      <div className="bg-[#070d1f]/95 border border-white/20 rounded-lg p-3 shadow-2xl text-xs font-mono backdrop-blur-xl">
        <div className="flex items-center justify-between gap-4 text-[#bac9cc] border-b border-white/10 pb-1 mb-2">
          <span>TIME: {pt.timeLabel}</span>
          <span className="text-[10px] text-[#00daf3] uppercase font-bold">
            {pt.isHistory ? "HISTORICAL CGM" : "HYBRID PREDICTION"}
          </span>
        </div>

        {pt.historicalGlucose !== null && (
          <div className="flex justify-between gap-4 text-[#dce1fb]">
            <span>CGM Value:</span>
            <span className="font-bold">{pt.historicalGlucose} mg/dL</span>
          </div>
        )}

        {pt.forecastGlucose !== null && (
          <div className="space-y-1">
            <div className="flex justify-between gap-4 text-white font-bold">
              <span>Hybrid Forecast:</span>
              <span className="text-[#00daf3] text-sm">{pt.forecastGlucose} mg/dL</span>
            </div>
            {pt.lower95 !== undefined && (
              <div className="flex justify-between gap-4 text-[#bac9cc] text-[10px]">
                <span>95% Uncertainty:</span>
                <span>[{pt.lower95} – {pt.upper95}]</span>
              </div>
            )}
            {pt.odeGlucose !== null && (
              <div className="flex justify-between gap-4 text-[#00daf3] text-[10px]">
                <span>M-ODE Simulation:</span>
                <span>{pt.odeGlucose} mg/dL</span>
              </div>
            )}
            {pt.neuralGlucose !== null && (
              <div className="flex justify-between gap-4 text-[#d0bcff] text-[10px]">
                <span>N-ODE Prediction:</span>
                <span>{pt.neuralGlucose} mg/dL</span>
              </div>
            )}
            {pt.whatIfGlucose !== null && (
              <div className="flex justify-between gap-4 text-[#ec4899] font-bold border-t border-white/10 pt-1 mt-1">
                <span>What-If Simulated:</span>
                <span>{pt.whatIfGlucose} mg/dL</span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="glass-panel instrument-border rounded-xl flex flex-col relative overflow-hidden h-full">
      {/* Header Bar matching Stitch */}
      <div className="p-3.5 border-b border-white/10 flex flex-wrap justify-between items-center bg-[#070d1f]/60 gap-3">
        <div className="flex items-center gap-4">
          <span className="font-mono text-xs font-bold text-white tracking-widest uppercase">
            PREDICTIVE_HORIZON_{horizonView}
          </span>
          <div className="hidden sm:flex items-center gap-3 font-mono text-[10px] text-[#bac9cc]">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-[#d0bcff]"></span>
              <span>N-ODE</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-[#00daf3]"></span>
              <span>M-ODE</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-white shadow-[0_0_4px_#fff]"></span>
              <span className="text-white font-bold">HYBRID</span>
            </div>
            {whatIfTrajectory && (
              <div className="flex items-center gap-1.5 text-[#ec4899] font-bold">
                <span className="w-2.5 h-0.5 bg-[#ec4899]"></span>
                <span>WHAT-IF</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSubComponents(!showSubComponents)}
            className={`font-mono text-[10px] uppercase border px-2 py-1 rounded transition-colors ${
              showSubComponents
                ? "border-[#00daf3]/40 bg-[#00daf3]/10 text-[#00daf3]"
                : "border-white/10 text-[#bac9cc] hover:border-white/30"
            }`}
          >
            {showSubComponents ? "Sub-Models: ON" : "Sub-Models: OFF"}
          </button>
          <button
            onClick={() => setHorizonView("1H")}
            className={`font-mono text-[10px] uppercase border px-2.5 py-1 rounded transition-colors ${
              horizonView === "1H"
                ? "border-[#00daf3] bg-[#00daf3]/20 text-[#00daf3] font-bold"
                : "border-white/10 text-[#bac9cc] hover:border-white/30"
            }`}
          >
            1H
          </button>
          <button
            onClick={() => setHorizonView("5H")}
            className={`font-mono text-[10px] uppercase border px-2.5 py-1 rounded transition-colors ${
              horizonView === "5H"
                ? "border-[#00daf3] bg-[#00daf3]/20 text-[#00daf3] font-bold"
                : "border-white/10 text-[#bac9cc] hover:border-white/30"
            }`}
          >
            5H
          </button>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="p-4 w-full h-80 sm:h-96 relative">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
            <defs>
              {/* Stitch Volumetric 95% Wash */}
              <linearGradient id="stitchWash95" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ffffff" stopOpacity={0.06} />
                <stop offset="100%" stopColor="#ffffff" stopOpacity={0.01} />
              </linearGradient>
              {/* Stitch Volumetric 80% Wash */}
              <linearGradient id="stitchWash80" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#5516be" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#5516be" stopOpacity={0.08} />
              </linearGradient>
            </defs>

            {/* Target Glycemic Band (70 - 180 mg/dL) */}
            <ReferenceArea
              y1={GLUCOSE_THRESHOLDS.TARGET_MIN}
              y2={GLUCOSE_THRESHOLDS.TARGET_MAX}
              fill="#00daf3"
              fillOpacity={0.03}
            />

            {/* Threshold Reference Lines matching Stitch */}
            <ReferenceLine y={180} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
            <ReferenceLine y={120} stroke="#00daf3" strokeDasharray="3 3" strokeOpacity={0.4} />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
            <ReferenceLine x="NOW" stroke="#00daf3" strokeDasharray="2 2" strokeOpacity={0.7} />

            <XAxis
              dataKey="timeLabel"
              stroke="#64748B"
              fontSize={10}
              tickLine={false}
              fontFamily="JetBrains Mono"
            />
            <YAxis
              domain={[40, 260]}
              ticks={[50, 70, 120, 180, 250]}
              stroke="#64748B"
              fontSize={10}
              tickLine={false}
              fontFamily="JetBrains Mono"
              unit=" mg"
            />

            <Tooltip content={<CustomTooltip />} />

            {/* 95% Volumetric Wash */}
            <Area
              type="monotone"
              dataKey="band95"
              stroke="transparent"
              fill="url(#stitchWash95)"
              isAnimationActive={false}
            />

            {/* 80% Volumetric Wash */}
            <Area
              type="monotone"
              dataKey="band80"
              stroke="transparent"
              fill="url(#stitchWash80)"
              isAnimationActive={false}
            />

            {/* Historical CGM Trace (Faded) */}
            <Line
              type="monotone"
              dataKey="historicalGlucose"
              stroke="rgba(220,225,251,0.5)"
              strokeWidth={2}
              dot={{ fill: "rgba(220,225,251,0.7)", r: 2 }}
              isAnimationActive={false}
            />

            {/* M-ODE Simulation (Cyan dashed glow) */}
            {showSubComponents && (
              <Line
                type="monotone"
                dataKey="odeGlucose"
                stroke="#00daf3"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                isAnimationActive={false}
              />
            )}

            {/* N-ODE Forecast (Violet dashed glow) */}
            {showSubComponents && (
              <Line
                type="monotone"
                dataKey="neuralGlucose"
                stroke="#d0bcff"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                isAnimationActive={false}
              />
            )}

            {/* Hybrid Adaptive Forecast (Luminous Solid White) */}
            <Line
              type="monotone"
              dataKey="forecastGlucose"
              stroke="#ffffff"
              strokeWidth={3}
              dot={{ fill: "#00daf3", stroke: "#070d1f", strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, fill: "#00daf3" }}
              isAnimationActive={false}
            />

            {/* What-If Counterfactual (Pink dashed) */}
            {whatIfTrajectory && (
              <Line
                type="monotone"
                dataKey="whatIfGlucose"
                stroke="#ec4899"
                strokeWidth={2.5}
                strokeDasharray="5 3"
                dot={{ fill: "#ec4899", r: 3 }}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
