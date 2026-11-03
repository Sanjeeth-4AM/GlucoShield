import React from "react";
import {
  LayoutDashboard,
  TrendingUp,
  Cpu,
  FlaskConical,
  Camera,
  AlertTriangle,
  User,
  History,
  Settings,
  Shield,
  GitCompare
} from "lucide-react";

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, iconName: "dashboard" },
  { id: "comparison", label: "Comparative Intelligence", icon: GitCompare, iconName: "compare_arrows", highlight: true },
  { id: "profile", label: "Patient Profile", icon: User, iconName: "person" },
  { id: "forecast", label: "Forecast", icon: TrendingUp, iconName: "trending_up" },
  { id: "digital_twin", label: "Digital Twin", icon: Cpu, iconName: "vital_signs" },
  { id: "what_if", label: "What-If Simulation", icon: FlaskConical, iconName: "biotech" },
  { id: "food_vision", label: "Food Vision", icon: Camera, iconName: "restaurant" },
  { id: "risk_explanation", label: "Risk & Explanation", icon: AlertTriangle, iconName: "emergency" },
  { id: "history", label: "History", icon: History, iconName: "history" },
  { id: "settings", label: "Settings", icon: Settings, iconName: "settings" }
];

export function SideNavBar({ activeTab, setActiveTab }) {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface-container-lowest z-50 flex flex-col shadow-[0_1px_8px_rgba(0,0,0,0.04)] border-r border-surface-container select-none hidden md:flex">
      {/* Brand Header */}
      <div className="h-16 px-space-lg flex items-center gap-space-sm bg-surface-container-lowest border-b border-surface-container/50">
        <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center text-primary">
          <Shield className="w-5 h-5 text-primary" />
        </div>
        <div className="flex flex-col">
          <span className="font-headline-sm text-headline-sm text-on-surface leading-tight font-semibold">
            GlucoShield
          </span>
          <span className="font-code-sm text-code-sm text-primary uppercase tracking-wider font-semibold">
            Metabolic AI
          </span>
        </div>
      </div>

      {/* Cohort Header Badge */}
      <div className="px-space-md py-space-sm">
        <div className="bg-surface-container-low px-space-sm py-space-xs rounded flex items-center justify-between border border-surface-container">
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase font-medium">
            Active Clinical Cohort
          </span>
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-space-md py-space-xs flex flex-col gap-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              data-testid={`nav-item-${item.id}`}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-space-sm px-space-sm py-2 rounded transition-colors text-left text-sm ${
                isActive
                  ? "bg-primary-container text-on-primary-container font-semibold shadow-sm"
                  : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface font-medium"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-on-primary-container" : "text-on-surface-variant"}`} />
              <span className="flex-1 truncate">{item.label}</span>
              {item.highlight && !isActive && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container-high text-primary font-semibold">
                  ODE
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Persistent Production Serving Badge */}
      <div className="p-space-md bg-surface-container-low mx-space-md mb-space-md rounded border border-surface-container">
        <div className="flex items-center justify-between mb-space-xs">
          <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">Model Serving</span>
          <span className="font-code-sm text-code-sm text-primary font-semibold">Combination C</span>
        </div>
        <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
          <div className="bg-primary h-full w-full"></div>
        </div>
        <div className="flex items-center justify-between mt-space-xs text-[11px] font-mono">
          <span className="text-on-surface-variant">V1 Neural + ODE</span>
          <span className="text-tertiary font-semibold">Active</span>
        </div>
      </div>
    </aside>
  );
}
