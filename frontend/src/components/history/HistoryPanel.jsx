import React, { useState, useEffect, useMemo } from "react";
import {
  History,
  TrendingUp,
  Activity,
  HeartPulse,
  Calendar,
  CheckCircle,
  FileDown,
  Layers,
  Utensils,
  Sparkles,
  Info,
  Clock,
  Sliders,
  ChevronDown
} from "lucide-react";
import {
  apiGetCGMHistory,
  apiGetMealHistory,
  apiGetForecastHistory,
  apiGetDecisionHistory,
  apiGetWhatIfHistory
} from "../../api/auth";
import {
  apiGetAnalyticsSummary,
  apiGetDiurnalAnalytics
} from "../../api/analytics";

export function HistoryPanel({ token, patientProfile, isDemoMode, historyReadings = [], cohortPatient = null }) {
  const [timeframe, setTimeframe] = useState("7d");
  const [filterType, setFilterType] = useState("all");
  const [expandedRowId, setExpandedRowId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const [cgmRecords, setCgmRecords] = useState([]);
  const [mealRecords, setMealRecords] = useState([]);
  const [forecastRecords, setForecastRecords] = useState([]);
  const [decisionRecords, setDecisionRecords] = useState([]);
  const [whatIfRecords, setWhatIfRecords] = useState([]);
  const [analyticsSummary, setAnalyticsSummary] = useState(null);
  const [diurnalData, setDiurnalData] = useState(null);

  const patientId = patientProfile?.id || null;

  const isCohortPatient = patientId === "PATIENT_A" || patientId === "PATIENT_B" || Boolean(cohortPatient) || (!token && historyReadings.length > 0);

  useEffect(() => {
    // When displaying real clinical cohort demonstration patient, populate strictly from memory telemetry readings
    if (isCohortPatient && Array.isArray(historyReadings) && historyReadings.length > 0) {
      setLoading(false);
      setFetchError(null);

      const gVals = historyReadings.map(r => r.cgm_glucose).filter(v => typeof v === "number" && !isNaN(v));
      if (gVals.length > 0) {
        const mean = gVals.reduce((a, b) => a + b, 0) / gVals.length;
        const sqDiff = gVals.map(v => Math.pow(v - mean, 2));
        const std = Math.sqrt(sqDiff.reduce((a, b) => a + b, 0) / gVals.length);
        const cv = mean > 0 ? (std / mean) * 100 : 0;
        const gmi = 3.31 + 0.02392 * mean;
        const tir = (gVals.filter(v => v >= 70 && v <= 180).length / gVals.length) * 100;
        const tbrL1 = (gVals.filter(v => v < 70).length / gVals.length) * 100;
        const tbrL2 = (gVals.filter(v => v < 54).length / gVals.length) * 100;
        const tarL1 = (gVals.filter(v => v > 180).length / gVals.length) * 100;
        const tarL2 = (gVals.filter(v => v > 250).length / gVals.length) * 100;

        setAnalyticsSummary({
          has_data: true,
          total_readings: gVals.length,
          days_of_data: 1.0,
          glycemic_bands: {
            tir_pct: Math.round(tir * 10) / 10,
            tbr_l1_pct: Math.round(tbrL1 * 10) / 10,
            tbr_l2_pct: Math.round(tbrL2 * 10) / 10,
            tar_l1_pct: Math.round(tarL1 * 10) / 10,
            tar_l2_pct: Math.round(tarL2 * 10) / 10
          },
          glycemic_variability: {
            mean_glucose: Math.round(mean * 10) / 10,
            std_glucose: Math.round(std * 10) / 10,
            cv_pct: Math.round(cv * 10) / 10,
            gmi_pct: Math.round(gmi * 10) / 10
          }
        });

        // Compute 24h diurnal hourly profile
        const hourlyData = [];
        for (let h = 0; h < 24; h++) {
          const hSlice = gVals.slice(h * 4, (h + 1) * 4);
          if (hSlice.length > 0) {
            hSlice.sort((a, b) => a - b);
            hourlyData.push({
              hour: h,
              reading_count: hSlice.length,
              median_glucose: hSlice[Math.floor(hSlice.length / 2)],
              p10: hSlice[0],
              p25: hSlice[0],
              p75: hSlice[hSlice.length - 1],
              p90: hSlice[hSlice.length - 1]
            });
          }
        }
        setDiurnalData({
          has_data: true,
          hourly_agp: hourlyData
        });

        // Populate genuine historical records from 24-hour window
        setCgmRecords(historyReadings.map((r, i) => ({
          id: `cgm-${i}`,
          timestamp: r.timestamp || new Date(Date.now() - (historyReadings.length - 1 - i) * 15 * 60000).toISOString(),
          cgm_glucose: r.cgm_glucose,
          insulin_bolus: r.insulin_bolus || 0,
          insulin_basal: r.insulin_basal || 0,
          meal_carbs: r.meal_carbs || 0
        })).reverse());
      }
      return;
    }

    if (!token || isDemoMode || !patientId) {
      setLoading(false);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setFetchError(null);

    const apiPeriod = timeframe === "today" ? "24h" : timeframe;

    Promise.all([
      apiGetCGMHistory(token, patientId, 48).catch(() => []),
      apiGetMealHistory(token, patientId, 20).catch(() => []),
      apiGetForecastHistory(token, patientId, 10).catch(() => []),
      apiGetDecisionHistory(token, patientId, 10).catch(() => []),
      apiGetAnalyticsSummary(token, patientId, apiPeriod).catch(() => null),
      apiGetDiurnalAnalytics(token, patientId, apiPeriod).catch(() => null),
      apiGetWhatIfHistory(token, patientId, 20).catch(() => [])
    ])
      .then(([cgm, meals, forecasts, decisions, summary, diurnal, whatIfs]) => {
        if (!isMounted) return;
        setCgmRecords(cgm || []);
        setMealRecords(meals || []);
        setForecastRecords(forecasts || []);
        setDecisionRecords(decisions || []);
        setAnalyticsSummary(summary);
        setDiurnalData(diurnal);
        setWhatIfRecords(whatIfs || []);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error("[History Load Error]", err);
        setFetchError("Unable to retrieve longitudinal history records.");
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [token, patientId, timeframe, isDemoMode, historyReadings, cohortPatient, isCohortPatient]);

  // Genuine verified events built strictly from persisted database records
  const verifiedEvents = useMemo(() => {
    const list = [];

    // 1. Persisted Meals
    (mealRecords || []).forEach((m, idx) => {
      const d = m.timestamp || m.created_at;
      const dateObj = d ? new Date(d) : new Date();
      list.push({
        id: `meal-${m.id || idx}`,
        rawDate: dateObj,
        timestamp: dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }),
        event: m.meal_name || "Logged Meal",
        type: "meal",
        nutrition: `${m.carbs_g}g CHO${m.calories_kcal ? ` • ${Math.round(m.calories_kcal)} kcal` : ""}`,
        insulin: "—",
        predictedPeak: "—",
        actualPeak: "—",
        variance: null,
        status: m.user_confirmed ? "Confirmed Meal" : "Logged Event"
      });
    });

    // 2. Persisted Forecasts
    (forecastRecords || []).forEach((f, idx) => {
      const d = f.timestamp || f.created_at;
      const dateObj = d ? new Date(d) : new Date();
      const predPeak = Array.isArray(f.point_forecast) && f.point_forecast.length > 0
        ? Math.round(Math.max(...f.point_forecast))
        : "—";

      list.push({
        id: `fc-${f.id || idx}`,
        rawDate: dateObj,
        timestamp: dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }),
        event: "5-Hour Forecast Window",
        type: "forecast",
        nutrition: f.current_cob ? `${Math.round(f.current_cob)}g COB` : "0g COB",
        insulin: f.current_iob ? `${Number(f.current_iob).toFixed(1)} U IOB` : "0 U IOB",
        predictedPeak: predPeak,
        actualPeak: "—",
        variance: null,
        status: "Forecast Model",
        rawForecast: f
      });
    });

    // 3. Persisted Clinical Decisions
    (decisionRecords || []).forEach((dec, idx) => {
      const d = dec.timestamp || dec.created_at;
      const dateObj = d ? new Date(d) : new Date();
      list.push({
        id: `dec-${dec.id || idx}`,
        rawDate: dateObj,
        timestamp: dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }),
        event: dec.recommended_action || "Decision Report",
        type: "decision",
        nutrition: "—",
        insulin: "—",
        predictedPeak: "—",
        actualPeak: "—",
        variance: null,
        status: dec.alert_status || "Decision"
      });
    });

    // 4. Persisted In Silico What-If Simulations (Counterfactual simulations isolated from clinical events)
    (whatIfRecords || []).forEach((w, idx) => {
      const d = w.timestamp || w.created_at;
      const dateObj = d ? new Date(d) : new Date();
      const peak = w.peak_glucose != null ? Math.round(w.peak_glucose) : "—";
      list.push({
        id: `whatif-${w.id || idx}`,
        rawDate: dateObj,
        timestamp: dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }),
        event: w.scenario_name ? `Simulation: ${w.scenario_name}` : "What-If Simulation",
        type: "what_if",
        nutrition: w.scenario_meal_carbs_g != null ? `${w.scenario_meal_carbs_g}g CHO (Sim)` : "—",
        insulin: w.scenario_insulin_bolus_u != null ? `${Number(w.scenario_insulin_bolus_u).toFixed(1)} U (Sim)` : "—",
        predictedPeak: peak,
        actualPeak: "—",
        variance: null,
        status: "What-If Simulation",
        isSimulation: true,
        rawWhatIf: w
      });
    });

    return list.sort((a, b) => b.rawDate - a.rawDate);
  }, [mealRecords, forecastRecords, decisionRecords, whatIfRecords]);

  const filteredEvents = verifiedEvents.filter((ev) => {
    if (filterType === "all") return true;
    if (filterType === "meals") return ev.type === "meal";
    if (filterType === "boluses") return ev.insulin !== "—";
    if (filterType === "forecasts") return ev.type === "forecast";
    if (filterType === "simulations" || filterType === "what_if") return ev.type === "what_if";
    return true;
  });

  // Analytics Metrics Extraction
  const hasAnalyticsData = Boolean(analyticsSummary?.has_data);
  const totalReadings = analyticsSummary?.total_readings ?? 0;
  const daysOfData = analyticsSummary?.days_of_data != null ? analyticsSummary.days_of_data.toFixed(1) : "0.0";

  // Card 1: Time in Range (70-180 mg/dL)
  const tirVal = hasAnalyticsData && analyticsSummary?.glycemic_bands?.tir_pct != null
    ? analyticsSummary.glycemic_bands.tir_pct.toFixed(1)
    : "—";
  const tirNum = hasAnalyticsData && analyticsSummary?.glycemic_bands?.tir_pct != null
    ? analyticsSummary.glycemic_bands.tir_pct
    : null;
  const tirBadge = tirNum === null
    ? { label: "No Data", bg: "bg-surface-container-high", text: "text-on-surface-variant", dot: "bg-outline" }
    : tirNum >= 70
    ? { label: "Target Met", bg: "bg-tertiary-fixed", text: "text-on-tertiary-fixed", dot: "bg-tertiary" }
    : { label: "Below Target", bg: "bg-error-container", text: "text-on-error-container", dot: "bg-error" };

  // Card 2: Time Below Range (<70 mg/dL)
  const tbrVal = hasAnalyticsData && analyticsSummary?.glycemic_bands?.tbr_l1_pct != null
    ? analyticsSummary.glycemic_bands.tbr_l1_pct.toFixed(1)
    : "—";
  const tbrNum = hasAnalyticsData && analyticsSummary?.glycemic_bands?.tbr_l1_pct != null
    ? analyticsSummary.glycemic_bands.tbr_l1_pct
    : null;
  const tbrBadge = tbrNum === null
    ? { label: "No Data", bg: "bg-surface-container-high", text: "text-on-surface-variant", dot: "bg-outline" }
    : tbrNum < 4
    ? { label: "Controlled", bg: "bg-secondary-fixed", text: "text-on-secondary-fixed-variant", dot: "bg-secondary" }
    : { label: "Elevated", bg: "bg-error-container", text: "text-on-error-container", dot: "bg-error" };

  // Card 3: Mean Glucose & Variability
  const meanVal = hasAnalyticsData && analyticsSummary?.glycemic_variability?.mean_glucose != null
    ? Math.round(analyticsSummary.glycemic_variability.mean_glucose)
    : "—";
  const gmiVal = hasAnalyticsData && analyticsSummary?.glycemic_variability?.gmi_pct != null
    ? `GMI: ${analyticsSummary.glycemic_variability.gmi_pct.toFixed(1)}%`
    : "GMI: —";
  const cvVal = hasAnalyticsData && analyticsSummary?.glycemic_variability?.cv_pct != null
    ? `SD: ${Math.round(analyticsSummary.glycemic_variability.std_glucose || 0)} mg/dL (CV ${analyticsSummary.glycemic_variability.cv_pct.toFixed(1)}%)`
    : "Glycemic Variability: —";

  // Card 4: Sensor Stream Badge
  const streamBadge = totalReadings > 0
    ? { label: "Active Stream", bg: "bg-tertiary-fixed", text: "text-on-tertiary-fixed", icon: true }
    : { label: "No Data", bg: "bg-surface-container-high", text: "text-on-surface-variant", icon: false };

  // AGP Profile calculation
  const hasAgpPoints = Boolean(
    diurnalData?.has_data &&
    Array.isArray(diurnalData?.hourly_agp) &&
    diurnalData.hourly_agp.some((p) => p.reading_count > 0 && p.median_glucose != null)
  );

  // SVG coordinate helpers (X: 50 -> 980 for hour 0 -> 23; Y: 40 -> 280 for 250 -> 40 mg/dL)
  const getAgpX = (hour) => 50 + (hour / 23) * (980 - 50);
  const getAgpY = (val) => {
    const clamped = Math.max(40, Math.min(250, val));
    return 280 - ((clamped - 40) / 210) * 240;
  };

  const validAgpPoints = useMemo(() => {
    if (!hasAgpPoints) return [];
    return diurnalData.hourly_agp
      .filter((p) => p.reading_count > 0 && p.median_glucose != null)
      .sort((a, b) => a.hour - b.hour);
  }, [hasAgpPoints, diurnalData]);

  // Construct SVG paths if valid points exist
  const { medianPath, p25p75Path, p10p90Path } = useMemo(() => {
    if (validAgpPoints.length < 2) {
      return { medianPath: "", p25p75Path: "", p10p90Path: "" };
    }

    const medParts = validAgpPoints.map((p, idx) => {
      const x = getAgpX(p.hour).toFixed(1);
      const y = getAgpY(p.median_glucose).toFixed(1);
      return `${idx === 0 ? "M" : "L"} ${x} ${y}`;
    });

    const p90Top = validAgpPoints.map((p, idx) => {
      const x = getAgpX(p.hour).toFixed(1);
      const y = getAgpY(p.p90 ?? p.median_glucose).toFixed(1);
      return `${idx === 0 ? "M" : "L"} ${x} ${y}`;
    });
    const p10Bottom = [...validAgpPoints].reverse().map((p) => {
      const x = getAgpX(p.hour).toFixed(1);
      const y = getAgpY(p.p10 ?? p.median_glucose).toFixed(1);
      return `L ${x} ${y}`;
    });

    const p75Top = validAgpPoints.map((p, idx) => {
      const x = getAgpX(p.hour).toFixed(1);
      const y = getAgpY(p.p75 ?? p.median_glucose).toFixed(1);
      return `${idx === 0 ? "M" : "L"} ${x} ${y}`;
    });
    const p25Bottom = [...validAgpPoints].reverse().map((p) => {
      const x = getAgpX(p.hour).toFixed(1);
      const y = getAgpY(p.p25 ?? p.median_glucose).toFixed(1);
      return `L ${x} ${y}`;
    });

    return {
      medianPath: medParts.join(" "),
      p25p75Path: `${p75Top.join(" ")} ${p25Bottom.join(" ")} Z`,
      p10p90Path: `${p90Top.join(" ")} ${p10Bottom.join(" ")} Z`
    };
  }, [validAgpPoints]);

  return (
    <div className="flex flex-col w-full space-y-6">
      {/* Top Triage & Timeframe Command Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-space-xs mb-1">
            <span className="font-code-sm text-code-sm text-primary uppercase font-semibold tracking-wider">
              Longitudinal Telemetry Log: {timeframe}
            </span>
            <span className="text-outline-variant">•</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant">
              Continuous CGM Telemetry
            </span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight">
            Longitudinal Glycemic History &amp; Retrospective Performance
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-0.5">
            Historical CGM logs, meal/insulin interventions, and AI forecast verification against continuous biosignals.
          </p>
        </div>

        {/* Timeframe Selector */}
        <div className="flex items-center bg-surface-container-low p-1 rounded-lg gap-1 self-start lg:self-center shadow-sm border border-surface-container">
          {["today", "7d", "14d", "30d"].map((t) => (
            <button
              key={t}
              onClick={() => setTimeframe(t)}
              className={`px-space-md py-1.5 font-label-sm text-label-sm rounded transition-colors ${
                timeframe === t
                  ? "bg-primary text-on-primary font-semibold shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {t === "today" ? "Today" : t === "7d" ? "Last 7 Days" : t === "14d" ? "Last 14 Days" : "Last 30 Days"}
            </button>
          ))}
          <button className="flex items-center gap-1 px-space-md py-1.5 font-label-sm text-label-sm text-on-surface-variant hover:text-on-surface transition-colors rounded">
            <Calendar className="w-3.5 h-3.5" />
            <span>Custom Range</span>
          </button>
        </div>
      </div>

      {/* Real Clinical Cohort Provenance Banner */}
      {isCohortPatient && (
        <div className="p-space-md rounded-xl bg-surface-container-low border border-surface-container flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            <span className="font-semibold text-on-surface">Data Provenance:</span>
            <span className="text-on-surface-variant">Research Dataset Cohort (meta_test.csv / cleaned_master.csv)</span>
          </div>
          <div className="flex items-center gap-2 text-on-surface-variant">
            <span>Window: 96 observations (24h @ 15m)</span>
            <span>•</span>
            <span className="text-primary font-semibold">Loaded in Memory</span>
            <span>•</span>
            <span className="text-outline">Not stored in database</span>
          </div>
        </div>
      )}

      {/* Non-24h Warning in Cohort Mode */}
      {isCohortPatient && timeframe !== "today" && (
        <div className="p-space-md rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs font-mono flex items-center gap-2">
          <Info className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>24-Hour Demonstration Window Selected:</strong> Exactly 96 observations are available for this cohort profile. Multi-day longitudinal trends ({timeframe.toUpperCase()}) require active continuous monitoring records in the database. Showing 24-hour baseline.
          </span>
        </div>
      )}

      {/* Unauthenticated / Error Banner */}
      {!token && !isDemoMode && !isCohortPatient && (
        <div className="mb-space-lg p-space-md bg-surface-container border border-surface-container-high rounded-lg flex items-center gap-space-sm text-on-surface">
          <Info className="w-5 h-5 text-primary shrink-0" />
          <span className="font-body-md text-body-md text-on-surface-variant">
            Please log in or select a demo patient profile to stream longitudinal telemetry and retrospective records.
          </span>
        </div>
      )}
      {fetchError && (
        <div className="mb-space-lg p-space-md bg-error-container/20 border border-error-container rounded-lg flex items-center gap-space-sm text-error">
          <Info className="w-5 h-5 text-error shrink-0" />
          <span className="font-body-md text-body-md">
            {fetchError}
          </span>
        </div>
      )}

      {/* Key Performance Indicators (4 Real-Data Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Time in Range */}
        <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
                Time in Range
              </span>
              <div className="font-code-sm text-code-sm text-outline mt-0.5">70 – 180 mg/dL</div>
            </div>
            <span className={`px-2 py-0.5 rounded ${tirBadge.bg} ${tirBadge.text} font-code-sm text-code-sm font-semibold flex items-center gap-1`}>
              <span className={`w-1.5 h-1.5 rounded-full ${tirBadge.dot}`}></span> {tirBadge.label}
            </span>
          </div>
          <div className="my-space-md flex items-baseline gap-space-xs">
            <span className="font-telemetry-display text-telemetry-display text-on-surface tracking-tight font-bold">
              {tirVal}
            </span>
            {tirVal !== "—" && (
              <span className="font-telemetry-unit text-telemetry-unit text-outline uppercase font-semibold">%</span>
            )}
          </div>
          <div className="flex items-center justify-between pt-space-xs bg-surface-container-low/50 px-space-sm py-1.5 rounded border border-surface-container">
            <span className="font-body-sm text-body-sm text-on-surface-variant">Clinical Target: &gt;70%</span>
            <span className="font-code-sm text-code-sm text-on-surface font-semibold">
              {tirNum !== null ? `${tirNum >= 70 ? "+" : ""}${(tirNum - 70).toFixed(1)}% margin` : "0 readings"}
            </span>
          </div>
        </div>

        {/* Card 2: Time Below Range */}
        <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
                Time Below Range
              </span>
              <div className="font-code-sm text-code-sm text-outline mt-0.5">&lt;70 mg/dL (Hypo)</div>
            </div>
            <span className={`px-2 py-0.5 rounded ${tbrBadge.bg} ${tbrBadge.text} font-code-sm text-code-sm font-semibold flex items-center gap-1`}>
              <span className={`w-1.5 h-1.5 rounded-full ${tbrBadge.dot}`}></span> {tbrBadge.label}
            </span>
          </div>
          <div className="my-space-md flex items-baseline gap-space-xs">
            <span className="font-telemetry-display text-telemetry-display text-on-surface tracking-tight font-bold">
              {tbrVal}
            </span>
            {tbrVal !== "—" && (
              <span className="font-telemetry-unit text-telemetry-unit text-outline uppercase font-semibold">%</span>
            )}
          </div>
          <div className="flex items-center justify-between pt-space-xs bg-surface-container-low/50 px-space-sm py-1.5 rounded border border-surface-container">
            <span className="font-body-sm text-body-sm text-on-surface-variant">Clinical Threshold: &lt;4%</span>
            <span className="font-code-sm text-code-sm text-on-surface font-semibold">
              {tbrNum !== null ? `Safe • ${(4 - tbrNum).toFixed(1)}% buffer` : "0 readings"}
            </span>
          </div>
        </div>

        {/* Card 3: Mean Glucose */}
        <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
                Mean Glucose
              </span>
              <div className="font-code-sm text-code-sm text-outline mt-0.5">{timeframe} Continuous Vector</div>
            </div>
            <span className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant font-code-sm text-code-sm font-semibold">
              {gmiVal}
            </span>
          </div>
          <div className="my-space-md flex items-baseline gap-space-xs">
            <span className="font-telemetry-display text-telemetry-display text-on-surface tracking-tight font-bold">
              {meanVal}
            </span>
            {meanVal !== "—" && (
              <span className="font-telemetry-unit text-telemetry-unit text-outline uppercase font-semibold">mg/dL</span>
            )}
          </div>
          <div className="flex items-center justify-between pt-space-xs bg-surface-container-low/50 px-space-sm py-1.5 rounded border border-surface-container">
            <span className="font-body-sm text-body-sm text-on-surface-variant">Glycemic Variability</span>
            <span className="font-code-sm text-code-sm text-on-surface font-semibold">{cvVal}</span>
          </div>
        </div>

        {/* Card 4: Sensor Stream */}
        <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col justify-between relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
                Sensor Stream
              </span>
              <div className="font-code-sm text-code-sm text-outline mt-0.5">Continuous Monitoring</div>
            </div>
            <span className={`px-2 py-0.5 rounded ${streamBadge.bg} ${streamBadge.text} font-code-sm text-code-sm font-semibold flex items-center gap-1`}>
              {streamBadge.icon && <CheckCircle className="w-3.5 h-3.5 text-primary" />}
              {streamBadge.label}
            </span>
          </div>
          <div className="my-space-md flex items-baseline gap-space-xs">
            <span className="font-telemetry-display text-telemetry-display text-primary tracking-tight font-bold">
              {totalReadings}
            </span>
            <span className="font-telemetry-unit text-telemetry-unit text-outline uppercase font-semibold">readings</span>
          </div>
          <div className="flex items-center justify-between pt-space-xs bg-surface-container-low/50 px-space-sm py-1.5 rounded border border-surface-container">
            <span className="font-body-sm text-body-sm text-on-surface-variant">Sensor Glucose Readings</span>
            <span className="font-code-sm text-code-sm text-primary font-semibold">
              {daysOfData} days of data
            </span>
          </div>
        </div>
      </div>

      {/* Multi-Day Modal Glycemic Profile (Ambulatory Glucose Profile - AGP) */}
      <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md mb-space-lg">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                {isCohortPatient ? "24-Hour Diurnal Glucose Curve (Cohort Window)" : `Ambulatory Glucose Profile (AGP) - ${timeframe} Modal View`}
              </h2>
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant mt-0.5">
              {isCohortPatient
                ? "Hourly median curve with 10th-90th and 25th-75th interquartile ranges mapped to a synchronous 24-hour cycle. Standardized clinical AGP reports require ≥14 days of longitudinal data (Battelino et al., 2019)."
                : "Median curve (50th percentile) with 10th–90th and 25th–75th interquartile ranges mapped to a synchronous 24-hour cycle."}
            </p>
          </div>

          {/* Legend Indicator */}
          {hasAgpPoints && (
            <div className="flex flex-wrap items-center gap-space-md bg-surface-container-low px-space-md py-1.5 rounded-lg border border-surface-container">
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-1 bg-primary rounded-full"></span>
                <span className="font-label-sm text-label-sm text-on-surface">Median Trajectory</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-2.5 bg-primary/20 rounded"></span>
                <span className="font-label-sm text-label-sm text-on-surface-variant">25th–75th IQR</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-2.5 bg-secondary-fixed/40 rounded"></span>
                <span className="font-label-sm text-label-sm text-on-surface-variant">10th–90th Range</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-2 bg-tertiary-fixed/60 rounded"></span>
                <span className="font-label-sm text-label-sm text-on-surface-variant">Target (70-180)</span>
              </div>
            </div>
          )}
        </div>

        {/* AGP Trend Visualizer, Loading State, or Empty State */}
        {loading ? (
          <div className="h-72 flex flex-col items-center justify-center text-center p-space-xl bg-surface-container-low/30 rounded-lg border border-surface-container">
            <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin mb-3"></div>
            <div className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-1">
              Loading Longitudinal Telemetry...
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
              Synchronizing continuous CGM observations and modal percentiles.
            </p>
          </div>
        ) : hasAgpPoints ? (
          <div className="w-full overflow-x-auto">
            <div className="min-w-[760px] relative bg-surface-container-low/30 rounded-lg p-space-md border border-surface-container">
              <svg className="w-full h-72 overflow-visible select-none" preserveAspectRatio="none" viewBox="0 0 1000 360">
                <defs>
                  <linearGradient id="agpTargetGrad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#85f8c4" stopOpacity="0.18" />
                    <stop offset="100%" stopColor="#85f8c4" stopOpacity="0.08" />
                  </linearGradient>
                  <linearGradient id="agpRange90Grad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#006398" stopOpacity="0.10" />
                    <stop offset="100%" stopColor="#006398" stopOpacity="0.04" />
                  </linearGradient>
                  <linearGradient id="agpRange75Grad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#00685f" stopOpacity="0.22" />
                    <stop offset="100%" stopColor="#00685f" stopOpacity="0.12" />
                  </linearGradient>
                </defs>

                {/* Horizontal Reference Lines */}
                <line x1="45" y1="40" x2="980" y2="40" stroke="#bcc9c6" strokeDasharray="3 3" strokeWidth="0.75" opacity="0.6" />
                <text x="35" y="44" textAnchor="end" className="font-code-sm text-[10px] fill-outline">250</text>

                {/* Target 180 (Y: 120) */}
                <line x1="45" y1="120" x2="980" y2="120" stroke="#00855d" strokeDasharray="4 2" strokeWidth="1.2" opacity="0.7" />
                <text x="35" y="124" textAnchor="end" className="font-code-sm text-[10px] font-semibold fill-tertiary">180</text>

                {/* Target Safe Zone 70 - 180 */}
                <rect x="45" y="120" width="935" height="125" rx="2" fill="url(#agpTargetGrad)" />

                {/* Target 70 (Y: 245) */}
                <line x1="45" y1="245" x2="980" y2="245" stroke="#ba1a1a" strokeDasharray="4 2" strokeWidth="1.2" opacity="0.6" />
                <text x="35" y="249" textAnchor="end" className="font-code-sm text-[10px] font-semibold fill-error">70</text>

                {/* Baseline 40 (Y: 280) */}
                <line x1="45" y1="280" x2="980" y2="280" stroke="#bcc9c6" strokeWidth="0.75" opacity="0.4" />
                <text x="35" y="284" textAnchor="end" className="font-code-sm text-[10px] fill-outline">40</text>

                {/* Vertical Time Rules */}
                <line x1="50" y1="30" x2="50" y2="295" stroke="#dae2fd" strokeWidth="1" />
                <line x1="205" y1="30" x2="205" y2="295" stroke="#dae2fd" strokeDasharray="2 2" strokeWidth="1" />
                <line x1="360" y1="30" x2="360" y2="295" stroke="#dae2fd" strokeDasharray="2 2" strokeWidth="1" />
                <line x1="515" y1="30" x2="515" y2="295" stroke="#dae2fd" strokeDasharray="2 2" strokeWidth="1" />
                <line x1="670" y1="30" x2="670" y2="295" stroke="#dae2fd" strokeDasharray="2 2" strokeWidth="1" />
                <line x1="825" y1="30" x2="825" y2="295" stroke="#dae2fd" strokeDasharray="2 2" strokeWidth="1" />
                <line x1="980" y1="30" x2="980" y2="295" stroke="#dae2fd" strokeWidth="1" />

                {/* Dynamic Shaded Ribbon: 10th-90th Percentile */}
                {p10p90Path && <path d={p10p90Path} fill="url(#agpRange90Grad)" />}

                {/* Dynamic Shaded Ribbon: 25th-75th Interquartile */}
                {p25p75Path && <path d={p25p75Path} fill="url(#agpRange75Grad)" />}

                {/* Dynamic Median Trajectory Curve */}
                {medianPath && (
                  <path
                    d={medianPath}
                    fill="none"
                    stroke="#00685f"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                )}

                {/* Time Scale Labels */}
                <text x="50" y="320" textAnchor="start" className="font-code-sm text-[10px] fill-on-surface-variant font-medium">
                  00:00 (Midnight)
                </text>
                <text x="205" y="320" textAnchor="middle" className="font-code-sm text-[10px] fill-on-surface-variant font-medium">
                  04:00 (Dawn)
                </text>
                <text x="360" y="320" textAnchor="middle" className="font-code-sm text-[10px] fill-on-surface-variant font-medium">
                  08:00 (Breakfast)
                </text>
                <text x="515" y="320" textAnchor="middle" className="font-code-sm text-[10px] fill-on-surface-variant font-medium">
                  12:00 (Lunch)
                </text>
                <text x="670" y="320" textAnchor="middle" className="font-code-sm text-[10px] fill-on-surface-variant font-medium">
                  16:00 (Afternoon)
                </text>
                <text x="825" y="320" textAnchor="middle" className="font-code-sm text-[10px] fill-on-surface-variant font-medium">
                  20:00 (Dinner)
                </text>
                <text x="980" y="320" textAnchor="end" className="font-code-sm text-[10px] fill-on-surface-variant font-medium">
                  23:59
                </text>
              </svg>
            </div>
          </div>
        ) : (
          <div className="h-72 flex flex-col items-center justify-center text-center p-space-xl bg-surface-container-low/30 rounded-lg border border-surface-container">
            <Info className="w-8 h-8 text-outline mb-2" />
            <div className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-1">
              Insufficient longitudinal data for AGP
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
              At least 7+ days (or 70% sensor active time) of continuous CGM telemetry are required for modal AGP percentiles. Telemetry will automatically populate as readings are logged.
            </p>
            <div className="mt-3 font-code-sm text-code-sm text-outline">
              Current readings logged: {totalReadings}
            </div>
          </div>
        )}

        {/* Diagnostic Insight Bar */}
        {hasAgpPoints ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md mt-space-lg pt-space-md bg-surface-container-low/40 p-space-md rounded-lg border border-surface-container">
            <div className="flex items-start gap-space-sm">
              <Sparkles className="w-5 h-5 text-tertiary mt-0.5 shrink-0" />
              <div>
                <span className="font-label-md text-label-md text-on-surface font-semibold">
                  Morning Phase (00:00 – 08:00)
                </span>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
                  Overnight baseline trajectory verified through continuous sensor observations.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-space-sm">
              <Utensils className="w-5 h-5 text-primary mt-0.5 shrink-0" />
              <div>
                <span className="font-label-md text-label-md text-on-surface font-semibold">
                  Midday Ingestion (08:00 – 16:00)
                </span>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
                  Postprandial glycemic excursions tracked against logged nutrition events.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-space-sm">
              <Clock className="w-5 h-5 text-secondary mt-0.5 shrink-0" />
              <div>
                <span className="font-label-md text-label-md text-on-surface font-semibold">
                  Evening Equilibrium (16:00 – 24:00)
                </span>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
                  Post-dinner recovery trajectory monitored across the nocturnal transition window.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-space-lg p-space-md bg-surface-container-low/40 rounded-lg border border-surface-container text-center">
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Diagnostic insights require verified 7-day longitudinal data.
            </span>
          </div>
        )}
      </div>

      {/* Retrospective Clinical Interventions & Forecast Verification Table */}
      <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-surface-container overflow-hidden">
        <div className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface-container-lowest border-b border-surface-container">
          <div>
            <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
              Verified Interventions &amp; Forecast Performance Log
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              Historical log of recorded meals, insulin doses, and corresponding CGM responses.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 bg-surface-container-low p-1 rounded-lg border border-surface-container">
            {[
              { id: "all", label: "All Events" },
              { id: "meals", label: "Meals" },
              { id: "boluses", label: "Boluses" },
              { id: "forecasts", label: "Forecast Audits" },
              { id: "simulations", label: "What-If Simulations" }
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterType(f.id)}
                className={`px-space-sm py-1 font-label-sm text-label-sm rounded transition-colors ${
                  filterType === f.id
                    ? "bg-surface-container-lowest text-on-surface font-semibold shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Clinical Data Table */}
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider">
                <th className="py-2.5 px-space-lg font-semibold">Timestamp / Event</th>
                <th className="py-2.5 px-space-md font-semibold">Nutrition (CHO)</th>
                <th className="py-2.5 px-space-md font-semibold">Insulin Delivered</th>
                <th className="py-2.5 px-space-md font-semibold text-right">Predicted Peak</th>
                <th className="py-2.5 px-space-md font-semibold text-right">Actual CGM Peak</th>
                <th className="py-2.5 px-space-md font-semibold">Model Variance</th>
                <th className="py-2.5 px-space-lg font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container text-body-md font-body-md text-on-surface">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-on-surface-variant font-body-md">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                      <span>Loading longitudinal telemetry records...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-on-surface-variant font-body-md">
                    No verified events recorded for this timeframe
                  </td>
                </tr>
              ) : (
                filteredEvents.map((row) => {
                  const isExpanded = expandedRowId === row.id;
                  const hasDetails = Boolean(row.rawForecast || row.rawWhatIf);

                  return (
                    <React.Fragment key={row.id}>
                      <tr
                        onClick={() => hasDetails && setExpandedRowId(isExpanded ? null : row.id)}
                        className={`transition-colors ${
                          hasDetails ? "cursor-pointer hover:bg-surface-container-low/70" : "hover:bg-surface-container-low/50"
                        } ${isExpanded ? "bg-surface-container-low" : ""}`}
                      >
                        <td className="py-3 px-space-lg whitespace-nowrap">
                          <div className="flex items-center gap-space-sm">
                            {row.isSimulation ? (
                              <Sliders className="w-4 h-4 text-purple-400 shrink-0" />
                            ) : (
                              <CheckCircle className="w-4 h-4 text-tertiary shrink-0" />
                            )}
                            <div>
                              <div className="font-code-sm text-code-sm font-semibold text-on-surface flex items-center gap-1.5">
                                {row.timestamp}
                                {hasDetails && (
                                  <ChevronDown className={`w-3.5 h-3.5 text-primary transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                                )}
                              </div>
                              <div className="font-body-sm text-body-sm text-on-surface-variant">{row.event}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-space-md whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded font-code-sm text-code-sm font-semibold ${
                            row.isSimulation ? "bg-purple-900/30 text-purple-200 border border-purple-500/20" : "bg-surface-container text-on-surface"
                          }`}>
                            {row.nutrition}
                          </span>
                        </td>
                        <td className={`py-3 px-space-md whitespace-nowrap font-code-sm text-code-sm font-semibold ${
                          row.isSimulation ? "text-purple-300" : "text-secondary"
                        }`}>
                          {row.insulin}
                        </td>
                        <td className="py-3 px-space-md whitespace-nowrap text-right font-telemetry-metric text-on-surface">
                          {row.predictedPeak} {row.predictedPeak !== "—" && <span className="font-telemetry-unit text-outline">mg/dL</span>}
                        </td>
                        <td className="py-3 px-space-md whitespace-nowrap text-right font-telemetry-metric text-on-surface">
                          {row.actualPeak} {row.actualPeak !== "—" && <span className="font-telemetry-unit text-outline">mg/dL</span>}
                        </td>
                        <td className="py-3 px-space-md whitespace-nowrap">
                          {row.variance !== null ? (
                            <span
                              className={`px-2 py-0.5 rounded font-code-sm text-code-sm font-semibold ${
                                Math.abs(row.variance) <= 3
                                  ? "bg-tertiary-fixed text-on-tertiary-fixed"
                                  : "bg-surface-container text-on-surface"
                              }`}
                            >
                              {row.variance > 0 ? `+${row.variance}` : row.variance} mg/dL
                            </span>
                          ) : (
                            <span className="font-code-sm text-outline">—</span>
                          )}
                        </td>
                        <td className="py-3 px-space-lg whitespace-nowrap text-right">
                          {row.isSimulation ? (
                            <span className="px-2 py-0.5 rounded bg-purple-900/40 text-purple-200 border border-purple-500/30 font-label-sm text-label-sm font-semibold tracking-wide">
                              SIMULATION
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded bg-surface-container text-on-surface font-label-sm text-label-sm font-medium">
                              {row.status}
                            </span>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Forecast Performance & Audit Details */}
                      {isExpanded && row.rawForecast && (
                        <tr className="bg-surface-container-low/40">
                          <td colSpan={7} className="px-space-lg py-3">
                            <div className="p-3 rounded-lg bg-surface-container-lowest border border-surface-container space-y-2 text-xs font-mono">
                              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-container pb-2">
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-on-surface">Forecast Record ID:</span>
                                  <span className="text-primary font-bold">{row.rawForecast.id}</span>
                                </div>
                                <div className="text-on-surface-variant text-[11px]">
                                  ISO Timestamp: {row.rawForecast.timestamp || row.rawForecast.created_at}
                                </div>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 py-1 text-[11px]">
                                <div>
                                  <span className="text-on-surface-variant">Current State: </span>
                                  <span className="font-semibold text-on-surface">
                                    {row.rawForecast.current_glucose} mg/dL (IOB: {row.rawForecast.current_iob} U, COB: {row.rawForecast.current_cob} g)
                                  </span>
                                </div>
                                <div>
                                  <span className="text-on-surface-variant">Risk Assessment: </span>
                                  <span className="font-semibold text-primary">
                                    {row.rawForecast.risk_assessment?.primary_status} ({row.rawForecast.risk_assessment?.alert_level})
                                  </span>
                                </div>
                                <div>
                                  <span className="text-on-surface-variant">95% Uncertainty (t+15m): </span>
                                  <span className="font-semibold text-on-surface">
                                    {row.rawForecast.lower_95?.[0]} – {row.rawForecast.upper_95?.[0]} mg/dL
                                  </span>
                                </div>
                              </div>

                              <div className="text-[11px] border-t border-surface-container pt-1.5">
                                <span className="text-on-surface-variant">20-Step Point Forecast (mg/dL): </span>
                                <span className="text-on-surface">
                                  {Array.isArray(row.rawForecast.point_forecast) ? row.rawForecast.point_forecast.join(", ") : "—"}
                                </span>
                              </div>

                              {row.rawForecast.explanation?.headline && (
                                <div className="text-[11px] text-on-surface-variant pt-1">
                                  <span>Explanation: </span>
                                  <span className="text-on-surface font-sans font-medium">{row.rawForecast.explanation.headline}</span>
                                </div>
                              )}

                              {Array.isArray(row.rawForecast.risk_assessment?.active_alerts) && row.rawForecast.risk_assessment.active_alerts.length > 0 && (
                                <div className="text-[11px] text-amber-600 dark:text-amber-400 font-semibold pt-1">
                                  <span>Active Alerts: </span>
                                  <span>{row.rawForecast.risk_assessment.active_alerts.join("; ")}</span>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}

                      {/* Expandable What-If Simulation Details & Research Disclaimer */}
                      {isExpanded && row.rawWhatIf && (
                        <tr className="bg-surface-container-low/40">
                          <td colSpan={7} className="px-space-lg py-3">
                            <div className="p-3 rounded-lg bg-surface-container-lowest border border-purple-500/30 space-y-2 text-xs font-mono">
                              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-container pb-2">
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-purple-300">What-If Simulation Record ID:</span>
                                  <span className="text-purple-200 font-bold">{row.rawWhatIf.id}</span>
                                </div>
                                <div className="text-on-surface-variant text-[11px]">
                                  ISO Timestamp: {row.rawWhatIf.timestamp || row.rawWhatIf.created_at}
                                </div>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 py-1 text-[11px]">
                                <div>
                                  <span className="text-on-surface-variant">Scenario Name: </span>
                                  <span className="font-semibold text-on-surface">{row.rawWhatIf.scenario_name}</span>
                                </div>
                                <div>
                                  <span className="text-on-surface-variant">Simulated Meal: </span>
                                  <span className="font-semibold text-purple-300">
                                    {row.rawWhatIf.scenario_meal_carbs_g} g CHO
                                  </span>
                                </div>
                                <div>
                                  <span className="text-on-surface-variant">Simulated Bolus: </span>
                                  <span className="font-semibold text-secondary">
                                    {row.rawWhatIf.scenario_insulin_bolus_u} U
                                  </span>
                                </div>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 py-1 text-[11px] border-t border-surface-container pt-1.5">
                                <div>
                                  <span className="text-on-surface-variant">Projected Peak: </span>
                                  <span className="font-semibold text-on-surface">
                                    {row.rawWhatIf.peak_glucose} mg/dL (t+{row.rawWhatIf.time_to_peak_min}m)
                                  </span>
                                </div>
                                <div>
                                  <span className="text-on-surface-variant">Projected Nadir: </span>
                                  <span className="font-semibold text-on-surface">
                                    {row.rawWhatIf.nadir_glucose} mg/dL (t+{row.rawWhatIf.time_to_nadir_min}m)
                                  </span>
                                </div>
                                <div>
                                  <span className="text-on-surface-variant">Time in Range (70-180): </span>
                                  <span className="font-semibold text-tertiary">
                                    {row.rawWhatIf.time_in_range_pct}%
                                  </span>
                                </div>
                              </div>

                              <div className="text-[11px] border-t border-surface-container pt-1.5">
                                <span className="text-on-surface-variant">Simulated Trajectory (20 steps / 5 hours, mg/dL): </span>
                                <span className="text-on-surface">
                                  {Array.isArray(row.rawWhatIf.simulated_trajectory)
                                    ? row.rawWhatIf.simulated_trajectory.map((v) => Math.round(v)).join(", ")
                                    : "—"}
                                </span>
                              </div>

                              {/* Prominent Disclaimer */}
                              <div className="mt-2 p-2.5 rounded bg-purple-950/40 border border-purple-500/40 text-[11px] text-purple-200 font-sans leading-relaxed">
                                <div className="font-bold flex items-center gap-1.5 text-purple-300 mb-0.5">
                                  <span>🔬</span>
                                  <span>IN SILICO COUNTERFACTUAL SIMULATION ONLY</span>
                                </div>
                                <div>
                                  This record represents an in silico what-if simulation from the physiological digital twin and neural residual engine. It is NOT an actual clinical event, logged meal, or administered insulin injection. Do NOT interpret counterfactual simulations as real patient history or use them for medical dosing decisions.
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer */}
        <div className="p-space-md bg-surface-container-low/60 flex flex-col sm:flex-row items-center justify-between gap-space-sm border-t border-surface-container">
          <div className="flex items-center gap-space-xs text-on-surface-variant font-body-sm text-body-sm">
            <Activity className="w-4 h-4 text-primary" />
            <span>Showing {filteredEvents.length} logged event sequences from {verifiedEvents.length} total recorded interventions</span>
          </div>
          <div className="flex items-center gap-space-sm">
            <button
              onClick={() => {
                const csv = "timestamp,event,nutrition,insulin,predicted_peak,actual_peak,variance\n" +
                  filteredEvents.map(e => `"${e.timestamp}","${e.event}","${e.nutrition}","${e.insulin}",${e.predictedPeak},${e.actualPeak},${e.variance ?? ""}`).join("\n");
                const blob = new Blob([csv], { type: "text/csv" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "glucoshield_interventions.csv";
                a.click();
              }}
              className="px-space-md py-1 bg-surface-container-lowest hover:bg-surface-container text-on-surface font-label-sm text-label-sm rounded shadow-sm transition-colors border border-surface-container"
            >
              Export CSV
            </button>
            <button
              onClick={() => window.print()}
              className="px-space-md py-1 bg-primary text-on-primary font-label-sm text-label-sm rounded shadow-sm hover:opacity-95 transition-opacity"
            >
              Export Report (PDF)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
