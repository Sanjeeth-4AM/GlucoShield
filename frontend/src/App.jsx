import React, { useState } from "react";
import { useGlucoShieldAPI } from "./hooks/useGlucoShieldAPI.js";
import { SideNavBar, NAV_ITEMS } from "./components/layout/SideNavBar.jsx";
import { Header } from "./components/layout/Header.jsx";
import { MetabolicShaderBackground } from "./components/layout/MetabolicShaderBackground.jsx";
import { DisclaimerModal } from "./components/layout/DisclaimerModal.jsx";

// Specialized Views
import { CurrentGlucoseCard } from "./components/dashboard/CurrentGlucoseCard.jsx";
import { ForecastChart } from "./components/dashboard/ForecastChart.jsx";
import { RiskGaugePanel } from "./components/dashboard/RiskGaugePanel.jsx";
import { ExplanationCard } from "./components/dashboard/ExplanationCard.jsx";
import { DigitalTwinVisualizer } from "./components/digitalTwin/DigitalTwinVisualizer.jsx";
import { WhatIfSimulator } from "./components/whatIf/WhatIfSimulator.jsx";
import { MealAnalysisWorkflow } from "./components/foodVision/MealAnalysisWorkflow.jsx";
import { DecisionCenterView } from "./components/decisionCenter/DecisionCenterView.jsx";
import { WearableContextPanel } from "./components/wearables/WearableContextPanel.jsx";
import { PatientProfilePanel } from "./components/profile/PatientProfilePanel.jsx";
import { SystemSpecsPanel } from "./components/system/SystemSpecsPanel.jsx";

export function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const {
    isDemoMode,
    setIsDemoMode,
    currentScenario,
    setCurrentScenario,
    backendHealth,
    historyReadings,
    forecastData,
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
    runFullDecisionFlow,
    updateStaticProfile,
    updateWearableContext
  } = useGlucoShieldAPI();

  const handleTransferToWhatIf = (confirmedCarbs) => {
    runWhatIfSimulation({ meal_carbs_g: confirmedCarbs, bolus_insulin_u: 4.5 });
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
    <div className="bg-[#0c1324] text-[#dce1fb] min-h-screen flex flex-col relative selection:bg-[#00daf3] selection:text-[#001f24]">
      {/* Background Ambient Metabolic Shader */}
      <MetabolicShaderBackground />

      <div className="flex-1 flex relative z-10">
        {/* Desktop Side Navigation Bar */}
        <SideNavBar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex flex-col md:hidden p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-white/10 pb-4">
              <span className="font-bold text-lg text-[#00daf3] font-mono">GLUCOSHIELD COMMAND</span>
              <button onClick={() => setMobileMenuOpen(false)} className="text-white p-1">✕</button>
            </div>
            <div className="flex-1 space-y-2 overflow-y-auto">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActiveTab(item.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl font-mono text-xs uppercase ${
                      activeTab === item.id ? "bg-[#00daf3]/20 text-[#00daf3] font-bold border border-[#00daf3]/40" : "text-[#bac9cc]"
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
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          <Header
            isDemoMode={isDemoMode}
            setIsDemoMode={setIsDemoMode}
            backendHealth={backendHealth}
            currentScenario={currentScenario}
            setCurrentScenario={setCurrentScenario}
            onRefresh={runForecast}
            isLoading={isLoadingForecast}
            mobileMenuOpen={mobileMenuOpen}
            setMobileMenuOpen={setMobileMenuOpen}
          />

          <main className="flex-1 p-4 lg:p-8 space-y-6 max-w-7xl w-full mx-auto">
            {/* Error banner if any */}
            {errorMessage && (
              <div className="p-3.5 rounded-xl bg-[#ef4444]/15 border border-[#ef4444]/40 text-[#ffdad6] text-xs font-mono">
                {errorMessage}
              </div>
            )}

            {/* TAB 1: MAIN GLUCOSE INTELLIGENCE DASHBOARD */}
            {activeTab === "dashboard" && (
              <div className="space-y-6">
                {/* Hero Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  {/* Left Hero Column: Current Glucose & Pods */}
                  <div className="lg:col-span-4">
                    <CurrentGlucoseCard
                      currentState={forecastData?.current_state}
                      hybridComponents={forecastData?.hybrid_components}
                      riskAssessment={forecastData?.risk_assessment}
                    />
                  </div>

                  {/* Right Hero Column: 5-Hour Horizon Predictive Chart */}
                  <div className="lg:col-span-8">
                    <ForecastChart
                      historyReadings={historyReadings}
                      forecastData={forecastData}
                      whatIfTrajectory={whatIfResult?.simulated_trajectory}
                    />
                  </div>
                </div>

                {/* Bottom Row: Risk Gauge + Interpretable AI Explanation */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <RiskGaugePanel riskAssessment={forecastData?.risk_assessment} />
                  <ExplanationCard
                    explanations={forecastData?.explanations}
                    hybridComponents={forecastData?.hybrid_components}
                  />
                </div>
              </div>
            )}

            {/* TAB 2: LIVING DIGITAL TWIN */}
            {activeTab === "digital_twin" && (
              <DigitalTwinVisualizer
                forecastData={forecastData}
                staticProfile={staticProfile}
              />
            )}

            {/* TAB 3: FORECAST & RISK */}
            {activeTab === "forecast" && (
              <div className="space-y-6">
                <ForecastChart
                  historyReadings={historyReadings}
                  forecastData={forecastData}
                  whatIfTrajectory={whatIfResult?.simulated_trajectory}
                />
                <RiskGaugePanel riskAssessment={forecastData?.risk_assessment} />
              </div>
            )}

            {/* TAB 4: WHAT-IF PHYSIOLOGY LAB */}
            {activeTab === "what_if" && (
              <WhatIfSimulator
                onSimulate={runWhatIfSimulation}
                whatIfResult={whatIfResult}
                isSimulating={isSimulatingWhatIf}
                onTransferToDecision={handleTransferToDecision}
              />
            )}

            {/* TAB 5: FOOD VISION & USDA */}
            {activeTab === "food_vision" && (
              <MealAnalysisWorkflow
                onAnalyzeMeal={runMealAnalysis}
                analysisResult={mealAnalysisResult}
                isAnalyzing={isAnalyzingMeal}
                onTransferToWhatIf={handleTransferToWhatIf}
              />
            )}

            {/* TAB 6: DECISION CENTER */}
            {activeTab === "decision_center" && (
              <DecisionCenterView
                onExecuteFullFlow={runFullDecisionFlow}
                fullFlowResult={fullFlowResult}
                isExecuting={isExecutingFullFlow}
              />
            )}

            {/* TAB 7: WEARABLES */}
            {activeTab === "wearables" && (
              <WearableContextPanel
                wearableContext={wearableContext}
                onUpdateWearable={updateWearableContext}
              />
            )}

            {/* TAB 8: PATIENT PROFILE */}
            {activeTab === "profile" && (
              <PatientProfilePanel
                staticProfile={staticProfile}
                onUpdateProfile={updateStaticProfile}
              />
            )}

            {/* TAB 9: SYSTEM SPECS */}
            {activeTab === "system" && (
              <SystemSpecsPanel backendHealth={backendHealth} />
            )}
          </main>

          <DisclaimerModal />
        </div>
      </div>
    </div>
  );
}

export default App;
