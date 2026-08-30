import React, { useState } from "react";
import { Camera, Search, Upload, CheckCircle2, ShieldAlert, Sparkles, ArrowRight, Utensils } from "lucide-react";

export function MealAnalysisWorkflow({ onAnalyzeMeal, analysisResult, isAnalyzing, onTransferToWhatIf }) {
  const [foodQuery, setFoodQuery] = useState("grilled chicken salad with rice");
  const [portionGrams, setPortionGrams] = useState(250.0);
  const [userConfirmed, setUserConfirmed] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleSearch = (e) => {
    e.preventDefault();
    if (onAnalyzeMeal && foodQuery.trim()) {
      onAnalyzeMeal({
        food_name_query: foodQuery.trim(),
        portion_g: parseFloat(portionGrams)
      });
      setUserConfirmed(false);
    }
  };

  const handleSimulatedDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    setFoodQuery("apple pie with crust");
    if (onAnalyzeMeal) {
      onAnalyzeMeal({
        food_name_query: "apple pie with crust",
        portion_g: parseFloat(portionGrams)
      });
      setUserConfirmed(false);
    }
  };

  const selectedFood = analysisResult?.selected_food || "standard meal";
  const macronutrients = analysisResult?.macronutrients || {
    carbohydrates_g: 45.0,
    calories_kcal: 380.0,
    protein_g: 22.0,
    fat_g: 12.0
  };
  const candidates = analysisResult?.candidates || [
    { food_name: "grilled chicken salad with rice", confidence: 0.92 },
    { food_name: "brown rice with vegetables", confidence: 0.78 },
    { food_name: "quinoa bowl with chicken", confidence: 0.65 }
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-[#00daf3]/10 text-[#00daf3] border border-[#00daf3]/30">
              <Camera className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-white font-mono tracking-tight uppercase">
              FOOD_VISION_INTELLIGENCE (USDA NUTRITION ENGINE)
            </h2>
          </div>
          <p className="text-xs text-[#bac9cc] max-w-2xl">
            Multimodal visual meal ingestion with USDA FoodData Central macronutrient mapping and mandatory human-in-the-loop clinical confirmation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-[#f9bd22] bg-[#f9bd22]/10 border border-[#f9bd22]/30 px-2.5 py-1 rounded-lg">
            Safety Invariant: Requires User Sign-Off
          </span>
        </div>
      </div>

      {/* Main Grid: Upload & Search Left, Identified Nutrition Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Drag & Drop + Search */}
        <div className="lg:col-span-6 space-y-4">
          {/* Dropzone with scanning animation */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleSimulatedDrop}
            className={`glass-panel instrument-border rounded-xl p-8 border-dashed flex flex-col items-center justify-center text-center relative overflow-hidden transition-all ${
              dragActive ? "border-[#00daf3] bg-[#00daf3]/10" : "border-white/20 hover:border-white/40"
            }`}
          >
            {/* Scanning line effect */}
            <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-[#00daf3] to-transparent animate-pulse top-0 pointer-events-none"></div>

            <div className="w-14 h-14 rounded-2xl bg-[#070d1f] border border-white/10 flex items-center justify-center mb-4 shadow-xl">
              <Upload className="w-6 h-6 text-[#00daf3]" />
            </div>

            <h3 className="font-mono text-sm text-white font-bold mb-1">
              Drop Meal Photograph or Capture
            </h3>
            <p className="text-xs text-[#bac9cc] max-w-sm mb-4">
              AI Food-101 deep visual recognition estimates food type and queries USDA nutrient density database.
            </p>

            <button
              onClick={() => handleSimulatedDrop({ preventDefault: () => {} })}
              className="font-mono text-xs px-4 py-2 rounded-lg bg-[#070d1f] border border-white/15 text-[#bac9cc] hover:text-white hover:border-[#00daf3]/50 transition-all"
            >
              Simulate Sample Meal Upload
            </button>
          </div>

          {/* Text Search Form */}
          <form onSubmit={handleSearch} className="glass-panel instrument-border rounded-xl p-4 space-y-3">
            <span className="font-mono text-xs text-[#bac9cc] font-bold uppercase tracking-wider block">
              Or Search USDA Food Registry
            </span>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Search className="w-4 h-4 text-[#bac9cc] absolute left-3 top-3" />
                <input
                  type="text"
                  value={foodQuery}
                  onChange={(e) => setFoodQuery(e.target.value)}
                  placeholder="e.g. Oatmeal with banana and honey"
                  className="w-full bg-[#070d1f] border border-white/10 rounded-xl pl-9 pr-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#00daf3]"
                />
              </div>
              <button
                type="submit"
                disabled={isAnalyzing}
                className="px-4 py-2 rounded-xl bg-[#00daf3] text-[#001f24] font-mono font-bold text-xs hover:bg-[#9cf0ff] transition-all disabled:opacity-50"
              >
                {isAnalyzing ? "ANALYZING..." : "ANALYZE"}
              </button>
            </div>

            {/* Portion Weight Slider */}
            <div className="pt-2">
              <div className="flex justify-between items-center mb-1">
                <span className="font-mono text-[11px] text-[#bac9cc]">Portion Weight (grams):</span>
                <span className="font-mono text-xs text-[#00daf3] font-bold">{portionGrams} g</span>
              </div>
              <input
                type="range"
                min="50"
                max="600"
                step="10"
                value={portionGrams}
                onChange={(e) => setPortionGrams(parseFloat(e.target.value))}
                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-[#00daf3]"
              />
            </div>
          </form>
        </div>

        {/* Right: Candidates, USDA Macronutrients, and Mandatory Confirmation */}
        <div className="lg:col-span-6 space-y-4">
          {/* Candidates */}
          <div className="glass-panel instrument-border rounded-xl p-4">
            <span className="font-mono text-xs text-white font-bold uppercase tracking-wider block mb-3">
              Vision Candidates & Confidence Scores
            </span>
            <div className="space-y-2">
              {candidates.map((c, i) => (
                <div
                  key={i}
                  className={`p-2.5 rounded-lg border font-mono text-xs flex justify-between items-center transition-all ${
                    i === 0
                      ? "bg-[#00daf3]/10 border-[#00daf3]/40 text-white font-bold"
                      : "bg-[#070d1f]/60 border-white/10 text-[#bac9cc]"
                  }`}
                >
                  <span className="capitalize">{c.food_name}</span>
                  <span className="text-[11px] text-[#00daf3]">{(c.confidence * 100).toFixed(0)}% Match</span>
                </div>
              ))}
            </div>
          </div>

          {/* USDA Macronutrient Breakdown */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/70 text-center">
              <span className="font-mono text-[10px] text-[#f9bd22] uppercase block">Carbs</span>
              <span className="text-xl font-mono font-bold text-white">
                {macronutrients.carbohydrates_g?.toFixed(1)} <span className="text-[10px] text-[#bac9cc]">g</span>
              </span>
            </div>

            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/70 text-center">
              <span className="font-mono text-[10px] text-[#bac9cc] uppercase block">Calories</span>
              <span className="text-xl font-mono font-bold text-white">
                {Math.round(macronutrients.calories_kcal || 0)} <span className="text-[10px] text-[#bac9cc]">kcal</span>
              </span>
            </div>

            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/70 text-center">
              <span className="font-mono text-[10px] text-[#d0bcff] uppercase block">Protein</span>
              <span className="text-xl font-mono font-bold text-white">
                {macronutrients.protein_g?.toFixed(1)} <span className="text-[10px] text-[#bac9cc]">g</span>
              </span>
            </div>

            <div className="glass-panel instrument-border rounded-xl p-3 bg-[#070d1f]/70 text-center">
              <span className="font-mono text-[10px] text-[#ec4899] uppercase block">Fat</span>
              <span className="text-xl font-mono font-bold text-white">
                {macronutrients.fat_g?.toFixed(1)} <span className="text-[10px] text-[#bac9cc]">g</span>
              </span>
            </div>
          </div>

          {/* Mandatory Human-in-the-Loop Confirmation */}
          <div className="glass-panel instrument-border rounded-xl p-4 space-y-3 bg-[#070d1f]/90 border-l-2 border-l-[#f9bd22]">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[#f9bd22]" />
              <span className="font-mono text-xs text-white font-bold uppercase tracking-wider">
                Clinical Safety Verification Policy
              </span>
            </div>

            <label className="flex items-start gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={userConfirmed}
                onChange={(e) => setUserConfirmed(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded bg-[#070d1f] border-white/20 text-[#00daf3] focus:ring-0 cursor-pointer"
              />
              <span className="text-xs text-[#bac9cc] leading-relaxed">
                I verify that this identification (<strong className="text-white">{selectedFood}</strong>) and estimated carbohydrate quantity (<strong className="text-[#f9bd22]">{macronutrients.carbohydrates_g?.toFixed(1)}g</strong>) accurately reflect actual intake.
              </span>
            </label>

            {onTransferToWhatIf && (
              <button
                onClick={() => onTransferToWhatIf(macronutrients.carbohydrates_g || 45.0)}
                disabled={!userConfirmed}
                className="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-[#00daf3] text-[#001f24] font-mono font-bold text-xs hover:bg-[#9cf0ff] transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-lg shadow-[#00daf3]/10"
              >
                <span>Transfer Confirmed Carbs to What-If Lab</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
