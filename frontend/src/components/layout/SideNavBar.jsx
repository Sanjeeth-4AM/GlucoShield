import React from "react";
import {
  LayoutDashboard,
  Cpu,
  TrendingUp,
  FlaskConical,
  Camera,
  CheckCircle2,
  Watch,
  UserCheck,
  Settings,
  HelpCircle,
  ShieldAlert,
  Activity
} from "lucide-react";

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, tag: "Command Center" },
  { id: "digital_twin", label: "Digital Twin", icon: Cpu, tag: "Mechanistic ODE", highlight: true },
  { id: "forecast", label: "Forecast & Risk", icon: TrendingUp, tag: "5-Hour Sequence" },
  { id: "what_if", label: "Physiology Lab", icon: FlaskConical, tag: "What-If Simulator" },
  { id: "food_vision", label: "Food Vision", icon: Camera, tag: "Meal Recognition" },
  { id: "decision_center", label: "Decision Center", icon: CheckCircle2, tag: "Multimodal Synthesis" },
  { id: "wearables", label: "Wearables", icon: Watch, tag: "Contextual Telemetry" },
  { id: "profile", label: "Patient Profile", icon: UserCheck, tag: "Static Phenotype" },
  { id: "system", label: "System Specs", icon: Settings, tag: "API & Hashes" }
];

export function SideNavBar({ activeTab, setActiveTab }) {
  return (
    <nav className="bg-[#070d1f]/95 backdrop-blur-xl flex flex-col h-full py-6 w-64 border-r border-white/10 z-40 flex-shrink-0 hidden md:flex select-none">
      {/* Brand Header */}
      <div className="px-6 mb-8 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-[#151b2d] flex items-center justify-center border border-white/15 overflow-hidden relative shadow-lg shadow-[#00daf3]/10">
          <div className="absolute inset-0 bg-gradient-to-tr from-[#00daf3]/20 via-[#8b5cf6]/20 to-transparent"></div>
          <Activity className="w-5 h-5 text-[#00daf3] animate-pulse relative z-10" />
        </div>
        <div>
          <h1 className="font-bold text-lg text-[#00daf3] tracking-tighter leading-none">
            GLUCOSHIELD
          </h1>
          <span className="font-mono text-[10px] text-[#bac9cc] opacity-80 mt-1 block tracking-wider">
            V1.0 HYBRID ODE
          </span>
        </div>
      </div>

      {/* Main Navigation Links */}
      <div className="flex-1 px-3 space-y-1 overflow-y-auto scrollbar-none">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-mono uppercase tracking-wider transition-all text-left relative ${
                isActive
                  ? "text-[#00daf3] font-bold border-r-2 border-[#00daf3] bg-[#00daf3]/10 shadow-[inset_-10px_0_15px_-10px_rgba(0,218,243,0.35)]"
                  : "text-[#bac9cc]/70 hover:bg-[#191f31]/60 hover:text-white"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-[#00daf3]" : (item.highlight ? "text-[#f9bd22]" : "text-[#bac9cc]/70")}`} />
              <span className="flex-1 truncate">{item.label}</span>
              {item.highlight && !isActive && (
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#f9bd22]/20 text-[#f9bd22] border border-[#f9bd22]/30">
                  ODE
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer Navigation */}
      <div className="px-4 mt-auto pt-4 border-t border-white/10 space-y-1 text-xs font-mono text-[#bac9cc]/60">
        <div className="px-3 py-2 text-[10px] text-[#bac9cc]/40 uppercase tracking-widest">
          Research Deployment
        </div>
        <div className="px-3 py-1 flex items-center justify-between text-[10px]">
          <span>Core Forecaster:</span>
          <span className="text-[#00daf3]">22-Channel V1</span>
        </div>
        <div className="px-3 py-1 flex items-center justify-between text-[10px]">
          <span>Physics Engine:</span>
          <span className="text-[#f9bd22]">Hovorka ODE</span>
        </div>
      </div>
    </nav>
  );
}
