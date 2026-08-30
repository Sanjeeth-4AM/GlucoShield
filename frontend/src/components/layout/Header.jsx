import React from "react";
import { Activity, Sparkles, Wifi, RefreshCw, Layers, Menu, X, ShieldAlert } from "lucide-react";

export function Header({
  isDemoMode,
  setIsDemoMode,
  backendHealth,
  currentScenario,
  setCurrentScenario,
  onRefresh,
  isLoading,
  mobileMenuOpen,
  setMobileMenuOpen
}) {
  return (
    <header className="bg-[#0c1324]/85 backdrop-blur-xl border-b border-white/10 sticky top-0 z-30 px-4 lg:px-8 py-3 flex items-center justify-between gap-4">
      {/* Mobile Toggle & Brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileMenuOpen && setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden text-[#bac9cc] hover:text-white p-1 rounded-lg bg-[#191f31]"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <div className="flex items-center gap-2 md:hidden">
          <div className="w-8 h-8 rounded bg-[#151b2d] flex items-center justify-center border border-white/15">
            <Activity className="w-4 h-4 text-[#00daf3]" />
          </div>
          <span className="font-bold text-base text-[#00daf3] tracking-tighter">
            GLUCOSHIELD
          </span>
        </div>

        {/* Live Status Pill */}
        <div className="hidden sm:flex items-center gap-2 border border-white/10 bg-[#070d1f]/80 px-3 py-1 rounded-lg text-xs font-mono">
          <div className="w-2 h-2 rounded-full bg-[#00daf3] pulse-glow"></div>
          <span className="text-[#00daf3] tracking-wider font-semibold">
            {backendHealth?.status === "healthy" ? "SYSTEM_LIVE" : (isDemoMode ? "DEMO_MODE" : "INITIALIZING")}
          </span>
        </div>
      </div>

      {/* Center: Scenario Switcher */}
      <div className="flex items-center gap-1.5 bg-[#070d1f]/90 border border-white/10 rounded-xl p-1 text-xs">
        <span className="text-[#bac9cc]/60 px-2 font-mono text-[10px] hidden sm:flex items-center gap-1">
          <Layers className="w-3 h-3 text-[#00daf3]" />
          SCENARIO:
        </span>
        {[
          { id: "stable", label: "Stable Baseline" },
          { id: "postprandial", label: "Postprandial Spike" },
          { id: "hypo_risk", label: "Hypo Risk" }
        ].map((scen) => (
          <button
            key={scen.id}
            onClick={() => setCurrentScenario(scen.id)}
            className={`px-2.5 py-1 rounded-lg font-mono text-[11px] transition-all ${
              currentScenario === scen.id
                ? "bg-[#00daf3]/20 text-[#00daf3] font-bold border border-[#00daf3]/40 shadow-sm"
                : "text-[#bac9cc]/70 hover:text-white"
            }`}
          >
            {scen.label}
          </button>
        ))}
      </div>

      {/* Right Controls: Live/Demo Toggle & Refresh */}
      <div className="flex items-center gap-3">
        {/* Live / Demo Mode Toggle */}
        <div className="flex items-center gap-1 bg-[#070d1f] border border-white/10 rounded-xl p-1">
          <button
            onClick={() => setIsDemoMode(false)}
            className={`flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-lg transition-colors ${
              !isDemoMode
                ? "bg-[#00daf3]/20 text-[#00daf3] font-bold border border-[#00daf3]/40"
                : "text-[#bac9cc]/60 hover:text-white"
            }`}
          >
            <Wifi className="w-3 h-3" />
            Live API
          </button>
          <button
            onClick={() => setIsDemoMode(true)}
            className={`flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-lg transition-colors ${
              isDemoMode
                ? "bg-[#f9bd22]/20 text-[#f9bd22] font-bold border border-[#f9bd22]/40"
                : "text-[#bac9cc]/60 hover:text-white"
            }`}
          >
            <Sparkles className="w-3 h-3" />
            Demo
          </button>
        </div>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh forecast from backend"
          className="p-2 rounded-xl bg-[#070d1f] hover:bg-[#191f31] border border-white/10 text-[#bac9cc] hover:text-[#00daf3] transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-[#00daf3]" : ""}`} />
        </button>
      </div>
    </header>
  );
}
