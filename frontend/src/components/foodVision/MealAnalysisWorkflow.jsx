import React, { useState, useEffect } from "react";
import {
  Utensils,
  Camera,
  Search,
  CheckCircle,
  Sparkles,
  RefreshCw,
  Sliders,
  ShieldCheck,
  Layers,
  Info,
  Upload,
  AlertTriangle,
  ListPlus
} from "lucide-react";

// Standard reference components for composite South Indian Thali breakdown
const DEFAULT_THALI_INGREDIENTS = [
  { name: "Steamed White Rice", portionG: 150, carbsPer100g: 28.2, proteinPer100g: 2.7, fatPer100g: 0.3 },
  { name: "Dal / Sambar (Lentils)", portionG: 100, carbsPer100g: 19.5, proteinPer100g: 9.0, fatPer100g: 0.4 },
  { name: "Vegetable Curry / Poriyal", portionG: 80, carbsPer100g: 8.5, proteinPer100g: 2.0, fatPer100g: 4.5 },
  { name: "Plain Curd / Yogurt", portionG: 50, carbsPer100g: 3.6, proteinPer100g: 10.0, fatPer100g: 0.4 },
  { name: "Roasted Papad", portionG: 15, carbsPer100g: 33.2, proteinPer100g: 5.1, fatPer100g: 17.5 }
];

export function MealAnalysisWorkflow({
  onAnalyzeMeal,
  analysisResult,
  isAnalyzing,
  onTransferToWhatIf
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [userImage, setUserImage] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showUpload, setShowUpload] = useState(true);
  const [portionG, setPortionG] = useState(250.0);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [ingredients, setIngredients] = useState(DEFAULT_THALI_INGREDIENTS);

  // Authoritative Confirmation State Machine:
  // "EMPTY" -> "INPUT_PROVIDED" -> "ESTIMATE_AVAILABLE" -> "AWAITING_CONFIRMATION" -> "CONFIRMED" -> "TRANSFERRED"
  const [workflowState, setWorkflowState] = useState("EMPTY");

  // Extract from backend analysisResult if present
  const hasAnalysis = Boolean(analysisResult && (analysisResult.selected_food || analysisResult.final_macros || analysisResult.nutrition_density));
  const macros = analysisResult?.final_macros || analysisResult?.macronutrients || {};
  const density = analysisResult?.nutrition_density || analysisResult?.nutrition || null;
  const foodName = analysisResult?.selected_food || (hasAnalysis ? "Identified Meal" : "Awaiting Meal Input");
  const candidates = analysisResult?.image_food_candidates || analysisResult?.candidates || [];
  const warnings = [
    ...(analysisResult?.warnings || []),
    ...(density?.warnings || [])
  ].filter((w, i, arr) => arr.indexOf(w) === i);

  const isCompositeMeal = Boolean(
    (foodName && (foodName.toLowerCase().includes("thali") || foodName.toLowerCase().includes("platter") || foodName.toLowerCase().includes("combo"))) ||
    (density?.food_name && density.food_name.toLowerCase().includes("thali"))
  );

  // Strictly distinguish true numeric values from null (unavailable in USDA)
  const rawCarbs = (macros.carbs_g !== undefined ? macros.carbs_g : macros.carbohydrates_g);
  const estCarbs = rawCarbs !== null && rawCarbs !== undefined && !isNaN(Number(rawCarbs))
    ? Math.round(Number(rawCarbs) * 10) / 10
    : null;

  const rawProtein = macros.protein_g;
  const protein = rawProtein !== null && rawProtein !== undefined && !isNaN(Number(rawProtein))
    ? Math.round(Number(rawProtein) * 10) / 10
    : null;

  const rawFat = macros.fat_g;
  const fat = rawFat !== null && rawFat !== undefined && !isNaN(Number(rawFat))
    ? Math.round(Number(rawFat) * 10) / 10
    : null;

  const rawCals = macros.calories_kcal;
  const calories = rawCals !== null && rawCals !== undefined && !isNaN(Number(rawCals))
    ? Math.round(Number(rawCals))
    : null;

  const [confirmedCarbs, setConfirmedCarbs] = useState(estCarbs ?? 0);

  // Sync portion if analysisResult has an explicit portion_g
  useEffect(() => {
    if (analysisResult?.portion_g != null) {
      setPortionG(analysisResult.portion_g);
    }
  }, [analysisResult?.portion_g]);

  // Synchronize state when analysis result updates
  useEffect(() => {
    if (isAnalyzing) {
      setWorkflowState("INPUT_PROVIDED");
    } else if (hasAnalysis) {
      if (estCarbs !== null) {
        setConfirmedCarbs(estCarbs);
      } else {
        setConfirmedCarbs(0);
      }
      setWorkflowState("AWAITING_CONFIRMATION");
    } else {
      setWorkflowState("EMPTY");
    }
  }, [analysisResult, isAnalyzing, estCarbs, hasAnalysis]);

  // Transition: Human Confirmation
  const handleConfirm = () => {
    if (!hasAnalysis) return;
    if (confirmedCarbs <= 0 && estCarbs === null && !isEditing) {
      setIsEditing(true);
      return;
    }
    setWorkflowState("CONFIRMED");
    setIsEditing(false);
  };

  // Transition: Transfer to What-If simulation
  const handleTransfer = () => {
    if (workflowState !== "CONFIRMED" || confirmedCarbs <= 0) return;
    setWorkflowState("TRANSFERRED");
    if (onTransferToWhatIf) {
      onTransferToWhatIf({
        carbs_g: Number(confirmedCarbs),
        food_name: foodName || "Confirmed Meal",
        portion_g: Number(portionG) || 250,
        source: "food_vision",
        is_confirmed: true,
        transferred_at: new Date().toISOString()
      });
    }
  };

  // Invalidate confirmation on any input modification
  const invalidateConfirmation = () => {
    if (workflowState === "CONFIRMED" || workflowState === "TRANSFERRED") {
      setWorkflowState("AWAITING_CONFIRMATION");
    }
  };

  const handleImageFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      invalidateConfirmation();
      const url = URL.createObjectURL(file);
      setUserImage(url);
      setWorkflowState("INPUT_PROVIDED");

      // Read image as Base64 Data URL and trigger real vision inference
      const reader = new FileReader();
      reader.onload = (event) => {
        const b64 = event.target?.result;
        if (b64 && onAnalyzeMeal) {
          onAnalyzeMeal({
            image_base64: b64,
            portion_g: Number(portionG) || 250.0
          });
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (onAnalyzeMeal && searchQuery.trim()) {
      invalidateConfirmation();
      setWorkflowState("INPUT_PROVIDED");
      onAnalyzeMeal({
        food_name_query: searchQuery.trim(),
        portion_g: Number(portionG) || 250.0
      });
    }
  };

  const handleSelectCandidate = (idx) => {
    if (onAnalyzeMeal && candidates[idx]) {
      invalidateConfirmation();
      setWorkflowState("INPUT_PROVIDED");
      const candName = candidates[idx].name || candidates[idx].food_name || candidates[idx].raw_label;
      onAnalyzeMeal({
        food_name_query: candName,
        portion_g: Number(portionG) || 250.0,
        selected_candidate_index: idx
      });
    }
  };

  const handleIngredientPortionChange = (idx, newPortion) => {
    invalidateConfirmation();
    setIngredients((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, portionG: Math.max(0, Number(newPortion) || 0) } : item))
    );
  };

  const handleApplyIngredientBreakdown = () => {
    invalidateConfirmation();
    const totalCarbs = ingredients.reduce((sum, item) => sum + (item.carbsPer100g * (item.portionG / 100)), 0);
    const totalPortion = ingredients.reduce((sum, item) => sum + item.portionG, 0);
    const roundedCarbs = Math.round(totalCarbs * 10) / 10;
    setConfirmedCarbs(roundedCarbs);
    setPortionG(Math.round(totalPortion));
    setShowBreakdown(false);
  };

  return (
    <div className="flex flex-col w-full space-y-6">
      {/* Top Bar / Breadcrumb Context */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-space-lg mb-space-lg">
        <div className="flex flex-col gap-space-xs">
          <div className="flex items-center gap-space-xs text-primary font-code-sm text-code-sm uppercase tracking-wider font-semibold">
            <span>Vision Telemetry Status: Food Classification Pipeline</span>
            <span className="text-outline-variant">•</span>
            <span>Food-101 &amp; USDA Nutrition Engine</span>
          </div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface">
            Food Vision &amp; Meal Glycemic Impact
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
            Computer vision food classification, USDA macronutrient decomposition, and counterfactual simulation for insulin bolus precision.
          </p>
        </div>

        <div className="mt-space-md lg:mt-0 flex items-center gap-space-md self-start lg:self-center">
          <div className="bg-surface-container px-space-md py-space-sm rounded-xl flex items-center gap-space-sm border border-surface-container">
            <span className={`w-2.5 h-2.5 rounded-full ${
              workflowState === "TRANSFERRED"
                ? "bg-primary"
                : workflowState === "CONFIRMED"
                ? "bg-tertiary"
                : workflowState === "INPUT_PROVIDED"
                ? "bg-amber-500 animate-pulse"
                : "bg-outline"
            }`}></span>
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface font-semibold">
                Event: Food Vision Pipeline
              </span>
              <span className={`font-code-sm text-code-sm font-medium ${
                workflowState === "CONFIRMED" || workflowState === "TRANSFERRED"
                  ? "text-tertiary"
                  : "text-on-surface-variant"
              }`}>
                Status: {
                  workflowState === "TRANSFERRED"
                    ? "Transferred to What-If ✓"
                    : workflowState === "CONFIRMED"
                    ? "Human Verified ✓"
                    : workflowState === "INPUT_PROVIDED"
                    ? "Analyzing Meal Input..."
                    : workflowState === "AWAITING_CONFIRMATION" || workflowState === "ESTIMATE_AVAILABLE"
                    ? "Pending Confirmation"
                    : "No Meal Input"
                }
              </span>
            </div>
          </div>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="bg-primary text-on-primary hover:bg-surface-tint font-label-sm text-label-sm px-space-md py-space-sm rounded-lg flex items-center gap-space-xs transition-colors shadow-sm"
          >
            <Camera className="w-4 h-4" />
            <span>Analyze New Meal</span>
          </button>
        </div>
      </div>

      {/* Upload / Search Drawer */}
      {showUpload && (
        <div className="mb-6 p-4 bg-surface-container-lowest rounded-xl shadow-sm border border-surface-container flex flex-col gap-3">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-3 text-on-surface-variant" />
              <input
                type="text"
                placeholder="Enter meal description (e.g. 'South Indian thali', 'Grilled chicken bowl with rice')"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  invalidateConfirmation();
                }}
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-surface-container-low border border-surface-container text-sm text-on-surface"
              />
            </div>
            <div className="flex items-center gap-1 bg-surface-container-low border border-surface-container rounded-lg px-3 py-1">
              <label htmlFor="portion-input" className="text-xs text-on-surface-variant whitespace-nowrap">Portion:</label>
              <input
                id="portion-input"
                type="number"
                min="10"
                max="2500"
                step="10"
                value={portionG}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setPortionG(val);
                  invalidateConfirmation();
                }}
                className="w-16 py-1 bg-transparent text-sm text-on-surface text-right font-medium focus:outline-none"
              />
              <span className="text-xs text-on-surface-variant font-medium">g</span>
            </div>
            <button
              type="submit"
              disabled={isAnalyzing}
              className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary-container disabled:opacity-50 whitespace-nowrap transition-colors"
            >
              {isAnalyzing ? "Querying USDA..." : "Decompose Meal"}
            </button>
          </form>

          <div className="flex items-center justify-between pt-2 border-t border-surface-container flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container text-xs font-semibold text-on-surface cursor-pointer hover:bg-surface-container-high transition-colors">
                <Upload className="w-3.5 h-3.5" />
                <span>Upload Plate Photo</span>
                <input type="file" accept="image/*" onChange={handleImageFileChange} className="hidden" />
              </label>
              <span className="text-xs text-on-surface-variant">Food-101 top-k classification + USDA FoodData Central mapping</span>
            </div>
            {userImage && (
              <span className="text-xs text-primary font-medium">Photo loaded for inference ✓</span>
            )}
          </div>
        </div>
      )}

      {/* Primary Asymmetric Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 items-start">
        {/* LEFT COLUMN: Image Analysis, Semantic Overlays & Visual Breakdown (Cols 1-5) */}
        <div className="lg:col-span-5 flex flex-col gap-space-lg">
          {/* Card: Meal Visual Decomposition */}
          <div className="bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm border border-surface-container flex flex-col gap-space-md relative overflow-hidden">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <Utensils className="w-5 h-5 text-primary" />
                <span className="font-headline-sm text-headline-sm text-on-surface">Meal Photograph &amp; CV Input</span>
              </div>
              <span className="bg-surface-container-high text-on-surface-variant font-code-sm text-code-sm px-space-xs py-0.5 rounded">
                Food-101 Classifier
              </span>
            </div>

            {/* User-Uploaded Image or Clean Capture Canvas */}
            <div className="relative w-full h-72 rounded-xl overflow-hidden bg-surface-container-low shadow-inner flex flex-col items-center justify-center border border-dashed border-surface-container select-none">
              {userImage ? (
                <img
                  alt="Uploaded meal"
                  className="w-full h-full object-cover"
                  src={userImage}
                />
              ) : (
                <div className="flex flex-col items-center text-center p-space-md">
                  <Camera className="w-10 h-10 text-outline mb-2" />
                  <span className="font-label-md text-label-md text-on-surface font-semibold mb-1">
                    No Plate Photograph Uploaded
                  </span>
                  <p className="font-body-sm text-body-sm text-on-surface-variant max-w-xs mb-3">
                    Upload an image or enter a textual meal query to trigger Food-101 classification and USDA macronutrient analysis.
                  </p>
                  <label className="px-space-md py-1.5 bg-primary text-on-primary rounded font-label-sm text-label-sm font-semibold cursor-pointer hover:bg-primary-container transition-colors shadow-sm flex items-center gap-1.5">
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload Image</span>
                    <input type="file" accept="image/*" onChange={handleImageFileChange} className="hidden" />
                  </label>
                </div>
              )}
            </div>

            {/* Architectural Truth Notice */}
            <div className="p-space-sm bg-surface-container-low rounded-lg border border-surface-container flex items-start gap-2">
              <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <p className="font-code-sm text-xs text-on-surface-variant leading-relaxed">
                <strong>Model Scope Note:</strong> Image classification uses Food-101 (101 standard categories). Unlisted regional dishes or mixed composite plates require manual text description or ingredient breakdown below.
              </p>
            </div>

            {/* Detected Food Classes List */}
            <div className="flex flex-col gap-space-xs pt-space-xs">
              <div className="flex items-center justify-between">
                <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
                  Classification Candidates
                </span>
                {candidates.length > 0 && (
                  <span className="text-[11px] text-outline font-code-sm">
                    {candidates.some((c) => c.source === "manual_user_entry" || c.source === "text_search" || c.confidence == null)
                      ? "User Description / Query"
                      : "Top-k Model Predictions"}
                  </span>
                )}
              </div>

              {isAnalyzing ? (
                <div className="p-space-sm bg-surface-container-low rounded-lg border border-surface-container text-xs text-on-surface-variant font-mono text-center flex items-center justify-center gap-2">
                  <span className="w-3 h-3 rounded-full border-2 border-primary border-t-transparent animate-spin inline-block"></span>
                  Processing visual inference and USDA mapping...
                </div>
              ) : candidates.length > 0 ? (
                candidates.map((c, idx) => {
                  const candName = c.name || c.food_name || c.class_name || c.raw_label || "Identified Item";
                  const isSelected = foodName === candName || (analysisResult?.selected_candidate_index === idx);
                  const isManualOrText = c.source === "manual_user_entry" || c.source === "text_search" || c.confidence == null;
                  const isLowConf = !isManualOrText && c.confidence != null && c.confidence < 0.50;
                  return (
                    <div
                      key={idx}
                      className={`flex items-center justify-between p-space-sm rounded-lg border transition-colors ${
                        isSelected
                          ? "bg-primary/10 border-primary/40 shadow-xs"
                          : "bg-surface-container-low border-surface-container hover:bg-surface-container"
                      }`}
                    >
                      <div className="flex items-center gap-space-sm">
                        <span className={`w-2.5 h-2.5 rounded-full ${isSelected ? "bg-primary animate-pulse" : "bg-outline"}`}></span>
                        <div className="flex flex-col">
                          <span className="font-label-md text-label-md text-on-surface font-medium">
                            {candName}
                          </span>
                          {isLowConf && (
                            <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium">
                              Low visual confidence
                            </span>
                          )}
                          {isManualOrText && (
                            <span className="text-[10px] text-outline font-code-sm">
                              User text search entry
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-space-sm font-code-sm text-code-sm">
                        {isManualOrText ? (
                          <span className="text-[11px] text-on-surface-variant bg-surface-container px-1.5 py-0.5 rounded font-mono font-medium">
                            Text Match
                          </span>
                        ) : (
                          <span className={`font-semibold ${isLowConf ? "text-amber-600 dark:text-amber-400" : "text-primary"}`}>
                            {(c.confidence * 100).toFixed(1)}%
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => handleSelectCandidate(idx)}
                          className={`px-2 py-0.5 rounded text-xs transition-colors cursor-pointer ${
                            isSelected
                              ? "bg-primary text-on-primary font-semibold"
                              : "bg-surface-container text-on-surface-variant hover:bg-primary hover:text-on-primary"
                          }`}
                        >
                          {isSelected ? "Selected ✓" : "Select"}
                        </button>
                      </div>
                    </div>
                  );
                })
              ) : userImage ? (
                <div className="p-space-sm bg-surface-container-low rounded-lg border border-surface-container text-xs text-on-surface-variant text-center space-y-1">
                  {warnings.some((w) => w.toLowerCase().includes("visual classification unavailable")) ? (
                    <>
                      <div className="text-amber-600 dark:text-amber-400 font-semibold">Visual Recognition Engine Offline / Unavailable</div>
                      <div className="text-on-surface-variant">
                        {warnings.find((w) => w.toLowerCase().includes("visual classification unavailable"))}
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="text-amber-600 dark:text-amber-400 font-semibold">Image classification unavailable / unlisted</div>
                      <div>No food items recognized from photo in Food-101 vocabulary. Use the text search above to find USDA records.</div>
                    </>
                  )}
                </div>
              ) : (
                <div className="p-space-sm bg-surface-container-low rounded-lg border border-surface-container text-xs text-on-surface-variant font-mono text-center">
                  Upload meal photo or enter a food query to view candidate classifications.
                </div>
              )}
            </div>
          </div>

          {/* Quick Safety Notice */}
          <div className="bg-surface-container-low p-space-md rounded-xl flex items-start gap-space-sm border border-surface-container">
            <ShieldCheck className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div className="flex flex-col gap-0.5">
              <span className="font-label-md text-label-md text-on-surface font-semibold">
                Clinical Verification Protocol
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Food Vision estimates are never automatically executed. Bolus simulations require explicit human-in-the-loop confirmation.
              </span>
            </div>
          </div>
        </div>

        {/* CENTER COLUMN: Estimated vs Confirmed Nutritional Breakdown (Cols 6-8) */}
        <div className="lg:col-span-4 flex flex-col gap-space-lg">
          <div className="bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm border border-surface-container flex flex-col gap-space-md">
            <div className="flex items-start justify-between gap-2">
              <div className="flex flex-col">
                <h2 className="font-headline-sm text-headline-sm text-on-surface">
                  {foodName}
                </h2>
                {density?.food_name && density.food_name !== foodName && (
                  <span className="text-xs text-on-surface-variant font-code-sm mt-0.5">
                    USDA Match: <strong className="text-on-surface">{density.food_name}</strong>
                  </span>
                )}
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-on-surface-variant font-code-sm">Portion:</span>
                  <input
                    type="number"
                    min="10"
                    max="2000"
                    step="10"
                    value={portionG}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setPortionG(val);
                      invalidateConfirmation();
                    }}
                    className="w-16 px-1.5 py-0.5 rounded bg-surface-container text-xs text-on-surface font-mono border border-surface-container text-right"
                  />
                  <span className="text-xs text-on-surface-variant font-code-sm">g</span>
                  {hasAnalysis && foodName && foodName !== "Awaiting Meal Input" && (
                    <button
                      type="button"
                      onClick={() => {
                        if (onAnalyzeMeal) {
                          invalidateConfirmation();
                          onAnalyzeMeal({
                            food_name_query: foodName,
                            portion_g: Number(portionG) || 250.0
                          });
                        }
                      }}
                      className="text-xs text-primary hover:underline font-code-sm px-1.5 py-0.5 rounded hover:bg-primary/10 transition-colors"
                    >
                      Scale
                    </button>
                  )}
                </div>
              </div>
              <span className={`font-code-sm text-code-sm px-2 py-0.5 rounded font-semibold border shrink-0 ${
                workflowState === "TRANSFERRED"
                  ? "bg-primary/10 text-primary border-primary/30"
                  : workflowState === "CONFIRMED"
                  ? "bg-tertiary/10 text-tertiary border-tertiary/30"
                  : "bg-surface-container-high text-on-surface-variant border-surface-container"
              }`}>
                {workflowState === "TRANSFERRED"
                  ? "TRANSFERRED ✓"
                  : workflowState === "CONFIRMED"
                  ? "CONFIRMED ✓"
                  : hasAnalysis
                  ? "PENDING CONFIRMATION"
                  : "AWAITING INPUT"}
              </span>
            </div>

            {/* Warnings Banner if any */}
            {warnings.length > 0 && (
              <div className="p-space-sm bg-amber-500/10 border border-amber-500/20 rounded-lg flex flex-col gap-1">
                <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-semibold text-xs">
                  <Info className="w-3.5 h-3.5" />
                  <span>Clinical Composition Notice</span>
                </div>
                {warnings.map((w, idx) => (
                  <p key={idx} className="text-xs text-on-surface-variant font-body-sm leading-relaxed pl-5">
                    • {w}
                  </p>
                ))}
              </div>
            )}

            {/* Step-by-Step State Machine Tracker */}
            <div className="flex items-center gap-space-sm p-space-xs bg-surface-container rounded-lg font-code-sm text-code-sm overflow-x-auto">
              <span className={`px-2 py-0.5 rounded font-semibold ${
                hasAnalysis
                  ? "bg-surface-container-high text-on-surface"
                  : "bg-surface-container text-outline"
              }`}>
                1. AI ESTIMATE
              </span>
              <span className="text-outline">→</span>
              <span className={`px-2 py-0.5 rounded font-semibold ${
                workflowState === "CONFIRMED" || workflowState === "TRANSFERRED"
                  ? "bg-tertiary text-on-tertiary"
                  : workflowState === "AWAITING_CONFIRMATION" || workflowState === "ESTIMATE_AVAILABLE"
                  ? "bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-500/30"
                  : "bg-surface-container text-outline"
              }`}>
                {workflowState === "CONFIRMED" || workflowState === "TRANSFERRED"
                  ? "2. CONFIRMED ✓"
                  : "2. AWAITING CONFIRMATION"}
              </span>
              <span className="text-outline">→</span>
              <span className={`px-2 py-0.5 rounded font-semibold ${
                workflowState === "TRANSFERRED"
                  ? "bg-primary text-on-primary"
                  : "bg-surface-container text-outline"
              }`}>
                {workflowState === "TRANSFERRED" ? "3. TRANSFERRED ✓" : "3. TRANSFER"}
              </span>
              <span className="text-outline-variant ml-auto text-xs hidden sm:inline">Human-in-the-loop</span>
            </div>

            {/* Metric Item 1: Carbohydrates (Key Bolus Driver) */}
            <div className="bg-surface-container-low rounded-xl p-space-md flex flex-col gap-space-sm border border-surface-container relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider">
                  Total Carbohydrates
                </span>
                <span className="bg-primary/10 text-primary font-code-sm text-code-sm px-2 py-0.5 rounded font-bold border border-primary/20">
                  Key Bolus Driver
                </span>
              </div>

              {/* Dual Stack: AI Estimate vs Confirmed */}
              <div className="grid grid-cols-2 gap-space-sm mt-space-xs">
                <div className="bg-surface-container-lowest p-space-sm rounded-lg flex flex-col border border-surface-container">
                  <span className="font-code-sm text-code-sm text-on-surface-variant flex items-center gap-1">
                    AI Estimate
                    <span className="text-xs text-outline">(USDA)</span>
                  </span>
                  <span className="font-telemetry-metric text-telemetry-metric text-on-surface mt-1">
                    {estCarbs !== null ? `${estCarbs}g CHO` : (hasAnalysis ? "Unavailable" : "—")}
                  </span>
                  <span className="font-code-sm text-code-sm text-outline">
                    {hasAnalysis && density?.carbs_g_per_100g !== null && density?.carbs_g_per_100g !== undefined
                      ? `${density.carbs_g_per_100g}g / 100g`
                      : "Per portion serving"}
                  </span>
                </div>

                <div className="bg-tertiary-container/10 p-space-sm rounded-lg flex flex-col border border-tertiary/20">
                  <span className={`font-code-sm text-code-sm flex items-center gap-1 font-semibold ${
                    workflowState === "CONFIRMED" || workflowState === "TRANSFERRED" ? "text-tertiary" : "text-on-surface-variant"
                  }`}>
                    Patient / Clinician
                    {workflowState === "CONFIRMED" || workflowState === "TRANSFERRED" ? (
                      <span className="text-xs bg-tertiary text-on-tertiary px-1 rounded">CONFIRMED ✓</span>
                    ) : (
                      <span className="text-xs bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-500/30 px-1 rounded font-medium">PENDING CONFIRMATION</span>
                    )}
                  </span>
                  {isEditing ? (
                    <div className="flex items-center gap-1 mt-0.5">
                      <input
                        type="number"
                        min="0"
                        max="500"
                        step="0.5"
                        value={confirmedCarbs}
                        onChange={(e) => {
                          setConfirmedCarbs(Math.max(0, Number(e.target.value)));
                          invalidateConfirmation();
                        }}
                        className="font-telemetry-display text-telemetry-display text-tertiary font-bold bg-transparent border-b-2 border-tertiary w-24 focus:outline-none"
                      />
                      <span className="text-tertiary font-bold">g</span>
                    </div>
                  ) : (
                    <span className="font-telemetry-display text-telemetry-display text-tertiary mt-0.5 font-bold leading-none">
                      {hasAnalysis ? `${confirmedCarbs}g` : "—"}
                    </span>
                  )}
                  <span className="font-code-sm text-code-sm text-tertiary font-medium mt-1">
                    {hasAnalysis && estCarbs !== null
                      ? `${confirmedCarbs - estCarbs >= 0 ? `+${(confirmedCarbs - estCarbs).toFixed(1)}` : (confirmedCarbs - estCarbs).toFixed(1)}g vs AI estimate`
                      : hasAnalysis && estCarbs === null
                      ? "Manual entry required"
                      : "Awaiting input"}
                  </span>
                </div>
              </div>
            </div>

            {/* Metric Item 2: Total Protein */}
            <div className="bg-surface-container-low rounded-xl p-space-md flex items-center justify-between border border-surface-container">
              <div className="flex flex-col">
                <div className="flex items-center gap-space-xs">
                  <span className="font-label-md text-label-md text-on-surface font-semibold">Total Protein</span>
                  <span className="font-code-sm text-code-sm bg-surface-container-high text-on-surface-variant px-1.5 py-0.5 rounded font-medium">
                    USDA Analysis
                  </span>
                </div>
                <span className="font-body-sm text-body-sm text-on-surface-variant">Protective lean mass intake</span>
              </div>
              <div className="text-right">
                <span className="font-telemetry-metric text-telemetry-metric text-secondary">
                  {protein !== null ? `${protein}g` : (hasAnalysis ? "Unavailable" : "—")}
                </span>
                {density?.protein_g_per_100g !== null && density?.protein_g_per_100g !== undefined && (
                  <div className="font-code-sm text-xs text-outline">{density.protein_g_per_100g}g / 100g</div>
                )}
              </div>
            </div>

            {/* Metric Item 3: Total Lipids (Fat Buffer) */}
            <div className="bg-surface-container-low rounded-xl p-space-md flex flex-col gap-space-xs border border-surface-container">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="font-label-md text-label-md text-on-surface font-semibold">Total Lipids</span>
                  <span className="font-code-sm text-code-sm bg-surface-container-high text-on-surface-variant px-1.5 py-0.5 rounded font-medium">
                    USDA Analysis
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-telemetry-metric text-telemetry-metric text-on-surface">
                    {fat !== null ? `${fat}g` : (hasAnalysis ? "Unavailable" : "—")}
                  </span>
                  {density?.fat_g_per_100g !== null && density?.fat_g_per_100g !== undefined && (
                    <div className="font-code-sm text-xs text-outline">{density.fat_g_per_100g}g / 100g</div>
                  )}
                </div>
              </div>
              <div className="bg-surface-container p-space-xs rounded flex items-center gap-space-xs">
                <span className="w-2 h-2 rounded-full bg-secondary"></span>
                <span className="font-code-sm text-code-sm text-on-secondary-container font-medium">
                  Fat-protein delayed absorption buffer evaluated
                </span>
              </div>
            </div>

            {/* Optional Composite Meal Ingredient Breakdown Accordion */}
            {isCompositeMeal && (
              <div className="bg-surface-container-low rounded-xl p-space-sm border border-surface-container flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => setShowBreakdown(!showBreakdown)}
                  className="flex items-center justify-between text-xs text-primary font-semibold hover:underline px-1"
                >
                  <span className="flex items-center gap-1.5">
                    <ListPlus className="w-3.5 h-3.5" />
                    <span>Itemized Platter Breakdown (Supply Exact Serving Weights)</span>
                  </span>
                  <span>{showBreakdown ? "▲ Hide" : "▼ Expand"}</span>
                </button>

                {showBreakdown && (
                  <div className="flex flex-col gap-2 pt-2 border-t border-surface-container">
                    <p className="text-[11px] text-on-surface-variant leading-relaxed">
                      Generic composition values are population approximations. Adjust each item's weight in grams to calculate aggregate carbohydrates from exact plate contents:
                    </p>
                    <div className="flex flex-col gap-1.5">
                      {ingredients.map((item, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs bg-surface-container p-1.5 rounded">
                          <span className="text-on-surface font-medium">{item.name}</span>
                          <div className="flex items-center gap-1">
                            <input
                              type="number"
                              min="0"
                              max="1000"
                              step="5"
                              value={item.portionG}
                              onChange={(e) => handleIngredientPortionChange(idx, e.target.value)}
                              className="w-14 px-1 py-0.5 rounded bg-surface-container-lowest text-xs text-on-surface text-right border border-surface-container font-mono"
                            />
                            <span className="text-outline text-[11px]">g</span>
                            <span className="text-primary font-mono text-[11px] w-14 text-right">
                              {((item.carbsPer100g * item.portionG) / 100).toFixed(1)}g
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={handleApplyIngredientBreakdown}
                      className="mt-1 py-1 px-3 bg-secondary text-on-secondary rounded text-xs font-semibold hover:bg-secondary-container transition-colors self-end"
                    >
                      Apply Itemized Sum ({ingredients.reduce((s, it) => s + (it.carbsPer100g * it.portionG) / 100, 0).toFixed(1)}g CHO)
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Action Controls */}
            <div className="pt-space-xs flex flex-col gap-space-sm">
              <div className="flex items-center gap-space-sm">
                <button
                  type="button"
                  onClick={() => setIsEditing(!isEditing)}
                  className="flex-1 bg-surface-container hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm py-2 rounded-lg flex items-center justify-center gap-1 transition-colors border border-surface-container"
                >
                  <Sliders className="w-3.5 h-3.5" />
                  <span>{isEditing ? "Save Manual Input" : "Edit Quantities"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (estCarbs !== null) {
                      setConfirmedCarbs(estCarbs);
                    }
                    setWorkflowState("AWAITING_CONFIRMATION");
                  }}
                  disabled={estCarbs === null}
                  className="flex-1 bg-surface-container hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm py-2 rounded-lg flex items-center justify-center gap-1 transition-colors border border-surface-container disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Reset to AI Est</span>
                </button>
              </div>

              <button
                type="button"
                onClick={handleConfirm}
                disabled={!hasAnalysis || (confirmedCarbs <= 0 && estCarbs === null) || workflowState === "CONFIRMED" || workflowState === "TRANSFERRED"}
                className={`w-full font-label-md text-label-md py-2.5 rounded-lg flex items-center justify-center gap-space-xs transition-colors shadow-sm font-semibold ${
                  workflowState === "CONFIRMED" || workflowState === "TRANSFERRED"
                    ? "bg-tertiary/20 text-tertiary border border-tertiary/40 cursor-default"
                    : "bg-tertiary text-on-tertiary hover:bg-tertiary-container cursor-pointer"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <CheckCircle className="w-4 h-4" />
                <span>
                  {workflowState === "CONFIRMED" || workflowState === "TRANSFERRED"
                    ? `Confirmed (${confirmedCarbs}g CHO Active) ✓`
                    : `Confirm Values (${confirmedCarbs}g CHO)`}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Forecast Impact & Decision Reasoning (Cols 9-12) */}
        <div className="lg:col-span-3 flex flex-col gap-space-lg">
          {/* Card: Scientific Guardrail & Transfer Action */}
          <div className="bg-surface-container-lowest rounded-xl p-5 sm:p-6 shadow-sm border border-surface-container flex flex-col gap-space-md">
            <div className="flex items-center gap-space-xs">
              <Sparkles className="w-4 h-4 text-primary" />
              <h3 className="font-headline-sm text-headline-sm text-on-surface">Simulation Transfer</h3>
            </div>

            <p className="font-body-sm text-body-sm text-on-surface-variant">
              {workflowState === "TRANSFERRED"
                ? `Successfully transferred ${confirmedCarbs}g carbohydrate intake into the What-If Counterfactual Simulator.`
                : workflowState === "CONFIRMED"
                ? `Confirmed carbohydrate intake of ${confirmedCarbs}g ready for counterfactual postprandial simulation.`
                : hasAnalysis
                ? `Review and explicitly confirm estimated ${confirmedCarbs}g carbohydrates before transferring to the What-If simulator.`
                : `Analyze a meal to estimate carbohydrates before counterfactual simulation.`}
            </p>

            <button
              disabled={workflowState !== "CONFIRMED" || confirmedCarbs <= 0}
              onClick={handleTransfer}
              className={`w-full font-label-md text-label-md py-2.5 rounded-lg flex items-center justify-center gap-space-xs transition-colors shadow-sm font-semibold ${
                workflowState === "CONFIRMED" && confirmedCarbs > 0
                  ? "bg-primary text-on-primary hover:bg-primary-container cursor-pointer"
                  : "bg-surface-container-high text-on-surface-variant/40 cursor-not-allowed border border-surface-container"
              }`}
            >
              <span>{workflowState === "TRANSFERRED" ? "Transferred to What-If Simulator ✓" : "Transfer to What-If Simulator →"}</span>
            </button>
            {(workflowState !== "CONFIRMED" || confirmedCarbs <= 0) && (
              <span className="text-[11px] text-outline font-code-sm text-center">
                {workflowState !== "CONFIRMED"
                  ? "Human confirmation required before transfer to What-If simulation."
                  : "Valid carbohydrate intake (> 0g) required before transfer."}
              </span>
            )}

            {/* Strict Scientific Disclaimer Card */}
            <div className="bg-surface-container-high/60 p-space-sm rounded-lg flex items-start gap-space-xs border border-surface-container mt-2">
              <ShieldCheck className="w-4 h-4 text-outline mt-0.5 shrink-0" />
              <span className="font-code-sm text-code-sm text-on-surface-variant">
                <strong>Scientific Guardrail:</strong> Food Vision estimates are never automatically executed. Bolus simulations require explicit human-in-the-loop confirmation.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
