import React from "react";

export function MetabolicShaderBackground() {
  return (
    <div
      className="fixed inset-0 pointer-events-none z-0 bg-[#faf8ff]"
      aria-hidden="true"
    >
      {/* Crisp subtle micro-dot grid for clinical telemetry workstation aesthetic */}
      <div
        className="w-full h-full opacity-40"
        style={{
          backgroundImage: "radial-gradient(#bcc9c6 0.75px, transparent 0.75px)",
          backgroundSize: "24px 24px"
        }}
      />
    </div>
  );
}
