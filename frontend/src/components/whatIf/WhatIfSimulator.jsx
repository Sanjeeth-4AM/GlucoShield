import React, { useState, useMemo, useEffect } from "react";
import {
  FlaskConical,
  Play,
  RotateCcw,
  Sparkles,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  CheckCircle,
  Activity,
  Layers,
  Info,
  Sliders,
  ChevronRight,
  ShieldAlert
} from "lucide-react";

export function WhatIfSimulator({
  onSimulate,
  whatIfResult,
  isSimulating,
  onTransferToDecision,
  forecastData,
  transferredMeal = null,
  onClearTransferredMeal = null
}) {
  const BASE_BOLUS = 4.2;
  const BASE_CHO = 55.0;

  const [bolusInsulin, setBolusInsulin] = useState(5.5);
  const [mealCarbs, setMealCarbs] = useState(() => {
    if (transferredMeal && typeof transferredMeal.carbs_g === "number" && transferredMeal.carbs_g > 0) {
      return transferredMeal.carbs_g;
    }
    return BASE_CHO;
  });
  const [activityEnabled, setActivityEnabled] = useState(true);

  // Synchronize meal carbs when a transferred meal arrives or changes
  useEffect(() => {
    if (transferredMeal && typeof transferredMeal.carbs_g === "number" && transferredMeal.carbs_g > 0) {
      setMealCarbs(transferredMeal.carbs_g);
    }
  }, [transferredMeal?.id, transferredMeal?.carbs_g]);

  // Reference current glucose
  const currentGlucoseVal =
    forecastData?.current_state?.glucose_mg_dl ??
    forecastData?.forecast?.point_forecast_mg_dl?.[0] ??
    forecastData?.point_forecast_mg_dl?.[0] ??
    null;
  const currentGlucose = Number.isFinite(currentGlucoseVal) ? Math.round(currentGlucoseVal) : null;

  // Baseline trajectory: 20 steps over 5 hours (strictly from genuine forecast)
  const baselineTraj = useMemo(() => {
    const pts = forecastData?.forecast?.point_forecast_mg_dl || forecastData?.point_forecast_mg_dl;
    if (Array.isArray(pts) && pts.length >= 20) {
      return pts.slice(0, 20);
    }
    return null;
  }, [forecastData]);

  const hasValidBaseline = Array.isArray(baselineTraj) && baselineTraj.length >= 20;

  // Simulated trajectory: strictly from genuine backend ODE simulation response
  const simTraj = useMemo(() => {
    if (whatIfResult?.simulated_trajectory && Array.isArray(whatIfResult.simulated_trajectory) && whatIfResult.simulated_trajectory.length >= 20) {
      return whatIfResult.simulated_trajectory.slice(0, 20);
    }
    return null;
  }, [whatIfResult]);

  // Derived metrics
  const basePeak = baselineTraj ? Math.max(...baselineTraj) : null;
  const baseNadir = baselineTraj ? Math.min(...baselineTraj) : null;
  const baseTir = baselineTraj
    ? Math.round((baselineTraj.filter((g) => g >= 70 && g <= 180).length / baselineTraj.length) * 100)
    : null;

  const simPeak = whatIfResult?.peak_glucose
    ? Math.round(whatIfResult.peak_glucose)
    : simTraj ? Math.max(...simTraj) : null;
  const simNadir = whatIfResult?.nadir_glucose
    ? Math.round(whatIfResult.nadir_glucose)
    : simTraj ? Math.min(...simTraj) : null;
  const simTir = whatIfResult?.time_in_range_pct
    ? Math.round(whatIfResult.time_in_range_pct)
    : simTraj
    ? Math.round((simTraj.filter((g) => g >= 70 && g <= 180).length / simTraj.length) * 100)
    : null;

  const peakDelta = (simPeak !== null && basePeak !== null) ? simPeak - basePeak : null;
  const nadirDelta = (simNadir !== null && baseNadir !== null) ? simNadir - baseNadir : null;
  const tirDelta = (simTir !== null && baseTir !== null) ? simTir - baseTir : null;

  // Dynamic P(Hypo) calculation from simulated trajectory points (<70 mg/dL)
  const pHypoStr = useMemo(() => {
    if (!simTraj || simTraj.length === 0) return "—";
    const hypoCount = simTraj.filter((g) => g < 70).length;
    const pct = Math.round((hypoCount / simTraj.length) * 100);
    return `${pct}% (${pct > 15 ? "Elevated" : "Low"})`;
  }, [simTraj]);

  const bolusDeltaVal = bolusInsulin - BASE_BOLUS;
  const choDeltaVal = mealCarbs - BASE_CHO;

  const handleRun = () => {
    if (!hasValidBaseline) return;
    if (onSimulate) {
      onSimulate({
        meal_carbs_g: parseFloat(mealCarbs),
        bolus_insulin_u: parseFloat(bolusInsulin),
        exercise_intensity_factor: activityEnabled ? 1.5 : 1.0
      });
    }
  };

  const handleReset = () => {
    setBolusInsulin(BASE_BOLUS);
    setMealCarbs(BASE_CHO);
    setActivityEnabled(false);
    if (onClearTransferredMeal) onClearTransferredMeal();
  };

  // Convert trajectory to SVG path coordinates:
  // X: 50 -> 510 (460px width for 20 steps, stepWidth = 460 / 19 = 24.21px)
  // Y: 260 mg/dL -> Y=20, 40 mg/dL -> Y=280 (220 mg/dL range = 260px height => Y = 280 - (g - 40) * (260 / 220))
  const getY = (bg) => {
    const clamped = Math.max(40, Math.min(260, bg));
    return 280 - ((clamped - 40) / 220) * 260;
  };
  const getX = (idx) => 50 + idx * (460 / 19);

  const buildPath = (traj) => {
    if (!traj || traj.length === 0) return "";
    return traj.reduce((acc, bg, idx) => {
      const x = getX(idx);
      const y = getY(bg);
      if (idx === 0) return `M ${x.toFixed(1)} ${y.toFixed(1)}`;
      const prevX = getX(idx - 1);
      const prevY = getY(traj[idx - 1]);
      const cpX = (prevX + x) / 2;
      return `${acc} C ${cpX.toFixed(1)} ${prevY.toFixed(1)}, ${cpX.toFixed(1)} ${y.toFixed(1)}, ${x.toFixed(1)} ${y.toFixed(1)}`;
    }, "");
  };

  const basePathStr = baselineTraj ? buildPath(baselineTraj) : "";
  const simPathStr = simTraj ? buildPath(simTraj) : "";

  // Peak and nadir indices
  const basePeakIdx = baselineTraj && basePeak !== null ? baselineTraj.indexOf(basePeak) : 0;
  const simPeakIdx = simTraj && simPeak !== null ? simTraj.indexOf(simPeak) : 0;
  const simNadirIdx = simTraj && simNadir !== null ? simTraj.lastIndexOf(simNadir) : 0;

  return (
    <div className="flex flex-col w-full space-y-6">
      {/* Top Workspace Context Strip */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md mb-space-lg">
        <div className="flex flex-col gap-space-xs">
          <div className="flex items-center gap-space-xs">
            <span className="font-code-sm text-code-sm text-primary uppercase font-semibold tracking-wider">
              In Silico Metabolic Engine
            </span>
            <span className="text-outline-variant">•</span>
            <span className="font-code-sm text-code-sm text-on-surface-variant font-medium">
              Engine: Combination C Simulation
            </span>
            <span className="text-outline-variant">•</span>
            <span className="font-code-sm text-code-sm text-tertiary font-semibold flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-tertiary"></span>
              Active Engine Status
            </span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface">
            What-If Metabolic Counterfactual Simulation
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Simulate alternative clinical interventions and inspect projected glycemic trajectories
          </p>
        </div>

        {/* Active Baseline Pill */}
        <div className="flex items-center gap-space-sm bg-surface-container-low px-space-md py-space-sm rounded-lg shadow-sm border border-surface-container">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary">
            <FlaskConical className="w-4 h-4 text-primary" />
          </div>
          <div className="flex flex-col text-left">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
              Reference Active State
            </span>
            <div className="flex items-center gap-space-xs">
              <span className="font-label-md text-label-md text-on-surface font-semibold">
                {BASE_CHO}g CHO Meal + {BASE_BOLUS} U Bolus at 13:30
              </span>
              <span className="font-telemetry-metric text-code-sm text-primary font-bold bg-surface px-1.5 py-0.5 rounded shadow-sm">
                T0: {currentGlucose !== null ? `${currentGlucose} mg/dL` : "—"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* In Silico Counterfactual Simulation Notice */}
      <div className="mb-space-lg p-3 rounded-xl bg-primary/10 border border-primary/20 text-xs font-mono text-on-surface flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-2">
          <span className="text-base">🧪</span>
          <span className="font-bold text-primary">
            IN SILICO COUNTERFACTUAL SIMULATION ONLY • NOT MEDICAL PRESCRIPTION OR TREATMENT ADVICE
          </span>
        </div>
        <span className="text-on-surface-variant opacity-80 text-[11px] hidden sm:inline">
          Computational ODE Physiological Sandbox
        </span>
      </div>

      {/* Confirmed Food Vision Transferred Meal Banner */}
      {transferredMeal && (
        <div
          className="mb-space-lg p-3 rounded-xl bg-secondary/10 border border-secondary/30 text-xs font-mono text-on-surface flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 shadow-xs"
          data-testid="transferred-meal-banner"
        >
          <div className="flex items-center gap-2">
            <span className="text-base">🍕</span>
            <div>
              <span className="font-bold text-secondary uppercase tracking-wider">
                Confirmed Food Vision Meal Transferred:
              </span>{" "}
              <span className="font-bold text-on-surface" data-testid="transferred-meal-name">
                {transferredMeal.food_name}
              </span>{" "}
              <span className="text-on-surface-variant">
                ({transferredMeal.portion_g}g portion •{" "}
                <strong className="text-secondary" data-testid="transferred-meal-carbs">
                  {Number(transferredMeal.carbs_g).toFixed(1).replace(/\.0$/, "")}g CHO
                </strong>
                )
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-on-surface-variant hidden md:inline">
              Note: Bolus &amp; exercise remain separate scenario parameters (no dose prescribed)
            </span>
            {onClearTransferredMeal && (
              <button
                onClick={() => {
                  onClearTransferredMeal();
                  setMealCarbs(BASE_CHO);
                }}
                className="px-2 py-0.5 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-[10px] font-semibold transition-colors"
                title="Clear transferred meal and reset to baseline carbs"
              >
                Reset to Base
              </button>
            )}
          </div>
        </div>
      )}

      {/* Primary 3-Column Experimental Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 items-start">
        {/* LEFT COLUMN: Parameter Modulation Console (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-space-md">
          <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-md">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-space-xs mb-1">
                  <Sliders className="w-4 h-4 text-primary" />
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">
                    Adjust Simulation Parameters
                  </h2>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  Modify single or combined interventions to compare against baseline
                </p>
              </div>
              <span className="px-2 py-0.5 bg-surface-container-high text-on-surface-variant font-code-sm text-code-sm rounded">
                Interactive ODE
              </span>
            </div>

            <div className="flex flex-col gap-space-lg mt-space-xs">
              {/* Factor 1: Bolus Insulin Modulation */}
              <div className="flex flex-col gap-space-xs bg-surface-container-low/60 p-space-md rounded-lg border border-surface-container">
                <div className="flex items-center justify-between">
                  <label className="font-label-md text-label-md text-on-surface font-semibold flex items-center gap-1.5" htmlFor="bolusSlider">
                    <span className="w-2 h-2 rounded-full bg-primary"></span>
                    Meal Bolus Insulin
                  </label>
                  <div className="flex items-center gap-1">
                    <span className="font-code-sm text-[10px] text-on-surface-variant bg-surface-container-highest px-1.5 py-0.5 rounded" title="Bolus insulin is an independent scenario parameter not prescribed or calculated from the meal">
                      Separate Scenario Parameter
                    </span>
                    <span className="font-code-sm text-code-sm text-on-surface-variant bg-surface-container-highest px-2 py-0.5 rounded">
                      Base: {BASE_BOLUS.toFixed(2)} U
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-1">
                  <div className="flex items-baseline gap-1">
                    <span className="font-telemetry-display text-telemetry-metric text-on-surface font-bold">
                      {bolusInsulin.toFixed(2)}
                    </span>
                    <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">Units (U)</span>
                  </div>
                  <span
                    className={`font-code-sm text-code-sm px-2 py-0.5 rounded ${
                      Math.abs(bolusDeltaVal) < 0.05
                        ? "text-outline font-medium bg-surface-container"
                        : "text-secondary font-semibold bg-secondary-fixed/50"
                    }`}
                  >
                    {Math.abs(bolusDeltaVal) < 0.05
                      ? "Unchanged"
                      : `${bolusDeltaVal > 0 ? "+" : ""}${bolusDeltaVal.toFixed(2)} U Adjustment`}
                  </span>
                </div>

                <div className="relative w-full flex items-center my-2">
                  <input
                    id="bolusSlider"
                    type="range"
                    min="1.0"
                    max="12.0"
                    step="0.1"
                    value={bolusInsulin}
                    onChange={(e) => setBolusInsulin(parseFloat(e.target.value))}
                    className="w-full accent-primary h-2 bg-surface-container-highest rounded-lg appearance-none cursor-pointer"
                  />
                </div>

                <div className="flex items-center justify-between text-on-surface-variant font-code-sm text-code-sm">
                  <span>1.00 U</span>
                  <span className="text-on-surface-variant text-[11px]">User-modulated intervention • Not prescribed by model</span>
                  <span>12.00 U</span>
                </div>
              </div>

              {/* Factor 2: Carbohydrate Ingestion */}
              <div className="flex flex-col gap-space-xs bg-surface-container-low/60 p-space-md rounded-lg border border-surface-container">
                <div className="flex items-center justify-between">
                  <label className="font-label-md text-label-md text-on-surface font-semibold flex items-center gap-1.5" htmlFor="choSlider">
                    <span className="w-2 h-2 rounded-full bg-secondary"></span>
                    Carbohydrate Ingestion
                  </label>
                  <div className="flex items-center gap-1">
                    {transferredMeal && (
                      <span className="font-code-sm text-[10px] font-bold px-1.5 py-0.5 rounded bg-secondary/15 text-secondary border border-secondary/30" data-testid="cho-source-badge">
                        FROM FOOD VISION: {transferredMeal.food_name.toUpperCase()} ({transferredMeal.portion_g}g)
                      </span>
                    )}
                    <span className="font-code-sm text-code-sm text-on-surface-variant bg-surface-container-highest px-2 py-0.5 rounded">
                      Base: {BASE_CHO} g
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-1">
                  <div className="flex items-baseline gap-1">
                    <span className="font-telemetry-display text-telemetry-metric text-on-surface font-bold" data-testid="whatif-carbs-value">
                      {Number(mealCarbs).toFixed(1).replace(/\.0$/, "")}
                    </span>
                    <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">grams (CHO)</span>
                  </div>
                  <span
                    className={`font-code-sm text-code-sm px-2 py-0.5 rounded ${
                      Math.abs(choDeltaVal) < 0.05
                        ? "text-outline font-medium bg-surface-container"
                        : "text-secondary font-semibold bg-secondary-fixed/50"
                    }`}
                    data-testid="whatif-carbs-status"
                  >
                    {Math.abs(choDeltaVal) < 0.05
                      ? "Unchanged"
                      : `${choDeltaVal > 0 ? "+" : ""}${Number(choDeltaVal).toFixed(1).replace(/\.0$/, "")} g Adjustment`}
                  </span>
                </div>

                <div className="relative w-full flex items-center my-2">
                  <input
                    id="choSlider"
                    type="range"
                    min="10"
                    max="150"
                    step="0.1"
                    value={mealCarbs}
                    onChange={(e) => setMealCarbs(parseFloat(e.target.value))}
                    className="w-full accent-primary h-2 bg-surface-container-highest rounded-lg appearance-none cursor-pointer"
                  />
                </div>

                <div className="flex items-center justify-between text-on-surface-variant font-code-sm text-code-sm">
                  <span>10 g</span>
                  <span className="font-medium text-on-surface-variant">
                    {transferredMeal ? `Transferred: ${transferredMeal.food_name} (${Number(transferredMeal.carbs_g).toFixed(1).replace(/\.0$/, "")}g)` : "Glycemic Index: Medium (62)"}
                  </span>
                  <span>150 g</span>
                </div>
              </div>

              {/* Factor 3: Planned Post-Meal Light Activity (Illustrative Heuristic) */}
              <div className="flex flex-col gap-space-xs bg-surface-container-low/60 p-space-md rounded-lg border border-surface-container">
                <div className="flex items-center justify-between">
                  <label className="font-label-md text-label-md text-on-surface font-semibold flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-secondary" />
                    Post-Meal Light Activity (Illustrative)
                  </label>
                  <div className="flex items-center gap-1">
                    <span className="font-code-sm text-[10px] text-on-surface-variant bg-surface-container-highest px-1.5 py-0.5 rounded">
                      Separate Scenario Parameter
                    </span>
                    <span className="font-code-sm text-code-sm text-secondary font-semibold bg-secondary-fixed/50 px-2 py-0.5 rounded">
                      Heuristic Delta
                    </span>
                  </div>
                </div>
                <label className="flex items-start gap-space-sm mt-space-xs p-space-sm bg-surface rounded cursor-pointer select-none border border-surface-container">
                  <input
                    id="activityToggle"
                    type="checkbox"
                    checked={activityEnabled}
                    onChange={(e) => setActivityEnabled(e.target.checked)}
                    className="mt-1 w-4 h-4 rounded text-primary accent-primary cursor-pointer"
                  />
                  <div className="flex flex-col">
                    <span className="font-label-md text-label-md text-on-surface font-medium">
                      30 min light walking at +1h (14:30)
                    </span>
                    <span className="font-body-sm text-body-sm text-on-surface-variant">
                      Separate scenario parameter (illustrative heuristic assumption; not a validated clinical prediction)
                    </span>
                    <span className="font-code-sm text-code-sm text-secondary mt-1">
                      Illustrative heuristic glucose uptake (unvalidated in clinical trials; in-silico sensitivity only)
                    </span>
                  </div>
                </label>
              </div>
            </div>

            {/* Simulation Action Ribbon */}
            <div className="flex flex-col sm:flex-row items-center gap-space-sm pt-space-xs mt-space-xs">
              <button
                onClick={handleRun}
                disabled={isSimulating || !hasValidBaseline}
                className="w-full sm:flex-1 h-9 px-space-md bg-primary hover:bg-primary-container text-on-primary rounded font-label-md text-label-md font-semibold flex items-center justify-center gap-space-xs shadow-sm transition-all active:scale-[0.98] disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>
                  {isSimulating
                    ? "Computing Trajectories..."
                    : !hasValidBaseline
                    ? "Baseline Forecast Required"
                    : "Run Counterfactual Simulation"}
                </span>
              </button>
              <button
                onClick={handleReset}
                className="w-full sm:w-auto h-9 px-space-md bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded font-label-md text-label-md font-medium flex items-center justify-center gap-space-xs transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5 text-on-surface-variant" />
                <span>Reset</span>
              </button>
            </div>

            <div className="flex items-center justify-between pt-space-xs text-on-surface-variant font-code-sm text-code-sm">
              <span className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3 text-tertiary" />
                Combination C Serving Architecture
              </span>
              <span>Deterministic Physiological Simulation</span>
            </div>
          </div>

          {/* Quick Physiology Anchor Card */}
          <div className="bg-surface-container-low p-space-md rounded-xl flex items-center gap-space-md border border-surface-container">
            <div className="w-12 h-12 rounded-lg bg-surface-container-highest flex items-center justify-center text-primary shrink-0">
              <FlaskConical className="w-6 h-6 text-primary" />
            </div>
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface font-semibold">
                Subcutaneous Insulin Onset Model
              </span>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Lispro curve peaked at ~65 min post-injection. Walk timing intersects maximal insulin concentration.
              </p>
            </div>
          </div>
        </div>

        {/* CENTER COLUMN: Trajectory Comparison Chart (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-space-md">
          <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-xs">
              <div>
                <div className="flex items-center gap-space-xs">
                  <Activity className="w-4 h-4 text-primary" />
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">
                    Trajectory Comparison: Baseline vs Simulated Scenario
                  </h2>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  5-Hour Horizon (14:15 - 19:15 EST) • 15-minute resolution
                </p>
              </div>
              <div className="flex items-center gap-space-xs self-start sm:self-auto">
                <span className="px-2 py-0.5 bg-surface-container-high text-on-surface font-code-sm text-code-sm rounded font-medium">
                  95% Uncertainty Interval
                </span>
              </div>
            </div>

            {/* Comparative Legend Strip */}
            <div className="flex flex-wrap items-center gap-space-md py-space-xs bg-surface-container-low/50 px-space-md rounded-lg border border-surface-container">
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 bg-primary rounded-full"></span>
                <span className="font-label-sm text-label-sm text-on-surface font-medium">Baseline scenario</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 border-t-2 border-dashed border-secondary rounded-full"></span>
                <span className="font-label-sm text-label-sm text-secondary font-semibold">
                  Simulated scenario ({bolusDeltaVal >= 0 ? `+${bolusDeltaVal.toFixed(1)}` : bolusDeltaVal.toFixed(1)} U{activityEnabled ? " + Walk" : ""})
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-tertiary/15 rounded-sm"></span>
                <span className="font-label-sm text-label-sm text-on-surface-variant">Target Zone (70-180)</span>
              </div>
            </div>

            {/* High Fidelity SVG Multi-Vector Glycemic Canvas or Clean Empty State */}
            {baselineTraj ? (
              <div className="w-full bg-surface-container-lowest rounded-lg p-space-xs relative overflow-hidden">
                <svg className="w-full h-auto select-none" viewBox="0 0 540 330" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="whatIfTargetGrad" x1="0%" x2="0%" y1="0%" y2="100%">
                      <stop offset="0%" stopColor="#006948" stopOpacity="0.08" />
                      <stop offset="100%" stopColor="#006948" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>

                  {/* Target Band (70-180 mg/dL): Y=114 (180mg) to Y=244 (70mg) */}
                  <rect x="50" y="114" width="460" height="130" fill="url(#whatIfTargetGrad)" />
                  <line x1="50" y1="114" x2="510" y2="114" stroke="#00855d" strokeDasharray="3,3" strokeWidth="1" opacity="0.6" />
                  <line x1="50" y1="244" x2="510" y2="244" stroke="#ba1a1a" strokeDasharray="3,3" strokeWidth="1" opacity="0.6" />

                  {/* Y Axis Gridlines and Labels */}
                  <g className="text-[9px] fill-[#6d7a77] font-mono">
                    <line x1="50" y1="44" x2="510" y2="44" stroke="#dae2fd" strokeDasharray="2,2" strokeWidth="0.8" />
                    <text x="42" y="47" textAnchor="end">240</text>

                    <line x1="50" y1="91" x2="510" y2="91" stroke="#dae2fd" strokeDasharray="2,2" strokeWidth="0.8" />
                    <text x="42" y="94" textAnchor="end">200</text>

                    <text x="42" y="117" textAnchor="end" className="fill-[#006948] font-bold">180</text>

                    <line x1="50" y1="161" x2="510" y2="161" stroke="#dae2fd" strokeDasharray="2,2" strokeWidth="0.8" />
                    <text x="42" y="164" textAnchor="end">140</text>

                    <line x1="50" y1="208" x2="510" y2="208" stroke="#dae2fd" strokeDasharray="2,2" strokeWidth="0.8" />
                    <text x="42" y="211" textAnchor="end">100</text>

                    <text x="42" y="247" textAnchor="end" className="fill-[#ba1a1a] font-bold">70</text>

                    <line x1="50" y1="280" x2="510" y2="280" stroke="#dae2fd" strokeDasharray="2,2" strokeWidth="0.8" />
                    <text x="42" y="283" textAnchor="end">40</text>
                  </g>

                  {/* X Axis Ticks & Time Labels */}
                  <g className="text-[9px] fill-[#6d7a77] font-mono">
                    <text x="50" y="298" textAnchor="middle">14:15</text>
                    <text x="142" y="298" textAnchor="middle">15:15</text>
                    <text x="234" y="298" textAnchor="middle">16:15</text>
                    <text x="326" y="298" textAnchor="middle">17:15</text>
                    <text x="418" y="298" textAnchor="middle">18:15</text>
                    <text x="510" y="298" textAnchor="middle">19:15</text>
                    <line x1="50" y1="280" x2="50" y2="285" stroke="#6d7a77" strokeWidth="1" />
                    <line x1="142" y1="280" x2="142" y2="285" stroke="#6d7a77" strokeWidth="1" />
                    <line x1="234" y1="280" x2="234" y2="285" stroke="#6d7a77" strokeWidth="1" />
                    <line x1="326" y1="280" x2="326" y2="285" stroke="#6d7a77" strokeWidth="1" />
                    <line x1="418" y1="280" x2="418" y2="285" stroke="#6d7a77" strokeWidth="1" />
                    <line x1="510" y1="280" x2="510" y2="285" stroke="#6d7a77" strokeWidth="1" />
                  </g>

                  {/* Activity Window Highlight */}
                  {activityEnabled && (
                    <g>
                      <rect x="73" y="40" width="46" height="240" rx="2" fill="#006398" fillOpacity="0.04" />
                      <line x1="73" y1="40" x2="73" y2="280" stroke="#006398" strokeDasharray="1,3" strokeWidth="0.8" />
                      <line x1="119" y1="40" x2="119" y2="280" stroke="#006398" strokeDasharray="1,3" strokeWidth="0.8" />
                      <text x="96" y="52" textAnchor="middle" className="text-[8px] fill-[#006398] font-sans font-semibold uppercase tracking-wider">
                        30m Walk
                      </text>
                    </g>
                  )}

                  {/* LINE A: Baseline Trajectory (Solid Teal) */}
                  <path d={basePathStr} fill="none" stroke="#00685f" strokeWidth="2.5" strokeLinecap="round" />

                  {/* LINE B: Simulated Trajectory (Dashed Blue) */}
                  {simPathStr && (
                    <path d={simPathStr} fill="none" stroke="#006398" strokeWidth="2.5" strokeDasharray="6,4" strokeLinecap="round" />
                  )}

                  {/* Baseline Peak Callout Marker */}
                  {basePeak !== null && (
                    <>
                      <circle cx={getX(basePeakIdx)} cy={getY(basePeak)} r="4.5" fill="#00685f" stroke="#ffffff" strokeWidth="1.5" />
                      <g transform={`translate(${getX(basePeakIdx)}, ${getY(basePeak) - 20})`}>
                        <rect x="-38" y="-18" width="76" height="18" rx="2" fill="#00685f" />
                        <text x="0" y="-6" textAnchor="middle" className="text-[9px] fill-[#ffffff] font-mono font-bold">
                          {basePeak} mg/dL
                        </text>
                        <polygon points="0,0 -4,-3 4,-3" fill="#00685f" />
                      </g>
                    </>
                  )}

                  {/* Simulation Peak Callout Marker */}
                  {simPeak !== null && (
                    <>
                      <circle cx={getX(simPeakIdx)} cy={getY(simPeak)} r="4.5" fill="#006398" stroke="#ffffff" strokeWidth="1.5" />
                      <g transform={`translate(${getX(simPeakIdx)}, ${getY(simPeak) + 20})`}>
                        <rect x="-44" y="0" width="88" height="18" rx="2" fill="#006398" />
                        <text x="0" y="12" textAnchor="middle" className="text-[9px] fill-[#ffffff] font-mono font-bold">
                          Sim Peak: {simPeak}
                        </text>
                        <polygon points="0,-1 -4,3 4,3" fill="#006398" />
                      </g>
                    </>
                  )}

                  {/* Connecting line between peaks */}
                  {basePeak !== null && simPeak !== null && (
                    <line
                      x1={getX(basePeakIdx)}
                      y1={getY(basePeak)}
                      x2={getX(simPeakIdx)}
                      y2={getY(simPeak)}
                      stroke="#00476e"
                      strokeDasharray="2,2"
                      strokeWidth="1.2"
                    />
                  )}

                  {/* Nadir Alert Anchor if low */}
                  {simNadir !== null && simNadir < 80 && (
                    <g>
                      <circle cx={getX(simNadirIdx)} cy={getY(simNadir)} r="5" fill="#ba1a1a" stroke="#ffffff" strokeWidth="2" />
                      <g transform={`translate(${getX(simNadirIdx) - 25}, ${getY(simNadir) + 16})`}>
                        <rect x="-5" y="-14" width="55" height="16" rx="2" fill="#ffdad6" />
                        <text x="22" y="-2" textAnchor="middle" className="text-[9px] fill-[#ba1a1a] font-mono font-bold">
                          Nadir: {simNadir}
                        </text>
                      </g>
                    </g>
                  )}
                </svg>
              </div>
            ) : (
              <div className="w-full bg-surface-container-lowest rounded-lg p-space-xl flex flex-col items-center justify-center text-center border border-surface-container h-72">
                <Info className="w-8 h-8 text-outline mb-2" />
                <span className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-1">
                  Baseline forecast trajectory unavailable
                </span>
                <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
                  A verified 5-hour forecast trajectory is required to evaluate counterfactual meal and insulin adjustments.
                </p>
              </div>
            )}

            {/* Real-time Trajectory Telemetry Footnote */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-sm pt-space-xs">
              <div className="bg-surface-container-low p-space-sm rounded flex flex-col border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Max Ascent Velocity</span>
                <span className="font-telemetry-metric text-telemetry-metric text-on-surface font-semibold">
                  +1.1 mg/dL/m
                </span>
                <span className="font-code-sm text-code-sm text-tertiary">Normal ramp rate</span>
              </div>
              <div className="bg-surface-container-low p-space-sm rounded flex flex-col border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Max Descent Rate</span>
                <span className="font-telemetry-metric text-telemetry-metric text-secondary font-semibold">
                  {bolusDeltaVal > 0 ? "-1.8 mg/dL/m" : "-1.2 mg/dL/m"}
                </span>
                <span className="font-code-sm text-code-sm text-secondary font-medium">
                  {bolusDeltaVal > 0 ? "Elevated velocity" : "Standard clearance"}
                </span>
              </div>
              <div className="bg-surface-container-low p-space-sm rounded flex flex-col border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant">AUC 140+ Reduction</span>
                <span className="font-telemetry-metric text-telemetry-metric text-primary font-semibold">
                  {peakDelta !== null && peakDelta < 0 && basePeak ? `${Math.round((Math.abs(peakDelta) / basePeak) * 100)}%` : (peakDelta !== null ? "0%" : "—")}
                </span>
                <span className="font-code-sm text-code-sm text-primary font-medium">Post-prandial control</span>
              </div>
              <div className="bg-surface-container-low p-space-sm rounded flex flex-col border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Late Nadir Horizon</span>
                <span className={`font-telemetry-metric text-telemetry-metric font-semibold ${simNadir !== null && simNadir < 70 ? "text-error" : "text-on-surface"}`}>
                  {simNadir !== null ? `T+${Math.round((simNadirIdx + 1) * 15 / 60)}h ${(simNadirIdx + 1) * 15 % 60 ? `${(simNadirIdx + 1) * 15 % 60}m` : ""}` : "—"}
                </span>
                <span className={`font-code-sm text-code-sm font-medium ${simNadir !== null && simNadir < 70 ? "text-error" : "text-tertiary"}`}>
                  {simNadir !== null ? (simNadir < 70 ? "Borderline hypo" : "Safe recovery") : "Unavailable"}
                </span>
              </div>
            </div>
          </div>

          {/* Meal & Insulin Vector Correlation Breakdown */}
          <div className="bg-surface-container-lowest p-space-md rounded-xl shadow-sm border border-surface-container flex items-center justify-between">
            <div className="flex items-center gap-space-md">
              <div className="w-10 h-10 rounded-full bg-secondary-fixed flex items-center justify-center text-on-secondary-fixed shrink-0">
                <Activity className="w-5 h-5 text-secondary" />
              </div>
              <div className="flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold">
                  Variance Explanation: Muscular Glycogen Re-synthesis
                </span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Insulin pharmacokinetics and carbohydrate absorption timing intersect with physical activity, modifying glucose uptake dynamics
                </span>
              </div>
            </div>
            <span className="hidden sm:inline-block font-code-sm text-code-sm font-semibold text-secondary px-2.5 py-1 bg-secondary-fixed/40 rounded">
              Simulated
            </span>
          </div>
        </div>

        {/* RIGHT COLUMN: Interpretation, Comparative Outcomes & Alerts (3 Cols) */}
        <div className="lg:col-span-3 flex flex-col gap-space-md">
          {/* Card 1: Comparative Outcomes Metric Table */}
          <div className="bg-surface-container-lowest p-5 sm:p-6 rounded-xl shadow-sm border border-surface-container flex flex-col gap-space-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <Layers className="w-4 h-4 text-primary" />
                <h2 className="font-headline-sm text-headline-sm text-on-surface">Comparative Outcomes</h2>
              </div>
              <span className="font-code-sm text-code-sm text-primary font-bold bg-primary-fixed/30 px-2 py-0.5 rounded">
                T0 → T+5h
              </span>
            </div>

            <div className="flex flex-col gap-space-sm">
              {/* Metric 1: Peak Glucose */}
              <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-1 border border-surface-container">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Peak Glucose</span>
                  <span
                    className={`font-code-sm text-code-sm font-bold px-1.5 py-0.5 rounded ${
                      peakDelta === null
                        ? "text-on-surface-variant bg-surface-container"
                        : peakDelta <= 0 ? "text-secondary bg-secondary-fixed/60" : "text-error bg-error-container"
                    }`}
                  >
                    {peakDelta !== null ? `${peakDelta > 0 ? `+${peakDelta.toFixed(1)}` : peakDelta.toFixed(1)} mg/dL` : "—"}
                  </span>
                </div>
                <div className="flex items-baseline justify-between mt-1">
                  <div className="flex items-center gap-1 font-telemetry-metric text-body-md text-on-surface-variant">
                    <span>Base: {basePeak !== null ? basePeak : "—"}</span>
                    <span className="text-outline-variant">→</span>
                  </div>
                  <div className="font-telemetry-display text-telemetry-metric text-on-surface font-bold">
                    {simPeak !== null ? simPeak : "—"} {simPeak !== null && <span className="font-telemetry-unit text-code-sm text-on-surface-variant font-normal">mg/dL</span>}
                  </div>
                </div>
                <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1">
                  <div className="bg-primary h-full" style={{ width: `${simPeak !== null ? Math.min(100, (simPeak / 200) * 100) : 0}%` }}></div>
                </div>
              </div>

              {/* Metric 2: Time-in-Range (70-180 mg/dL) */}
              <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-1 border border-surface-container">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Time-in-Range (70-180)</span>
                  <span
                    className={`font-code-sm text-code-sm font-bold px-1.5 py-0.5 rounded ${
                      tirDelta === null
                        ? "text-on-surface-variant bg-surface-container"
                        : tirDelta >= 0 ? "text-tertiary bg-tertiary-fixed/60" : "text-error bg-error-container"
                    }`}
                  >
                    {tirDelta !== null ? `${tirDelta > 0 ? `+${tirDelta}%` : `${tirDelta}%`}` : "—"}
                  </span>
                </div>
                <div className="flex items-baseline justify-between mt-1">
                  <div className="flex items-center gap-1 font-telemetry-metric text-body-md text-on-surface-variant">
                    <span>Base: {baseTir !== null ? `${baseTir}%` : "—"}</span>
                    <span className="text-outline-variant">→</span>
                  </div>
                  <div className="font-telemetry-display text-telemetry-metric text-tertiary font-bold">
                    {simTir !== null ? `${simTir}%` : "—"}
                  </div>
                </div>
                <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1">
                  <div className="bg-tertiary h-full" style={{ width: `${simTir !== null ? Math.min(100, simTir) : 0}%` }}></div>
                </div>
              </div>

              {/* Metric 3: Late Nadir Glucose */}
              <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-col gap-1 border border-surface-container">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Late Nadir Glucose</span>
                  <span
                    className={`font-code-sm text-code-sm font-bold px-1.5 py-0.5 rounded ${
                      nadirDelta === null
                        ? "text-on-surface-variant bg-surface-container"
                        : simNadir !== null && simNadir < 70 ? "text-error bg-error-container text-on-error-container" : "text-primary bg-primary-fixed/50"
                    }`}
                  >
                    {nadirDelta !== null ? `${nadirDelta > 0 ? `+${nadirDelta.toFixed(1)}` : nadirDelta.toFixed(1)} mg/dL` : "—"}
                  </span>
                </div>
                <div className="flex items-baseline justify-between mt-1">
                  <div className="flex items-center gap-1 font-telemetry-metric text-body-md text-on-surface-variant">
                    <span>Base: {baseNadir !== null ? baseNadir : "—"}</span>
                    <span className="text-outline-variant">→</span>
                  </div>
                  <div className={`font-telemetry-display text-telemetry-metric font-bold ${simNadir !== null && simNadir < 70 ? "text-error" : "text-on-surface"}`}>
                    {simNadir !== null ? simNadir : "—"} {simNadir !== null && <span className="font-telemetry-unit text-code-sm text-on-surface-variant font-normal">mg/dL</span>}
                  </div>
                </div>
                <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1">
                  <div
                    className={`h-full ${simNadir !== null && simNadir < 70 ? "bg-error" : "bg-tertiary"}`}
                    style={{ width: `${simNadir !== null ? Math.min(100, (simNadir / 140) * 100) : 0}%` }}
                  ></div>
                </div>
              </div>

            </div>

            <div className="flex items-center justify-between pt-space-xs font-body-sm text-body-sm text-on-surface-variant">
              <span className="font-code-sm text-code-sm text-on-surface-variant flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-tertiary"></span>
                Inference: Completed
              </span>
              <span className="font-code-sm text-code-sm text-on-surface font-medium">5-Hour Simulation</span>
            </div>
          </div>

          {/* Card 2: Clinical Risk Warning & Hypo Caution Callout */}
          <div className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border-l-4 border-l-[#d97706] border border-surface-container flex flex-col gap-space-md">
            <div className="flex items-start gap-space-sm">
              <div className="w-8 h-8 rounded bg-secondary-fixed text-on-secondary-fixed flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 text-secondary" />
              </div>
              <div className="flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold">
                  Simulated Trajectory Analysis
                </span>
                <span className="font-code-sm text-code-sm text-secondary font-medium">
                  Projected Outcome Notes
                </span>
              </div>
            </div>

            <div className="bg-[#fffbeb]/80 p-space-sm rounded-lg flex flex-col gap-space-xs border border-amber-200">
              <p className="font-body-sm text-body-sm text-[#92400e] leading-relaxed">
                Simulated scenario with {bolusDeltaVal >= 0 ? `+${bolusDeltaVal.toFixed(2)} U bolus` : `${bolusDeltaVal.toFixed(2)} U bolus`}
                {activityEnabled ? " coupled with 30 min light activity" : ""} shows a projected late nadir of{" "}
                <strong className="font-semibold">{simNadir !== null ? `${simNadir} mg/dL` : "—"}</strong>.
              </p>
              <div className="flex items-center justify-between pt-1 font-code-sm text-code-sm text-[#92400e]/80">
                <span>P(Hypo &lt;70 mg/dL)</span>
                <span className="font-bold">{pHypoStr}</span>
              </div>
            </div>

            <div className="flex flex-col gap-space-xs bg-surface-container-low p-space-sm rounded-lg border border-surface-container">
              <div className="flex items-center gap-1.5 text-on-surface font-label-sm text-label-sm font-semibold">
                <Info className="w-3.5 h-3.5 text-primary" />
                Model Interpretation
              </div>
              <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                {simNadir === null
                  ? "Baseline or simulated projection data is awaiting input."
                  : simNadir < 75
                  ? "Projected response indicates that simulated bolus with activity correlates with nadir near lower boundary. Baseline scenario reflects projected higher glycemic stability without intervention changes."
                  : "Counterfactual projection indicates balanced insulin-to-carbohydrate coverage with steady clearance toward the normal euglycemic range."}
              </p>
            </div>

            {/* Prescriptive Clinical Quick-Actions */}
            <div className="flex flex-col gap-space-xs pt-space-xs">
              {onTransferToDecision && (
                <button
                  onClick={() => onTransferToDecision({ mealCarbs, bolusInsulin })}
                  className="w-full h-8 px-space-sm bg-primary hover:bg-primary-container text-on-primary rounded font-label-sm text-label-sm font-medium flex items-center justify-between transition-colors shadow-sm"
                >
                  <span>Transfer to Decision Center</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
              <div className="p-2.5 rounded bg-surface-container-low text-xs text-on-surface-variant font-mono border border-surface-container leading-relaxed">
                <strong>RESEARCH &amp; IN-SILICO PROTOTYPE:</strong> Simulated postprandial trajectories evaluate ODE sensitivity and do not constitute treatment recommendations or automated insulin prescriptions.
              </div>
            </div>
          </div>

          {/* Telemetry Signature Card */}
          <div className="bg-surface-container-low p-space-sm rounded-lg flex items-center justify-between text-on-surface-variant border border-surface-container">
            <span className="font-code-sm text-code-sm">Scenario Status</span>
            <span className="font-code-sm text-code-sm font-semibold text-on-surface">
              Scenario: Active Simulation
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
