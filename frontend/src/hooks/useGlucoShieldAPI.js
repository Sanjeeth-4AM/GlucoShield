import { useState, useEffect, useCallback } from "react";
import { fetchHealth, fetchForecast, fetchWhatIf, fetchFoodAnalyze, fetchFullFlow } from "../api/client";
import { generateSyntheticHistory, DEMO_STATIC_PROFILE, getSyntheticForecastResponse, getSyntheticWhatIfResponse } from "../api/demoData";

export function useGlucoShieldAPI() {
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [backendHealth, setBackendHealth] = useState(null);
  const [currentScenario, setCurrentScenario] = useState("stable");
  const [historyReadings, setHistoryReadings] = useState(() => generateSyntheticHistory("stable"));
  const [staticProfile, setStaticProfile] = useState(DEMO_STATIC_PROFILE);
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

  // Check health on mount
  const checkBackendHealth = useCallback(async () => {
    const h = await fetchHealth();
    setBackendHealth(h);
    if (!h) {
      setIsDemoMode(true); // Fallback to demo mode if backend is not running yet
    }
  }, []);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  // Load Forecast
  const runForecast = useCallback(async (readings = historyReadings, profile = staticProfile, overrideScenario = null) => {
    setIsLoadingForecast(true);
    setErrorMessage(null);

    const activeScen = overrideScenario || currentScenario;

    if (isDemoMode) {
      // Simulate quick latency
      setTimeout(() => {
        const demoRes = getSyntheticForecastResponse(activeScen);
        setForecastData(demoRes);
        setIsLoadingForecast(false);
      }, 400);
      return;
    }

    try {
      const payload = {
        patient_id: "patient_live_001",
        history_readings: readings,
        static_profile: profile,
        wearable_context: wearableContext
      };
      const res = await fetchForecast(payload);
      setForecastData(res);
    } catch (err) {
      console.error("[Forecast Error]", err);
      setErrorMessage(`Live forecast failed: ${err.message}. Falling back to demo preview.`);
      setForecastData(getSyntheticForecastResponse(activeScen));
    } finally {
      setIsLoadingForecast(false);
    }
  }, [isDemoMode, historyReadings, staticProfile, wearableContext, currentScenario]);

  // Run initial forecast when scenario or demo mode changes
  useEffect(() => {
    const newHistory = generateSyntheticHistory(currentScenario);
    setHistoryReadings(newHistory);
    runForecast(newHistory, staticProfile, currentScenario);
  }, [currentScenario, isDemoMode]);

  // Run What-If Simulation
  const runWhatIf = useCallback(async (carbsG = 50.0, bolusU = 4.0) => {
    setIsLoadingWhatIf(true);
    setErrorMessage(null);

    if (isDemoMode) {
      setTimeout(() => {
        const curG = forecastData?.current_state?.glucose_mg_dl || 120.0;
        const res = getSyntheticWhatIfResponse(carbsG, bolusU, curG);
        setWhatIfData(res);
        setIsLoadingWhatIf(false);
      }, 350);
      return;
    }

    try {
      const payload = {
        patient_id: "patient_live_001",
        history_readings: historyReadings,
        static_profile: staticProfile,
        scenario_meal_carbs_g: Number(carbsG),
        scenario_insulin_bolus_u: Number(bolusU)
      };
      const res = await fetchWhatIf(payload);
      setWhatIfData(res);
    } catch (err) {
      console.error("[What-If Error]", err);
      setErrorMessage(`What-If simulation failed: ${err.message}`);
      const curG = forecastData?.current_state?.glucose_mg_dl || 120.0;
      setWhatIfData(getSyntheticWhatIfResponse(carbsG, bolusU, curG));
    } finally {
      setIsLoadingWhatIf(false);
    }
  }, [isDemoMode, historyReadings, staticProfile, forecastData]);

  // Run Food Analysis
  const runFoodAnalyze = useCallback(async ({ imageBase64, foodNameQuery, portionG }) => {
    setIsLoadingFood(true);
    setErrorMessage(null);

    if (isDemoMode) {
      setTimeout(() => {
        const query = foodNameQuery || "Mixed meal";
        setFoodAnalysisData({
          image_food_candidates: [
            { name: query, confidence: 0.94, source: "HuggingFace Food-101", raw_label: query.toLowerCase() },
            { name: "Alternative dish", confidence: 0.05, source: "HuggingFace Food-101", raw_label: "alt" }
          ],
          selected_food: query,
          portion_g: Number(portionG) || 150.0,
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
        image_base64: imageBase64 || null,
        food_name_query: foodNameQuery || null,
        portion_g: Number(portionG) || 100.0,
        selected_candidate_index: 0
      };
      const res = await fetchFoodAnalyze(payload);
      setFoodAnalysisData(res);
    } catch (err) {
      console.error("[Food Analyze Error]", err);
      setErrorMessage(`Food analysis failed: ${err.message}`);
    } finally {
      setIsLoadingFood(false);
    }
  }, [isDemoMode]);

  // Run Full-Flow Multimodal Decision
  const runFullFlow = useCallback(async ({ foodQuery, imageBase64, portionG, bolusU }) => {
    setIsLoadingFullFlow(true);
    setErrorMessage(null);

    try {
      const payload = {
        patient_id: "patient_live_001",
        history_readings: historyReadings,
        static_profile: staticProfile,
        meal_image_base64: imageBase64 || null,
        meal_food_query: foodQuery || null,
        meal_portion_g: Number(portionG) || 100.0,
        proposed_insulin_bolus_u: bolusU !== undefined ? Number(bolusU) : null,
        wearable_context: wearableContext
      };

      if (isDemoMode) {
        setTimeout(() => {
          const forecast = getSyntheticForecastResponse(currentScenario);
          const whatIf = getSyntheticWhatIfResponse(portionG ? portionG * 0.25 : 45.0, bolusU || 3.5);
          setFullFlowData({
            disclaimer: forecast.disclaimer,
            patient_id: "demo_patient_001",
            food_analysis: foodAnalysisData,
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

      const res = await fetchFullFlow(payload);
      setFullFlowData(res);
    } catch (err) {
      console.error("[Full Flow Error]", err);
      setErrorMessage(`Full flow decision synthesis failed: ${err.message}`);
    } finally {
      setIsLoadingFullFlow(false);
    }
  }, [isDemoMode, historyReadings, staticProfile, wearableContext, currentScenario, foodAnalysisData]);

  return {
    isDemoMode,
    setIsDemoMode,
    backendHealth,
    checkBackendHealth,
    currentScenario,
    setCurrentScenario,
    historyReadings,
    staticProfile,
    setStaticProfile,
    wearableContext,
    setWearableContext,
    forecastData,
    whatIfData,
    foodAnalysisData,
    fullFlowData,
    isLoadingForecast,
    isLoadingWhatIf,
    isLoadingFood,
    isLoadingFullFlow,
    errorMessage,
    setErrorMessage,
    runForecast,
    runWhatIf,
    runFoodAnalyze,
    runFullFlow
  };
}
