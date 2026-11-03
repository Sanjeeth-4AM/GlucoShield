import React, { useState, useEffect, useCallback } from "react";
import { useGlucoShieldAPI } from "./hooks/useGlucoShieldAPI.js";
import { useAuth } from "./hooks/useAuth.js";
import { apiUpdatePatient, apiGetCGMHistory, apiGetMealHistory, apiGetDecisionHistory } from "./api/auth.js";
import { fetchCohortDemoPatients, fetchCohortComparison } from "./api/client.js";
import { SideNavBar, NAV_ITEMS } from "./components/layout/SideNavBar.jsx";
import { Header } from "./components/layout/Header.jsx";
import { MetabolicShaderBackground } from "./components/layout/MetabolicShaderBackground.jsx";
import { DisclaimerModal } from "./components/layout/DisclaimerModal.jsx";
import { AuthModal } from "./components/auth/AuthModal.jsx";

// Certified Stitch-Aligned & Comparative Views
import { DashboardTopCards } from "./components/dashboard/DashboardTopCards.jsx";
import { ForecastChart } from "./components/dashboard/ForecastChart.jsx";
import { DashboardAccordions } from "./components/dashboard/DashboardAccordions.jsx";
import { CustomerOnboardingModal } from "./components/onboarding/CustomerOnboardingModal.jsx";
import { ComparativeGlucoseIntelligence } from "./components/comparison/ComparativeGlucoseIntelligence.jsx";

import { PatientProfilePanel } from "./components/profile/PatientProfilePanel.jsx";
import { ForecastView } from "./components/forecast/ForecastView.jsx";
import { DigitalTwinVisualizer } from "./components/digitalTwin/DigitalTwinVisualizer.jsx";
import { WhatIfSimulator } from "./components/whatIf/WhatIfSimulator.jsx";
import { MealAnalysisWorkflow } from "./components/foodVision/MealAnalysisWorkflow.jsx";
import { RiskExplanationView } from "./components/riskExplanation/RiskExplanationView.jsx";
import { HistoryPanel } from "./components/history/HistoryPanel.jsx";
import { SettingsPanel } from "./components/settings/SettingsPanel.jsx";

// Optional secondary workflow views
import { DecisionCenterView } from "./components/decisionCenter/DecisionCenterView.jsx";
import { WearableContextPanel } from "./components/wearables/WearableContextPanel.jsx";
import { SystemSpecsPanel } from "./components/system/SystemSpecsPanel.jsx";
import { LongitudinalAnalytics } from "./components/analytics/LongitudinalAnalytics.jsx";

export function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [onboardingModalOpen, setOnboardingModalOpen] = useState(false);

  const {
    isAuthenticated,
    token,
    user,
    patientProfile,
    setPatientProfile,
    authError,
    setAuthError,
    login,
    register,
    logout
  } = useAuth();

  const {
    isDemoMode,
    setIsDemoMode,
    currentScenario,
    setCurrentScenario,
    backendHealth,
    historyReadings,
    setHistoryReadings,
    forecastData,
    setForecastData,
    whatIfResult,
    mealAnalysisResult,
    fullFlowResult,
    staticProfile,
    wearableContext,
    isLoadingForecast,
    isSimulatingWhatIf,
    isAnalyzingMeal,
    isExecutingFullFlow,
    errorMessage,
    runForecast,
    runWhatIfSimulation,
    runMealAnalysis,
    updateStaticProfile,
    updateWearableContext,
    clearInferenceState
  } = useGlucoShieldAPI();

  const [persistedRecentEvents, setPersistedRecentEvents] = useState([]);
  const [transferredMeal, setTransferredMeal] = useState(null);
  const [cohortData, setCohortData] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [activePatientId, setActivePatientId] = useState("PATIENT_A");

  // Load real clinical cohort demonstration data (Patient A & Patient B) on startup
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchCohortDemoPatients(),
      fetchCohortComparison()
    ]).then(([cohort, comp]) => {
      if (cancelled) return;
      if (cohort) setCohortData(cohort);
      if (comp) setComparisonData(comp);

      // If not authenticated, populate Patient A (Stable Euglycemic) from the actual dataset
      if (!isAuthenticated && cohort?.patientA) {
        const p = cohort.patientA;
        setHistoryReadings(p.history_readings);
        updateStaticProfile(p.static_profile);
        setForecastData({
          forecast: p.forecast,
          risk_assessment: p.risk_assessment,
          explanation: p.explanation,
          current_state: {
            glucose_mg_dl: p.cgm_stats?.current_glucose ?? (p.history_readings?.[p.history_readings.length - 1]?.cgm_glucose ?? 100.8),
            trend_direction: "flat",
            trend_slope_mg_dl_per_min: 0.0,
            timestamp: p.history_readings?.[p.history_readings.length - 1]?.timestamp || new Date().toISOString()
          },
          disclaimer: "RESEARCH PROTOTYPE ONLY"
        });
        setPatientProfile({
          id: p.id,
          dataset_internal_id: p.dataset_internal_id,
          patient_display_id: p.display_id,
          clinical_type: p.clinical_type,
          diabetes_type: p.diabetes_type || "Type 2 Diabetes (T2D)",
          data_provenance: p.data_provenance || "Research Dataset Cohort (meta_test.csv / cleaned_master.csv)",
          data_status: p.data_status || "HISTORICAL_DATASET",
          sampling_interval_min: p.sampling_interval_min || 15,
          observation_count: p.history_readings?.length || 96,
          ...p.static_profile
        });
      }
    }).catch((err) => {
      console.warn("[App] Could not load demo cohort:", err.message);
    });

    return () => { cancelled = true; };
  }, [isAuthenticated, setHistoryReadings, updateStaticProfile, setForecastData, setPatientProfile]);

  // Seamless 1-click patient switching between Patient A (Stable) and Patient B (Elevated)
  const handleSelectPatient = useCallback((targetPatientId) => {
    setActivePatientId(targetPatientId);
    clearInferenceState();
    setTransferredMeal(null);

    const p = targetPatientId === "PATIENT_B"
      ? cohortData?.patientB
      : cohortData?.patientA;

    if (p) {
      setHistoryReadings(p.history_readings);
      updateStaticProfile(p.static_profile);
      setForecastData({
        forecast: p.forecast,
        risk_assessment: p.risk_assessment,
        explanation: p.explanation,
        current_state: {
          glucose_mg_dl: p.cgm_stats?.current_glucose ?? (p.history_readings?.[p.history_readings.length - 1]?.cgm_glucose ?? (targetPatientId === "PATIENT_B" ? 199.8 : 100.8)),
          trend_direction: "flat",
          trend_slope_mg_dl_per_min: 0.0,
          timestamp: p.history_readings?.[p.history_readings.length - 1]?.timestamp || new Date().toISOString()
        },
        disclaimer: "RESEARCH PROTOTYPE ONLY"
      });
      setPatientProfile({
        id: p.id,
        dataset_internal_id: p.dataset_internal_id,
        patient_display_id: p.display_id,
        clinical_type: p.clinical_type,
        diabetes_type: p.diabetes_type || "Type 2 Diabetes (T2D)",
        data_provenance: p.data_provenance || "Research Dataset Cohort (meta_test.csv / cleaned_master.csv)",
        data_status: p.data_status || "HISTORICAL_DATASET",
        sampling_interval_min: p.sampling_interval_min || 15,
        observation_count: p.history_readings?.length || 96,
        ...p.static_profile
      });
    }
  }, [cohortData, clearInferenceState, updateStaticProfile, setHistoryReadings, setForecastData, setPatientProfile]);

  // In Live API mode, load genuine CGM readings and persisted events when authenticated patient is available
  useEffect(() => {
    if (!isDemoMode && isAuthenticated && token && patientProfile?.id) {
      let cancelled = false;
      // Immediately reset previous patient's inference results to eliminate cross-patient stale state bleed
      clearInferenceState();
      setTransferredMeal(null);

      Promise.all([
        apiGetCGMHistory(token, patientProfile.id, 96).catch(() => []),
        apiGetMealHistory(token, patientProfile.id, 5).catch(() => []),
        apiGetDecisionHistory(token, patientProfile.id, 5).catch(() => [])
      ])
        .then(([cgmRecords, mealRecords, decisionRecords]) => {
          if (cancelled) return;
          if (Array.isArray(cgmRecords) && cgmRecords.length > 0) {
            const sorted = [...cgmRecords].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            const formatted = sorted.map((r) => ({
              timestamp: r.timestamp || null,
              cgm_glucose: Number(r.cgm_glucose),
              insulin_bolus: Number(r.insulin_bolus || 0.0),
              insulin_basal: Number(r.insulin_basal || 0.0),
              meal_carbs: Number(r.meal_carbs || 0.0)
            })).filter((r) => typeof r.cgm_glucose === "number" && !isNaN(r.cgm_glucose) && r.cgm_glucose >= 20 && r.cgm_glucose <= 600);
            setHistoryReadings(formatted);
            if (formatted.length >= 96) {
              const eligible96 = formatted.slice(-96);
              runForecast(eligible96, patientProfile, null, patientProfile.id);
            }
          } else {
            setHistoryReadings((prev) => (prev && prev.length > 0 ? [] : prev));
          }

          // Combine genuine persisted meal and decision events for RecentEventsCard
          const combined = [
            ...(Array.isArray(mealRecords) ? mealRecords : []),
            ...(Array.isArray(decisionRecords) ? decisionRecords : [])
          ];
          setPersistedRecentEvents(combined);
        })
        .catch((err) => {
          console.warn("[App] Unable to fetch patient telemetry / events:", err.message);
          if (!cancelled) {
            setHistoryReadings((prev) => (prev && prev.length > 0 ? [] : prev));
            setPersistedRecentEvents([]);
          }
        });

      return () => {
        cancelled = true;
      };
    } else if (!isDemoMode && !isAuthenticated && !cohortData) {
      clearInferenceState();
      setTransferredMeal(null);
      setHistoryReadings((prev) => (prev && prev.length > 0 ? [] : prev));
      setPersistedRecentEvents([]);
    }
  }, [isDemoMode, isAuthenticated, token, patientProfile?.id, cohortData, clearInferenceState, runForecast]);

  const isSynthetic = isDemoMode || Boolean(patientProfile?.patient_display_id?.startsWith("DEMO"));


  // Sync loaded patient profile covariates into staticProfile state
  useEffect(() => {
    if (patientProfile) {
      updateStaticProfile({
        age: patientProfile.age ?? null,
        bmi: patientProfile.bmi ?? null,
        diabetes_duration_years: patientProfile.diabetes_duration_years ?? null,
        hba1c: patientProfile.hba1c ?? null,
        glycated_albumin: patientProfile.glycated_albumin ?? null,
        fasting_glucose: patientProfile.fasting_glucose ?? null,
        fasting_c_peptide: patientProfile.fasting_c_peptide ?? null,
        macrovascular_comp_count: patientProfile.macrovascular_comp_count ?? null,
        microvascular_comp_count: patientProfile.microvascular_comp_count ?? null,
        is_t1dm: patientProfile.is_t1dm ?? null
      });
    }
  }, [patientProfile, updateStaticProfile]);

  const handleSavePatientProfile = async (newProfile) => {
    if (isAuthenticated && token && patientProfile?.id) {
      const updated = await apiUpdatePatient(token, patientProfile.id, newProfile);
      setPatientProfile(updated);
      updateStaticProfile(newProfile);
      runForecast(historyReadings, newProfile).catch((err) =>
        console.warn("[App] Background forecast after profile save failed:", err.message)
      );
      return updated;
    } else {
      updateStaticProfile(newProfile);
      runForecast(historyReadings, newProfile).catch((err) =>
        console.warn("[App] Background forecast after profile save failed:", err.message)
      );
      return newProfile;
    }
  };

  const handleTransferToWhatIf = (mealPayload) => {
    const rawCarbs = typeof mealPayload === "object" && mealPayload !== null
      ? (mealPayload.carbs_g ?? mealPayload.meal_carbs_g)
      : mealPayload;
    const numCarbs = Number(rawCarbs);
    if (!Number.isFinite(numCarbs) || numCarbs <= 0) {
      console.warn("[App] Blocked transfer: unconfirmed or non-positive carbohydrate estimate", mealPayload);
      return;
    }

    const payload = {
      id: `transferred_${Date.now()}`,
      food_name: (typeof mealPayload === "object" && mealPayload?.food_name) ? mealPayload.food_name : "Confirmed Meal",
      portion_g: (typeof mealPayload === "object" && mealPayload?.portion_g) ? Number(mealPayload.portion_g) : 250,
      carbs_g: Math.round(numCarbs * 10) / 10,
      source: "food_vision",
      transferred_at: new Date().toISOString()
    };

    setTransferredMeal(payload);
    setActiveTab("what_if");
  };

  const handleTransferToDecision = ({ mealCarbs, bolusInsulin }) => {
    runFullDecisionFlow({
      food_name_query: "Planned Meal Formulation",
      portion_g: 250.0,
      bolus_insulin_u: bolusInsulin,
      user_confirmed: true
    });
    setActiveTab("decision_center");
  };

  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col relative font-body-md text-body-md antialiased selection:bg-primary/20 selection:text-primary overflow-x-hidden w-full max-w-full">
      {/* Background Micro-Dot Grid */}
      <MetabolicShaderBackground />

      <div className="flex-1 flex relative z-10 w-full max-w-full min-w-0">
        {/* Desktop Side Navigation Bar */}
        <SideNavBar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex flex-col md:hidden p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-surface-container pb-4 bg-surface-container-lowest p-4 rounded-xl">
              <span className="font-bold text-base text-primary font-headline-sm">
                GlucoShield Metabolic AI
              </span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="text-on-surface-variant p-1 rounded-lg hover:bg-surface-container"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 space-y-1.5 overflow-y-auto bg-surface-container-lowest p-3 rounded-xl shadow-lg border border-surface-container">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;

                return (
                  <button
                    key={item.id}
                    data-testid={`mobile-nav-item-${item.id}`}
                    onClick={() => {
                      setActiveTab(item.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary-container text-on-primary-container font-semibold"
                        : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <div className="md:pl-64 flex-1 flex flex-col min-w-0 max-w-full overflow-x-hidden">
          <Header
            isDemoMode={isDemoMode}
            setIsDemoMode={setIsDemoMode}
            backendHealth={backendHealth}
            currentScenario={currentScenario}
            setCurrentScenario={setCurrentScenario}
            onRefresh={() => {
              if (historyReadings.length >= 96) {
                runForecast(historyReadings.slice(-96), patientProfile, null, patientProfile?.id || activePatientId);
              }
            }}
            isLoading={isLoadingForecast}
            mobileMenuOpen={mobileMenuOpen}
            setMobileMenuOpen={setMobileMenuOpen}
            user={user}
            isAuthenticated={isAuthenticated}
            patientProfile={patientProfile}
            onOpenAuthModal={() => setAuthModalOpen(true)}
            onOpenOnboarding={() => setOnboardingModalOpen(true)}
            onLogout={logout}
            activePatientId={activePatientId}
            onSelectPatient={handleSelectPatient}
          />

          <main className="flex-1 w-full max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-7 py-5 space-y-6 min-w-0">
            {/* Global Demo Mode Disclaimer Banner */}
            {isSynthetic && (
              <div className="flex items-center justify-between px-4 py-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 font-mono text-xs font-semibold shadow-xs">
                <div className="flex items-center gap-2">
                  <span className="text-base">⚠️</span>
                  <span>SYNTHETIC DEMONSTRATION DATA • SYSTEM VALIDATION ONLY • NOT CLINICAL EVIDENCE</span>
                </div>
                <span className="text-[11px] opacity-80 hidden md:inline">Demo Patient: DEMO-SYNTHETIC-PATIENT-001 (Isolated Sandbox)</span>
              </div>
            )}

            {/* Error banner if any */}
            {errorMessage && (
              <div className="p-3.5 rounded-xl bg-error-container/80 border border-error/30 text-on-error-container text-xs font-mono">
                {errorMessage}
              </div>
            )}

            {/* SCREEN 1: DASHBOARD */}
            {activeTab === "dashboard" && (
              <div className="space-y-6">
                {/* Stitch-Aligned Top 4 Cards Grid & Clinical Downside Notice */}
                <DashboardTopCards
                  currentState={forecastData?.current_state}
                  latestReading={historyReadings?.[historyReadings.length - 1]}
                  forecastData={forecastData}
                  historyReadings={historyReadings}
                  riskAssessment={forecastData?.risk_assessment}
                  patientProfile={patientProfile}
                />

                {/* Hero 5-Hour Horizon Predictive Forecast */}
                <div className="grid grid-cols-1 gap-space-lg">
                  <ForecastChart
                    historyReadings={historyReadings}
                    forecastData={forecastData}
                    whatIfTrajectory={whatIfResult?.simulated_trajectory}
                    isLoading={isLoadingForecast}
                    isDemoMode={isSynthetic}
                    errorMessage={errorMessage}
                    onRetry={() => {
                      if (historyReadings.length >= 96) {
                        runForecast(historyReadings.slice(-96), patientProfile, null, patientProfile?.id);
                      }
                    }}
                  />
                </div>

                {/* Stitch-Aligned Expandable Accordions for Secondary Details */}
                <DashboardAccordions
                  forecastData={forecastData}
                  historyReadings={historyReadings}
                  persistedRecentEvents={persistedRecentEvents}
                  onNavigateToTab={setActiveTab}
                />
              </div>
            )}

            {/* SCREEN: COMPARATIVE GLUCOSE INTELLIGENCE */}
            {activeTab === "comparison" && (
              <ComparativeGlucoseIntelligence
                cohortData={cohortData}
                comparisonData={comparisonData}
                activePatientId={activePatientId}
                onSelectPatient={handleSelectPatient}
              />
            )}

            {/* SCREEN 2: PATIENT PROFILE */}
            {activeTab === "profile" && (
              <PatientProfilePanel
                staticProfile={staticProfile}
                onUpdateProfile={handleSavePatientProfile}
                user={user}
                patientProfile={patientProfile}
                onOpenOnboarding={() => setOnboardingModalOpen(true)}
              />
            )}

            {/* SCREEN 3: 5-HOUR FORECAST */}
            {activeTab === "forecast" && (
              <ForecastView
                forecastData={forecastData}
                historyReadings={historyReadings}
                whatIfTrajectory={whatIfResult?.simulated_trajectory}
                isLoading={isLoadingForecast}
                onRefresh={() => {
                  if (historyReadings.length >= 96) {
                    runForecast(historyReadings.slice(-96), patientProfile, null, patientProfile?.id || activePatientId);
                  }
                }}
              />
            )}

            {/* SCREEN 4: DIGITAL TWIN */}
            {activeTab === "digital_twin" && (
              <DigitalTwinVisualizer
                forecastData={forecastData}
                staticProfile={staticProfile}
                onRefresh={() => {
                  if (historyReadings.length >= 96) {
                    runForecast(historyReadings.slice(-96), patientProfile, null, patientProfile?.id || activePatientId);
                  }
                }}
              />
            )}

            {/* SCREEN 5: WHAT-IF SIMULATION */}
            {activeTab === "what_if" && (
              <WhatIfSimulator
                onSimulate={runWhatIfSimulation}
                whatIfResult={whatIfResult}
                isSimulating={isSimulatingWhatIf}
                onTransferToDecision={handleTransferToDecision}
                forecastData={forecastData}
                transferredMeal={transferredMeal}
                onClearTransferredMeal={() => setTransferredMeal(null)}
              />
            )}

            {/* SCREEN 6: FOOD VISION */}
            {activeTab === "food_vision" && (
              <MealAnalysisWorkflow
                onAnalyzeMeal={runMealAnalysis}
                analysisResult={mealAnalysisResult}
                isAnalyzing={isAnalyzingMeal}
                onTransferToWhatIf={handleTransferToWhatIf}
              />
            )}

            {/* SCREEN 7: RISK & EXPLANATION */}
            {activeTab === "risk_explanation" && (
              <RiskExplanationView forecastData={forecastData} />
            )}

            {/* SCREEN 8: HISTORY */}
            {activeTab === "history" && (
              <HistoryPanel
                token={token}
                patientProfile={patientProfile}
                isDemoMode={isDemoMode}
                historyReadings={historyReadings}
                cohortPatient={activePatientId === "PATIENT_B" ? cohortData?.patientB : cohortData?.patientA}
              />
            )}

            {/* SCREEN 9: SETTINGS */}
            {activeTab === "settings" && (
              <SettingsPanel backendHealth={backendHealth} />
            )}

            {/* OPTIONAL EXTENSIONS */}
            {activeTab === "decision_center" && (
              <DecisionCenterView
                onExecuteFullFlow={runFullDecisionFlow}
                fullFlowResult={fullFlowResult}
                isExecuting={isExecutingFullFlow}
              />
            )}

            {activeTab === "analytics" && (
              <LongitudinalAnalytics
                patientId={patientProfile?.id}
                token={token}
                isAuthenticated={isAuthenticated}
                isDemoMode={isDemoMode}
              />
            )}

            {activeTab === "wearables" && (
              <WearableContextPanel
                wearableContext={wearableContext}
                onUpdateWearable={updateWearableContext}
              />
            )}

            {activeTab === "system" && (
              <SystemSpecsPanel backendHealth={backendHealth} />
            )}
          </main>

          <DisclaimerModal />
        </div>
      </div>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onLogin={login}
        onRegister={register}
        authError={authError}
        setAuthError={setAuthError}
        onRegistered={() => setOnboardingModalOpen(true)}
      />

      {/* Guided Customer Setup & CGM Ingestion Modal */}
      <CustomerOnboardingModal
        isOpen={onboardingModalOpen}
        onClose={() => setOnboardingModalOpen(false)}
        token={token}
        user={user}
        patientProfile={patientProfile}
        onUpdatePatientProfile={handleSavePatientProfile}
        onIngestSuccess={async () => {
          if (token && patientProfile?.id) {
            try {
              const cgmRecords = await apiGetCGMHistory(token, patientProfile.id, 96);
              if (Array.isArray(cgmRecords) && cgmRecords.length > 0) {
                const sorted = [...cgmRecords].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                const formatted = sorted.map((r) => ({
                  timestamp: r.timestamp || null,
                  cgm_glucose: Number(r.cgm_glucose),
                  insulin_bolus: Number(r.insulin_bolus || 0.0),
                  insulin_basal: Number(r.insulin_basal || 0.0),
                  meal_carbs: Number(r.meal_carbs || 0.0)
                })).filter((r) => typeof r.cgm_glucose === "number" && !isNaN(r.cgm_glucose) && r.cgm_glucose >= 20 && r.cgm_glucose <= 600);
                setHistoryReadings(formatted);
              }
            } catch (e) {
              console.warn("[App] Post-ingestion history refresh failed:", e.message);
            }
          }
        }}
        onTriggerForecast={async () => {
          if (historyReadings && historyReadings.length >= 96) {
            await runForecast(historyReadings.slice(-96), patientProfile, null, patientProfile?.id);
          } else {
            await runForecast();
          }
        }}
        isLoadingForecast={isLoadingForecast}
      />
    </div>
  );
}

export default App;
