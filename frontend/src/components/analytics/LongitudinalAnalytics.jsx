import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  Clock,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Layers,
  Utensils,
  Syringe,
  Watch
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend
} from "recharts";
import {
  apiGetAnalyticsSummary,
  apiGetGlucoseAnalytics,
  apiGetDiurnalAnalytics,
  apiGetForecastPerformance,
  apiGetRiskFactors,
  apiGetTimeline,
  generateDemoAnalytics
} from "../../api/analytics.js";

export function LongitudinalAnalytics({
  patientId,
  token,
  isAuthenticated,
  isDemoMode
}) {
  const [period, setPeriod] = useState("14d");
  const [activeSubTab, setActiveSubTab] = useState("overview"); // overview, diurnal, forecast, factors, timeline
  const [timelineFilter, setTimelineFilter] = useState("all");

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Analytics states
  const [summaryData, setSummaryData] = useState(null);
  const [glucoseData, setGlucoseData] = useState(null);
  const [diurnalData, setDiurnalData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [timelineData, setTimelineData] = useState(null);

  const loadAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    // If demo mode or unauthenticated without patientId, use realistic demo analytics
    if (isDemoMode || !isAuthenticated || !patientId) {
      const demo = generateDemoAnalytics(period);
      setSummaryData(demo.summary);
      setDiurnalData(demo.diurnal);
      setForecastData(demo.forecast);
      setTimelineData(demo.timeline);
      setGlucoseData({ has_data: true, glucose_readings: [] });
      setIsLoading(false);
      return;
    }

    try {
      const [sum, gluc, diurn, fc, rsk, tl] = await Promise.all([
        apiGetAnalyticsSummary(token, patientId, period).catch(() => null),
        apiGetGlucoseAnalytics(token, patientId, period).catch(() => null),
        apiGetDiurnalAnalytics(token, patientId, period).catch(() => null),
        apiGetForecastPerformance(token, patientId, period).catch(() => null),
        apiGetRiskFactors(token, patientId, period).catch(() => null),
        apiGetTimeline(token, patientId, 50, 0, timelineFilter === "all" ? null : timelineFilter, period).catch(() => null)
      ]);

      setSummaryData(sum);
      setGlucoseData(gluc);
      setDiurnalData(diurn);
      setForecastData(fc);
      setRiskData(rsk);
      setTimelineData(tl);
    } catch (err) {
      console.error("[LongitudinalAnalytics] Error loading analytics:", err);
      setError(err.message || "Failed to load longitudinal analytics");
    } finally {
      setIsLoading(false);
    }
  }, [patientId, token, isAuthenticated, isDemoMode, period, timelineFilter]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const periods = [
    { id: "24h", label: "24 Hours" },
    { id: "7d", label: "7 Days" },
    { id: "14d", label: "14 Days" },
    { id: "30d", label: "30 Days" },
    { id: "all", label: "All Time" }
  ];

  const subTabs = [
    { id: "overview", label: "Glycemic Overview", icon: Activity },
    { id: "diurnal", label: "Diurnal AGP Profile", icon: Clock },
    { id: "forecast", label: "Forecast Accuracy", icon: TrendingUp },
    { id: "factors", label: "Nutrition & Factors", icon: Utensils },
    { id: "timeline", label: "Event Stream", icon: Layers }
  ];

  const hasData = summaryData?.has_data || false;
  const varMetrics = summaryData?.glycemic_variability || {};
  const bands = summaryData?.glycemic_bands || {};
  const episodes = summaryData?.episodes || {};

  return (
    <div className="space-y-6">
      {/* Research Disclaimer Header */}
      <div className="bg-[#10172a]/90 border border-cyan-500/20 rounded-xl p-4 flex items-center justify-between shadow-lg shadow-cyan-950/20 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white tracking-wide">
              Longitudinal Glycemic Analytics & Retrospective Forecast Calibration
            </h2>
            <p className="text-xs text-slate-400">
              Transforming historical patient data into causal trends, consensus TIR metrics, and forecast accuracy benchmarks.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Period Selector Tabs */}
          <div className="flex items-center bg-[#0a0f1d] p-1 rounded-lg border border-slate-800">
            {periods.map((p) => (
              <button
                key={p.id}
                onClick={() => setPeriod(p.id)}
                className={`px-3 py-1 text-xs font-mono rounded-md transition-all ${
                  period === p.id
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <button
            onClick={loadAnalytics}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition"
            title="Refresh Analytics"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/40 border border-red-500/30 rounded-xl p-4 text-red-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!hasData && !isLoading && (
        <div className="bg-slate-900/60 border border-slate-700/60 rounded-xl p-4 text-slate-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-cyan-400 flex-shrink-0" />
            <span>
              No historical data recorded for this patient profile in the selected window ({period}). Ingest CGM data or switch to demo mode to observe retrospective analytics.
            </span>
          </div>
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Mean Glucose */}
        <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-3.5 backdrop-blur-sm shadow-sm">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Mean Glucose</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold text-white font-mono">
              {varMetrics.mean_glucose != null ? `${varMetrics.mean_glucose}` : "--"}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">mg/dL</span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">
            Median: {varMetrics.median_glucose ?? "--"} mg/dL
          </span>
        </div>

        {/* GMI (Est. HbA1c) */}
        <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-3.5 backdrop-blur-sm shadow-sm">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Est. GMI / HbA1c</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold text-cyan-300 font-mono">
              {varMetrics.gmi_pct != null ? `${varMetrics.gmi_pct}%` : "--"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Bergenstal et al. formula</span>
        </div>

        {/* CV (Variability) */}
        <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-3.5 backdrop-blur-sm shadow-sm">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Variability (CV)</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className={`text-2xl font-bold font-mono ${
              (varMetrics.cv_pct ?? 0) <= 36.0 ? "text-emerald-400" : "text-amber-400"
            }`}>
              {varMetrics.cv_pct != null ? `${varMetrics.cv_pct}%` : "--"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Target ≤ 36.0%</span>
        </div>

        {/* Time in Range */}
        <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-3.5 backdrop-blur-sm shadow-sm">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Time in Range</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className={`text-2xl font-bold font-mono ${
              (bands.tir_pct ?? 0) >= 70.0 ? "text-emerald-400" : "text-amber-400"
            }`}>
              {bands.tir_pct != null ? `${bands.tir_pct}%` : "--"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">70-180 mg/dL (Goal &gt;70%)</span>
        </div>

        {/* LBGI (Hypo Risk) */}
        <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-3.5 backdrop-blur-sm shadow-sm">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Hypo Risk (LBGI)</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className={`text-2xl font-bold font-mono ${
              (varMetrics.lbgi ?? 0) < 2.5 ? "text-emerald-400" : "text-red-400"
            }`}>
              {varMetrics.lbgi != null ? `${varMetrics.lbgi}` : "--"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">
            {(varMetrics.lbgi ?? 0) < 2.5 ? "Low risk (<2.5)" : "Elevated risk"}
          </span>
        </div>

        {/* HBGI (Hyper Risk) */}
        <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-3.5 backdrop-blur-sm shadow-sm">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Hyper Risk (HBGI)</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className={`text-2xl font-bold font-mono ${
              (varMetrics.hbgi ?? 0) < 5.0 ? "text-emerald-400" : "text-amber-400"
            }`}>
              {varMetrics.hbgi != null ? `${varMetrics.hbgi}` : "--"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">
            {(varMetrics.hbgi ?? 0) < 5.0 ? "Low risk (<5.0)" : "Moderate risk"}
          </span>
        </div>
      </div>

      {/* Stacked Consensus Time-in-Range Bar */}
      <div className="bg-[#0b1329]/90 border border-white/10 rounded-xl p-4 shadow-md backdrop-blur-sm space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-200">Consensus Glycemic Distribution Bands</span>
          <span className="text-slate-400 font-mono text-[11px]">
            {summaryData?.total_readings ?? 0} valid readings ({summaryData?.days_of_data ?? 0} days)
          </span>
        </div>

        {/* Visual Stacked Progress Bar */}
        <div className="w-full h-5 rounded-full overflow-hidden flex bg-slate-900 border border-slate-700/50">
          <div
            style={{ width: `${bands.tbr_l2_pct ?? 0}%` }}
            className="bg-red-600 h-full transition-all"
            title={`TBR Level 2 (<54 mg/dL): ${bands.tbr_l2_pct ?? 0}%`}
          />
          <div
            style={{ width: `${bands.tbr_l1_pct ?? 0}%` }}
            className="bg-amber-500 h-full transition-all"
            title={`TBR Level 1 (54-69 mg/dL): ${bands.tbr_l1_pct ?? 0}%`}
          />
          <div
            style={{ width: `${bands.tir_pct ?? 0}%` }}
            className="bg-emerald-500 h-full transition-all"
            title={`TIR (70-180 mg/dL): ${bands.tir_pct ?? 0}%`}
          />
          <div
            style={{ width: `${bands.tar_l1_pct ?? 0}%` }}
            className="bg-orange-500 h-full transition-all"
            title={`TAR Level 1 (181-250 mg/dL): ${bands.tar_l1_pct ?? 0}%`}
          />
          <div
            style={{ width: `${bands.tar_l2_pct ?? 0}%` }}
            className="bg-red-700 h-full transition-all"
            title={`TAR Level 2 (>250 mg/dL): ${bands.tar_l2_pct ?? 0}%`}
          />
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 pt-1 text-[11px] font-mono">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-red-600 flex-shrink-0" />
            <span className="text-slate-300">TBR L2 (&lt;54):</span>
            <span className="text-white font-bold">{bands.tbr_l2_pct ?? 0}%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-amber-500 flex-shrink-0" />
            <span className="text-slate-300">TBR L1 (54-69):</span>
            <span className="text-white font-bold">{bands.tbr_l1_pct ?? 0}%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-emerald-500 flex-shrink-0" />
            <span className="text-slate-300">TIR (70-180):</span>
            <span className="text-white font-bold">{bands.tir_pct ?? 0}%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-orange-500 flex-shrink-0" />
            <span className="text-slate-300">TAR L1 (181-250):</span>
            <span className="text-white font-bold">{bands.tar_l1_pct ?? 0}%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-red-700 flex-shrink-0" />
            <span className="text-slate-300">TAR L2 (&gt;250):</span>
            <span className="text-white font-bold">{bands.tar_l2_pct ?? 0}%</span>
          </div>
        </div>
      </div>

      {/* Sub-tab Navigation */}
      <div className="flex border-b border-white/10 gap-2">
        {subTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium transition-all border-b-2 -mb-px ${
                isActive
                  ? "text-cyan-400 border-cyan-400 font-semibold"
                  : "text-slate-400 border-transparent hover:text-slate-200"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Sub-tab 1: Glycemic Overview */}
      {activeSubTab === "overview" && (
        <div className="space-y-6">
          {/* Episode Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4">
              <div className="flex items-center gap-2 text-red-400 text-xs font-semibold mb-2">
                <AlertTriangle className="w-4 h-4" />
                <span>Hypoglycemic Episodes (&lt;70 mg/dL)</span>
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {episodes.hypo_episode_count ?? 0}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Avg duration: {episodes.mean_hypo_duration_minutes ?? 0} min | Severe (&lt;54): {episodes.severe_hypo_episode_count ?? 0}
              </div>
            </div>

            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4">
              <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold mb-2">
                <TrendingUp className="w-4 h-4" />
                <span>Hyperglycemic Episodes (&gt;180 mg/dL)</span>
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {episodes.hyper_episode_count ?? 0}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Avg duration: {episodes.mean_hyper_duration_minutes ?? 0} min
              </div>
            </div>

            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold mb-2">
                <CheckCircle className="w-4 h-4" />
                <span>Tight Glycemic Control (TITR 70-140)</span>
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {bands.titr_pct != null ? `${bands.titr_pct}%` : "--"}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Duration: {Math.round((bands.titr_minutes ?? 0) / 60)} hours in period
              </div>
            </div>
          </div>

          {/* Longitudinal Glucose Readings Line Chart */}
          {glucoseData?.glucose_readings && glucoseData.glucose_readings.length > 0 ? (
            <div className="bg-[#0b1329]/90 border border-white/10 rounded-xl p-5 shadow-lg">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center justify-between">
                <span>Longitudinal Glucose Trajectory (CGM)</span>
                <span className="text-xs font-mono text-cyan-400">{glucoseData.glucose_readings.length} data points</span>
              </h3>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={glucoseData.glucose_readings}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="timestamp"
                      stroke="#64748b"
                      fontSize={10}
                      tickFormatter={(t) => new Date(t).toLocaleDateString([], { month: "short", day: "numeric" })}
                    />
                    <YAxis domain={[40, 300]} stroke="#64748b" fontSize={10} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                      labelFormatter={(t) => new Date(t).toLocaleString()}
                    />
                    <ReferenceLine y={180} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "180 mg/dL", fill: "#f59e0b", fontSize: 10 }} />
                    <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "70 mg/dL", fill: "#ef4444", fontSize: 10 }} />
                    <Line type="monotone" dataKey="cgm_glucose" stroke="#00daf3" dot={false} strokeWidth={1.5} name="Glucose (mg/dL)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="bg-[#0b1329]/60 border border-white/5 rounded-xl p-8 text-center text-slate-400 text-xs">
              Continuous trend chart will appear as live CGM readings are recorded over this window.
            </div>
          )}
        </div>
      )}

      {/* Sub-tab 2: Diurnal AGP Profile */}
      {activeSubTab === "diurnal" && (
        <div className="space-y-6">
          {/* Quadrant Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {(diurnalData?.quadrants || []).map((q) => (
              <div key={q.quadrant} className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">{q.quadrant}</span>
                  <span className="text-[10px] font-mono text-slate-500">{q.hours}</span>
                </div>
                <div className="text-xl font-bold font-mono text-cyan-300">
                  {q.mean_glucose != null ? `${q.mean_glucose} mg/dL` : "--"}
                </div>
                <div className="text-[11px] font-mono text-slate-400 space-y-1">
                  <div>TIR: <span className="text-emerald-400">{q.tir_pct != null ? `${q.tir_pct}%` : "--"}</span></div>
                  <div>CV: <span className="text-slate-300">{q.cv_pct != null ? `${q.cv_pct}%` : "--"}</span></div>
                  <div>Count: <span className="text-slate-500">{q.reading_count} pts</span></div>
                </div>
              </div>
            ))}
          </div>

          {/* 24-Hour Ambulatory Glucose Profile (AGP) Chart */}
          <div className="bg-[#0b1329]/90 border border-white/10 rounded-xl p-5 shadow-lg">
            <h3 className="text-sm font-semibold text-white mb-1">
              24-Hour Ambulatory Glucose Profile (AGP)
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Hourly median glucose trajectory with 10th-90th percentile envelope across all days in period.
            </p>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={diurnalData?.hourly_agp || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="hour" stroke="#64748b" fontSize={10} tickFormatter={(h) => `${h}:00`} />
                  <YAxis domain={[40, 260]} stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }} />
                  <ReferenceLine y={180} stroke="#f59e0b" strokeDasharray="4 4" />
                  <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="4 4" />
                  <Area type="monotone" dataKey="p90" stroke="transparent" fill="#00daf3" fillOpacity={0.15} name="90th Percentile" />
                  <Area type="monotone" dataKey="p10" stroke="transparent" fill="#0b1329" fillOpacity={1.0} name="10th Percentile" />
                  <Line type="monotone" dataKey="median_glucose" stroke="#00daf3" strokeWidth={2} dot={{ r: 3 }} name="Median Glucose" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Sub-tab 3: Forecast Accuracy & Calibration */}
      {activeSubTab === "forecast" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400 uppercase">Mean Absolute Error (MAE)</span>
              <div className="text-2xl font-bold font-mono text-white mt-1">
                {forecastData?.overall_mae_mg_dl != null ? `${forecastData.overall_mae_mg_dl}` : "--"}
                <span className="text-xs text-slate-400 ml-1">mg/dL</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Retrospective ground truth evaluation</span>
            </div>

            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400 uppercase">Root Mean Square Error (RMSE)</span>
              <div className="text-2xl font-bold font-mono text-white mt-1">
                {forecastData?.overall_rmse_mg_dl != null ? `${forecastData.overall_rmse_mg_dl}` : "--"}
                <span className="text-xs text-slate-400 ml-1">mg/dL</span>
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Penalizes large excursion misses</span>
            </div>

            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400 uppercase">80% Interval Coverage</span>
              <div className={`text-2xl font-bold font-mono mt-1 ${
                (forecastData?.overall_coverage_80_pct ?? 0) >= 80.0 ? "text-emerald-400" : "text-amber-400"
              }`}>
                {forecastData?.overall_coverage_80_pct != null ? `${forecastData.overall_coverage_80_pct}%` : "--"}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Target: ≥ 80.0% coverage</span>
            </div>

            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400 uppercase">95% Interval Coverage</span>
              <div className={`text-2xl font-bold font-mono mt-1 ${
                (forecastData?.overall_coverage_95_pct ?? 0) >= 95.0 ? "text-emerald-400" : "text-amber-400"
              }`}>
                {forecastData?.overall_coverage_95_pct != null ? `${forecastData.overall_coverage_95_pct}%` : "--"}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Target: ≥ 95.0% coverage</span>
            </div>
          </div>

          {/* Horizon Degradation Curve */}
          {forecastData?.horizon_metrics && forecastData.horizon_metrics.length > 0 && (
            <div className="bg-[#0b1329]/90 border border-white/10 rounded-xl p-5 shadow-lg">
              <h3 className="text-sm font-semibold text-white mb-1">
                Error Scaling Across Forecast Horizons (15 min to 5 Hours)
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                MAE and RMSE degradation profile as prediction horizon expands into the future.
              </p>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={forecastData.horizon_metrics}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="horizon_minutes" stroke="#64748b" fontSize={10} tickFormatter={(m) => `${m}m`} />
                    <YAxis stroke="#64748b" fontSize={10} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }} />
                    <Legend wrapperStyle={{ fontSize: "11px" }} />
                    <Line type="monotone" dataKey="mae_mg_dl" stroke="#00daf3" name="MAE (mg/dL)" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="rmse_mg_dl" stroke="#f43f5e" name="RMSE (mg/dL)" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sub-tab 4: Factors & Nutrition */}
      {activeSubTab === "factors" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold">
                <Utensils className="w-4 h-4" />
                <span>Nutrition & Carbohydrates</span>
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {summaryData?.daily_metrics?.mean_daily_carbs_g ?? "--"} g/day
              </div>
              <div className="text-xs text-slate-400 space-y-1">
                <div>Total logged: {summaryData?.daily_metrics?.total_carbs_g ?? 0}g</div>
                <div>Meals logged: {summaryData?.daily_metrics?.meal_count ?? 0}</div>
              </div>
            </div>

            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2 text-violet-400 text-xs font-semibold">
                <Syringe className="w-4 h-4" />
                <span>Insulin Dosing & TDD</span>
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {summaryData?.daily_metrics?.total_daily_dose_tdd ?? "--"} U/day
              </div>
              <div className="text-xs text-slate-400 space-y-1">
                <div>Bolus: {summaryData?.daily_metrics?.mean_daily_bolus_units ?? 0} U/day</div>
                <div>Basal: {summaryData?.daily_metrics?.mean_daily_basal_units ?? 0} U/day</div>
                <div>Ratio: {summaryData?.daily_metrics?.bolus_basal_ratio ?? "--"}</div>
              </div>
            </div>

            <div className="bg-[#0b1329]/80 border border-white/5 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
                <Watch className="w-4 h-4" />
                <span>Wearable Context</span>
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {riskData?.wearable_trends?.mean_daily_steps != null
                  ? `${riskData.wearable_trends.mean_daily_steps} steps`
                  : "--"}
              </div>
              <div className="text-xs text-slate-400 space-y-1">
                <div>Avg Heart Rate: {riskData?.wearable_trends?.mean_heart_rate_bpm ?? "--"} bpm</div>
                <div>Syncs logged: {riskData?.wearable_trends?.observation_count ?? 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-tab 5: Unified Chronological Event Timeline */}
      {activeSubTab === "timeline" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs text-slate-400 font-mono">
              Displaying {timelineData?.events?.length ?? 0} of {timelineData?.total_events ?? 0} historical events
            </div>

            {/* Event Filter Chips */}
            <div className="flex items-center gap-1.5 bg-[#0a0f1d] p-1 rounded-lg border border-slate-800 text-xs">
              {["all", "cgm", "meal", "insulin", "forecast", "decision"].map((f) => (
                <button
                  key={f}
                  onClick={() => setTimelineFilter(f)}
                  className={`px-2.5 py-1 rounded capitalize transition ${
                    timelineFilter === f
                      ? "bg-cyan-500/20 text-cyan-300 font-semibold"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            {(timelineData?.events || []).map((ev) => {
              const sevColors = {
                critical: "border-l-4 border-l-red-500 bg-red-950/20 text-red-200",
                warning: "border-l-4 border-l-amber-500 bg-amber-950/20 text-amber-200",
                normal: "border-l-4 border-l-emerald-500 bg-[#0b1329]/80 text-slate-200",
                info: "border-l-4 border-l-cyan-500 bg-[#0b1329]/80 text-slate-200"
              };
              const sevClass = sevColors[ev.severity] || sevColors.info;

              return (
                <div
                  key={ev.id}
                  className={`p-3.5 rounded-lg border border-white/5 backdrop-blur-sm flex items-center justify-between transition hover:border-white/20 ${sevClass}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase bg-white/10 text-cyan-300">
                      {ev.event_type}
                    </span>
                    <div>
                      <h4 className="text-xs font-semibold text-white">{ev.title}</h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">{ev.secondary_value}</p>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-bold font-mono text-white">{ev.primary_value}</div>
                    <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                      {new Date(ev.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              );
            })}

            {(!timelineData?.events || timelineData.events.length === 0) && (
              <div className="text-center py-8 text-slate-500 text-xs">
                No events recorded for this patient in the selected filter window.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
