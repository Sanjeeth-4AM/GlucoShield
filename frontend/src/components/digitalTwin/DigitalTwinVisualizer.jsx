import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Cpu, Activity, Utensils, Droplets, Sliders, ShieldCheck, Layers, Eye, RefreshCw } from "lucide-react";

export function DigitalTwinVisualizer({ forecastData, staticProfile }) {
  const mountRef = useRef(null);
  const [viewMode, setViewMode] = useState("3d"); // "3d" or "2d"
  const [selectedHorizonStep, setSelectedHorizonStep] = useState(0);

  const currentState = forecastData?.current_state || {};
  const glucose = currentState.glucose_mg_dl ?? 120.0;
  const iob = currentState.iob_units ?? 1.4;
  const cob = currentState.cob_grams ?? 24.0;
  const neuralPct = forecastData?.hybrid_components?.mean_neural_weight_pct ?? 72;
  const odePct = 100 - neuralPct;
  const alphaArray = forecastData?.hybrid_components?.neural_weight_alpha || [0.85, 0.82, 0.78, 0.74, 0.71, 0.68];

  // Calibrated physiological parameters
  const params = {
    SI: "5.18 × 10⁻⁴ min⁻¹/(μU/mL)",
    kempt: "0.024 min⁻¹ (τ = 41m)",
    SG: "0.014 min⁻¹",
    Gb: "108 mg/dL",
    VG: "12.0 L (0.16 L/kg)",
    VI: "4.0 L (0.05 L/kg)"
  };

  // 3D Three.js Scene Setup matching Stitch
  useEffect(() => {
    if (viewMode !== "3d") return;
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(70, width / height, 0.1, 1000);
    camera.position.set(0, 0, 11);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // Node Colors matching Stitch palette
    const colors = {
      gut: 0xf9bd22,       // Amber / Gold (COB)
      plasma: 0x00daf3,    // Cyan (Glucose)
      insulin: 0xd0bcff,   // Violet (IOB)
      peripheral: 0x2dd4bf // Teal (Tissue Uptake)
    };

    // Helper to create glowing physiological compartment node
    const createCompartment = (name, x, y, z, color) => {
      const group = new THREE.Group();

      // Solid core
      const coreGeo = new THREE.SphereGeometry(0.7, 32, 32);
      const coreMat = new THREE.MeshPhongMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.85,
        transparent: true,
        opacity: 0.85
      });
      const core = new THREE.Mesh(coreGeo, coreMat);
      group.add(core);

      // Wireframe shell
      const shellGeo = new THREE.SphereGeometry(1.0, 16, 16);
      const shellMat = new THREE.MeshBasicMaterial({
        color: color,
        wireframe: true,
        transparent: true,
        opacity: 0.15
      });
      const shell = new THREE.Mesh(shellGeo, shellMat);
      group.add(shell);

      group.position.set(x, y, z);
      scene.add(group);
      return group;
    };

    const gutNode = createCompartment("GUT", -4.5, 2.5, 0, colors.gut);
    const plasmaNode = createCompartment("PLASMA", 0, 0, 0, colors.plasma);
    const insulinNode = createCompartment("INSULIN", 4.5, 2.5, 0, colors.insulin);
    const peripheralNode = createCompartment("PERIPHERAL", 0, -3.2, 0, colors.peripheral);

    // Particle Flux System
    const particleCount = 200;
    const particles = [];

    for (let i = 0; i < particleCount; i++) {
      const geo = new THREE.SphereGeometry(0.045, 8, 8);
      const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8 });
      const p = new THREE.Mesh(geo, mat);

      // Routing: 0: Gut -> Plasma, 1: Insulin -> Plasma, 2: Plasma -> Peripheral
      const pathType = i % 3;

      p.userData = {
        progress: Math.random(),
        speed: 0.002 + Math.random() * 0.005,
        path: pathType,
        offset: new THREE.Vector3(
          (Math.random() - 0.5) * 1.2,
          (Math.random() - 0.5) * 1.2,
          (Math.random() - 0.5) * 1.2
        )
      };
      scene.add(p);
      particles.push(p);
    }

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x334155, 1.2);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xffffff, 1.5, 50);
    pointLight.position.set(0, 5, 8);
    scene.add(pointLight);

    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      const time = Date.now() * 0.0015;

      // Subtle breathing scale on compartments
      [gutNode, plasmaNode, insulinNode, peripheralNode].forEach((node, idx) => {
        const s = 1.0 + Math.sin(time * 2.0 + idx * 1.2) * 0.04;
        node.scale.set(s, s, s);
      });

      // Update flux particles
      particles.forEach((p) => {
        p.userData.progress += p.userData.speed;
        if (p.userData.progress > 1) p.userData.progress = 0;

        let start, end, colorHex;
        if (p.userData.path === 0) {
          start = gutNode.position;
          end = plasmaNode.position;
          colorHex = colors.gut;
        } else if (p.userData.path === 1) {
          start = insulinNode.position;
          end = plasmaNode.position;
          colorHex = colors.insulin;
        } else {
          start = plasmaNode.position;
          end = peripheralNode.position;
          colorHex = colors.plasma;
        }

        p.position.lerpVectors(start, end, p.userData.progress);
        p.position.add(p.userData.offset.clone().multiplyScalar(Math.sin(p.userData.progress * Math.PI)));
        p.material.color.setHex(colorHex);
        p.material.opacity = Math.sin(p.userData.progress * Math.PI) * 0.85;
      });

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || 800;
      const h = container.clientHeight || 500;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      renderer.dispose();
    };
  }, [viewMode]);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel instrument-border rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded-md bg-[#00daf3]/10 text-[#00daf3] border border-[#00daf3]/30">
              <Cpu className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-white font-mono tracking-tight uppercase">
              DIGITAL_TWIN_COMMAND_CENTER (HOVORKA KINETICS)
            </h2>
          </div>
          <p className="text-xs text-[#bac9cc] max-w-2xl">
            Mechanistic moving-horizon parameter estimation simulating multi-compartment carbohydrate absorption, subcutaneous insulin depot clearance, and peripheral glucose disposal.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-[#070d1f] border border-white/10 p-1 rounded-lg">
            <button
              onClick={() => setViewMode("3d")}
              className={`font-mono text-[10px] uppercase px-2.5 py-1 rounded transition-colors ${
                viewMode === "3d"
                  ? "bg-[#00daf3]/20 text-[#00daf3] font-bold border border-[#00daf3]/40"
                  : "text-[#bac9cc] hover:text-white"
              }`}
            >
              3D Kinetic Command
            </button>
            <button
              onClick={() => setViewMode("2d")}
              className={`font-mono text-[10px] uppercase px-2.5 py-1 rounded transition-colors ${
                viewMode === "2d"
                  ? "bg-[#f9bd22]/20 text-[#f9bd22] font-bold border border-[#f9bd22]/40"
                  : "text-[#bac9cc] hover:text-white"
              }`}
            >
              2D Analytical Matrix
            </button>
          </div>
        </div>
      </div>

      {/* Living Three.js & Overlay Workspace */}
      <div className="glass-panel instrument-border rounded-xl relative overflow-hidden min-h-[480px] flex flex-col">
        {/* Background 3D Canvas */}
        {viewMode === "3d" ? (
          <div ref={mountRef} className="w-full h-[480px] relative z-10" />
        ) : (
          /* 2D Analytical Matrix SVG */
          <div className="w-full h-[480px] p-6 flex items-center justify-center relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl">
              {/* Gut */}
              <div className="glass-panel instrument-border-amber rounded-xl p-4 bg-[#070d1f]/80">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-xs text-[#f9bd22] font-bold">GUT (D1/D2)</span>
                  <Utensils className="w-4 h-4 text-[#f9bd22]" />
                </div>
                <div className="text-2xl font-light font-mono text-white mb-2">{cob.toFixed(1)} <span className="text-xs text-[#bac9cc]">g</span></div>
                <div className="space-y-1 font-mono text-[10px] text-[#bac9cc] border-t border-white/10 pt-2">
                  <div className="flex justify-between"><span>k_empt:</span><span className="text-[#f9bd22]">{params.kempt}</span></div>
                  <div className="flex justify-between"><span>Flux R_a:</span><span className="text-white">{(cob * 0.12).toFixed(2)} mg/min</span></div>
                </div>
              </div>

              {/* Plasma */}
              <div className="glass-panel instrument-border-cyan rounded-xl p-4 bg-[#070d1f]/80">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-xs text-[#00daf3] font-bold">PLASMA (Q1/Q2)</span>
                  <Activity className="w-4 h-4 text-[#00daf3]" />
                </div>
                <div className="text-2xl font-light font-mono text-white mb-2">{Math.round(glucose)} <span className="text-xs text-[#bac9cc]">mg/dL</span></div>
                <div className="space-y-1 font-mono text-[10px] text-[#bac9cc] border-t border-white/10 pt-2">
                  <div className="flex justify-between"><span>Volume V_G:</span><span className="text-[#00daf3]">{params.VG}</span></div>
                  <div className="flex justify-between"><span>Basal G_b:</span><span className="text-white">{params.Gb}</span></div>
                </div>
              </div>

              {/* Insulin */}
              <div className="glass-panel instrument-border-purple rounded-xl p-4 bg-[#070d1f]/80">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-xs text-[#d0bcff] font-bold">INSULIN (S1/S2/x)</span>
                  <Droplets className="w-4 h-4 text-[#d0bcff]" />
                </div>
                <div className="text-2xl font-light font-mono text-white mb-2">{iob.toFixed(2)} <span className="text-xs text-[#bac9cc]">U</span></div>
                <div className="space-y-1 font-mono text-[10px] text-[#bac9cc] border-t border-white/10 pt-2">
                  <div className="flex justify-between"><span>Sensitivity S_I:</span><span className="text-[#d0bcff]">{params.SI}</span></div>
                  <div className="flex justify-between"><span>Volume V_I:</span><span className="text-white">{params.VI}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Floating HUD Pods Overlay (Top Left & Bottom Right) */}
        {viewMode === "3d" && (
          <div className="absolute inset-0 pointer-events-none p-6 flex flex-col justify-between z-20">
            {/* Top Row Pods */}
            <div className="flex justify-between items-start">
              {/* Gut Readout */}
              <div className="pointer-events-auto bg-[#070d1f]/85 border border-white/10 backdrop-blur-xl rounded-xl p-3.5 w-60 shadow-xl">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-[11px] text-[#f9bd22] font-bold">GUT (D1/D2)</span>
                  <Utensils className="w-3.5 h-3.5 text-[#f9bd22]" />
                </div>
                <div className="text-xl font-light font-mono text-white">{cob.toFixed(1)} <span className="text-xs text-[#bac9cc]">g COB</span></div>
                <div className="mt-2 border-t border-white/10 pt-1.5 flex justify-between font-mono text-[10px] text-[#bac9cc]">
                  <span>k_empt:</span>
                  <span className="text-[#f9bd22]">{params.kempt}</span>
                </div>
              </div>

              {/* Insulin Action Readout */}
              <div className="pointer-events-auto bg-[#070d1f]/85 border border-white/10 backdrop-blur-xl rounded-xl p-3.5 w-60 shadow-xl">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-[11px] text-[#d0bcff] font-bold">INSULIN (S1/S2/x)</span>
                  <Droplets className="w-3.5 h-3.5 text-[#d0bcff]" />
                </div>
                <div className="text-xl font-light font-mono text-white">{iob.toFixed(2)} <span className="text-xs text-[#bac9cc]">U IOB</span></div>
                <div className="mt-2 border-t border-white/10 pt-1.5 flex justify-between font-mono text-[10px] text-[#bac9cc]">
                  <span>S_I Sensitivity:</span>
                  <span className="text-[#d0bcff]">5.2e-4</span>
                </div>
              </div>
            </div>

            {/* Bottom Row Pods */}
            <div className="flex justify-between items-end">
              {/* Peripheral Uptake */}
              <div className="pointer-events-auto bg-[#070d1f]/85 border border-white/10 backdrop-blur-xl rounded-xl p-3.5 w-60 shadow-xl">
                <span className="font-mono text-[11px] text-[#2dd4bf] font-bold block mb-1">PERIPHERAL UPTAKE</span>
                <div className="text-xl font-light font-mono text-white mb-2">72.4% <span className="text-xs text-[#bac9cc]">Active</span></div>
                <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-[#2dd4bf] w-[72%]"></div>
                </div>
              </div>

              {/* Central Plasma Pool */}
              <div className="pointer-events-auto bg-[#070d1f]/85 border border-white/10 backdrop-blur-xl rounded-xl p-3.5 w-60 shadow-xl text-right">
                <span className="font-mono text-[11px] text-[#00daf3] font-bold block mb-1">CENTRAL PLASMA (Q1)</span>
                <div className="text-xl font-light font-mono text-white">{Math.round(glucose)} <span className="text-xs text-[#bac9cc]">mg/dL</span></div>
                <div className="mt-2 border-t border-white/10 pt-1.5 flex justify-between font-mono text-[10px] text-[#bac9cc]">
                  <span>Basal G_b:</span>
                  <span className="text-[#00daf3]">{params.Gb}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Adaptive α(t) Blending Controller & Sequence Breakdown */}
      <div className="glass-panel instrument-border rounded-xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="font-mono text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#00daf3]" />
              Adaptive Gated Blending Sequence: α(t) [0 → +300m]
            </h3>
            <p className="text-[11px] text-[#bac9cc] mt-0.5">
              Multi-horizon gate weight balancing Deep GRU-128 sequence features with Hovorka ODE physics priors.
            </p>
          </div>
          <span className="font-mono text-xs text-[#00daf3] font-bold">
            Mean Neural Weight: {neuralPct}% | ODE Prior: {odePct}%
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
          {[0, 1, 2, 3, 4, 5].map((step) => {
            const val = alphaArray[step] ?? (0.85 - step * 0.03);
            const nP = Math.round(val * 100);
            const oP = 100 - nP;
            const mins = step * 60;
            return (
              <div
                key={step}
                className="bg-[#070d1f]/80 p-3 rounded-lg border border-white/10 text-center font-mono"
              >
                <span className="text-[10px] text-[#bac9cc] block font-bold">+{mins} min</span>
                <div className="my-2 h-1.5 bg-white/10 rounded-full flex overflow-hidden">
                  <div className="bg-[#00daf3]" style={{ width: `${oP}%` }} title={`ODE: ${oP}%`}></div>
                  <div className="bg-[#d0bcff]" style={{ width: `${nP}%` }} title={`NN: ${nP}%`}></div>
                </div>
                <span className="text-xs text-white font-bold">α = {val.toFixed(2)}</span>
                <span className="text-[9px] text-[#bac9cc]/60 block mt-0.5">{nP}% NN</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
