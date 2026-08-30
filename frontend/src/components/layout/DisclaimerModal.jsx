import React, { useState } from "react";
import { ShieldAlert, Info, X, ExternalLink } from "lucide-react";
import { RESEARCH_DISCLAIMER } from "../../api/types.js";

export function DisclaimerModal() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Persistent Bottom Disclaimer Bar */}
      <footer className="bg-[#070d1f]/95 border-t border-white/10 py-2.5 px-4 lg:px-8 text-center text-xs font-mono text-[#bac9cc]/70 flex flex-wrap items-center justify-between gap-3 z-30">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-[#f9bd22]" />
          <span>
            <strong>RESEARCH & CLINICAL DECISION-SUPPORT PROTOTYPE ONLY</strong> — Investigational platform; not cleared for direct autonomous therapy adjustment.
          </span>
        </div>
        <button
          onClick={() => setIsOpen(true)}
          className="text-[#00daf3] hover:underline font-bold text-[11px]"
        >
          View Full Clinical Protocol
        </button>
      </footer>

      {/* Protocol Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel instrument-border rounded-2xl max-w-xl w-full p-6 space-y-4 relative shadow-2xl bg-[#0c1324]/95 text-xs font-mono text-[#dce1fb]">
            <div className="flex justify-between items-center border-b border-white/10 pb-3">
              <div className="flex items-center gap-2 text-white font-bold text-sm">
                <ShieldAlert className="w-5 h-5 text-[#f9bd22]" />
                <span>GLUCOSHIELD CLINICAL RESEARCH PROTOCOL</span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-[#bac9cc] hover:text-white p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 leading-relaxed text-[#bac9cc] max-h-96 overflow-y-auto">
              <p>
                {RESEARCH_DISCLAIMER}
              </p>
              <div className="p-3 rounded-lg bg-[#070d1f] border border-white/10 space-y-1">
                <div className="text-white font-bold">Protocol Invariants:</div>
                <div>1. 22-Channel Dynamic Feature Assembly (1, 96, 22)</div>
                <div>2. Moving-Horizon State Estimation with Hovorka ODE Priors</div>
                <div>3. Leave-One-Out Cross-Validation on Glucdict Cohort (LOOCV)</div>
                <div>4. Mandatory Human Confirmation for Visual Meal Recognition</div>
              </div>
            </div>

            <div className="pt-3 border-t border-white/10 flex justify-end">
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 rounded-xl bg-[#00daf3] text-[#001f24] font-bold hover:bg-[#9cf0ff] transition-all"
              >
                I Understand & Acknowledge
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
