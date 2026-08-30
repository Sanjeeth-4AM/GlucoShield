import React from "react";
import {
  LayoutDashboard,
  TrendingUp,
  Activity,
  FlaskConical,
  Camera,
  CheckCircle2,
  Watch,
  UserCheck,
  Info
} from "lucide-react";

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, tag: "Command Center" },
  { id: "forecast", label: "Forecast & Risk", icon: TrendingUp, tag: "5-Hour Sequence" },
  { id: "digital_twin", label: "Digital Twin", icon: Activity, tag: "Mechanistic ODE", highlight: true },
  { id: "what_if", label: "Physiology Lab", icon: FlaskConical, tag: "What-If Simulator" },
  { id: "food_vision", label: "Food Vision", icon: Camera, tag: "Meal Recognition" },
  { id: "decision_center", label: "Decision Center", icon: CheckCircle2, tag: "Multimodal Synthesis" },
  { id: "wearables", label: "Wearables", icon: Watch, tag: "Contextual Telemetry" },
  { id: "profile", label: "Patient Profile", icon: UserCheck, tag: "Static Phenotype" },
  { id: "system", label: "System Specs", icon: Info, tag: "API & Hashes" }
];

export function Navigation({ activeTab, setActiveTab }) {
  return (
    <nav className="border-b border-slate-800 bg-slate-950/60 backdrop-blur-md px-4 lg:px-8 py-2 overflow-x-auto scrollbar-none">
      <div className="flex items-center gap-1.5 min-w-max">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all relative ${
                isActive
                  ? "bg-slate-800/90 text-cyan-300 border border-cyan-500/40 shadow-lg shadow-cyan-500/10"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent"
              } ${item.highlight && !isActive ? "text-amber-300/80 hover:text-amber-200" : ""}`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : (item.highlight ? "text-amber-400" : "text-slate-400")}`} />
              <span>{item.label}</span>
              {item.highlight && (
                <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  ODE
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
