# GlucoShield — Clinical Intelligence Core & Digital Twin Command Center

## Quickstart Guide

This guide describes how to run and operate the **GlucoShield Clinical Intelligence Core & Digital Twin Command Center**, built using the approved Stitch Medical AI Command Center design system.

---

## 1. Prerequisites

- **Node.js**: v18+ (tested on Node.js v24.14.0)
- **Python**: 3.10+ (tested on Python 3.12.3)
- **PyTorch**: with CUDA or CPU support
- **Three.js & WebGL**: supported in modern browsers (Chrome, Edge, Firefox, Safari)

---

## 2. Launch Modes

### Option A: Unified FastAPI Production Mode (Recommended)

FastAPI serves both the backend REST endpoints (`/api/v1/...`) and the compiled high-performance React + Three.js SPA (`/`).

1. Build the production React assets (already compiled in `frontend/dist`):
   ```bash
   cd frontend
   npm run build
   cd ..
   ```

2. Start the FastAPI microservice:
   ```bash
   python -m uvicorn api.service:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Open your browser:
   - **Command Center Dashboard:** [http://localhost:8000](http://localhost:8000)
   - **Interactive OpenAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Option B: Standalone Vite Development Mode (Hot Reloading)

1. Terminal 1 (Start Backend):
   ```bash
   python -m uvicorn api.service:app --host 127.0.0.1 --port 8000
   ```

2. Terminal 2 (Start Vite Dev Server):
   ```bash
   cd frontend
   npm run dev
   ```

3. Open your browser:
   - **Vite Hot-Reload App:** [http://localhost:5173](http://localhost:5173)

---

## 3. Core Visual & Scientific Capabilities

1. **Mission Control Dashboard (`/dashboard`)**:
   - **`CGM.NOW` Pod:** High-contrast glucose value, metabolic velocity ($\Delta G$), and live indicator.
   - **`IOB` & `COB` Pods:** Real-time active insulin and carbohydrate tracking with micro-visualizers.
   - **`α(t)` Blend Weight Pod:** Dual ratio bar displaying the adaptive Neural vs Hovorka ODE balance.
   - **5-Hour Predictive Horizon Chart:** Composed chart with 95% and 80% volumetric uncertainty washes, faded historical CGM, M-ODE prior (cyan dashed), N-ODE neural trajectory (violet dashed), and luminous hybrid point forecast (white solid line).
   - **Risk Gauge & Clinical Explainer:** Multi-horizon hypo/hyper probabilities and natural language metabolic drivers.

2. **Living Digital Twin 3D / 2D (`/digital_twin`)**:
   - **Three.js WebGL 3D Visualization:** Glowing compartment nodes (Gut $D_1/D_2$, Plasma $Q_1/Q_2$, Insulin $S_1/S_2/x$, Peripheral Uptake) with real-time particle fluxes ($R_a(t)$ Amber, $S_I$ Violet, Uptake Cyan).
   - **Floating Instrument HUD Pods:** Real-time parameter readouts ($k_{\text{empt}}, V_G, G_b, S_I, S_G$).
   - **Adaptive Sequence Breakdown:** Interactive $\alpha(t)$ weights from $t=0$ to $t=+300\text{ min}$.

3. **Physiology Simulation Lab (`/what_if`)**:
   - Interactive carbohydrate ($0-150\text{g}$) and bolus ($0-15\text{U}$) sliders with quick presets.
   - In silico counterfactual ODE postprandial trajectory curves.
   - Projected Peak, Nadir, Time to Nadir, and predicted Time in Range (TIR %).

4. **Food Vision & USDA Nutrition (`/food_vision`)**:
   - Meal photograph dropzone with neural scanline animation and text search.
   - Top candidate recognition with confidence matching.
   - USDA FoodData Central macronutrient breakdown.
   - **Mandatory User Confirmation Policy** (`requires_user_confirmation=True`).

5. **Decision Center (`/decision_center`)**:
   - Multimodal case formulation coordinating Food Vision $\rightarrow$ Dynamic Forecaster $\rightarrow$ What-If Simulator $\rightarrow$ Actionable Recommendation.

6. **Wearables Context (`/wearables`)**:
   - Smartwatch activity and heart rate logging with **strict Phase 7C isolation guarantee** ($W = 34.0, p = 0.455$).

---

## 4. Automated Testing Suite

```bash
# Frontend Unit & Contract Tests (Node.js)
node --test frontend/src/api/api.test.js

# Frontend & Static Routing Integration Tests (Python)
python -m unittest api/tests/test_frontend_integration.py

# Full Repository Test Suite
python -m unittest discover -s api/tests -p "test_*.py"
```
