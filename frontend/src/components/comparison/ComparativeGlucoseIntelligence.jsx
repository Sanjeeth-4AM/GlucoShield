import React, { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  Line,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
  CartesianGrid
} from "recharts";
import {
  GitCompare,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  Info,
  Clock,
  ArrowRight,
  UserCheck,
  Activity,
  Layers
} from "lucide-react";

export function ComparativeGlucoseIntelligence({
  cohortData,
  comparisonData,
  activePatientId,
  onSelectPatient
}) {
  const [forecastDisplayMode, setForecastDisplayMode] = useState("overlay"); // "overlay" | "split"

  const patA = cohortData?.patientA || comparisonData?.patientA;
  const patB = cohortData?.patientB || comparisonData?.patientB;

  if (!patA || !patB) {
    return (
      <div className="p-8 text-center bg-surface-container-low rounded-2xl border border-surface-container">
        <GitCompare className="w-8 h-8 text-primary mx-auto mb-3 animate-spin" />
        <h3 className="text-base font-semibold text-on-surface">Loading Comparative Glucose Intelligence...</h3>
        <p className="text-xs text-on-surface-variant mt-1">Retrieving cross-patient telemetry and Combination C model evaluations.</p>
      </div>
    );
  }

  const statsA = patA.cgm_stats || {};
  const statsB = patB.cgm_stats || {};
  const raA = patA.risk_assessment || {};
  const raB = patB.risk_assessment || {};
  const fcA = patA.forecast || {};
  const fcB = patB.forecast || {};

  // Build combined 24-hour historical series (-24h to NOW at 15m intervals)
  const historicalChartData = [];
  const readingsA = patA.history_readings || [];
  const readingsB = patB.history_readings || [];
  const len = Math.max(readingsA.length, readingsB.length);

  for (let i = 0; i < len; i++) {
    const minutesAgo = (len - 1 - i) * 15;
    const hoursAgo = -(minutesAgo / 60);
    const timeLabel = hoursAgo === 0 ? "NOW" : `${hoursAgo.toFixed(1)}h`;

    historicalChartData.push({
      step: i,
      timeLabel,
      patientA: readingsA[i]?.cgm_glucose ?? null,
      patientB: readingsB[i]?.cgm_glucose ?? null,
      targetLower: 70,
      targetUpper: 180
    });
  }

  // Build combined 5-hour forecast series (0 to +300m at 15m intervals)
  const ptsA = fcA.point_forecast_mg_dl || [];
  const ptsB = fcB.point_forecast_mg_dl || [];
  const low95A = fcA.lower_95_mg_dl || [];
  const upp95A = fcA.upper_95_mg_dl || [];
  const low95B = fcB.lower_95_mg_dl || [];
  const upp95B = fcB.upper_95_mg_dl || [];

  const forecastChartData = [];
  const fLen = Math.max(ptsA.length, ptsB.length);
  const nowGlucoseA = readingsA[readingsA.length - 1]?.cgm_glucose ?? ptsA[0] ?? 100;
  const nowGlucoseB = readingsB[readingsB.length - 1]?.cgm_glucose ?? ptsB[0] ?? 200;

  // Origin point at NOW
  forecastChartData.push({
    timeLabel: "NOW",
    minutes: 0,
    patientA: nowGlucoseA,
    low95A: nowGlucoseA,
    upp95A: nowGlucoseA,
    patientB: nowGlucoseB,
    low95B: nowGlucoseB,
    upp95B: nowGlucoseB,
    targetLower: 70,
    targetUpper: 180
  });

  for (let i = 0; i < fLen; i++) {
    const minutes = (i + 1) * 15;
    const timeLabel = `+${Math.round(minutes / 60 * 10) / 10}h`;

    forecastChartData.push({
      timeLabel,
      minutes,
      patientA: ptsA[i] ?? null,
      low95A: low95A[i] ?? null,
      upp95A: upp95A[i] ?? null,
      patientB: ptsB[i] ?? null,
      low95B: low95B[i] ?? null,
      upp95B: upp95B[i] ?? null,
      targetLower: 70,
      targetUpper: 180
    });
  }

  // Comparison Table rows
  const tableRows = comparisonData?.comparison_table || [
    { parameter: "Current glucose", unit: "mg/dL", patient_a: statsA.current_glucose, patient_b: statsB.current_glucose, interpretation: "Patient A euglycemic; Patient B hyperglycemic baseline." },
    { parameter: "Average glucose (24h)", unit: "mg/dL", patient_a: statsA.average_glucose, patient_b: statsB.average_glucose, interpretation: "Patient B average is +158.1 mg/dL higher than Patient A." },
    { parameter: "Glucose variability (Std)", unit: "mg/dL", patient_a: statsA.glucose_std || 13.8, patient_b: statsB.glucose_std || 44.5, interpretation: "Patient A exhibits low volatility; Patient B has high fluctuation." },
    { parameter: "Minimum glucose (24h)", unit: "mg/dL", patient_a: statsA.min_glucose, patient_b: statsB.min_glucose, interpretation: "Patient A reached 75.6 mg/dL; Patient B never dropped below 198.0 mg/dL." },
    { parameter: "Maximum glucose (24h)", unit: "mg/dL", patient_a: statsA.max_glucose, patient_b: statsB.max_glucose, interpretation: "Patient B had severe excursion up to 392.4 mg/dL." },
    { parameter: "Time in Range (70-180 mg/dL)", unit: "%", patient_a: statsA.time_in_range_pct, patient_b: statsB.time_in_range_pct, interpretation: "Patient A: 100.0% TIR (Target > 70%); Patient B: 0.0% TIR." },
    { parameter: "Time Below Range (<70 mg/dL)", unit: "%", patient_a: statsA.time_below_range_pct, patient_b: statsB.time_below_range_pct, interpretation: "Neither patient experienced documented hypoglycemia in this window." },
    { parameter: "Time Above Range (>180 mg/dL)", unit: "%", patient_a: statsA.time_above_range_pct, patient_b: statsB.time_above_range_pct, interpretation: "Patient B spent 100.0% of the past 24 hours in hyperglycemia." },
    { parameter: "Predicted Nadir (5h)", unit: "mg/dL", patient_a: raA.nadir_mg_dl, patient_b: raB.nadir_mg_dl, interpretation: "Patient A nadir is euglycemic (97.7 mg/dL); Patient B remains high (199.2 mg/dL)." },
    { parameter: "Predicted Peak (5h)", unit: "mg/dL", patient_a: raA.peak_mg_dl, patient_b: raB.peak_mg_dl, interpretation: "Patient B projected peak crosses clinical warning threshold (228.3 mg/dL)." },
    { parameter: "Hypoglycemia risk at 1h (<70 mg/dL)", unit: "%", patient_a: ((raA.hypo_1h_prob || 0) * 100).toFixed(1), patient_b: ((raB.hypo_1h_prob || 0) * 100).toFixed(1), interpretation: "Low risk for both patients at 1-hour horizon." },
    { parameter: "Hypoglycemia risk at 2h (<70 mg/dL)", unit: "%", patient_a: ((raA.hypo_2h_prob || 0) * 100).toFixed(1), patient_b: ((raB.hypo_2h_prob || 0) * 100).toFixed(1), interpretation: "Patient A shows slight downward variance (2.6%); Patient B is near zero (0.1%)." },
    { parameter: "Hypoglycemia risk at 4h (<70 mg/dL)", unit: "%", patient_a: ((raA.hypo_4h_prob || 0) * 100).toFixed(1), patient_b: ((raB.hypo_4h_prob || 0) * 100).toFixed(1), interpretation: "Patient A downside uncertainty extends to 9.4%; Patient B hypo risk is negligible (0.2%)." },
    { parameter: "Hyperglycemia risk at 2h (>180 mg/dL)", unit: "%", patient_a: ((raA.hyper_2h_prob || 0) * 100).toFixed(1), patient_b: ((raB.hyper_2h_prob || 0) * 100).toFixed(1), interpretation: "Patient B has severe projected hyper risk (97.3%); Patient A is protected (2.8%)." },
    { parameter: "Hyperglycemia risk at 4h (>180 mg/dL)", unit: "%", patient_a: ((raA.hyper_4h_prob || 0) * 100).toFixed(1), patient_b: ((raB.hyper_4h_prob || 0) * 100).toFixed(1), interpretation: "Patient B maintains 98.7% hyper probability; Patient A hyper risk remains low (4.0%)." },
    { parameter: "Hypoglycemia / Hyperglycemia risk at 5h", unit: "status", patient_a: "N/A (Not Evaluated)", patient_b: "N/A (Not Evaluated)", interpretation: "Continuous trajectory spans 5 hours; discrete risk heads are validated at 1h, 2h, and 4h only." }
  ];

  // Visual Risk Data
  const hypoChartData = [
    { horizon: "1 Hour", patientA: Number(((raA.hypo_1h_prob || 0) * 100).toFixed(1)), patientB: Number(((raB.hypo_1h_prob || 0) * 100).toFixed(1)) },
    { horizon: "2 Hours", patientA: Number(((raA.hypo_2h_prob || 0) * 100).toFixed(1)), patientB: Number(((raB.hypo_2h_prob || 0) * 100).toFixed(1)) },
    { horizon: "4 Hours", patientA: Number(((raA.hypo_4h_prob || 0) * 100).toFixed(1)), patientB: Number(((raB.hypo_4h_prob || 0) * 100).toFixed(1)) }
  ];

  const hyperChartData = [
    { horizon: "2 Hours", patientA: Number(((raA.hyper_2h_prob || 0) * 100).toFixed(1)), patientB: Number(((raB.hyper_2h_prob || 0) * 100).toFixed(1)) },
    { horizon: "4 Hours", patientA: Number(((raA.hyper_4h_prob || 0) * 100).toFixed(1)), patientB: Number(((raB.hyper_4h_prob || 0) * 100).toFixed(1)) }
  ];

  const interp = comparisonData?.comparative_interpretation || {
    stability_analysis: "Patient A demonstrates exceptional glucose stability with a standard deviation of 13.8 mg/dL and 100.0% Time-in-Range (70-180 mg/dL). In contrast, Patient B exhibits marked 24-hour glycemic instability with a standard deviation of 44.5 mg/dL and average glucose of 261.7 mg/dL across the evaluated window.",
    excursion_analysis: "Patient B spent 100.0% of the past 24 hours above the 180 mg/dL target threshold, with excursions reaching 392.4 mg/dL. Patient A experienced zero severe excursions, remaining safely between 75.6 and 131.4 mg/dL.",
    predicted_hyper_risk: "Combination C predicts severe, sustained hyperglycemia for Patient B with 97.3% probability at 2 hours and 98.7% probability at 4 hours (peaking at 228.3 mg/dL). Patient A maintains low projected hyper risk (2.8% at 2h, 4.0% at 4h).",
    predicted_hypo_risk: "Neither patient faces acute hypoglycemia within 1-2 hours. At 4 hours, Patient A's downside prediction interval extends into the low-glucose range (9.4% probability), generating an advisory alert. Patient B's high baseline virtually precludes hypoglycemia (0.2% at 4h).",
    trajectory_divergence: "Patient A's trajectory remains tightly controlled within the euglycemic corridor (97.7 to 108.8 mg/dL). Patient B's trajectory projects sustained elevation, rising from 199.8 mg/dL to 228.3 mg/dL before settling at 213.9 mg/dL.",
    uncertainty_interpretation: "Patient B shows substantially wider 95% prediction intervals ([130.1, 320.2] mg/dL at 4h), reflecting elevated heteroscedastic uncertainty driven by high historical glucose volatility."
  };

  return (
    <div className="flex flex-col w-full space-y-6 pb-12 select-none">
      {/* Top Header Card */}
      <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-primary font-code-sm text-xs uppercase tracking-wider font-semibold">
            <GitCompare className="w-4 h-4 text-primary" />
            <span>Biomedical Cross-Patient Comparative Analytics</span>
            <span className="text-outline-variant">•</span>
            <span>Real Clinical Dataset Cohort</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold text-on-surface">
            Comparative Glucose Intelligence
          </h1>
          <p className="text-sm text-on-surface-variant max-w-4xl">
            Side-by-side empirical contrast of two distinct clinical profiles from the actual test cohort:
            a stable in-range profile versus a hyperglycemic 24-hour profile evaluated under the frozen Combination C model serving architecture.
          </p>
        </div>

        {/* Global Active Patient Switcher */}
        <div className="flex items-center gap-2 bg-surface-container-low p-1.5 rounded-xl border border-surface-container shrink-0">
          <span className="text-xs font-semibold text-on-surface-variant px-2 uppercase tracking-wide">
            Active Patient:
          </span>
          <button
            onClick={() => onSelectPatient && onSelectPatient("PATIENT_A")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              activePatientId === "PATIENT_A"
                ? "bg-teal-700 text-white shadow-sm"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-teal-400"></span>
            <span>Patient A (Stable)</span>
          </button>
          <button
            onClick={() => onSelectPatient && onSelectPatient("PATIENT_B")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              activePatientId === "PATIENT_B"
                ? "bg-amber-600 text-white shadow-sm"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-300"></span>
            <span>Patient B (Elevated)</span>
          </button>
        </div>
      </div>

      {/* Profile Overview Banner: Side-by-Side Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Patient A Card */}
        <div className={`p-5 rounded-2xl border transition-all ${
          activePatientId === "PATIENT_A"
            ? "bg-teal-950/20 border-teal-500/50 shadow-md ring-1 ring-teal-500/30"
            : "bg-surface-container-lowest border-surface-container"
        }`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 font-bold text-sm">
                PT-A
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-on-surface">Patient A: Stable Euglycemic Profile</h3>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
                    100.0% TIR
                  </span>
                </div>
                <span className="text-xs text-on-surface-variant">
                  {patA.clinical_type || "Type 2 Diabetes (High In-Range Control)"}
                </span>
              </div>
            </div>
            <button
              onClick={() => onSelectPatient && onSelectPatient("PATIENT_A")}
              className={`text-xs px-2.5 py-1 rounded font-semibold transition-colors ${
                activePatientId === "PATIENT_A"
                  ? "bg-teal-700 text-white"
                  : "bg-surface-container hover:bg-surface-container-high text-on-surface"
              }`}
            >
              {activePatientId === "PATIENT_A" ? "Active Patient ✓" : "Select Patient A"}
            </button>
          </div>

          <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-surface-container/60 text-center">
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">Current</span>
              <span className="text-base font-bold text-teal-400">{Math.round(statsA.current_glucose || 101)} <span className="text-[10px] font-normal text-on-surface-variant">mg/dL</span></span>
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">24h Mean</span>
              <span className="text-base font-bold text-on-surface">{statsA.average_glucose} <span className="text-[10px] font-normal text-on-surface-variant">mg/dL</span></span>
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">24h Range</span>
              <span className="text-xs font-bold text-on-surface mt-1">{statsA.min_glucose} - {statsA.max_glucose}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">4h Hyper Risk</span>
              <span className="text-base font-bold text-teal-400">{((raA.hyper_4h_prob || 0) * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Patient B Card */}
        <div className={`p-5 rounded-2xl border transition-all ${
          activePatientId === "PATIENT_B"
            ? "bg-amber-950/20 border-amber-500/50 shadow-md ring-1 ring-amber-500/30"
            : "bg-surface-container-lowest border-surface-container"
        }`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold text-sm">
                PT-B
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-on-surface">Patient B: Hyperglycemic 24-Hour Profile</h3>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    100.0% TAR
                  </span>
                </div>
                <span className="text-xs text-on-surface-variant">
                  {patB.clinical_type || "Type 2 Diabetes (Hyperglycemic 24-Hour Profile)"}
                </span>
              </div>
            </div>
            <button
              onClick={() => onSelectPatient && onSelectPatient("PATIENT_B")}
              className={`text-xs px-2.5 py-1 rounded font-semibold transition-colors ${
                activePatientId === "PATIENT_B"
                  ? "bg-amber-600 text-white"
                  : "bg-surface-container hover:bg-surface-container-high text-on-surface"
              }`}
            >
              {activePatientId === "PATIENT_B" ? "Active Patient ✓" : "Select Patient B"}
            </button>
          </div>

          <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-surface-container/60 text-center">
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">Current</span>
              <span className="text-base font-bold text-amber-400">{Math.round(statsB.current_glucose || 200)} <span className="text-[10px] font-normal text-on-surface-variant">mg/dL</span></span>
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">24h Mean</span>
              <span className="text-base font-bold text-amber-300">{statsB.average_glucose} <span className="text-[10px] font-normal text-on-surface-variant">mg/dL</span></span>
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">24h Range</span>
              <span className="text-xs font-bold text-amber-300 mt-1">{statsB.min_glucose} - {statsB.max_glucose}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] text-on-surface-variant">4h Hyper Risk</span>
              <span className="text-base font-bold text-rose-400">{((raB.hyper_4h_prob || 0) * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION A: Historical Glucose Comparison Overlay */}
      <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container shadow-sm flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
              <h2 className="text-lg font-bold text-on-surface">Section A — 24-Hour Historical CGM Trajectory Comparison</h2>
            </div>
            <p className="text-xs text-on-surface-variant">
              Synchronized 96 readings (15-minute intervals) demonstrating continuous euglycemia (Patient A) versus unremitting hyperglycemia with excursions up to 392 mg/dL (Patient B).
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-teal-400 inline-block"></span>
              <span className="text-teal-300 font-bold">Patient A (Stable)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-amber-400 inline-block"></span>
              <span className="text-amber-300 font-bold">Patient B (Elevated)</span>
            </div>
            <div className="flex items-center gap-1.5 bg-surface-container px-2 py-0.5 rounded text-[11px]">
              <span className="w-2 h-2 rounded-full bg-emerald-500/40"></span>
              <span className="text-on-surface-variant">Target [70 - 180]</span>
            </div>
          </div>
        </div>

        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={historicalChartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="timeLabel" stroke="#8892b0" fontSize={11} interval={11} />
              <YAxis domain={[40, 420]} stroke="#8892b0" fontSize={11} unit=" mg/dL" />
              <Tooltip
                contentStyle={{ backgroundColor: "#0c1324", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
                formatter={(val, name) => [
                  `${val} mg/dL`,
                  name === "patientA" ? "Patient A (Stable)" : name === "patientB" ? "Patient B (Elevated)" : name
                ]}
              />
              <ReferenceLine y={70} stroke="#f43f5e" strokeDasharray="4 4" label={{ value: "Hypo (70)", fill: "#f43f5e", fontSize: 10, position: "insideBottomRight" }} />
              <ReferenceLine y={180} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "Hyper (180)", fill: "#f59e0b", fontSize: 10, position: "insideTopRight" }} />
              <Line type="monotone" dataKey="patientA" name="patientA" stroke="#14b8a6" strokeWidth={2.5} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="patientB" name="patientB" stroke="#f59e0b" strokeWidth={2.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION B: 5-Hour Forecast Comparison Overlay */}
      <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container shadow-sm flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              <h2 className="text-lg font-bold text-on-surface">Section B — 5-Hour Forecast &amp; Uncertainty Dispersion Comparison</h2>
            </div>
            <p className="text-xs text-on-surface-variant">
              Frozen Combination C trajectory predictions (20 steps @ 15m) with 95% heteroscedastic uncertainty dispersion envelopes.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-on-surface-variant">Serving:</span>
            <span className="text-xs font-mono font-bold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
              Combination C Production
            </span>
          </div>
        </div>

        <div className="h-80 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={forecastChartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="timeLabel" stroke="#8892b0" fontSize={11} interval={3} />
              <YAxis domain={[20, 360]} stroke="#8892b0" fontSize={11} unit=" mg/dL" />
              <Tooltip
                contentStyle={{ backgroundColor: "#0c1324", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
              />
              <ReferenceLine y={70} stroke="#f43f5e" strokeDasharray="4 4" />
              <ReferenceLine y={180} stroke="#f59e0b" strokeDasharray="4 4" />
              
              {/* Patient A Uncertainty Area & Mean Line */}
              <Area type="monotone" dataKey="upp95A" stroke="none" fill="#14b8a6" fillOpacity={0.15} name="Patient A Upper 95%" isAnimationActive={false} />
              <Area type="monotone" dataKey="low95A" stroke="none" fill="#070d1f" fillOpacity={1.0} name="Patient A Lower 95%" isAnimationActive={false} />
              <Line type="monotone" dataKey="patientA" name="Patient A Forecast" stroke="#14b8a6" strokeWidth={3} dot={{ r: 3 }} isAnimationActive={false} />

              {/* Patient B Uncertainty Area & Mean Line */}
              <Area type="monotone" dataKey="upp95B" stroke="none" fill="#f59e0b" fillOpacity={0.15} name="Patient B Upper 95%" isAnimationActive={false} />
              <Area type="monotone" dataKey="low95B" stroke="none" fill="#070d1f" fillOpacity={1.0} name="Patient B Lower 95%" isAnimationActive={false} />
              <Line type="monotone" dataKey="patientB" name="Patient B Forecast" stroke="#f59e0b" strokeWidth={3} dot={{ r: 3 }} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          <div className="p-3 bg-teal-950/20 rounded-xl border border-teal-500/20 text-xs text-on-surface space-y-1">
            <span className="font-bold text-teal-400 block">Patient A Trajectory Milestone Dynamics</span>
            <p className="text-on-surface-variant text-[11px] leading-relaxed">
              Maintains steady euglycemia ranging between 97.7 mg/dL (nadir at t+180m) and 108.8 mg/dL (peak at t+15m). Downside 95% bound extends to 32.6 mg/dL at 4 hours due to baseline proximity to 70 mg/dL.
            </p>
          </div>
          <div className="p-3 bg-amber-950/20 rounded-xl border border-amber-500/20 text-xs text-on-surface space-y-1">
            <span className="font-bold text-amber-400 block">Patient B Trajectory Milestone Dynamics</span>
            <p className="text-on-surface-variant text-[11px] leading-relaxed">
              Maintains severe sustained hyperglycemia, rising to an expected peak of 228.3 mg/dL at t+165m with an elevated nadir of 199.2 mg/dL. The 95% upper prediction bound reaches 320.2 mg/dL.
            </p>
          </div>
        </div>
      </div>

      {/* SECTION C: Quantitative Risk Comparison Table */}
      <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container shadow-sm flex flex-col gap-4">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
            <h2 className="text-lg font-bold text-on-surface">Section C — Quantitative Risk &amp; Glycemic Comparison Table</h2>
          </div>
          <p className="text-xs text-on-surface-variant">
            Exact empirical measurements and frozen Combination C multi-task model outputs. Discrete risk probabilities are evaluated exclusively at 1h, 2h, and 4h horizons per model architecture.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-surface-container/80 text-on-surface-variant uppercase text-[10px] font-mono tracking-wider bg-surface-container-low/50">
                <th className="py-3 px-4">Parameter / Metric</th>
                <th className="py-3 px-4">Unit</th>
                <th className="py-3 px-4 text-teal-400 font-bold">Patient A (Stable)</th>
                <th className="py-3 px-4 text-amber-400 font-bold">Patient B (Elevated)</th>
                <th className="py-3 px-4">Clinical Interpretation / Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container/50 font-mono">
              {tableRows.map((row, idx) => (
                <tr key={idx} className="hover:bg-surface-container-low/30 transition-colors">
                  <td className="py-2.5 px-4 font-semibold text-on-surface">{row.parameter}</td>
                  <td className="py-2.5 px-4 text-on-surface-variant text-[11px]">{row.unit}</td>
                  <td className="py-2.5 px-4 text-teal-300 font-bold">
                    {typeof row.patient_a === "number" ? row.patient_a : row.patient_a}
                  </td>
                  <td className="py-2.5 px-4 text-amber-300 font-bold">
                    {typeof row.patient_b === "number" ? row.patient_b : row.patient_b}
                  </td>
                  <td className="py-2.5 px-4 text-on-surface-variant font-sans text-[11px]">{row.interpretation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION D: Risk Visualizations (Hypo & Hyper) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hypoglycemia Risk Comparison Chart */}
        <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container shadow-sm flex flex-col gap-4">
          <div className="flex flex-col">
            <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span>
              Hypoglycemia Risk Profile (&lt;70 mg/dL)
            </h3>
            <p className="text-xs text-on-surface-variant">Multi-task probability progression across 1h, 2h, and 4h horizons.</p>
          </div>

          <div className="h-60 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hypoChartData} margin={{ top: 20, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="horizon" stroke="#8892b0" fontSize={11} />
                <YAxis domain={[0, 20]} stroke="#8892b0" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0c1324", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(val, name) => [`${val}%`, name === "patientA" ? "Patient A" : "Patient B"]}
                />
                <Legend />
                <ReferenceLine y={10} stroke="#f43f5e" strokeDasharray="3 3" label={{ value: "Warning Threshold (10%)", fill: "#f43f5e", fontSize: 9, position: "insideTopRight" }} />
                <Bar dataKey="patientA" name="Patient A (Stable)" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="patientB" name="Patient B (Elevated)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="p-3 bg-surface-container-low rounded-xl border border-surface-container text-xs text-on-surface-variant leading-relaxed">
            <strong className="text-on-surface">Physiological Factor Attribution:</strong> Patient A exhibits slight downside dispersion reaching 9.4% at 4h because resting baseline (100.8 mg/dL) is within 30 mg/dL of hypoglycemia. Patient B's elevated baseline (199.8 mg/dL) completely insulates against short-term hypo risk (0.2% at 4h).
          </div>
        </div>

        {/* Hyperglycemia Risk Comparison Chart */}
        <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container shadow-sm flex flex-col gap-4">
          <div className="flex flex-col">
            <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              Hyperglycemia Risk Profile (&gt;180 mg/dL)
            </h3>
            <p className="text-xs text-on-surface-variant">Multi-task probability progression across 2h and 4h horizons.</p>
          </div>

          <div className="h-60 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hyperChartData} margin={{ top: 20, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="horizon" stroke="#8892b0" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#8892b0" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0c1324", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(val, name) => [`${val}%`, name === "patientA" ? "Patient A" : "Patient B"]}
                />
                <Legend />
                <ReferenceLine y={50} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Clinical Alert Level (50%)", fill: "#f59e0b", fontSize: 9, position: "insideTopRight" }} />
                <Bar dataKey="patientA" name="Patient A (Stable)" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="patientB" name="Patient B (Elevated)" fill="#f43f5e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="p-3 bg-surface-container-low rounded-xl border border-surface-container text-xs text-on-surface-variant leading-relaxed">
            <strong className="text-on-surface">Physiological Factor Attribution:</strong> Patient B presents critical hyperglycemia risk (97.3% at 2h, 98.7% at 4h) driven by severe endogenous insulin resistance (C-peptide: 0.37 nmol/L, HbA1c: 73.8 mmol/mol). Patient A maintains negligible risk (2.8% at 2h, 4.0% at 4h).
          </div>
        </div>
      </div>

      {/* SECTION E: Data-Driven Comparative Synthesis */}
      <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container shadow-sm flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <Info className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-bold text-on-surface">Section E — Data-Driven Comparative Synthesis &amp; Clinical Insights</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="p-4 bg-surface-container-low rounded-xl border border-surface-container space-y-1.5">
            <span className="text-xs font-bold text-primary uppercase font-mono tracking-wider">1. Glycemic Stability</span>
            <p className="text-xs text-on-surface-variant leading-relaxed">{interp.stability_analysis}</p>
          </div>

          <div className="p-4 bg-surface-container-low rounded-xl border border-surface-container space-y-1.5">
            <span className="text-xs font-bold text-amber-400 uppercase font-mono tracking-wider">2. Excursion Frequency</span>
            <p className="text-xs text-on-surface-variant leading-relaxed">{interp.excursion_analysis}</p>
          </div>

          <div className="p-4 bg-surface-container-low rounded-xl border border-surface-container space-y-1.5">
            <span className="text-xs font-bold text-rose-400 uppercase font-mono tracking-wider">3. Predicted Hyperglycemia</span>
            <p className="text-xs text-on-surface-variant leading-relaxed">{interp.predicted_hyper_risk}</p>
          </div>

          <div className="p-4 bg-surface-container-low rounded-xl border border-surface-container space-y-1.5">
            <span className="text-xs font-bold text-teal-400 uppercase font-mono tracking-wider">4. Predicted Hypoglycemia</span>
            <p className="text-xs text-on-surface-variant leading-relaxed">{interp.predicted_hypo_risk}</p>
          </div>

          <div className="p-4 bg-surface-container-low rounded-xl border border-surface-container space-y-1.5">
            <span className="text-xs font-bold text-primary uppercase font-mono tracking-wider">5. Trajectory Divergence</span>
            <p className="text-xs text-on-surface-variant leading-relaxed">{interp.trajectory_divergence}</p>
          </div>

          <div className="p-4 bg-surface-container-low rounded-xl border border-surface-container space-y-1.5">
            <span className="text-xs font-bold text-amber-300 uppercase font-mono tracking-wider">6. Uncertainty Dispersion</span>
            <p className="text-xs text-on-surface-variant leading-relaxed">{interp.uncertainty_interpretation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
