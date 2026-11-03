import React from "react";
import { Utensils, Syringe, Radio, ExternalLink } from "lucide-react";

export function RecentEventsCard({ historyReadings, persistedEvents = [], onNavigate }) {
  // Extract events from genuine historyReadings
  const telemetryEvents = (historyReadings || [])
    .filter((r) => (r.insulin_bolus && r.insulin_bolus > 0) || (r.meal_carbs && r.meal_carbs > 0))
    .map((r, i) => {
      const isMeal = r.meal_carbs > 0;
      const d = new Date(r.timestamp);
      return {
        timestamp: r.timestamp,
        time: !isNaN(d.getTime()) ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : `T-${(historyReadings.length - i) * 15}m`,
        relativeTime: "Telemetry",
        title: isMeal ? "Meal Event Logged" : "Insulin Delivery Logged",
        description: isMeal ? `${r.meal_carbs}g CHO recorded` : `${r.insulin_bolus} U bolus administered`,
        icon: isMeal ? Utensils : Syringe,
        iconColor: isMeal ? "text-secondary" : "text-tertiary"
      };
    });

  // Extract genuine events from persisted database records (meals, insulin, decisions)
  const dbEvents = (persistedEvents || []).map((ev) => {
    const isMeal = ev.carbs_g !== undefined;
    const isInsulin = ev.units !== undefined || ev.dose_type !== undefined;
    const d = new Date(ev.timestamp || ev.created_at);
    const timeStr = !isNaN(d.getTime()) ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Verified";

    if (isMeal) {
      return {
        timestamp: ev.timestamp || ev.created_at,
        time: timeStr,
        relativeTime: "Verified",
        title: ev.meal_name || "Meal Event Logged",
        description: `${ev.carbs_g}g CHO recorded${ev.source ? ` (${ev.source})` : ""}`,
        icon: Utensils,
        iconColor: "text-secondary"
      };
    } else if (isInsulin) {
      return {
        timestamp: ev.timestamp || ev.created_at,
        time: timeStr,
        relativeTime: "Verified",
        title: "Insulin Delivery Logged",
        description: `${ev.units || 0} U ${ev.dose_type || "bolus"} administered`,
        icon: Syringe,
        iconColor: "text-tertiary"
      };
    } else {
      return {
        timestamp: ev.timestamp || ev.created_at,
        time: timeStr,
        relativeTime: "Clinical",
        title: ev.recommended_action || "Clinical Event",
        description: ev.decision_summary?.recommended_action || "Advisory guidance generated",
        icon: Radio,
        iconColor: "text-primary"
      };
    }
  });

  // Merge genuine events chronologically (most recent first), take top 3
  const eventsToDisplay = [...telemetryEvents, ...dbEvents]
    .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0))
    .slice(0, 3);

  return (
    <div className="bg-surface-container-lowest p-space-lg rounded-xl shadow-sm flex flex-col justify-between border border-surface-container h-full">
      <div>
        <div className="flex items-center gap-space-xs">
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">
            SECTION F
          </span>
          <span className="text-outline-variant">•</span>
          <h2 className="font-label-md text-label-md font-semibold text-on-surface">
            Recent Clinical Events
          </h2>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5 mb-space-md">
          High-confidence telemetry &amp; patient inputs
        </p>

        {/* Clean Verified Event List or Honest Empty State */}
        {eventsToDisplay.length === 0 ? (
          <div className="py-8 flex flex-col items-center justify-center text-center p-space-md bg-surface-container-low/40 rounded-lg border border-surface-container">
            <Radio className="w-6 h-6 text-outline mb-2" />
            <span className="font-label-sm text-label-sm text-on-surface font-semibold">
              No recent meal or bolus events
            </span>
            <p className="font-body-sm text-body-sm text-on-surface-variant max-w-xs mt-0.5">
              Logged carbohydrate and insulin events will appear here in chronological sequence.
            </p>
          </div>
        ) : (
          <div className="space-y-space-md">
            {eventsToDisplay.map((ev, i) => {
              const Icon = ev.icon;
              return (
                <div key={i} className="flex items-start gap-space-sm">
                  <div className="w-7 h-7 rounded bg-surface-container-high flex items-center justify-center shrink-0 mt-0.5">
                    <Icon className={`w-4 h-4 ${ev.iconColor}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-code-sm text-code-sm text-outline font-semibold">
                        {ev.time}
                      </span>
                      <span className="font-code-sm text-code-sm text-on-surface-variant">
                        {ev.relativeTime}
                      </span>
                    </div>
                    <h3 className="font-label-sm text-label-sm font-semibold text-on-surface">
                      {ev.title}
                    </h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant leading-tight">
                      {ev.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="pt-space-md">
        <button
          onClick={() => onNavigate && onNavigate("history")}
          className="w-full h-8 px-space-sm bg-surface-container hover:bg-surface-container-high text-on-surface rounded flex items-center justify-center gap-1 font-label-sm text-label-sm font-semibold transition-colors border border-surface-container"
        >
          <span>View Audit Log</span>
          <ExternalLink className="w-3.5 h-3.5 text-on-surface-variant" />
        </button>
      </div>
    </div>
  );
}
