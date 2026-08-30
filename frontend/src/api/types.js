/**
 * GlucoShield Constants and Types
 */

export const RESEARCH_DISCLAIMER = "GlucoShield is an investigational clinical decision-support research tool. Not approved as a primary diagnostic device or automated insulin delivery controller. All dosing decisions must be validated by a qualified healthcare professional.";

export const GLUCOSE_THRESHOLDS = {
  VERY_LOW: 54,     // Level 2 Hypo (mg/dL)
  LOW: 70,          // Level 1 Hypo (mg/dL)
  TARGET_MIN: 70,   // Target Range Min (mg/dL)
  TARGET_MAX: 180,  // Target Range Max (mg/dL)
  HIGH: 180,        // Level 1 Hyper (mg/dL)
  VERY_HIGH: 250,   // Level 2 Hyper (mg/dL)
};

export const ALERT_LEVELS = {
  NORMAL: {
    label: "NORMAL",
    color: "emerald",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text: "text-emerald-400",
    badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
  },
  WARNING: {
    label: "WARNING",
    color: "amber",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
    badge: "bg-amber-500/20 text-amber-300 border-amber-500/40"
  },
  CRITICAL: {
    label: "CRITICAL",
    color: "red",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    text: "text-red-400",
    badge: "bg-red-500/20 text-red-300 border-red-500/40"
  }
};
