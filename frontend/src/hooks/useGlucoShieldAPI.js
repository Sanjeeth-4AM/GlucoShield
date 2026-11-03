import { useState, useEffect, useCallback, useRef } from "react";
import { fetchHealth, fetchForecast, fetchWhatIf, fetchFoodAnalyze, fetchFullFlow } from "../api/client.js";
import {
  generateSyntheticHistory,
  DEMO_STATIC_PROFILE,
  getSyntheticForecastResponse,
  getSyntheticWhatIfResponse
} from "../api/demoData.js";

export function sanitizeProfile(profile) {
  if (!profile || typeof profile !== "object" || "nativeEvent" in profile || "target" in profile) {
    return undefined;
  }
  const clean = {};
  for (const [k, v] of Object.entries(profile)) {
    if (v !== null && v !== undefined && v !== "" && !isNaN(Number(v))) {
      clean[k] = Number(v);
    }
  }
  return Object.keys(clean).length > 0 ? clean : undefined;
}

export function useGlucoShieldAPI() {
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [backendHealth, setBackendHealth] = useState(null);
  const [currentScenario, setCurrentScenario] = useState("stable");
  // In Live API mode: historyReadings starts empty; demo generator used only when explicitly in demo mode
  const [historyReadings, setHistoryReadings] = useState([]);
  const [staticProfile, setStaticProfile] = useState(null);
  const [wearableContext, setWearableContext] = useState({
    steps_15m: [120.0, 140.0, 90.0, 180.0, 210.0],
    heart_rate_bpm: [72.0, 75.0, 74.0, 78.0, 82.0],
    device_source: "TicWatch Pro / Apple Watch Series 9"
  });

  // Active responses
  const [forecastData, setForecastData] = useState(null);
  const [whatIfData, setWhatIfData] = useState(null);
  const [foodAnalysisData, setFoodAnalysisData] = useState(null);
  const [fullFlowData, setFullFlowData] = useState(null);

  // Status flags
  const [isLoadingForecast, setIsLoadingForecast] = useState(false);
  const [isLoadingWhatIf, setIsLoadingWhatIf] = useState(false);
  const [isLoadingFood, setIsLoadingFood] = useState(false);
  const [isLoadingFullFlow, setIsLoadingFullFlow] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Synchronized refs guaranteeing stable callback references and preventing render loops
  const isDemoModeRef = useRef(isDemoMode);
  isDemoModeRef.current = isDemoMode;
  const historyReadingsRef = useRef(historyReadings);
  historyReadingsRef.current = historyReadings;
  const staticProfileRef = useRef(staticProfile);
  staticProfileRef.current = staticProfile;
  const wearableContextRef = useRef(wearableContext);
  wearableContextRef.current = wearableContext;
  const currentScenarioRef = useRef(currentScenario);
  currentScenarioRef.current = currentScenario;
  const forecastDataRef = useRef(forecastData);
  forecastDataRef.current = forecastData;
  const foodAnalysisDataRef = useRef(foodAnalysisData);
  foodAnalysisDataRef.current = foodAnalysisData;
  const forecastInFlightRef = useRef(false);

  // Check health on mount (never silently fall back to demo data on 502/unreachable)
  const checkBackendHealth = useCallback(async () => {
    const h = await fetchHealth();
    setBackendHealth(h || { status: "unreachable", error: "Backend server unavailable" });
    if (h && (h.status === "healthy" || h.status === "ok")) {
      setIsDemoMode(false);
    }
  }, []);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  // Clear all inference state during patient switching or logout
  const clearInferenceState = useCallback(() => {
    setForecastData(null);
    setWhatIfData(null);
    setFoodAnalysisData(null);
    setFullFlowData(null);
    setErrorMessage(null);
  }, []);

  // Load Forecast: Referentially stable callback using refs
  const runForecast = useCallback(async (readings, profile, overrideScenario = null, patientId = null) => {
    if (forecastInFlightRef.current) {
      console.log("[runForecast] forecast already in flight, skipping duplicate call");
      return;
    }
    forecastInFlightRef.current = true;
    console.log("[runForecast] started. isDemoModeRef:", isDemoModeRef.current, "readings len:", readings?.length);
    setIsLoadingForecast(true);
    setErrorMessage(null);

    // Robust type guards against React SyntheticEvent or DOM objects
    const validReadings = Array.isArray(readings) ? readings : (Array.isArray(historyReadingsRef.current) ? historyReadingsRef.current : []);
    const validProfile = (profile && typeof profile === "object" && !("nativeEvent" in profile) && !("target" in profile)) ? profile : staticProfileRef.current;
    const activeScen = (typeof overrideScenario === "string" && overrideScenario) ? overrideScenario : currentScenarioRef.current;

    try {
      if (isDemoModeRef.current) {
        // In Demo Mode: dispatch 96 demo observations to the real Combination C serving pipeline
        const demoReadings = (Array.isArray(validReadings) && validReadings.length >= 96)
          ? validReadings
          : generateSyntheticHistory(activeScen);
        setHistoryReadings(demoReadings);

        try {
          const payload = {
            patient_id: "DEMO-SYNTHETIC-PATIENT-001",
            history_readings: demoReadings.slice(-96),
            static_profile: sanitizeProfile(validProfile || DEMO_STATIC_PROFILE),
            wearable_context: wearableContextRef.current
          };
          console.log("[runForecast] demo payload sending to fetchForecast...");
          const res = await fetchForecast(payload);
          console.log("[runForecast] demo fetchForecast succeeded, risk:", res?.risk_assessment?.alert_level);
          setForecastData(res);
        } catch (err) {
          console.warn("[Demo Forecast Fallback] Serving backend unreachable, using deterministic fallback:", err.message);
          const demoRes = getSyntheticForecastResponse(activeScen);
          console.log("[runForecast] fallback demoRes set, risk:", demoRes?.risk_assessment?.alert_level);
          setForecastData(demoRes);
        }
        return;
      }

      // LIVE API MODE:
      // If genuine history is unavailable or insufficient (< 96 readings), remain in explicit awaiting state without fabricated numbers
      if (!validReadings || validReadings.length < 96) {
        setForecastData(null);
        return;
      }

      try {
        const payload = {
          patient_id: patientId || "patient_live_001",
          history_readings: validReadings,
          static_profile: sanitizeProfile(validProfile),
          wearable_context: wearableContextRef.current
        };
        const res = await fetchForecast(payload);
        setForecastData(res);
      } catch (err) {
        console.error("[Forecast Error]", err);
        // In Live API mode: never silently fall back to synthetic data
        setErrorMessage(`Live forecast unavailable: ${err.message}`);
        setForecastData(null);
      }
    } finally {
      forecastInFlightRef.current = false;
      setIsLoadingForecast(false);
    }
  }, []);

  const updateStaticProfile = useCallback((newProfile) => {
    if (newProfile && typeof newProfile === "object" && !("nativeEvent" in newProfile)) {
      setStaticProfile(newProfile);
    }
  }, []);

  // Handle scenario / demo mode changes strictly in Demo Mode
  useEffect(() => {
    if (isDemoMode) {
      // In Demo Mode: load synthetic demo history for the selected scenario
      const demoHistory = generateSyntheticHistory(currentScenario);
      setHistoryReadings(demoHistory);
      setStaticProfile(DEMO_STATIC_PROFILE);
      runForecast(demoHistory, DEMO_STATIC_PROFILE, currentScenario);
    }
  }, [currentScenario, isDemoMode, runForecast]);

  // Run What-If Simulation: Referentially stable callback using refs
  const runWhatIf = useCallback(async (carbsG = 50.0, bolusU = 4.0) => {
    setIsLoadingWhatIf(true);
    setErrorMessage(null);

    const resolvedCarbs = typeof carbsG === "object" && carbsG !== null
      ? (carbsG.meal_carbs_g ?? carbsG.scenario_meal_carbs_g ?? 50.0)
      : carbsG;
    const resolvedBolus = typeof carbsG === "object" && carbsG !== null
      ? (carbsG.bolus_insulin_u ?? carbsG.scenario_insulin_bolus_u ?? 4.0)
      : bolusU;

    if (isDemoModeRef.current) {
      const currentHistory = (Array.isArray(historyReadingsRef.current) && historyReadingsRef.current.length >= 96)
        ? historyReadingsRef.current
        : generateSyntheticHistory(currentScenarioRef.current);

      try {
        const payload = {
          patient_id: "DEMO-SYNTHETIC-PATIENT-001",
          history_readings: currentHistory.slice(-96),
          static_profile: sanitizeProfile(staticProfileRef.current || DEMO_STATIC_PROFILE),
          scenario_meal_carbs_g: Number(resolvedCarbs),
          scenario_insulin_bolus_u: Number(resolvedBolus)
        };
        const res = await fetchWhatIf(payload);
        setWhatIfData(res);
      } catch (err) {
        console.warn("[Demo What-If Fallback] Serving backend unreachable, using deterministic fallback:", err.message);
        const curG = forecastDataRef.current?.current_state?.glucose_mg_dl || 120.0;
        const res = getSyntheticWhatIfResponse(resolvedCarbs, resolvedBolus, curG);
        setWhatIfData(res);
      } finally {
        setIsLoadingWhatIf(false);
      }
      return;
    }

    // LIVE API MODE:
    const currentHistory = historyReadingsRef.current;
    if (!currentHistory || currentHistory.length < 96) {
      setWhatIfData(null);
      setErrorMessage("What-If simulation requires 24 hours of CGM history (96 readings).");
      setIsLoadingWhatIf(false);
      return;
    }

    try {
      const payload = {
        patient_id: "patient_live_001",
        history_readings: currentHistory,
        static_profile: sanitizeProfile(staticProfileRef.current),
        scenario_meal_carbs_g: Number(resolvedCarbs),
        scenario_insulin_bolus_u: Number(resolvedBolus)
      };
      const res = await fetchWhatIf(payload);
      setWhatIfData(res);
    } catch (err) {
      console.error("[What-If Error]", err);
      // In Live API mode: never silently fall back to synthetic data
      setErrorMessage(`What-If simulation failed: ${err.message}`);
      setWhatIfData(null);
    } finally {
      setIsLoadingWhatIf(false);
    }
  }, []);

  // Run Food Analysis: Referentially stable callback using refs
  const runFoodAnalyze = useCallback(async (params = {}) => {
    setIsLoadingFood(true);
    setErrorMessage(null);
    setFoodAnalysisData(null);

    const imageBase64 = params.imageBase64 || params.image_base64 || null;
    const foodNameQuery = params.foodNameQuery || params.food_name_query || null;
    const portionG = Number(params.portionG || params.portion_g) || 150.0;
    const candidateIdx = params.selectedCandidateIndex ?? params.selected_candidate_index ?? 0;

    if (isDemoModeRef.current) {
      setTimeout(() => {
        const query = foodNameQuery || (imageBase64 ? "Identified Plate Dish" : "Mixed meal");
        setFoodAnalysisData({
          image_food_candidates: [
            { name: query, confidence: 0.94, source: "HuggingFace Food-101", raw_label: query.toLowerCase() },
            { name: "Alternative dish", confidence: 0.05, source: "HuggingFace Food-101", raw_label: "alt" }
          ],
          selected_food: query,
          portion_g: portionG,
          nutrition_density: {
            food_name: query,
            carbs_g_per_100g: 24.5,
            protein_g_per_100g: 6.2,
            fat_g_per_100g: 4.8,
            calories_kcal_per_100g: 165.0,
            source: "USDA FoodData Central (fdc.nal.usda.gov)"
          },
          final_macros: {
            carbs_g: Math.round(24.5 * (portionG / 100) * 10) / 10,
            protein_g: Math.round(6.2 * (portionG / 100) * 10) / 10,
            fat_g: Math.round(4.8 * (portionG / 100) * 10) / 10,
            calories_kcal: Math.round(165 * (portionG / 100))
          },
          requires_user_confirmation: true,
          warnings: ["Advisory estimate only. Photo recognition cannot measure hidden oils, sugars, or exact recipe ratios."]
        });
        setIsLoadingFood(false);
      }, 500);
      return;
    }

    try {
      const payload = {
        image_base64: imageBase64,
        food_name_query: foodNameQuery,
        portion_g: portionG,
        selected_candidate_index: candidateIdx
      };
      const res = await fetchFoodAnalyze(payload);
      setFoodAnalysisData(res);
    } catch (err) {
      console.error("[Food Analyze Error]", err);
      setErrorMessage(`Food analysis failed: ${err.message}`);
    } finally {
      setIsLoadingFood(false);
    }
  }, []);

  // Run Full-Flow Multimodal Decision: Referentially stable callback using refs
  const runFullFlow = useCallback(async ({ foodQuery, imageBase64, portionG, bolusU }) => {
    setIsLoadingFullFlow(true);
    setErrorMessage(null);

    try {
      const payload = {
        patient_id: "patient_live_001",
        history_readings: historyReadingsRef.current,
        static_profile: sanitizeProfile(staticProfileRef.current),
        meal_image_base64: imageBase64 || null,
        meal_food_query: foodQuery || null,
        meal_portion_g: Number(portionG) || 100.0,
        proposed_insulin_bolus_u: bolusU !== undefined ? Number(bolusU) : null,
        wearable_context: wearableContextRef.current
      };

      if (isDemoModeRef.current) {
        setTimeout(() => {
          const forecast = getSyntheticForecastResponse(currentScenarioRef.current);
          const whatIf = getSyntheticWhatIfResponse(portionG ? portionG * 0.25 : 45.0, bolusU || 3.5);
          setFullFlowData({
            disclaimer: forecast.disclaimer,
            patient_id: "demo_patient_001",
            food_analysis: foodAnalysisDataRef.current,
            baseline_forecast: forecast,
            what_if_simulation: whatIf,
            decision_summary: {
              alert_status: forecast.risk_assessment.alert_level,
              recommended_action: forecast.risk_assessment.alert_level === "NORMAL" ? "Maintain target monitoring" : "Review impending excursion",
              meal_carbs_considered_g: 45.0,
              bolus_considered_u: bolusU || 3.5,
              requires_food_confirmation: true
            }
          });
          setIsLoadingFullFlow(false);
        }, 600);
        return;
      }

      if (!historyReadingsRef.current || historyReadingsRef.current.length < 96) {
        setFullFlowData(null);
        setErrorMessage("Full decision flow requires 24 hours of CGM history (96 readings).");
        setIsLoadingFullFlow(false);
        return;
      }

      const res = await fetchFullFlow(payload);
      setFullFlowData(res);
    } catch (err) {
      console.error("[Full Flow Error]", err);
      setErrorMessage(`Full flow decision synthesis failed: ${err.message}`);
      setFullFlowData(null);
    } finally {
      setIsLoadingFullFlow(false);
    }
  }, []);

  // Load verified patient inference directly (for demonstration cohort)
  const loadPatientInference = useCallback((readings, profile, forecast) => {
    if (Array.isArray(readings) && readings.length > 0) {
      setHistoryReadings(readings);
    }
    if (profile) {
      setStaticProfile(profile);
    }
    if (forecast) {
      setForecastData(forecast);
    }
  }, []);

  return {
    isDemoMode,
    setIsDemoMode,
    backendHealth,
    checkBackendHealth,
    currentScenario,
    setCurrentScenario,
    historyReadings,
    setHistoryReadings,
    staticProfile,
    setStaticProfile,
    wearableContext,
    setWearableContext,
    forecastData,
    setForecastData,
    loadPatientInference,
    whatIfData,
    whatIfResult: whatIfData,
    foodAnalysisData,
    mealAnalysisResult: foodAnalysisData,
    fullFlowData,
    fullFlowResult: fullFlowData,
    isLoadingForecast,
    isLoadingWhatIf,
    isSimulatingWhatIf: isLoadingWhatIf,
    isLoadingFood,
    isAnalyzingMeal: isLoadingFood,
    isLoadingFullFlow,
    isExecutingFullFlow: isLoadingFullFlow,
    errorMessage,
    setErrorMessage,
    runForecast,
    runWhatIf,
    runWhatIfSimulation: runWhatIf,
    runFoodAnalyze,
    runMealAnalysis: runFoodAnalyze,
    runFullFlow,
    runFullDecisionFlow: runFullFlow,
    updateStaticProfile,
    updateWearableContext: (newContext) => setWearableContext(newContext),
    clearInferenceState
  };
}
