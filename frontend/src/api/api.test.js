import { describe, it } from "node:test";
import assert from "node:assert";
import { generateSyntheticHistory, getSyntheticForecastResponse, getSyntheticWhatIfResponse, DEMO_STATIC_PROFILE } from "./demoData.js";
import { GLUCOSE_THRESHOLDS, ALERT_LEVELS, RESEARCH_DISCLAIMER } from "./types.js";

describe("Frontend API Contracts & Demo Data Integrity", () => {
  it("should generate exactly 96 15-minute readings for 24 hours", () => {
    const history = generateSyntheticHistory("stable");
    assert.strictEqual(history.length, 96);
    assert.strictEqual(typeof history[0].cgm_glucose, "number");
    assert.ok(history[0].cgm_glucose >= 20 && history[0].cgm_glucose <= 600);
  });

  it("should generate 20-step multi-horizon forecast data with monotonic 95% >= 80% intervals", () => {
    const forecast = getSyntheticForecastResponse("stable");
    assert.strictEqual(forecast.forecast.point_forecast_mg_dl.length, 20);
    assert.strictEqual(forecast.forecast.lower_80_mg_dl.length, 20);
    assert.strictEqual(forecast.forecast.upper_80_mg_dl.length, 20);
    assert.strictEqual(forecast.forecast.lower_95_mg_dl.length, 20);
    assert.strictEqual(forecast.forecast.upper_95_mg_dl.length, 20);

    for (let i = 0; i < 20; i++) {
      const w80 = forecast.forecast.upper_80_mg_dl[i] - forecast.forecast.lower_80_mg_dl[i];
      const w95 = forecast.forecast.upper_95_mg_dl[i] - forecast.forecast.lower_95_mg_dl[i];
      assert.ok(w95 >= w80 - 0.01, `Step ${i}: 95% interval width (${w95}) must be >= 80% interval width (${w80})`);
    }
  });

  it("should simulate What-If postprandial trajectories with peak, nadir, and TIR", () => {
    const whatIf = getSyntheticWhatIfResponse(60.0, 4.5, 120.0);
    assert.strictEqual(whatIf.simulated_trajectory.length, 20);
    assert.ok(typeof whatIf.peak_glucose === "number");
    assert.ok(typeof whatIf.nadir_glucose === "number");
    assert.ok(whatIf.time_in_range_pct >= 0 && whatIf.time_in_range_pct <= 100);
  });

  it("should preserve static profile 9-channel schema", () => {
    assert.strictEqual(Object.keys(DEMO_STATIC_PROFILE).length, 9);
    assert.strictEqual(DEMO_STATIC_PROFILE.is_t1dm, 1.0);
  });

  it("should enforce clinical research disclaimer string", () => {
    assert.ok(RESEARCH_DISCLAIMER.includes("decision-support"));
    assert.ok(RESEARCH_DISCLAIMER.includes("investigational"));
  });
});
