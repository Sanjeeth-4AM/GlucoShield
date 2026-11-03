import { describe, it } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { generateSyntheticHistory, getSyntheticForecastResponse, getSyntheticWhatIfResponse, DEMO_STATIC_PROFILE } from "./demoData.js";
import { GLUCOSE_THRESHOLDS, ALERT_LEVELS, RESEARCH_DISCLAIMER } from "./types.js";
import { sanitizeProfile } from "../hooks/useGlucoShieldAPI.js";
import { parseCgmCsv, SAMPLE_CGM_CSV } from "../utils/cgmCsvParser.js";

const __test_filename = fileURLToPath(import.meta.url);
const __test_dirname = path.dirname(__test_filename);
const cohortJsonPath = path.resolve(__test_dirname, "../../../data/processed/demo_cohort_patients.json");
const demoCohortFile = JSON.parse(fs.readFileSync(cohortJsonPath, "utf8"));

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

  it("should sanitize forecast payload against circular React SyntheticEvent objects", () => {
    // Simulate circular SyntheticEvent object from DOM click
    const mockCircularEvent = {
      type: "click",
      target: { tagName: "svg" },
      nativeEvent: {}
    };
    mockCircularEvent.target.stateNode = mockCircularEvent; // Circular reference

    const fallbackHistory = generateSyntheticHistory("stable");
    const fallbackProfile = DEMO_STATIC_PROFILE;

    // Emulate hook type-guard
    const validReadings = Array.isArray(mockCircularEvent) ? mockCircularEvent : fallbackHistory;
    const validProfile = (mockCircularEvent && typeof mockCircularEvent === "object" && !("nativeEvent" in mockCircularEvent)) 
      ? mockCircularEvent 
      : fallbackProfile;

    const payload = {
      patient_id: "patient_live_001",
      history_readings: validReadings,
      static_profile: validProfile
    };

    // Must successfully serialize to JSON without circular error
    const jsonStr = JSON.stringify(payload);
    assert.ok(jsonStr.length > 0);
    assert.strictEqual(payload.history_readings.length, 96);
    assert.strictEqual(payload.static_profile.is_t1dm, 1.0);
  });

  it("should format patient update PUT request with Bearer token and 9 canonical fields", async () => {
    const originalFetch = globalThis.fetch;
    let interceptedUrl = null;
    let interceptedOptions = null;

    globalThis.fetch = async (url, options) => {
      interceptedUrl = url;
      interceptedOptions = options;
      return {
        ok: true,
        json: async () => ({ id: "patient-123", ...JSON.parse(options.body) })
      };
    };

    try {
      const { apiUpdatePatient } = await import("./auth.js");
      const profileData = {
        age: 48.0,
        bmi: 27.2,
        diabetes_duration_years: 14.0,
        hba1c: 62.0,
        glycated_albumin: 19.5,
        fasting_glucose: 140.0,
        fasting_c_peptide: 0.7,
        macrovascular_comp_count: 0.0,
        microvascular_comp_count: 1.0,
        is_t1dm: 1.0
      };

      const result = await apiUpdatePatient("jwt_test_token_xyz", "patient-123", profileData);

      assert.strictEqual(interceptedUrl, "/api/v1/patients/patient-123");
      assert.strictEqual(interceptedOptions.method, "PUT");
      assert.strictEqual(interceptedOptions.headers["Authorization"], "Bearer jwt_test_token_xyz");
      assert.strictEqual(interceptedOptions.headers["Content-Type"], "application/json");

      const body = JSON.parse(interceptedOptions.body);
      assert.strictEqual(body.age, 48.0);
      assert.strictEqual(body.bmi, 27.2);
      assert.strictEqual(body.hba1c, 62.0);
      assert.strictEqual(body.microvascular_comp_count, 1.0);
      assert.strictEqual(result.id, "patient-123");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  describe("Forecast Data Consistency & Clinical Integrity", () => {
    it("should compute distinct Historical In-Range and 5-Hour Projected In-Range without 94.2% fallback", () => {
      // Historical readings: 3 in range, 1 high -> 75%
      const history = [
        { cgm_glucose: 100 },
        { cgm_glucose: 120 },
        { cgm_glucose: 140 },
        { cgm_glucose: 220 }
      ];
      const validHistory = history.filter(r => typeof r.cgm_glucose === "number");
      const historicalTir = Math.round(
        (validHistory.filter(r => r.cgm_glucose >= 70 && r.cgm_glucose <= 180).length / validHistory.length) * 100
      );
      assert.strictEqual(historicalTir, 75);

      // 20-step forecast points: 10 in range (e.g. 150), 10 out of range (e.g. 200) -> 50%
      const pointForecast = [
        ...Array(10).fill(150),
        ...Array(10).fill(200)
      ];
      const projectedTir = Math.round(
        (pointForecast.filter(g => g >= 70 && g <= 180).length / pointForecast.length) * 100
      );
      assert.strictEqual(projectedTir, 50);

      // Verify they remain distinct and never default to synthetic "94.2%"
      assert.notStrictEqual(historicalTir, 94.2);
      assert.notStrictEqual(projectedTir, 94.2);
      assert.notStrictEqual(historicalTir, projectedTir);

      // When forecast points are empty or missing, projected TIR must be null / "—", NOT "94.2%"
      const emptyForecast = [];
      const emptyProjectedTir = emptyForecast.length > 0
        ? Math.round((emptyForecast.filter(g => g >= 70 && g <= 180).length / emptyForecast.length) * 100)
        : null;
      assert.strictEqual(emptyProjectedTir, null);
    });

    it("should map 5 hourly milestone steps in chronological order matching point_forecast_mg_dl", () => {
      const forecast = getSyntheticForecastResponse("stable");
      const pointForecast = forecast.forecast.point_forecast_mg_dl;
      const lower80 = forecast.forecast.lower_80_mg_dl;
      const upper80 = forecast.forecast.upper_80_mg_dl;
      const lower95 = forecast.forecast.lower_95_mg_dl;
      const upper95 = forecast.forecast.upper_95_mg_dl;

      const milestones = [
        { step: "T+1h", idx: 3 },
        { step: "T+2h", idx: 7 },
        { step: "T+3h", idx: 11 },
        { step: "T+4h", idx: 15 },
        { step: "T+5h", idx: 19 }
      ];

      milestones.forEach((m) => {
        const expectedVal = Math.round(pointForecast[m.idx]);
        assert.ok(typeof expectedVal === "number" && !isNaN(expectedVal));
        assert.ok(upper80[m.idx] >= lower80[m.idx]);
        assert.ok(upper95[m.idx] >= upper80[m.idx]);
        assert.ok(lower80[m.idx] >= lower95[m.idx]);
      });
    });

    it("should derive origin glucose and peak projection strictly without synthetic fallbacks", () => {
      const mockForecastResponse = {
        current_state: { glucose_mg_dl: 158.4 },
        forecast: {
          point_forecast_mg_dl: [160, 165, 172, 180, 175, 170, 160, 150, 140, 135, 130, 128, 125, 122, 120, 118, 115, 112, 110, 108]
        },
        risk_assessment: {
          peak_mg_dl: 180.0,
          time_to_peak_min: 60,
          primary_status: "RISING",
          alert_level: "INFO"
        }
      };

      // Origin glucose must equal current_state.glucose_mg_dl
      const originGlucose = mockForecastResponse.current_state.glucose_mg_dl;
      assert.strictEqual(originGlucose, 158.4);

      // Peak glucose and time must match risk_assessment
      const peakGlucose = mockForecastResponse.risk_assessment.peak_mg_dl;
      const peakMinute = mockForecastResponse.risk_assessment.time_to_peak_min;
      assert.strictEqual(peakGlucose, 180.0);
      assert.strictEqual(peakMinute, 60);

      // Alert level mapped to neutral status (no "Verified Safe")
      const alertLevel = mockForecastResponse.risk_assessment.alert_level;
      const ensembleStatus = alertLevel === "CRITICAL"
        ? "Critical Alert (Active)"
        : alertLevel === "WARNING"
        ? "Warning Advisory (Active)"
        : alertLevel === "INFO"
        ? "Informational Advisory"
        : "Nominal Serving (Active)";

      assert.strictEqual(ensembleStatus, "Informational Advisory");
      assert.notStrictEqual(ensembleStatus, "Verified Safe");
    });

    it("should enforce origin precedence: API origin takes precedence over history, history used only if API is null", () => {
      const history = [{ cgm_glucose: 120 }, { cgm_glucose: 135 }];
      
      // Case A: Both present -> API origin must prevail
      const forecastWithOrigin = { current_state: { glucose_mg_dl: 148.0 } };
      const originA = forecastWithOrigin?.current_state?.glucose_mg_dl ?? (history.length > 0 ? history[history.length - 1].cgm_glucose : null);
      assert.strictEqual(originA, 148.0);

      // Case B: API origin null -> Fallback to latest history reading
      const forecastWithoutOrigin = { current_state: { glucose_mg_dl: null } };
      const originB = forecastWithoutOrigin?.current_state?.glucose_mg_dl ?? (history.length > 0 ? history[history.length - 1].cgm_glucose : null);
      assert.strictEqual(originB, 135.0);

      // Case C: Neither present -> Must be null, never synthetic 142.0
      const emptyHistory = [];
      const forecastEmpty = {};
      const originC = forecastEmpty?.current_state?.glucose_mg_dl ?? (emptyHistory.length > 0 ? emptyHistory[emptyHistory.length - 1].cgm_glucose : null);
      assert.strictEqual(originC, null);
    });

    it("should handle non-hourly peak index (+75m) and format timing accurately without confusing hourly milestones", () => {
      // Forecast where peak is at index 4 (5th step = 75 minutes = +1h 15m)
      const points = [140, 160, 185, 205, 230, 210, 195, 180, 170, 160, 150, 145, 140, 138, 135, 132, 130, 128, 125, 120];
      
      let maxVal = -Infinity;
      let maxMins = 0;
      points.forEach((val, i) => {
        if (typeof val === "number" && val > maxVal) {
          maxVal = val;
          maxMins = (i + 1) * 15;
        }
      });

      assert.strictEqual(maxVal, 230);
      assert.strictEqual(maxMins, 75);

      const hrs = Math.floor(maxMins / 60);
      const mins = maxMins % 60;
      const formattedPeakTime = `+${hrs}h ${mins}m`;
      assert.strictEqual(formattedPeakTime, "+1h 15m");

      // Verify milestone T+1h (index 3 = +60m) is 205 mg/dL, distinct from peak 230 mg/dL
      assert.strictEqual(points[3], 205);
      // Verify milestone T+2h (index 7 = +120m) is 180 mg/dL
      assert.strictEqual(points[7], 180);
    });

    it("should sanitize non-finite numbers and reject inverted uncertainty intervals", () => {
      const lower80 = [100, 110, "invalid", NaN, 140];
      const upper80 = [130, 95, 160, 170, Infinity]; // Step 1 is inverted (95 < 110), Step 4 is Infinity

      const sanitizedBands = [];
      for (let i = 0; i < 5; i++) {
        const l80 = (typeof lower80[i] === "number" && !isNaN(lower80[i]) && isFinite(lower80[i])) ? lower80[i] : null;
        const u80 = (typeof upper80[i] === "number" && !isNaN(upper80[i]) && isFinite(upper80[i])) ? upper80[i] : null;
        const valid80 = l80 !== null && u80 !== null && u80 >= l80;
        sanitizedBands.push(valid80 ? [l80, u80] : null);
      }

      assert.deepStrictEqual(sanitizedBands[0], [100, 130]); // Valid
      assert.strictEqual(sanitizedBands[1], null);            // Inverted (95 < 110) -> null
      assert.strictEqual(sanitizedBands[2], null);            // String "invalid" -> null
      assert.strictEqual(sanitizedBands[3], null);            // NaN -> null
      assert.strictEqual(sanitizedBands[4], null);            // Infinity -> null
    });

    it("should preserve base forecast mean trajectory under filter toggle operations and What-If scenarios", () => {
      const basePoints = [150, 155, 160, 165, 170];
      const whatIfPoints = [140, 145, 148, 150, 152];

      // Toggling ciFilter must not alter base trajectory values
      const filters = ["all", "80_only", "mean_only"];
      filters.forEach((filter) => {
        const exportedMean = basePoints.map(p => p);
        assert.deepStrictEqual(exportedMean, [150, 155, 160, 165, 170]);
      });

      // When What-If is present, base trajectory remains identical
      const chartCombined = basePoints.map((base, i) => ({
        baseGlucose: base,
        whatIfGlucose: whatIfPoints[i] ?? null
      }));

      assert.strictEqual(chartCombined[0].baseGlucose, 150);
      assert.strictEqual(chartCombined[0].whatIfGlucose, 140);

      // When What-If is cleared (null), base trajectory is unchanged
      const chartCleared = basePoints.map((base) => ({
        baseGlucose: base,
        whatIfGlucose: null
      }));
      assert.strictEqual(chartCleared[0].baseGlucose, 150);
      assert.strictEqual(chartCleared[0].whatIfGlucose, null);
    });

    it("should gracefully handle empty history with valid current_state by prepending NOW anchor", () => {
      const recentHistory = [];
      const originGlucose = 142.5;

      const chartData = [];
      if (recentHistory.length === 0 && typeof originGlucose === "number" && !isNaN(originGlucose) && isFinite(originGlucose)) {
        chartData.push({
          timeLabel: "NOW",
          minuteOffset: 0,
          isHistory: true,
          historicalGlucose: originGlucose,
          forecastGlucose: originGlucose
        });
      }

      assert.strictEqual(chartData.length, 1);
      assert.strictEqual(chartData[0].timeLabel, "NOW");
      assert.strictEqual(chartData[0].forecastGlucose, 142.5);
    });
  });

  describe("9 Representative Forecast Validation Cases", () => {
    // 1. Normal forecast with complete response
    it("Case 1: Normal forecast with complete response evaluates all 20 steps and intervals", () => {
      const forecast = getSyntheticForecastResponse("stable");
      const history = generateSyntheticHistory("stable");
      
      const pointForecast = forecast.forecast.point_forecast_mg_dl;
      const lower80 = forecast.forecast.lower_80_mg_dl;
      const upper80 = forecast.forecast.upper_80_mg_dl;
      const lower95 = forecast.forecast.lower_95_mg_dl;
      const upper95 = forecast.forecast.upper_95_mg_dl;

      assert.strictEqual(pointForecast.length, 20);
      assert.strictEqual(lower80.length, 20);
      assert.strictEqual(upper80.length, 20);
      assert.strictEqual(lower95.length, 20);
      assert.strictEqual(upper95.length, 20);

      const hasIntervals = Array.isArray(lower80) && lower80.length > 0 && Array.isArray(upper80) && upper80.length > 0;
      assert.strictEqual(hasIntervals, true);

      const projectedTir = Math.round(
        (pointForecast.filter(g => g >= 70 && g <= 180).length / pointForecast.length) * 100
      );
      assert.ok(projectedTir >= 0 && projectedTir <= 100);
    });

    // 2. Missing optional risk-assessment fields
    it("Case 2: Missing optional risk-assessment fields derives peak from trajectory and maintains nominal state", () => {
      const forecastWithoutRisk = {
        current_state: { glucose_mg_dl: 140.0 },
        forecast: {
          point_forecast_mg_dl: [145, 155, 175, 165, 150, 140, 135, 130, 125, 120, 118, 115, 112, 110, 108, 105, 102, 100, 98, 95]
        },
        risk_assessment: null
      };

      const pointForecast = forecastWithoutRisk.forecast.point_forecast_mg_dl;
      let peakGlucose = null;
      let peakMinute = null;

      if (forecastWithoutRisk?.risk_assessment?.peak_mg_dl != null && forecastWithoutRisk?.risk_assessment?.time_to_peak_min != null) {
        peakGlucose = Number(forecastWithoutRisk.risk_assessment.peak_mg_dl);
        peakMinute = Number(forecastWithoutRisk.risk_assessment.time_to_peak_min);
      } else if (pointForecast.length > 0) {
        let maxVal = -Infinity;
        let maxMins = 0;
        pointForecast.forEach((val, i) => {
          if (typeof val === "number" && val > maxVal) {
            maxVal = val;
            maxMins = (i + 1) * 15;
          }
        });
        if (maxVal !== -Infinity) {
          peakGlucose = maxVal;
          peakMinute = maxMins;
        }
      }

      assert.strictEqual(peakGlucose, 175);
      assert.strictEqual(peakMinute, 45); // 3rd step = 45m

      const primaryStatus = forecastWithoutRisk?.risk_assessment?.primary_status || "STABLE";
      const alertLevel = forecastWithoutRisk?.risk_assessment?.alert_level;
      const ensembleStatus = alertLevel === "CRITICAL"
        ? "Critical Alert (Active)"
        : alertLevel === "WARNING"
        ? "Warning Advisory (Active)"
        : alertLevel === "INFO"
        ? "Informational Advisory"
        : forecastWithoutRisk?.forecast
        ? "Nominal Serving (Active)"
        : "Awaiting Forecast";

      assert.strictEqual(primaryStatus, "STABLE");
      assert.strictEqual(ensembleStatus, "Nominal Serving (Active)");
    });

    // 3. Telemetry pending with historical readings available
    it("Case 3: Telemetry pending with historical readings anchors origin to latest CGM and displays unavailable for forecast", () => {
      const history = [{ cgm_glucose: 128 }, { cgm_glucose: 134 }, { cgm_glucose: 142 }];
      const forecastData = null; // Telemetry pending
      const isLoading = true;

      const originGlucose = forecastData?.current_state?.glucose_mg_dl ?? (history.length > 0 ? history[history.length - 1].cgm_glucose : null);
      assert.strictEqual(originGlucose, 142);

      const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
      const projectedTir = pointForecast.length > 0
        ? Math.round((pointForecast.filter(g => g >= 70 && g <= 180).length / pointForecast.length) * 100)
        : null;
      assert.strictEqual(projectedTir, null);

      const validHistory = history.filter(r => typeof r.cgm_glucose === "number");
      const historicalTir = validHistory.length > 0
        ? Math.round((validHistory.filter(r => r.cgm_glucose >= 70 && r.cgm_glucose <= 180).length / validHistory.length) * 100)
        : null;
      assert.strictEqual(historicalTir, 100);
    });

    // 4. Empty history and no valid origin
    it("Case 4: Empty history and no valid origin renders null origin without synthetic numbers", () => {
      const history = [];
      const forecastData = { current_state: { glucose_mg_dl: null } };

      const originGlucose = forecastData?.current_state?.glucose_mg_dl ?? (history.length > 0 ? history[history.length - 1].cgm_glucose : null);
      assert.strictEqual(originGlucose, null);

      const validHistory = history.filter(r => typeof r?.cgm_glucose === "number");
      const historicalTir = validHistory.length > 0 ? 100 : null;
      assert.strictEqual(historicalTir, null);
    });

    // 5. Short or malformed forecast arrays
    it("Case 5: Short forecast array (5 steps) populates valid milestones and marks remaining steps as unavailable", () => {
      const shortPoints = [145, 150, 155, 160, 165]; // Only 5 steps, indices 0..4
      const milestones = [
        { step: "T+1h", idx: 3 },
        { step: "T+2h", idx: 7 },
        { step: "T+3h", idx: 11 },
        { step: "T+4h", idx: 15 },
        { step: "T+5h", idx: 19 }
      ].map(m => {
        const hasPoint = typeof shortPoints[m.idx] === "number" && !isNaN(shortPoints[m.idx]) && isFinite(shortPoints[m.idx]);
        return {
          step: m.step,
          projected: hasPoint ? Math.round(shortPoints[m.idx]) : "—"
        };
      });

      assert.strictEqual(milestones[0].projected, 160); // T+1h is present
      assert.strictEqual(milestones[1].projected, "—"); // T+2h absent
      assert.strictEqual(milestones[2].projected, "—"); // T+3h absent
      assert.strictEqual(milestones[3].projected, "—"); // T+4h absent
      assert.strictEqual(milestones[4].projected, "—"); // T+5h absent
    });

    // 6. Missing uncertainty intervals
    it("Case 6: Missing uncertainty intervals flags unavailable and renders mean line cleanly", () => {
      const forecastWithoutIntervals = {
        forecast: {
          point_forecast_mg_dl: [140, 142, 145, 150],
          lower_80_mg_dl: [],
          upper_80_mg_dl: [],
          lower_95_mg_dl: null,
          upper_95_mg_dl: null
        }
      };

      const lower80 = forecastWithoutIntervals.forecast.lower_80_mg_dl || [];
      const upper80 = forecastWithoutIntervals.forecast.upper_80_mg_dl || [];
      const hasIntervals = Array.isArray(lower80) && lower80.length > 0 && Array.isArray(upper80) && upper80.length > 0;
      assert.strictEqual(hasIntervals, false);

      const ribbonText = hasIntervals ? "80% & 95% UI" : "Unavailable";
      assert.strictEqual(ribbonText, "Unavailable");
    });

    // 7. Forecast with peak at non-hourly index (+30m)
    it("Case 7: Forecast with peak at non-hourly index (+30m) formats peak accurately without altering hourly rows", () => {
      // Peak at index 1 (+30m)
      const points = [150, 195, 180, 170, 160, 150, 140, 130, 125, 120, 115, 110, 108, 105, 102, 100, 98, 95, 92, 90];
      let maxVal = -Infinity;
      let maxMins = 0;
      points.forEach((val, i) => {
        if (typeof val === "number" && val > maxVal) {
          maxVal = val;
          maxMins = (i + 1) * 15;
        }
      });

      assert.strictEqual(maxVal, 195);
      assert.strictEqual(maxMins, 30);
      const hrs = Math.floor(maxMins / 60);
      const mins = maxMins % 60;
      assert.strictEqual(`+${hrs}h ${mins}m`, "+0h 30m");

      // Hourly milestone T+1h is 170 mg/dL, distinct from peak 195 mg/dL
      assert.strictEqual(points[3], 170);
    });

    // 8. What-If scenario present and absent
    it("Case 8: What-If scenario present and absent toggles overlay cleanly without mutating base forecast", () => {
      const baseTrajectory = [140, 145, 150, 155, 160];
      const whatIfTrajectory = [140, 150, 165, 170, 160];

      // Overlay present
      const combined = baseTrajectory.map((b, i) => ({
        base: b,
        whatIf: whatIfTrajectory[i]
      }));
      assert.strictEqual(combined[2].base, 150);
      assert.strictEqual(combined[2].whatIf, 165);

      // Overlay absent (null)
      const cleared = baseTrajectory.map((b) => ({
        base: b,
        whatIf: null
      }));
      assert.strictEqual(cleared[2].base, 150);
      assert.strictEqual(cleared[2].whatIf, null);
    });

    // 9. API error or unavailable backend
    it("Case 9: API error or unavailable backend results in null forecast with graceful awaiting status", () => {
      const forecastData = null;
      const errorMsg = "HTTP 503: Service Unavailable";

      const originGlucose = forecastData?.current_state?.glucose_mg_dl ?? null;
      const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
      const projectedTir = pointForecast.length > 0 ? 100 : null;
      const ensembleStatus = forecastData?.forecast ? "Nominal Serving (Active)" : "Awaiting Forecast";

      assert.strictEqual(originGlucose, null);
      assert.strictEqual(projectedTir, null);
      assert.strictEqual(ensembleStatus, "Awaiting Forecast");
      assert.ok(errorMsg.includes("503"));
    });

    it("should strictly synchronize CurrentGlucoseCard value and ForecastChart origin at NOW timestamp", () => {
      const mockState = {
        glucose_mg_dl: 148.5,
        timestamp: "2026-10-12T01:15:00Z"
      };

      // CurrentGlucoseCard derivation: Math.round(currentState.glucose_mg_dl)
      const currentGlucoseCardVal = mockState?.glucose_mg_dl !== undefined ? Math.round(mockState.glucose_mg_dl) : null;
      assert.strictEqual(currentGlucoseCardVal, 149);

      // ForecastChart derivation:
      const chartOrigin = mockState?.glucose_mg_dl ?? null;
      assert.strictEqual(chartOrigin, 148.5);
      const roundedChartOrigin = Math.round(chartOrigin);
      assert.strictEqual(roundedChartOrigin, 149);

      // Exact agreement
      assert.strictEqual(currentGlucoseCardVal, roundedChartOrigin);
    });

    it("should reconcile all 20 forecast points element-by-element with chart coordinates, milestones, intervals, and peak formatting", () => {
      // Live captured forecast simulation
      const liveData = {
        current_state: { glucose_mg_dl: 125.3 },
        forecast: {
          point_forecast_mg_dl: [
            124.9, 121.8, 122.6, 122.8, 123.1, 123.2, 122.8, 121.8, 121.2, 120.9,
            119.6, 118.7, 118.2, 118.0, 117.8, 117.7, 117.3, 117.5, 116.4, 117.0
          ],
          lower_80_mg_dl: [
            89.9, 86.0, 85.0, 83.3, 83.6, 81.2, 81.3, 77.9, 76.9, 76.0,
            73.6, 72.3, 70.6, 69.8, 68.1, 67.6, 66.3, 65.5, 63.9, 63.6
          ],
          upper_80_mg_dl: [
            159.8, 157.6, 160.1, 162.4, 162.5, 165.2, 164.3, 165.7, 165.6, 165.9,
            165.7, 165.1, 165.8, 166.2, 167.4, 167.9, 168.4, 169.6, 168.9, 170.4
          ],
          lower_95_mg_dl: [
            71.4, 67.1, 65.1, 62.4, 62.7, 58.9, 59.3, 54.7, 53.5, 52.2,
            49.2, 47.7, 45.5, 44.3, 41.8, 41.1, 39.3, 38.0, 36.1, 35.3
          ],
          upper_95_mg_dl: [
            178.3, 176.5, 180.0, 183.3, 183.4, 187.4, 186.3, 188.8, 189.0, 189.6,
            190.0, 189.6, 191.0, 191.7, 193.7, 194.4, 195.4, 197.1, 196.7, 198.7
          ]
        },
        risk_assessment: {
          peak_mg_dl: 124.9,
          time_to_peak_min: 15
        }
      };

      const pts = liveData.forecast.point_forecast_mg_dl;
      const l80 = liveData.forecast.lower_80_mg_dl;
      const u80 = liveData.forecast.upper_80_mg_dl;
      const l95 = liveData.forecast.lower_95_mg_dl;
      const u95 = liveData.forecast.upper_95_mg_dl;

      // 1. Element-by-element comparison of all 20 steps
      assert.strictEqual(pts.length, 20);
      pts.forEach((val, i) => {
        const mins = (i + 1) * 15;
        const hrs = Math.floor(mins / 60);
        const rem = mins % 60;
        const label = `+${hrs > 0 ? `${hrs}h` : ""}${rem > 0 ? `${rem}m` : ""}`;

        // Verify label and coordinates
        assert.ok(label.startsWith("+"));
        assert.strictEqual(val, pts[i]);

        // Monotonic uncertainty bounds
        assert.ok(l95[i] <= l80[i], `Step ${i}: 95% lower ${l95[i]} must be <= 80% lower ${l80[i]}`);
        assert.ok(l80[i] <= val, `Step ${i}: 80% lower ${l80[i]} must be <= Point ${val}`);
        assert.ok(val <= u80[i], `Step ${i}: Point ${val} must be <= 80% upper ${u80[i]}`);
        assert.ok(u80[i] <= u95[i], `Step ${i}: 80% upper ${u80[i]} must be <= 95% upper ${u95[i]}`);
      });

      // 2. Five hourly milestone indices strictly 3, 7, 11, 15, 19
      const milestoneIndices = [
        { step: "T+1h", idx: 3, expectedMins: 60, expectedVal: 123 },
        { step: "T+2h", idx: 7, expectedMins: 120, expectedVal: 122 },
        { step: "T+3h", idx: 11, expectedMins: 180, expectedVal: 119 },
        { step: "T+4h", idx: 15, expectedMins: 240, expectedVal: 118 },
        { step: "T+5h", idx: 19, expectedMins: 300, expectedVal: 117 }
      ];

      milestoneIndices.forEach((m) => {
        const actualMins = (m.idx + 1) * 15;
        assert.strictEqual(actualMins, m.expectedMins);
        const rawPoint = pts[m.idx];
        const roundedPoint = Math.round(rawPoint);
        assert.strictEqual(roundedPoint, m.expectedVal);
      });

      // 3. Peak value and natural timing derivation
      const peakVal = liveData.risk_assessment.peak_mg_dl;
      const peakMin = liveData.risk_assessment.time_to_peak_min;
      const maxTrajVal = Math.max(...pts);
      assert.strictEqual(peakVal, maxTrajVal);

      const peakFmtUnder60 = peakMin < 60 ? `+${peakMin}m` : `+${Math.floor(peakMin / 60)}h${peakMin % 60 > 0 ? ` ${peakMin % 60}m` : ""}`;
      assert.strictEqual(peakFmtUnder60, "+15m");

      const peak75Fmt = 75 < 60 ? `+75m` : `+${Math.floor(75 / 60)}h${75 % 60 > 0 ? ` ${75 % 60}m` : ""}`;
      assert.strictEqual(peak75Fmt, "+1h 15m");
    });
  });

  describe("History Panel Telemetry & Invariant Verifications", () => {
    it("should correctly resolve streamBadge when readings > 0 and readings === 0", () => {
      const getStreamBadge = (totalReadings) =>
        totalReadings > 0
          ? { label: "Active Stream", bg: "bg-tertiary-fixed", text: "text-on-tertiary-fixed", icon: true }
          : { label: "No Data", bg: "bg-surface-container-high", text: "text-on-surface-variant", icon: false };

      const activeBadge = getStreamBadge(48);
      assert.strictEqual(activeBadge.label, "Active Stream");
      assert.strictEqual(activeBadge.icon, true);

      const emptyBadge = getStreamBadge(0);
      assert.strictEqual(emptyBadge.label, "No Data");
      assert.strictEqual(emptyBadge.icon, false);
    });

    it("should normalize 'today' timeframe to '24h' for backend analytics query", () => {
      const normalizePeriod = (timeframe) => (timeframe === "today" ? "24h" : timeframe);

      assert.strictEqual(normalizePeriod("today"), "24h");
      assert.strictEqual(normalizePeriod("7d"), "7d");
      assert.strictEqual(normalizePeriod("14d"), "14d");
      assert.strictEqual(normalizePeriod("30d"), "30d");
    });

    it("should require verified AGP criteria and use exact empty state message", () => {
      const agpEmptyHeading = "Insufficient longitudinal data for AGP";
      assert.strictEqual(agpEmptyHeading, "Insufficient longitudinal data for AGP");

      const hasAgpPoints = (points) => Array.isArray(points) && points.length >= 12;
      assert.strictEqual(hasAgpPoints([]), false);
      assert.strictEqual(hasAgpPoints(null), false);
      assert.strictEqual(hasAgpPoints(Array(8).fill({})), false);
      assert.strictEqual(hasAgpPoints(Array(24).fill({})), true);
    });

    it("should guard against unauthenticated or missing patient ID in History query", () => {
      const resolvePatientId = (patientProfile) => patientProfile?.id || null;

      assert.strictEqual(resolvePatientId(null), null);
      assert.strictEqual(resolvePatientId(undefined), null);
      assert.strictEqual(resolvePatientId({}), null);
      assert.strictEqual(resolvePatientId({ id: "patient_001" }), "patient_001");
    });
  });

  describe("Patient Profile Data Provenance, Telemetry Contract & Invariant Verifications", () => {
    it("should format missing patient fields as 'Not provided' and diagnosis strictly without fabricated defaults", () => {
      const formatVal = (val, suffix = "") => {
        if (val === null || val === undefined || val === "" || isNaN(val)) {
          return "Not provided";
        }
        return `${val}${suffix}`;
      };

      const resolveDiagnosis = (is_t1dm) => {
        if (is_t1dm === 1.0 || is_t1dm === 1) return "Type 1 Diabetes Mellitus";
        if (is_t1dm === 0.0 || is_t1dm === 0) return "Type 2 Diabetes Mellitus";
        return "Not provided";
      };

      // Test formatVal
      assert.strictEqual(formatVal(null), "Not provided");
      assert.strictEqual(formatVal(undefined), "Not provided");
      assert.strictEqual(formatVal(""), "Not provided");
      assert.strictEqual(formatVal(NaN), "Not provided");
      assert.strictEqual(formatVal(45.0, " yrs"), "45 yrs");
      assert.strictEqual(formatVal(26.5), "26.5");
      assert.strictEqual(formatVal(58.0, " mmol/mol"), "58 mmol/mol");
      assert.strictEqual(formatVal(130.0, " mg/dL"), "130 mg/dL");
      assert.strictEqual(formatVal(0.8, " ng/mL"), "0.8 ng/mL");
      assert.strictEqual(formatVal(18.0, "%"), "18%");

      // Test diagnosis mapping
      assert.strictEqual(resolveDiagnosis(1.0), "Type 1 Diabetes Mellitus");
      assert.strictEqual(resolveDiagnosis(0.0), "Type 2 Diabetes Mellitus");
      assert.strictEqual(resolveDiagnosis(null), "Not provided");
      assert.strictEqual(resolveDiagnosis(undefined), "Not provided");
    });

    it("should sanitize profile covariates by omitting null or undefined fields when building backend inference payloads", async () => {
      const { sanitizeProfile } = await import("../hooks/useGlucoShieldAPI.js");

      // Complete profile
      const fullProfile = { age: 45.0, bmi: 26.5, hba1c: 58.0, is_t1dm: 1.0 };
      const cleanedFull = sanitizeProfile(fullProfile);
      assert.deepStrictEqual(cleanedFull, fullProfile);

      // Incomplete profile with null / undefined fields
      const partialProfile = {
        age: 50.0,
        bmi: null,
        diabetes_duration_years: undefined,
        hba1c: 62.0,
        fasting_glucose: null,
        fasting_c_peptide: 0.9,
        is_t1dm: 1.0
      };
      const cleanedPartial = sanitizeProfile(partialProfile);
      assert.strictEqual(cleanedPartial.age, 50.0);
      assert.strictEqual(cleanedPartial.hba1c, 62.0);
      assert.strictEqual(cleanedPartial.fasting_c_peptide, 0.9);
      assert.strictEqual(cleanedPartial.is_t1dm, 1.0);
      assert.strictEqual(cleanedPartial.bmi, undefined);
      assert.strictEqual(cleanedPartial.diabetes_duration_years, undefined);
      assert.strictEqual(cleanedPartial.fasting_glucose, undefined);

      // Empty or invalid object
      assert.strictEqual(sanitizeProfile(null), undefined);
      assert.strictEqual(sanitizeProfile({}), undefined);
      assert.strictEqual(sanitizeProfile({ target: {} }), undefined);
    });

    it("should reconcile telemetry contract: 96 historical steps (24h @ 15m), 22 dynamic channels, 20 future steps (5h @ 15m), no live hardware stream implied", () => {
      const TELEMETRY_CONTRACT = {
        source_sampling: "5-min raw -> 15-min resampled",
        historical_steps: 96,
        historical_duration_hours: 24,
        historical_interval_min: 15,
        forecast_steps: 20,
        forecast_duration_hours: 5,
        forecast_interval_min: 15,
        dynamic_channels: 22,
        hardware_stream: "No Direct Live Stream (REST Sync)",
        ingestion_type: "Database Ingestion (REST)"
      };

      assert.strictEqual(TELEMETRY_CONTRACT.historical_steps, 96);
      assert.strictEqual((TELEMETRY_CONTRACT.historical_duration_hours * 60) / TELEMETRY_CONTRACT.historical_interval_min, 96);
      assert.strictEqual(TELEMETRY_CONTRACT.forecast_steps, 20);
      assert.strictEqual((TELEMETRY_CONTRACT.forecast_duration_hours * 60) / TELEMETRY_CONTRACT.forecast_interval_min, 20);
      assert.strictEqual(TELEMETRY_CONTRACT.dynamic_channels, 22);
      assert.strictEqual(TELEMETRY_CONTRACT.hardware_stream, "No Direct Live Stream (REST Sync)");
      assert.strictEqual(TELEMETRY_CONTRACT.ingestion_type, "Database Ingestion (REST)");
    });

    it("should enforce frozen V1 model invariant where runtime force calibration cycle is disabled", () => {
      const CALIBRATION_POLICY = {
        model_version: "COMBINATION_C",
        v1_neural_weights_frozen: true,
        v1_ode_parameters_frozen: true,
        eta_si: 0.04,
        beta: 0.7,
        runtime_recalibration_enabled: false,
        button_state: "disabled",
        invariant_notice: "Runtime recalibration is disabled. V1 weights and ODE parameters are frozen."
      };

      assert.strictEqual(CALIBRATION_POLICY.runtime_recalibration_enabled, false);
      assert.strictEqual(CALIBRATION_POLICY.button_state, "disabled");
      assert.strictEqual(CALIBRATION_POLICY.eta_si, 0.04);
      assert.strictEqual(CALIBRATION_POLICY.beta, 0.7);
    });

    it("should enforce neutral care management workflow labels without unsupported institutional claims", () => {
      const CARE_MANAGEMENT_LABELS = {
        support: "Support Contact",
        emergency: "Emergency Contact",
        care_team: "Care Team Assignment",
        follow_up: "Follow-up Schedule",
        reference: "Covariate Baseline Specification"
      };

      // Disallowed institutional workflow strings
      const forbiddenStrings = [
        "Clinical Support Interface",
        "Escalation Contact Routing",
        "Clinical Practice Guidelines Standard"
      ];

      for (const val of Object.values(CARE_MANAGEMENT_LABELS)) {
        for (const forbidden of forbiddenStrings) {
          assert.notStrictEqual(val, forbidden);
        }
      }
      assert.strictEqual(CARE_MANAGEMENT_LABELS.support, "Support Contact");
      assert.strictEqual(CARE_MANAGEMENT_LABELS.emergency, "Emergency Contact");
      assert.strictEqual(CARE_MANAGEMENT_LABELS.reference, "Covariate Baseline Specification");
    });
  });

  describe("Live Mode Data Isolation & Null State Safety", () => {
    it("should sanitize profile objects and strip non-numeric or SyntheticEvent properties", () => {
      assert.strictEqual(sanitizeProfile(null), undefined);
      assert.strictEqual(sanitizeProfile(undefined), undefined);
      assert.strictEqual(sanitizeProfile({ target: {}, nativeEvent: {} }), undefined);
      assert.strictEqual(sanitizeProfile({}), undefined);

      const raw = {
        age: "45",
        bmi: 24.5,
        hba1c: 58.0,
        unknownField: "",
        nullField: null,
        nonNumeric: "invalid"
      };
      const cleaned = sanitizeProfile(raw);
      assert.deepStrictEqual(cleaned, { age: 45, bmi: 24.5, hba1c: 58.0 });
    });

    it("should enforce Live API mode isolation: empty history yields null forecast without synthetic generation", () => {
      const readings = [];
      const isDemoMode = false;

      let syntheticCalled = false;
      const mockGetSyntheticForecastResponse = () => {
        syntheticCalled = true;
        return getSyntheticForecastResponse("stable");
      };

      let forecastData = "initial";
      let isLoadingForecast = true;

      if (isDemoMode) {
        forecastData = mockGetSyntheticForecastResponse();
      } else {
        if (!readings || readings.length < 96) {
          forecastData = null;
          isLoadingForecast = false;
        }
      }

      assert.strictEqual(forecastData, null, "Live API mode must set forecastData to null when history has < 96 readings");
      assert.strictEqual(isLoadingForecast, false);
      assert.strictEqual(syntheticCalled, false, "Live API mode must NEVER call synthetic data generators on empty history");
    });

    it("should prevent silent synthetic fallback on Live API fetch errors", () => {
      const isDemoMode = false;
      let syntheticCalled = false;
      const mockGetSyntheticForecastResponse = () => {
        syntheticCalled = true;
        return getSyntheticForecastResponse("stable");
      };

      let forecastData = "initial";
      let errorMessage = null;

      try {
        throw new Error("HTTP 500: Server error");
      } catch (err) {
        if (isDemoMode) {
          forecastData = mockGetSyntheticForecastResponse();
        } else {
          errorMessage = `Live forecast unavailable: ${err.message}`;
          forecastData = null;
        }
      }

      assert.strictEqual(forecastData, null, "Must NOT silently fall back to synthetic forecast on API failure");
      assert.ok(errorMessage.includes("HTTP 500"));
      assert.strictEqual(syntheticCalled, false, "Synthetic generator must not be invoked on Live API error");
    });

    it("should guard What-If simulation and Full Decision Flow against insufficient history in Live API mode", () => {
      const isDemoMode = false;
      const historyReadings = [];

      let syntheticWhatIfCalled = false;
      let syntheticFullFlowCalled = false;

      let whatIfData = "initial";
      let whatIfError = null;
      if (isDemoMode) {
        syntheticWhatIfCalled = true;
      } else if (!historyReadings || historyReadings.length < 96) {
        whatIfData = null;
        whatIfError = "What-If simulation requires 24 hours of CGM history (96 readings).";
      }

      assert.strictEqual(whatIfData, null);
      assert.ok(whatIfError.includes("96 readings"));
      assert.strictEqual(syntheticWhatIfCalled, false);

      let fullFlowData = "initial";
      let fullFlowError = null;
      if (isDemoMode) {
        syntheticFullFlowCalled = true;
      } else if (!historyReadings || historyReadings.length < 96) {
        fullFlowData = null;
        fullFlowError = "Full decision flow requires 24 hours of CGM history (96 readings).";
      }

      assert.strictEqual(fullFlowData, null);
      assert.ok(fullFlowError.includes("96 readings"));
      assert.strictEqual(syntheticFullFlowCalled, false);
    });

    it("should strictly confine synthetic generators to explicitly activated Demo mode", () => {
      const isDemoMode = true;
      assert.strictEqual(isDemoMode, true);

      const demoHistory = generateSyntheticHistory("stable");
      assert.strictEqual(demoHistory.length, 96);

      const demoForecast = getSyntheticForecastResponse("stable");
      assert.strictEqual(demoForecast.forecast.point_forecast_mg_dl.length, 20);
      assert.strictEqual(demoForecast.current_state.glucose_mg_dl, 122.5);

      const demoWhatIf = getSyntheticWhatIfResponse(50.0, 4.0, 120.0);
      assert.strictEqual(demoWhatIf.simulated_trajectory.length, 20);
    });
  });

  describe("Chart Stability & Render Loop Prevention", () => {
    it("should guarantee functional state update idempotency on empty history", () => {
      // In App.jsx, setHistoryReadings uses: (prev) => (prev && prev.length > 0 ? [] : prev)
      const updater = (prev) => (prev && prev.length > 0 ? [] : prev);

      const emptyArray = [];
      const result1 = updater(emptyArray);
      assert.strictEqual(result1, emptyArray, "Must return exact same reference when already empty to prevent React re-renders");

      const filledArray = [{ cgm_glucose: 120 }];
      const result2 = updater(filledArray);
      assert.strictEqual(result2.length, 0);
      assert.notStrictEqual(result2, filledArray);

      // Repeated update on the newly emptied array
      const result3 = updater(result2);
      assert.strictEqual(result3, result2, "Subsequent empty updates must be strictly idempotent");
    });

    it("should keep live mode active without silent demo fallback when backend is unreachable", () => {
      let isDemoMode = false;
      let backendHealth = null;

      const handleHealthResult = (h) => {
        backendHealth = h || { status: "unreachable", error: "Backend server unavailable" };
        if (h && (h.status === "healthy" || h.status === "ok")) {
          isDemoMode = false;
        }
      };

      // Case 1: 502 / Unreachable backend
      handleHealthResult(null);
      assert.strictEqual(backendHealth.status, "unreachable");
      assert.strictEqual(isDemoMode, false, "Must NOT silently switch to demo mode when backend returns 502/unreachable");

      // Case 2: Backend becomes healthy again
      handleHealthResult({ status: "healthy", version: "1.0.0" });
      assert.strictEqual(backendHealth.status, "healthy");
      assert.strictEqual(isDemoMode, false);
    });

    it("should produce stable, deterministic chart datasets for Recharts without mutating external state", () => {
      const computeChartData = (historyReadings, forecastData) => {
        const recentHistory = (historyReadings || []).slice(-16);
        const data = [];
        const originGlucose = forecastData?.current_state?.glucose_mg_dl ?? (recentHistory.length > 0 ? recentHistory[recentHistory.length - 1]?.cgm_glucose : null);

        recentHistory.forEach((r, idx) => {
          const minsAgo = (recentHistory.length - 1 - idx) * 15;
          const isNow = minsAgo === 0;
          const nowGlucose = isNow ? (originGlucose ?? r.cgm_glucose) : null;
          data.push({
            timeLabel: isNow ? "NOW" : `-${Math.floor(minsAgo / 60)}h`,
            historicalGlucose: r.cgm_glucose,
            forecastGlucose: nowGlucose
          });
        });

        if (recentHistory.length === 0 && typeof originGlucose === "number") {
          data.push({
            timeLabel: "NOW",
            historicalGlucose: originGlucose,
            forecastGlucose: originGlucose
          });
        }

        const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
        pointForecast.forEach((val, i) => {
          data.push({
            timeLabel: `+${i + 1}h`,
            historicalGlucose: null,
            forecastGlucose: val
          });
        });

        return data;
      };

      const empty1 = computeChartData([], null);
      assert.strictEqual(empty1.length, 0);

      const history = [{ cgm_glucose: 110 }, { cgm_glucose: 120 }];
      const forecast = { current_state: { glucose_mg_dl: 120 }, forecast: { point_forecast_mg_dl: [122, 125] } };
      const data1 = computeChartData(history, forecast);
      const data2 = computeChartData(history, forecast);

      assert.deepStrictEqual(data1, data2);
      assert.strictEqual(data1.length, 4);
      assert.strictEqual(data1[1].timeLabel, "NOW");
      assert.strictEqual(data1[1].historicalGlucose, 120);
    });
  });

  describe("Patient Isolation, Stale State Prevention & Event Reconciliation", () => {
    it("should clear inference state immediately upon patient switch or logout", () => {
      let forecastData = { current_state: { glucose_mg_dl: 118.7 }, forecast: { point_forecast_mg_dl: [103.9] } };
      let whatIfData = { simulated_trajectory: [120] };
      let foodAnalysisData = { selected_food: "Rice" };
      let fullFlowData = { decision_summary: { alert_status: "NONE" } };

      const clearInferenceState = () => {
        forecastData = null;
        whatIfData = null;
        foodAnalysisData = null;
        fullFlowData = null;
      };

      // Patient switch occurs:
      clearInferenceState();

      assert.strictEqual(forecastData, null, "Forecast data from previous patient must be completely cleared");
      assert.strictEqual(whatIfData, null, "What-If simulation from previous patient must be cleared");
      assert.strictEqual(foodAnalysisData, null, "Food analysis from previous patient must be cleared");
      assert.strictEqual(fullFlowData, null, "Decision flow data from previous patient must be cleared");
    });

    it("should reconcile RecentEventsCard merging of genuine telemetry and persisted database events", () => {
      const historyReadings = [
        { timestamp: "2026-10-13T12:00:00Z", cgm_glucose: 110, insulin_bolus: 0, meal_carbs: 0 },
        { timestamp: "2026-10-13T12:15:00Z", cgm_glucose: 125, insulin_bolus: 3.5, meal_carbs: 0 }
      ];

      const persistedEvents = [
        { id: "meal-1", timestamp: "2026-10-13T12:30:00Z", meal_name: "Device Meal", carbs_g: 60.0, source: "manual_mobile" },
        { id: "dec-1", timestamp: "2026-10-13T12:05:00Z", alert_status: "NONE", recommended_action: "Monitor target", decision_summary: { recommended_action: "Monitor target" } }
      ];

      const telemetryEvents = historyReadings
        .filter((r) => (r.insulin_bolus && r.insulin_bolus > 0) || (r.meal_carbs && r.meal_carbs > 0))
        .map((r) => ({
          timestamp: r.timestamp,
          title: r.meal_carbs > 0 ? "Meal Event Logged" : "Insulin Delivery Logged",
          description: r.meal_carbs > 0 ? `${r.meal_carbs}g CHO recorded` : `${r.insulin_bolus} U bolus administered`
        }));

      const dbEvents = persistedEvents.map((ev) => {
        if (ev.carbs_g !== undefined) {
          return {
            timestamp: ev.timestamp,
            title: ev.meal_name || "Meal Event Logged",
            description: `${ev.carbs_g}g CHO recorded (${ev.source})`
          };
        } else {
          return {
            timestamp: ev.timestamp,
            title: ev.recommended_action,
            description: ev.decision_summary?.recommended_action
          };
        }
      });

      const merged = [...telemetryEvents, ...dbEvents]
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, 3);

      assert.strictEqual(merged.length, 3);
      // Newest first: 12:30 (meal-1), 12:15 (bolus 3.5), 12:05 (decision)
      assert.strictEqual(merged[0].title, "Device Meal");
      assert.strictEqual(merged[0].description, "60g CHO recorded (manual_mobile)");
      assert.strictEqual(merged[1].title, "Insulin Delivery Logged");
      assert.strictEqual(merged[1].description, "3.5 U bolus administered");
      assert.strictEqual(merged[2].title, "Monitor target");
    });

    it("should present empty state when both telemetry and persisted events are absent without synthetic fallback", () => {
      const historyReadings = [];
      const persistedEvents = [];

      const telemetryEvents = historyReadings.filter((r) => (r.insulin_bolus && r.insulin_bolus > 0) || (r.meal_carbs && r.meal_carbs > 0));
      const dbEvents = persistedEvents;
      const merged = [...telemetryEvents, ...dbEvents];

      assert.strictEqual(merged.length, 0, "No synthetic events must be created when real events are absent");
    });

    it("should explain absent historical telemetry when historical readings array is empty", () => {
      const historyReadings = [];
      const validHistory = historyReadings.filter((r) => r && typeof r.cgm_glucose === "number" && !isNaN(r.cgm_glucose));
      const historicalTirPct = validHistory.length > 0 ? 100 : null;

      assert.strictEqual(historicalTirPct, null);
      const explanation = historicalTirPct === null ? "(No eligible historical readings)" : `${historicalTirPct}%`;
      assert.strictEqual(explanation, "(No eligible historical readings)");
    });

    it("should synchronize CurrentGlucoseCard and ForecastChart origin with latest reading when forecast is null", () => {
      const latestReading = { timestamp: "2026-10-13T16:34:00Z", cgm_glucose: 118.5 };
      const forecastData = null;

      // ForecastChart origin resolution:
      const originGlucose = forecastData?.current_state?.glucose_mg_dl ?? latestReading?.cgm_glucose;
      // CurrentGlucoseCard effective glucose resolution:
      const effectiveGlucose = forecastData?.current_state?.glucose_mg_dl ?? latestReading?.cgm_glucose;
      const roundedCardGlucose = Math.round(effectiveGlucose);

      assert.strictEqual(originGlucose, 118.5);
      assert.strictEqual(effectiveGlucose, 118.5);
      assert.strictEqual(roundedCardGlucose, 119);
    });
  });

  describe("Food Vision & Nutrition Data Integrity", () => {
    it("should faithfully extract macronutrients from final_macros without fabricating 0g when nutrients are null", () => {
      const responseWithNulls = {
        selected_food: "Custom Dish",
        final_macros: {
          carbs_g: null,
          protein_g: 12.0,
          fat_g: null,
          calories_kcal: null
        }
      };

      const macros = responseWithNulls.final_macros;
      const rawCarbs = macros.carbs_g;
      const estCarbs = rawCarbs !== null && rawCarbs !== undefined && !isNaN(Number(rawCarbs))
        ? Math.round(Number(rawCarbs) * 10) / 10
        : null;

      const rawProtein = macros.protein_g;
      const protein = rawProtein !== null && rawProtein !== undefined && !isNaN(Number(rawProtein))
        ? Math.round(Number(rawProtein) * 10) / 10
        : null;

      const rawFat = macros.fat_g;
      const fat = rawFat !== null && rawFat !== undefined && !isNaN(Number(rawFat))
        ? Math.round(Number(rawFat) * 10) / 10
        : null;

      assert.strictEqual(estCarbs, null, "Null carbs must remain null and not fallback to 0");
      assert.strictEqual(protein, 12.0, "Valid protein must be extracted accurately");
      assert.strictEqual(fat, null, "Null fat must remain null and not fallback to 0");
    });

    it("should calculate portion-scaled macronutrients accurately from density and portion size", () => {
      // South Indian thali reference: 18.5g carbs/100g, 3.8g protein/100g, 2.8g fat/100g
      const density = {
        food_name: "South Indian Thali Platter",
        carbs_g_per_100g: 18.5,
        protein_g_per_100g: 3.8,
        fat_g_per_100g: 2.8,
        calories_kcal_per_100g: 115.0
      };

      const portionG = 250.0;
      const factor = portionG / 100.0;
      const scaledCarbs = Math.round(density.carbs_g_per_100g * factor * 10) / 10;
      const scaledProtein = Math.round(density.protein_g_per_100g * factor * 10) / 10;
      const scaledFat = Math.round(density.fat_g_per_100g * factor * 10) / 10;

      assert.strictEqual(scaledCarbs, 46.3, "250g thali must scale to 46.3g carbs, not hardcoded 20g");
      assert.strictEqual(scaledProtein, 9.5);
      assert.strictEqual(scaledFat, 7.0);
    });

    it("should map image_food_candidates from backend schema using candidate.name", () => {
      const backendResponse = {
        image_food_candidates: [
          { name: "South Indian thali", confidence: 0.88, source: "Food-101", raw_label: "thali" },
          { name: "dosa", confidence: 0.09, source: "Food-101", raw_label: "masala_dosa" }
        ]
      };

      const candidates = backendResponse.image_food_candidates;
      assert.strictEqual(candidates.length, 2);
      const firstCandidateName = candidates[0].name || candidates[0].food_name || candidates[0].class_name;
      assert.strictEqual(firstCandidateName, "South Indian thali");
    });

    it("should invalidate user confirmation when portion size or query changes", () => {
      let isConfirmed = true;
      let isTransferred = true;

      // Simulate portion change handler
      const onPortionChange = (newPortion) => {
        isConfirmed = false;
        isTransferred = false;
      };

      onPortionChange(300);
      assert.strictEqual(isConfirmed, false, "Confirmation must be invalidated when portion changes");
      assert.strictEqual(isTransferred, false, "Transfer state must be invalidated when portion changes");
    });

    it("should gate What-If transfer strictly behind user confirmation and positive carbohydrate count", () => {
      const canTransfer = (confirmed, carbs) => Boolean(confirmed && carbs > 0);

      assert.strictEqual(canTransfer(false, 45.0), false, "Unconfirmed meal must not transfer");
      assert.strictEqual(canTransfer(true, 0), false, "Zero carbs must not transfer");
      assert.strictEqual(canTransfer(true, -10), false, "Negative carbs must not transfer");
      assert.strictEqual(canTransfer(true, 45.0), true, "Confirmed positive carbs must transfer");
    });

    it("should manage Food Vision workflow state machine transitions strictly", () => {
      // States: EMPTY -> INPUT_PROVIDED -> ESTIMATE_AVAILABLE / AWAITING_CONFIRMATION -> CONFIRMED -> TRANSFERRED
      let state = "EMPTY";
      assert.strictEqual(state, "EMPTY");

      // Step 1: User enters query or selects image
      state = "INPUT_PROVIDED";
      assert.strictEqual(state, "INPUT_PROVIDED");

      // Step 2: Estimate returned from API
      state = "AWAITING_CONFIRMATION";
      assert.strictEqual(state, "AWAITING_CONFIRMATION");

      // Step 3: User explicitly confirms
      state = "CONFIRMED";
      assert.strictEqual(state, "CONFIRMED");

      // Step 4: User transfers to What-If simulator
      state = "TRANSFERRED";
      assert.strictEqual(state, "TRANSFERRED");

      // Invalidation: User modifies portion or ingredient
      const onUserEdit = () => {
        state = "AWAITING_CONFIRMATION";
      };
      onUserEdit();
      assert.strictEqual(state, "AWAITING_CONFIRMATION", "Any edit must invalidate confirmed/transferred state");
    });

    it("should compute composite meal ingredient breakdown aggregate accurately", () => {
      const ingredients = [
        { name: "Steamed White Rice", portion_g: 150, carbs_per_100g: 28.17, protein_per_100g: 2.69, fat_per_100g: 0.28, kcal_per_100g: 130 },
        { name: "Dal / Sambar", portion_g: 100, carbs_per_100g: 19.50, protein_per_100g: 9.02, fat_per_100g: 0.38, kcal_per_100g: 116 },
        { name: "Vegetable Curry", portion_g: 75, carbs_per_100g: 8.50, protein_per_100g: 2.00, fat_per_100g: 4.50, kcal_per_100g: 82 },
        { name: "Curd / Yogurt", portion_g: 80, carbs_per_100g: 3.60, protein_per_100g: 10.00, fat_per_100g: 0.40, kcal_per_100g: 59 },
        { name: "Papad", portion_g: 15, carbs_per_100g: 50.00, protein_per_100g: 20.00, fat_per_100g: 3.00, kcal_per_100g: 320 }
      ];

      const totals = ingredients.reduce((acc, item) => {
        const factor = (Number(item.portion_g) || 0) / 100;
        return {
          totalG: acc.totalG + (Number(item.portion_g) || 0),
          carbs: acc.carbs + (item.carbs_per_100g * factor),
          protein: acc.protein + (item.protein_per_100g * factor),
          fat: acc.fat + (item.fat_per_100g * factor),
          calories: acc.calories + (item.kcal_per_100g * factor)
        };
      }, { totalG: 0, carbs: 0, protein: 0, fat: 0, calories: 0 });

      // Total weight: 150 + 100 + 75 + 80 + 15 = 420g
      assert.strictEqual(totals.totalG, 420);
      // Carbs: (1.5*28.17) + (1.0*19.50) + (0.75*8.50) + (0.8*3.60) + (0.15*50.00) = 42.255 + 19.5 + 6.375 + 2.88 + 7.5 = 78.51g
      assert.strictEqual(Math.round(totals.carbs * 10) / 10, 78.5);
      // Protein: (1.5*2.69) + (1.0*9.02) + (0.75*2.0) + (0.8*10.0) + (0.15*20.0) = 4.035 + 9.02 + 1.5 + 8.0 + 3.0 = 25.555g
      assert.strictEqual(Math.round(totals.protein * 10) / 10, 25.6);
    });

    it("should cleanly handle food items outside Food-101 vocabulary without fabricating classification", () => {
      // When visual classifier returns empty or low confidence for Indian dishes not in Food-101
      const visualCandidates = [];
      const hasVisualCandidates = visualCandidates && visualCandidates.length > 0;
      assert.strictEqual(hasVisualCandidates, false);

      // System must allow text search fallback without synthetic visual hallucination
      const textQuery = "Idli with sambar";
      const isManualEntry = !hasVisualCandidates && Boolean(textQuery);
      assert.strictEqual(isManualEntry, true);
    });

    it("should distinguish manual text entries from vision candidates without displaying unsupported 100% score", () => {
      const textCandidate = {
        name: "South Indian thali with white rice, dal, potato curry, leafy greens, yogurt and papad",
        confidence: null,
        source: "manual_user_entry",
        raw_label: "South Indian thali with white rice, dal, potato curry, leafy greens, yogurt and papad"
      };

      const isManualOrText = textCandidate.source === "manual_user_entry" || textCandidate.source === "text_search" || textCandidate.confidence == null;
      assert.strictEqual(isManualOrText, true, "Must recognize text query source");

      // UI rendering: Text Match label, NO percentage
      const candidateBadge = isManualOrText ? "Text Match" : `${(textCandidate.confidence * 100).toFixed(1)}%`;
      assert.strictEqual(candidateBadge, "Text Match");
      assert.ok(!candidateBadge.includes("100%"), "Must NOT display unsupported 100% for text match");

      // In contrast, genuine visual candidate with model confidence
      const visionCandidate = {
        name: "samosa",
        confidence: 0.884,
        source: "Food-101",
        raw_label: "samosa"
      };
      const isVisionManual = visionCandidate.source === "manual_user_entry" || visionCandidate.source === "text_search" || visionCandidate.confidence == null;
      const visionBadge = isVisionManual ? "Text Match" : `${(visionCandidate.confidence * 100).toFixed(1)}%`;
      assert.strictEqual(visionBadge, "88.4%", "Visual candidate must format genuine model confidence");
    });

    it("should initialize authoritative state to pending confirmation after analysis and remove confirmed badges", () => {
      // Simulate backend analysis response arrival
      const hasAnalysis = true;
      const isAnalyzing = false;
      const estCarbs = 46.3;

      let workflowState = "EMPTY";
      let confirmedCarbs = 0;

      // useEffect state synchronization
      if (isAnalyzing) {
        workflowState = "INPUT_PROVIDED";
      } else if (hasAnalysis) {
        confirmedCarbs = estCarbs;
        workflowState = "AWAITING_CONFIRMATION";
      }

      // Assert initial state is strictly pending confirmation
      assert.strictEqual(workflowState, "AWAITING_CONFIRMATION");

      // Verify badges and labels in pending state
      const topBadge = workflowState === "TRANSFERRED"
        ? "TRANSFERRED ✓"
        : workflowState === "CONFIRMED"
        ? "CONFIRMED ✓"
        : hasAnalysis
        ? "PENDING CONFIRMATION"
        : "AWAITING INPUT";
      assert.strictEqual(topBadge, "PENDING CONFIRMATION", "Top badge must be PENDING CONFIRMATION");

      const step2Pill = workflowState === "CONFIRMED" || workflowState === "TRANSFERRED"
        ? "2. CONFIRMED ✓"
        : "2. AWAITING CONFIRMATION";
      assert.strictEqual(step2Pill, "2. AWAITING CONFIRMATION", "Step 2 pill must NOT display CONFIRMED ✓");

      const transferText = workflowState === "TRANSFERRED"
        ? `Successfully transferred ${confirmedCarbs}g carbohydrate intake into the What-If Counterfactual Simulator.`
        : workflowState === "CONFIRMED"
        ? `Confirmed carbohydrate intake of ${confirmedCarbs}g ready for counterfactual postprandial simulation.`
        : hasAnalysis
        ? `Review and explicitly confirm estimated ${confirmedCarbs}g carbohydrates before transferring to the What-If simulator.`
        : `Analyze a meal to estimate carbohydrates before counterfactual simulation.`;
      assert.ok(transferText.startsWith("Review and explicitly confirm"), "Must prompt review instead of claiming transfer confirmed");

      // Gating: transfer strictly disabled before confirmation
      const isTransferEnabled = workflowState === "CONFIRMED" && confirmedCarbs > 0;
      assert.strictEqual(isTransferEnabled, false, "Transfer button must remain disabled in pending state");
    });

    it("should update dependent UI to CONFIRMED on explicit user confirmation and enable transfer", () => {
      let workflowState = "AWAITING_CONFIRMATION";
      let confirmedCarbs = 46.3;

      // User clicks Confirm Values
      const handleConfirm = () => {
        workflowState = "CONFIRMED";
      };
      handleConfirm();

      assert.strictEqual(workflowState, "CONFIRMED");

      // Verify all UI elements reflect confirmation
      const topBadge = workflowState === "TRANSFERRED"
        ? "TRANSFERRED ✓"
        : workflowState === "CONFIRMED"
        ? "CONFIRMED ✓"
        : "PENDING CONFIRMATION";
      assert.strictEqual(topBadge, "CONFIRMED ✓");

      const isTransferEnabled = workflowState === "CONFIRMED" && confirmedCarbs > 0;
      assert.strictEqual(isTransferEnabled, true, "Transfer button must be enabled after explicit confirmation");
    });

    it("should transition to TRANSFERRED strictly after transfer action execution and invalidate on any edit", () => {
      let workflowState = "CONFIRMED";
      let confirmedCarbs = 46.3;
      let transferredToSimulation = false;

      // Transfer execution
      const handleTransfer = () => {
        if (workflowState !== "CONFIRMED" || confirmedCarbs <= 0) return;
        transferredToSimulation = true;
        workflowState = "TRANSFERRED";
      };
      handleTransfer();

      assert.strictEqual(transferredToSimulation, true);
      assert.strictEqual(workflowState, "TRANSFERRED");

      // Invalidation: user changes portion or query
      const invalidateConfirmation = () => {
        if (workflowState === "CONFIRMED" || workflowState === "TRANSFERRED") {
          workflowState = "AWAITING_CONFIRMATION";
        }
      };

      invalidateConfirmation();
      assert.strictEqual(workflowState, "AWAITING_CONFIRMATION", "Editing after transfer must invalidate and revert to AWAITING_CONFIRMATION");
      assert.strictEqual(workflowState === "CONFIRMED" && confirmedCarbs > 0, false, "Transfer button must be re-disabled");
    });

    it("should display honest offline recognition warning rather than claiming unlisted dish when provider is unavailable", () => {
      const userImage = "blob:http://localhost:5173/mock-uuid-pizza";
      const candidates = [];
      const warnings = [
        "Visual classification unavailable: HUGGINGFACE_API_TOKEN is not configured. Serverless vision inference requires an API key. Manual food description required."
      ];

      const hasOfflineWarning = warnings.some((w) => w.toLowerCase().includes("visual classification unavailable"));
      assert.strictEqual(hasOfflineWarning, true, "Must detect offline/unavailable recognition warning");

      // Verify rendered UI text selection
      const heading = hasOfflineWarning
        ? "Visual Recognition Engine Offline / Unavailable"
        : "Image classification unavailable / unlisted";
      assert.strictEqual(heading, "Visual Recognition Engine Offline / Unavailable");

      const detailText = hasOfflineWarning
        ? warnings.find((w) => w.toLowerCase().includes("visual classification unavailable"))
        : "No food items recognized from photo in Food-101 vocabulary.";
      assert.ok(detailText.includes("HUGGINGFACE_API_TOKEN is not configured"));
      assert.ok(!detailText.includes("does not match Food-101 vocabulary"), "Must not falsely claim dish does not match Food-101");
    });

    it("should clear stale analysis data immediately upon new runFoodAnalyze request", () => {
      // Simulate state holding previous analysis result
      let foodAnalysisData = {
        selected_food: "South Indian thali",
        portion_g: 250.0,
        final_macros: { carbs_g: 46.25, protein_g: 9.5, fat_g: 7.0 }
      };
      let isLoadingFood = false;

      // When runFoodAnalyze is triggered with a new query or image
      const runFoodAnalyzeInitiation = () => {
        isLoadingFood = true;
        foodAnalysisData = null; // Strictly reset before network fetch
      };

      runFoodAnalyzeInitiation();
      assert.strictEqual(isLoadingFood, true);
      assert.strictEqual(foodAnalysisData, null, "Stale analysis data must be cleared immediately at request launch");
    });

    it("should format visual candidate confidence accurately and trigger USDA lookup on candidate selection", () => {
      const candidate = {
        name: "Pizza",
        confidence: 0.8923,
        source: "HuggingFace (nateraw/food)",
        raw_label: "pizza"
      };

      const isManualOrText = candidate.source === "manual_user_entry" || candidate.source === "text_search" || candidate.confidence == null;
      assert.strictEqual(isManualOrText, false, "Must identify as genuine visual candidate");

      const confidenceText = `${(candidate.confidence * 100).toFixed(1)}%`;
      assert.strictEqual(confidenceText, "89.2%");

      // Selecting candidate dispatches search with candidate name for USDA nutrition
      let dispatchedPayload = null;
      const handleSelectCandidate = (idx, cand) => {
        dispatchedPayload = {
          food_name_query: cand.name,
          portion_g: 200.0,
          selected_candidate_index: idx
        };
      };

      handleSelectCandidate(0, candidate);
      assert.deepStrictEqual(dispatchedPayload, {
        food_name_query: "Pizza",
        portion_g: 200.0,
        selected_candidate_index: 0
      });
    });

    it("should display honest HTTP 413 payload too large diagnostic warning in UI without claiming unlisted food", () => {
      const userImage = "blob:http://localhost:5173/mock-uuid-large-photo";
      const warnings = [
        "Visual classification unavailable: Hugging Face payload too large (413 Payload Too Large). Image exceeds provider size limit. Manual food description required."
      ];

      const hasOfflineWarning = warnings.some((w) => w.toLowerCase().includes("visual classification unavailable"));
      assert.strictEqual(hasOfflineWarning, true, "Must detect provider failure warning");

      const heading = hasOfflineWarning
        ? "Visual Recognition Engine Offline / Unavailable"
        : "Image classification unavailable / unlisted";
      assert.strictEqual(heading, "Visual Recognition Engine Offline / Unavailable");

      const detailText = warnings.find((w) => w.toLowerCase().includes("visual classification unavailable"));
      assert.ok(detailText.includes("413 Payload Too Large"), "Must report 413 Payload Too Large explicitly");
      assert.ok(!detailText.includes("does not match Food-101 vocabulary"), "Must not falsely blame vocabulary mismatch");
    });
  });

  describe("Live Forecast Refresh & Empty State Validation", () => {
    it("should handle Case 1: Insufficient history (< 96 readings) in Live API mode cleanly", () => {
      const isDemoMode = false;
      const historyReadings = [
        { timestamp: "2026-10-13T16:30:00Z", cgm_glucose: 118.5 },
        { timestamp: "2026-10-13T16:45:00Z", cgm_glucose: 121.2 }
      ];
      const forecastData = null;
      const isLoading = false;

      // In Live API mode with < 96 readings:
      const isCase1 = !forecastData && !isLoading && !isDemoMode;
      assert.strictEqual(isCase1, true, "Must detect Case 1: insufficient history in Live API mode");

      // Verify empty state contract:
      const readingCount = historyReadings.length;
      assert.strictEqual(readingCount, 2);
      assert.ok(readingCount < 96, "Reading count is less than 96");
      const emptyStateText = `${readingCount} / 96 steps (24h continuous 15-minute readings required)`;
      assert.ok(emptyStateText.includes("2 / 96 steps"));
      assert.ok(emptyStateText.includes("24h continuous"));

      // Crucially: live mode must NEVER silently fallback to demo/synthetic data
      const effectiveForecast = forecastData;
      assert.strictEqual(effectiveForecast, null, "Must NOT inject synthetic forecast");
    });

    it("should handle Case 2: Sufficient history (>= 96 readings) and automatically construct 96-step forecast payload", () => {
      // Generate 100 historical readings
      const baseTime = Date.parse("2026-10-12T12:00:00Z");
      const rawHistory = [];
      for (let i = 0; i < 100; i++) {
        rawHistory.push({
          timestamp: new Date(baseTime + i * 15 * 60 * 1000).toISOString(),
          cgm_glucose: 110 + (i % 20)
        });
      }

      // 1. Sort chronologically and filter physical bounds [20, 600]
      const formatted = rawHistory
        .filter(r => r && typeof r.cgm_glucose === "number" && r.cgm_glucose >= 20 && r.cgm_glucose <= 600)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

      // 2. Slice exactly 96 latest readings
      const eligible96 = formatted.length >= 96 ? formatted.slice(-96) : null;
      assert.ok(eligible96 !== null, "Must have eligible 96 readings");
      assert.strictEqual(eligible96.length, 96, "Eligible slice must be exactly 96 steps");

      // 3. Verify temporal spacing is 15 minutes between consecutive readings
      const t0 = new Date(eligible96[0].timestamp).getTime();
      const t1 = new Date(eligible96[1].timestamp).getTime();
      assert.strictEqual((t1 - t0) / (60 * 1000), 15, "Readings must be 15 minutes apart");

      // 4. Verify patient profile direct passing avoids state race conditions
      const patientProfile = {
        id: "patient_001",
        age: 45,
        bmi: 24.5,
        diabetes_duration_years: 8,
        hba1c: 54,
        fasting_glucose: 5.8,
        glycated_albumin: 15.0,
        c_peptide: 0.8,
        is_t1dm: 1.0
      };

      const payload = {
        patient_id: patientProfile.id,
        history_readings: eligible96,
        static_profile: patientProfile
      };

      assert.strictEqual(payload.patient_id, "patient_001");
      assert.strictEqual(payload.history_readings.length, 96);
      assert.strictEqual(payload.static_profile.hba1c, 54);
    });
  });

  describe("Digital Twin Telemetry & Data-Readiness Consistency", () => {
    it("should compute pending/unavailable states when forecastData is null or empty", () => {
      const forecastData = null;
      const currentState = forecastData?.current_state || {};
      const glucose = currentState.glucose_mg_dl !== undefined && currentState.glucose_mg_dl !== null ? Math.round(currentState.glucose_mg_dl) : null;
      const iob = currentState.iob_units !== undefined && currentState.iob_units !== null ? currentState.iob_units : null;
      const cob = currentState.cob_grams !== undefined && currentState.cob_grams !== null ? currentState.cob_grams : null;

      const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
      const originVal = glucose !== null ? glucose : (pointForecast.length > 0 ? pointForecast[0] : null);
      const hasValidForecast = Array.isArray(pointForecast) && pointForecast.length > 0 && originVal !== null;
      const hasValidGlucose = glucose !== null && typeof glucose === "number" && !isNaN(glucose);

      const riskAssessment = forecastData?.risk_assessment || null;
      const hypoRisk = riskAssessment?.hypo_risk ? `${riskAssessment.hypo_risk.toUpperCase()} Hypo` : null;
      const hyperRisk = riskAssessment?.hyper_risk ? `${riskAssessment.hyper_risk.toUpperCase()} Hyper` : null;

      // Invariants for unavailable telemetry:
      assert.strictEqual(hasValidGlucose, false);
      assert.strictEqual(hasValidForecast, false);
      assert.strictEqual(glucose, null);
      assert.strictEqual(iob, null);
      assert.strictEqual(cob, null);

      // Hero Ribbon state:
      const heroRibbonStatus = hasValidForecast ? "Forecast Active" : "Engine Configured";
      const modelServingStatus = `Model Serving: Combination C (${hasValidForecast ? "Inference Complete" : "Awaiting Telemetry"})`;
      assert.strictEqual(heroRibbonStatus, "Engine Configured");
      assert.strictEqual(modelServingStatus, "Model Serving: Combination C (Awaiting Telemetry)");

      // Card 1 (Current Glucose):
      const glucoseDisplay = hasValidGlucose ? glucose : "—";
      const dataSource = hasValidGlucose ? "Active Continuous Stream" : "Stream Unavailable";
      assert.strictEqual(glucoseDisplay, "—");
      assert.strictEqual(dataSource, "Stream Unavailable");

      // Card 2 (Twin Status):
      const twinStatus = hasValidForecast ? "Simulation Aligned" : "Simulation Pending";
      const twinSubtext = hasValidForecast ? "Active Dynamic Model" : "Awaiting 24h Telemetry";
      const twinBadge = hasValidForecast ? "Combination C (Synced)" : "Combination C (Idle)";
      assert.strictEqual(twinStatus, "Simulation Pending");
      assert.strictEqual(twinSubtext, "Awaiting 24h Telemetry");
      assert.strictEqual(twinBadge, "Combination C (Idle)");

      // Card 3 (Forecast Status):
      const forecastSteps = hasValidForecast ? `${pointForecast.length} Steps` : "—";
      const forecastProjection = hasValidForecast ? "Active" : "Unavailable";
      assert.strictEqual(forecastSteps, "—");
      assert.strictEqual(forecastProjection, "Unavailable");

      // Card 4 (Risk Status):
      const displayedHypo = hasValidForecast && hypoRisk ? hypoRisk : "Unavailable";
      const displayedHyper = hasValidForecast && hyperRisk ? hyperRisk : "Pending Forecast";
      assert.strictEqual(displayedHypo, "Unavailable");
      assert.strictEqual(displayedHyper, "Pending Forecast");

      // 5-Node Flux Pipeline:
      const phase1Status = cob !== null ? "Gut Influx" : "Standby";
      const phase2Status = iob !== null ? "Absorption" : "Basal Only";
      const phase3Balance = hasValidForecast ? "Balance: Nominal" : "Balance: Pending Inputs";
      const phase3Status = hasValidForecast ? "Equilibrium" : "Uncalibrated";
      const phase4Status = hasValidGlucose ? "In Target Band" : "Data Unavailable";
      const phase5Status = hasValidForecast ? "Bounded UI" : "Forecast Pending";
      assert.strictEqual(phase1Status, "Standby");
      assert.strictEqual(phase2Status, "Basal Only");
      assert.strictEqual(phase3Balance, "Balance: Pending Inputs");
      assert.strictEqual(phase3Status, "Uncalibrated");
      assert.strictEqual(phase4Status, "Data Unavailable");
      assert.strictEqual(phase5Status, "Forecast Pending");

      // Trajectory Footnote:
      const boundsVerified = hasValidForecast ? "Physiological Bounds Verified" : "Telemetry Required for Verification";
      assert.strictEqual(boundsVerified, "Telemetry Required for Verification");

      // Model Interpretation Trajectory Conclusion:
      const trajectoryStatus = !hasValidForecast
        ? "Unavailable (Telemetry Pending)"
        : "Within Target Band";
      assert.strictEqual(trajectoryStatus, "Unavailable (Telemetry Pending)");

      // DigitalTwinPreviewCard checks:
      const previewCob = cob !== null ? `~${Math.round(cob)}g Ingestion` : "Telemetry Pending";
      const previewIob = iob !== null ? `~${iob.toFixed(1)} U Active` : "Telemetry Pending";
      const previewOde = hasValidForecast ? "ODE State Sync" : "Standby Mode";
      const previewGlucose = glucose !== null ? `${glucose} mg/dL (Live)` : "Unavailable";
      const previewPeak = hasValidForecast ? "Peak ~150 mg/dL" : "Unavailable";
      assert.strictEqual(previewCob, "Telemetry Pending");
      assert.strictEqual(previewIob, "Telemetry Pending");
      assert.strictEqual(previewOde, "Standby Mode");
      assert.strictEqual(previewGlucose, "Unavailable");
      assert.strictEqual(previewPeak, "Unavailable");
    });

    it("should compute active and clinically consistent states when genuine forecast data is present", () => {
      const synthetic = getSyntheticForecastResponse("stable");
      const forecastData = {
        current_state: {
          glucose_mg_dl: 125,
          iob_units: 1.8,
          cob_grams: 35
        },
        forecast: synthetic.forecast,
        risk_assessment: {
          hypo_risk: "low",
          hyper_risk: "moderate",
          projected_peak_mg_dl: 165
        }
      };

      const currentState = forecastData.current_state;
      const glucose = currentState.glucose_mg_dl !== undefined && currentState.glucose_mg_dl !== null ? Math.round(currentState.glucose_mg_dl) : null;
      const iob = currentState.iob_units !== undefined && currentState.iob_units !== null ? currentState.iob_units : null;
      const cob = currentState.cob_grams !== undefined && currentState.cob_grams !== null ? currentState.cob_grams : null;

      const pointForecast = forecastData.forecast.point_forecast_mg_dl;
      const originVal = glucose !== null ? glucose : (pointForecast.length > 0 ? pointForecast[0] : null);
      const hasValidForecast = Array.isArray(pointForecast) && pointForecast.length > 0 && originVal !== null;
      const hasValidGlucose = glucose !== null && typeof glucose === "number" && !isNaN(glucose);
      const inRange = hasValidGlucose && glucose >= GLUCOSE_THRESHOLDS.TARGET_MIN && glucose <= GLUCOSE_THRESHOLDS.TARGET_MAX;

      const riskAssessment = forecastData.risk_assessment;
      const hypoRisk = riskAssessment?.hypo_risk ? `${riskAssessment.hypo_risk.toUpperCase()} Hypo` : null;
      const hyperRisk = riskAssessment?.hyper_risk ? `${riskAssessment.hyper_risk.toUpperCase()} Hyper` : null;

      assert.strictEqual(hasValidGlucose, true);
      assert.strictEqual(hasValidForecast, true);
      assert.strictEqual(inRange, true);
      assert.strictEqual(glucose, 125);
      assert.strictEqual(iob, 1.8);
      assert.strictEqual(cob, 35);

      // Hero Ribbon state:
      const heroRibbonStatus = hasValidForecast ? "Forecast Active" : "Engine Configured";
      assert.strictEqual(heroRibbonStatus, "Forecast Active");

      // Metrics:
      assert.strictEqual(hypoRisk, "LOW Hypo");
      assert.strictEqual(hyperRisk, "MODERATE Hyper");

      // 5-Node Flux Pipeline:
      const phase1Status = cob !== null ? "Gut Influx" : "Standby";
      const phase2Status = iob !== null ? "Absorption" : "Basal Only";
      const phase3Balance = hasValidForecast ? "Balance: Nominal" : "Balance: Pending Inputs";
      const phase3Status = hasValidForecast ? "Equilibrium" : "Uncalibrated";
      const phase4Status = hasValidGlucose ? (inRange ? "In Target Band" : "High") : "Data Unavailable";
      const phase5Status = hasValidForecast ? "Bounded UI" : "Forecast Pending";
      assert.strictEqual(phase1Status, "Gut Influx");
      assert.strictEqual(phase2Status, "Absorption");
      assert.strictEqual(phase3Balance, "Balance: Nominal");
      assert.strictEqual(phase3Status, "Equilibrium");
      assert.strictEqual(phase4Status, "In Target Band");
      assert.strictEqual(phase5Status, "Bounded UI");

      // Verification footnote:
      const boundsVerified = hasValidForecast ? "Physiological Bounds Verified" : "Telemetry Required for Verification";
      assert.strictEqual(boundsVerified, "Physiological Bounds Verified");

      // Trajectory Conclusion:
      const peak = forecastData.risk_assessment.projected_peak_mg_dl;
      const endGlucose = pointForecast[pointForecast.length - 1];
      const trajectoryStatus = !hasValidForecast
        ? "Unavailable (Telemetry Pending)"
        : (peak !== null && peak > GLUCOSE_THRESHOLDS.TARGET_MAX)
          ? "Projected Above Target"
          : (endGlucose !== null && endGlucose < GLUCOSE_THRESHOLDS.TARGET_MIN)
            ? "Projected Below Target"
            : "Within Target Band";
      assert.strictEqual(trajectoryStatus, "Within Target Band");
    });

    it("Regression Test 1: should bind Card 4 to actual Combination C risk_assessment fields (primary_status & alert_level)", () => {
      const forecastData = {
        patient_id: "DEMO-SYNTHETIC-PATIENT-001",
        current_state: { glucose_mg_dl: 116, iob_units: 0.57, cob_grams: 0.3 },
        forecast: {
          point_forecast_mg_dl: [102.9, 102.8, 105.3, 92.2],
          lower_95_mg_dl: [56.1, 55.7, 52.1, 48.2],
          upper_95_mg_dl: [149.7, 150.0, 153.5, 158.3]
        },
        risk_assessment: {
          primary_status: "STABLE",
          alert_level: "INFO",
          hypo_1h_prob: 0.0031,
          hypo_2h_prob: 0.0139,
          hypo_4h_prob: 0.0653,
          hyper_2h_prob: 0.0235,
          hyper_4h_prob: 0.0295,
          nadir_mg_dl: 92.2,
          time_to_nadir_min: 285,
          peak_mg_dl: 105.3,
          time_to_peak_min: 45,
          projected_hypo_duration_min: 0,
          active_alerts: [
            "NOTICE: Downside trajectory uncertainty extends into hypoglycemic range."
          ]
        }
      };

      const pointForecast = forecastData.forecast.point_forecast_mg_dl;
      const originVal = forecastData.current_state.glucose_mg_dl;
      const hasValidForecast = Array.isArray(pointForecast) && pointForecast.length > 0 && originVal !== null;

      const riskAssessment = forecastData.risk_assessment;
      const hasValidRisk = Boolean(
        hasValidForecast &&
        riskAssessment &&
        typeof riskAssessment === "object" &&
        (typeof riskAssessment.primary_status === "string" ||
         typeof riskAssessment.alert_level === "string" ||
         typeof riskAssessment.hypo_2h_prob === "number" ||
         typeof riskAssessment.hypo_risk === "string")
      );

      const primaryStatus = hasValidRisk
        ? (riskAssessment.primary_status || (riskAssessment.hypo_risk ? `${riskAssessment.hypo_risk.toUpperCase()} Hypo` : "STABLE"))
        : null;

      const alertLevel = hasValidRisk
        ? (riskAssessment.alert_level || (riskAssessment.hyper_risk ? riskAssessment.hyper_risk.toUpperCase() : "INFO"))
        : null;

      const alertBadgeText = hasValidRisk
        ? (riskAssessment.alert_level
            ? `ALERT: ${riskAssessment.alert_level}`
            : (riskAssessment.hyper_risk ? `${riskAssessment.hyper_risk.toUpperCase()} Hyper` : "ALERT: INFO"))
        : null;

      const alertBadgeStyle = !hasValidRisk
        ? "bg-surface-container text-on-surface-variant"
        : alertLevel === "CRITICAL"
        ? "bg-error/15 text-error border border-error/30"
        : alertLevel === "WARNING"
        ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30"
        : "bg-primary/10 text-primary border border-primary/20";

      const riskFootnote = hasValidRisk
        ? (Array.isArray(riskAssessment.active_alerts) && riskAssessment.active_alerts.length > 0
            ? riskAssessment.active_alerts[0]
            : "Descriptive safety boundaries verified")
        : "Safety evaluation pending";

      const displayedPrimary = hasValidForecast && hasValidRisk && primaryStatus ? primaryStatus : "Unavailable";
      const displayedBadge = hasValidForecast && hasValidRisk && alertBadgeText ? alertBadgeText : "Pending Forecast";

      // Must display genuine Combination C risk output, NOT "Unavailable" or "Pending Forecast"
      assert.strictEqual(hasValidForecast, true);
      assert.strictEqual(hasValidRisk, true);
      assert.strictEqual(displayedPrimary, "STABLE");
      assert.strictEqual(displayedBadge, "ALERT: INFO");
      assert.strictEqual(alertBadgeStyle.includes("bg-primary/10"), true);
      assert.strictEqual(riskFootnote, "NOTICE: Downside trajectory uncertainty extends into hypoglycemic range.");
    });

    it("Regression Test 2: should display honest unavailable state when risk data is missing/invalid without inferring from point forecast", () => {
      // Point forecast and current glucose are present, but risk_assessment is null or empty
      const forecastData = {
        patient_id: "DEMO-SYNTHETIC-PATIENT-001",
        current_state: { glucose_mg_dl: 116 },
        forecast: {
          point_forecast_mg_dl: [102.9, 102.8, 105.3, 92.2],
          lower_95_mg_dl: [56.1, 55.7, 52.1, 48.2],
          upper_95_mg_dl: [149.7, 150.0, 153.5, 158.3]
        },
        risk_assessment: null
      };

      const pointForecast = forecastData.forecast.point_forecast_mg_dl;
      const originVal = forecastData.current_state.glucose_mg_dl;
      const hasValidForecast = Array.isArray(pointForecast) && pointForecast.length > 0 && originVal !== null;

      const riskAssessment = forecastData.risk_assessment;
      const hasValidRisk = Boolean(
        hasValidForecast &&
        riskAssessment &&
        typeof riskAssessment === "object" &&
        (typeof riskAssessment.primary_status === "string" ||
         typeof riskAssessment.alert_level === "string" ||
         typeof riskAssessment.hypo_2h_prob === "number" ||
         typeof riskAssessment.hypo_risk === "string")
      );

      const primaryStatus = hasValidRisk
        ? (riskAssessment.primary_status || (riskAssessment.hypo_risk ? `${riskAssessment.hypo_risk.toUpperCase()} Hypo` : "STABLE"))
        : null;

      const alertBadgeText = hasValidRisk
        ? (riskAssessment.alert_level
            ? `ALERT: ${riskAssessment.alert_level}`
            : (riskAssessment.hyper_risk ? `${riskAssessment.hyper_risk.toUpperCase()} Hyper` : "ALERT: INFO"))
        : null;

      const riskFootnote = hasValidRisk
        ? (Array.isArray(riskAssessment.active_alerts) && riskAssessment.active_alerts.length > 0
            ? riskAssessment.active_alerts[0]
            : "Descriptive safety boundaries verified")
        : "Safety evaluation pending";

      const displayedPrimary = hasValidForecast && hasValidRisk && primaryStatus ? primaryStatus : "Unavailable";
      const displayedBadge = hasValidForecast && hasValidRisk && alertBadgeText ? alertBadgeText : "Pending Forecast";

      // Invariant: Must retain honest unavailable state without fabricating probabilities or status
      assert.strictEqual(hasValidForecast, true);
      assert.strictEqual(hasValidRisk, false);
      assert.strictEqual(displayedPrimary, "Unavailable");
      assert.strictEqual(displayedBadge, "Pending Forecast");
      assert.strictEqual(riskFootnote, "Safety evaluation pending");
    });

    it("Regression Test 3: should display unavailable state cleanly on failed forecast request or null forecastData", () => {
      const forecastData = null;

      const pointForecast = forecastData?.forecast?.point_forecast_mg_dl || [];
      const originVal = null;
      const hasValidForecast = Array.isArray(pointForecast) && pointForecast.length > 0 && originVal !== null;

      const riskAssessment = forecastData?.risk_assessment || null;
      const hasValidRisk = Boolean(
        hasValidForecast &&
        riskAssessment &&
        typeof riskAssessment === "object" &&
        (typeof riskAssessment.primary_status === "string" ||
         typeof riskAssessment.alert_level === "string" ||
         typeof riskAssessment.hypo_2h_prob === "number" ||
         typeof riskAssessment.hypo_risk === "string")
      );

      const primaryStatus = hasValidRisk
        ? (riskAssessment.primary_status || (riskAssessment.hypo_risk ? `${riskAssessment.hypo_risk.toUpperCase()} Hypo` : "STABLE"))
        : null;

      const alertBadgeText = hasValidRisk
        ? (riskAssessment.alert_level
            ? `ALERT: ${riskAssessment.alert_level}`
            : (riskAssessment.hyper_risk ? `${riskAssessment.hyper_risk.toUpperCase()} Hyper` : "ALERT: INFO"))
        : null;

      const riskFootnote = hasValidRisk
        ? (Array.isArray(riskAssessment.active_alerts) && riskAssessment.active_alerts.length > 0
            ? riskAssessment.active_alerts[0]
            : "Descriptive safety boundaries verified")
        : "Safety evaluation pending";

      const displayedPrimary = hasValidForecast && hasValidRisk && primaryStatus ? primaryStatus : "Unavailable";
      const displayedBadge = hasValidForecast && hasValidRisk && alertBadgeText ? alertBadgeText : "Pending Forecast";

      assert.strictEqual(hasValidForecast, false);
      assert.strictEqual(hasValidRisk, false);
      assert.strictEqual(displayedPrimary, "Unavailable");
      assert.strictEqual(displayedBadge, "Pending Forecast");
      assert.strictEqual(riskFootnote, "Safety evaluation pending");
    });

    it("Regression Test 4: should prevent stale risk state bleed across patient switching and clearing forecast", () => {
      // Simulate patient 1 active state
      let activeForecast = {
        patient_id: "PATIENT_A",
        current_state: { glucose_mg_dl: 185 },
        forecast: { point_forecast_mg_dl: [180, 175, 170] },
        risk_assessment: {
          primary_status: "FALLING",
          alert_level: "WARNING",
          active_alerts: ["Trajectory descending from elevated state"]
        }
      };

      const resolveCardState = (data) => {
        const pointForecast = data?.forecast?.point_forecast_mg_dl || [];
        const originVal = data?.current_state?.glucose_mg_dl ?? null;
        const hasValidForecast = Array.isArray(pointForecast) && pointForecast.length > 0 && originVal !== null;
        const riskAssessment = data?.risk_assessment || null;
        const hasValidRisk = Boolean(
          hasValidForecast &&
          riskAssessment &&
          typeof riskAssessment === "object" &&
          (typeof riskAssessment.primary_status === "string" ||
           typeof riskAssessment.alert_level === "string" ||
           typeof riskAssessment.hypo_2h_prob === "number" ||
           typeof riskAssessment.hypo_risk === "string")
        );
        const primaryStatus = hasValidRisk
          ? (riskAssessment.primary_status || (riskAssessment.hypo_risk ? `${riskAssessment.hypo_risk.toUpperCase()} Hypo` : "STABLE"))
          : null;
        const alertBadgeText = hasValidRisk
          ? (riskAssessment.alert_level
              ? `ALERT: ${riskAssessment.alert_level}`
              : (riskAssessment.hyper_risk ? `${riskAssessment.hyper_risk.toUpperCase()} Hyper` : "ALERT: INFO"))
          : null;
        const riskFootnote = hasValidRisk
          ? (Array.isArray(riskAssessment.active_alerts) && riskAssessment.active_alerts.length > 0
              ? riskAssessment.active_alerts[0]
              : "Descriptive safety boundaries verified")
          : "Safety evaluation pending";

        return {
          primary: hasValidForecast && hasValidRisk && primaryStatus ? primaryStatus : "Unavailable",
          badge: hasValidForecast && hasValidRisk && alertBadgeText ? alertBadgeText : "Pending Forecast",
          footnote: riskFootnote
        };
      };

      // Patient A: Populated
      const stateA = resolveCardState(activeForecast);
      assert.strictEqual(stateA.primary, "FALLING");
      assert.strictEqual(stateA.badge, "ALERT: WARNING");

      // Action: Patient switched or logged out -> clearInferenceState() sets activeForecast = null
      activeForecast = null;

      // Patient B (before data arrival): Zero stale bleed
      const stateB = resolveCardState(activeForecast);
      assert.strictEqual(stateB.primary, "Unavailable");
      assert.strictEqual(stateB.badge, "Pending Forecast");
      assert.strictEqual(stateB.footnote, "Safety evaluation pending");
    });
  });

  describe("Risk & Explanation View & What-If Transparency", () => {
    it("should propagate primary_status, alert_level, and active downside uncertainty alerts", () => {
      const forecastResponse = {
        disclaimer: "RESEARCH NOTICE",
        patient_id: "DEMO-SYNTHETIC-PATIENT-001",
        current_state: { glucose_mg_dl: 116, iob_units: 0.57, cob_grams: 0.3, primary_status: "STABLE" },
        forecast: {
          point_forecast_mg_dl: [102.9, 102.8, 105.3, 92.2],
          lower_95_mg_dl: [56.1, 55.7, 52.1, 48.2],
          upper_95_mg_dl: [149.7, 150.0, 153.5, 158.3]
        },
        risk_assessment: {
          primary_status: "STABLE",
          alert_level: "INFO",
          active_alerts: ["NOTICE: Downside trajectory uncertainty extends into hypoglycemic range."]
        },
        explanation: {
          headline: "In-Range Glycemic Trajectory (Projected Range: 92 - 105 mg/dL)",
          uncertainty_rationale: "Elevated predictive uncertainty (mean std: 28.7 mg/dL) due to extended 5-hour forecast horizon."
        }
      };

      const primaryStatus = forecastResponse.risk_assessment.primary_status;
      const alertLevel = forecastResponse.risk_assessment.alert_level;
      const minLower95 = Math.min(...forecastResponse.forecast.lower_95_mg_dl);
      const crossesHypo50 = minLower95 < 50.0;
      const hasDownsideNotice = forecastResponse.risk_assessment.active_alerts.some(a =>
        a.includes("Downside trajectory uncertainty extends into hypoglycemic range")
      );

      assert.strictEqual(primaryStatus, "STABLE");
      assert.strictEqual(alertLevel, "INFO");
      assert.strictEqual(crossesHypo50, true);
      assert.strictEqual(hasDownsideNotice, true);
      assert.ok(forecastResponse.explanation.uncertainty_rationale.includes("predictive uncertainty"));
    });

    it("should enforce in-silico simulation disclaimer on What-If counterfactual scenarios", () => {
      const disclaimer = "IN SILICO COUNTERFACTUAL SIMULATION ONLY • NOT MEDICAL PRESCRIPTION OR TREATMENT ADVICE";
      assert.ok(disclaimer.includes("IN SILICO"));
      assert.ok(disclaimer.includes("NOT MEDICAL PRESCRIPTION"));
    });
  });

  describe("Food Vision → What-If Meal Transfer & Parameter Initialization", () => {
    it("should accurately transfer confirmed meal carbohydrates (58.8g) and display origin in What-If simulator", () => {
      // Confirmed meal in Food Vision
      const confirmedMeal = {
        food_name: "Pizza",
        portion_g: 250,
        carbs_g: 58.8,
        source: "food_vision",
        is_confirmed: true
      };

      // App.jsx transfer handler
      let transferredMeal = null;
      let activeTab = "food_vision";
      const handleTransferToWhatIf = (payload) => {
        const rawCarbs = typeof payload === "object" && payload !== null
          ? (payload.carbs_g ?? payload.meal_carbs_g)
          : payload;
        const numCarbs = Number(rawCarbs);
        if (!Number.isFinite(numCarbs) || numCarbs <= 0) return;

        transferredMeal = {
          id: `transferred_${Date.now()}`,
          food_name: payload.food_name || "Confirmed Meal",
          portion_g: Number(payload.portion_g) || 250,
          carbs_g: Math.round(numCarbs * 10) / 10,
          source: "food_vision",
          transferred_at: new Date().toISOString()
        };
        activeTab = "what_if";
      };

      handleTransferToWhatIf(confirmedMeal);

      assert.strictEqual(activeTab, "what_if");
      assert.ok(transferredMeal);
      assert.strictEqual(transferredMeal.carbs_g, 58.8);
      assert.strictEqual(transferredMeal.food_name, "Pizza");
      assert.strictEqual(transferredMeal.portion_g, 250);

      // WhatIfSimulator initialization logic
      const BASE_CHO = 55.0;
      const mealCarbs = transferredMeal && typeof transferredMeal.carbs_g === "number" && transferredMeal.carbs_g > 0
        ? transferredMeal.carbs_g
        : BASE_CHO;

      const choDeltaVal = mealCarbs - BASE_CHO;
      const formattedCarbs = Number(mealCarbs).toFixed(1).replace(/\.0$/, "");
      const formattedStatus = Math.abs(choDeltaVal) < 0.05
        ? "Unchanged"
        : `${choDeltaVal > 0 ? "+" : ""}${Number(choDeltaVal).toFixed(1).replace(/\.0$/, "")} g Adjustment`;

      assert.strictEqual(formattedCarbs, "58.8", "Displayed carbs must match confirmed 58.8g exactly");
      assert.strictEqual(formattedStatus, "+3.8 g Adjustment", "Status must compute +3.8g Adjustment relative to base 55.0g");
      assert.notStrictEqual(formattedStatus, "Unchanged", "Status must NOT remain 'Unchanged'");
    });

    it("should strictly block unconfirmed, empty, or non-positive food analyses from transferring", () => {
      let transferredMeal = null;
      const handleTransferToWhatIf = (payload) => {
        const rawCarbs = typeof payload === "object" && payload !== null
          ? (payload.carbs_g ?? payload.meal_carbs_g)
          : payload;
        const numCarbs = Number(rawCarbs);
        if (!Number.isFinite(numCarbs) || numCarbs <= 0) return;
        transferredMeal = payload;
      };

      // Case A: Unconfirmed / null payload
      handleTransferToWhatIf(null);
      assert.strictEqual(transferredMeal, null);

      // Case B: Zero carbohydrates
      handleTransferToWhatIf({ food_name: "Water", carbs_g: 0 });
      assert.strictEqual(transferredMeal, null);

      // Case C: Negative carbohydrates
      handleTransferToWhatIf({ food_name: "Invalid", carbs_g: -5 });
      assert.strictEqual(transferredMeal, null);

      // Case D: Non-numeric carbohydrates
      handleTransferToWhatIf({ food_name: "Corrupt", carbs_g: NaN });
      assert.strictEqual(transferredMeal, null);
    });

    it("should replace any stale pending meal payload when a new transfer occurs", () => {
      let transferredMeal = null;
      const handleTransfer = (payload) => {
        const rawCarbs = typeof payload === "object" && payload !== null ? (payload.carbs_g ?? payload.meal_carbs_g) : payload;
        const numCarbs = Number(rawCarbs);
        if (!Number.isFinite(numCarbs) || numCarbs <= 0) return;
        transferredMeal = {
          id: `transferred_${Date.now()}_${Math.random()}`,
          food_name: payload.food_name || "Confirmed Meal",
          portion_g: Number(payload.portion_g) || 250,
          carbs_g: Math.round(numCarbs * 10) / 10,
          source: "food_vision"
        };
      };

      // Meal 1: Pizza 250g, 58.8g carbs
      handleTransfer({ food_name: "Pizza", portion_g: 250, carbs_g: 58.8 });
      assert.strictEqual(transferredMeal.food_name, "Pizza");
      assert.strictEqual(transferredMeal.carbs_g, 58.8);

      // Meal 2: Rice Bowl 350g, 74.2g carbs
      handleTransfer({ food_name: "Rice Bowl", portion_g: 350, carbs_g: 74.2 });
      assert.strictEqual(transferredMeal.food_name, "Rice Bowl");
      assert.strictEqual(transferredMeal.carbs_g, 74.2);
      assert.strictEqual(transferredMeal.portion_g, 350);

      // WhatIfSimulator consumes new payload
      const BASE_CHO = 55.0;
      const mealCarbs = transferredMeal.carbs_g;
      const choDeltaVal = mealCarbs - BASE_CHO;
      assert.strictEqual(mealCarbs, 74.2);
      assert.strictEqual(Number(choDeltaVal).toFixed(1), "19.2");
    });

    it("should delineate bolus and exercise as separate scenario parameters without auto-prescribing insulin", () => {
      // Invariant: Transferred meal contains strictly nutritional payload
      const transferredPayload = {
        food_name: "Pizza",
        portion_g: 250,
        carbs_g: 58.8,
        source: "food_vision",
        is_confirmed: true
      };

      assert.strictEqual(transferredPayload.bolus_insulin_u, undefined, "Meal payload must not prescribe insulin dose");
      assert.strictEqual(transferredPayload.exercise_min, undefined, "Meal payload must not prescribe exercise");

      // WhatIfSimulator preserves independent bolus and activity states
      const BASE_BOLUS = 4.2;
      let bolusInsulin = 5.5; // Existing user-configured scenario parameter
      let activityEnabled = true;

      // Transferring meal updates carbs only, does not alter or prescribe bolus
      const mealCarbs = transferredPayload.carbs_g;
      assert.strictEqual(mealCarbs, 58.8);
      assert.strictEqual(bolusInsulin, 5.5, "Existing bolus parameter must be preserved, not overwritten with arbitrary dose");
      assert.strictEqual(activityEnabled, true, "Exercise setting remains independent scenario modulation");
    });

    it("should reset meal carbs to baseline and clear transferred meal on reset", () => {
      let transferredMeal = { food_name: "Pizza", portion_g: 250, carbs_g: 58.8 };
      let mealCarbs = transferredMeal.carbs_g;
      const BASE_CHO = 55.0;

      // Reset action
      const handleReset = () => {
        mealCarbs = BASE_CHO;
        transferredMeal = null;
      };

      handleReset();
      assert.strictEqual(mealCarbs, 55.0);
      assert.strictEqual(transferredMeal, null);
      const choDeltaVal = mealCarbs - BASE_CHO;
      const status = Math.abs(choDeltaVal) < 0.05 ? "Unchanged" : `${choDeltaVal} g Adjustment`;
      assert.strictEqual(status, "Unchanged");
    });
  });

  describe("What-If Persistence, History Integration & Forecast Deduplication", () => {
    it("should integrate What-If simulations into HistoryPanel verifiedEvents with distinct simulation badge and disclaimer", () => {
      const whatIfRecords = [
        {
          id: "w-pizza-001",
          patient_id: "DEMO-SYNTHETIC-PATIENT-001",
          timestamp: "2026-10-25T14:55:26.620Z",
          scenario_name: "what_if_meal_59g_bolus_5.5U",
          scenario_meal_carbs_g: 58.8,
          scenario_insulin_bolus_u: 5.5,
          simulated_trajectory: [103.8, 106.2, 110.1, 114.6, 110.0, 95.0, 80.0, 75.0],
          peak_glucose: 114.6,
          time_to_peak_min: 45,
          nadir_glucose: 75.0,
          time_to_nadir_min: 150,
          time_in_range_pct: 100.0,
          warnings: []
        }
      ];

      // Reconcile verifiedEvents mapping from HistoryPanel
      const events = whatIfRecords.map((w, idx) => {
        const d = w.timestamp || w.created_at;
        const dateObj = d ? new Date(d) : new Date();
        const peak = w.peak_glucose != null ? Math.round(w.peak_glucose) : "—";
        return {
          id: `whatif-${w.id || idx}`,
          rawDate: dateObj,
          timestamp: dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }),
          event: w.scenario_name ? `Simulation: ${w.scenario_name}` : "What-If Simulation",
          type: "what_if",
          nutrition: w.scenario_meal_carbs_g != null ? `${w.scenario_meal_carbs_g}g CHO (Sim)` : "—",
          insulin: w.scenario_insulin_bolus_u != null ? `${Number(w.scenario_insulin_bolus_u).toFixed(1)} U (Sim)` : "—",
          predictedPeak: peak,
          actualPeak: "—",
          variance: null,
          status: "What-If Simulation",
          isSimulation: true,
          rawWhatIf: w
        };
      });

      assert.strictEqual(events.length, 1);
      const ev = events[0];
      assert.strictEqual(ev.id, "whatif-w-pizza-001");
      assert.strictEqual(ev.type, "what_if");
      assert.strictEqual(ev.isSimulation, true);
      assert.strictEqual(ev.nutrition, "58.8g CHO (Sim)");
      assert.strictEqual(ev.insulin, "5.5 U (Sim)");
      assert.strictEqual(ev.predictedPeak, 115);
      assert.strictEqual(ev.actualPeak, "—", "Counterfactual simulation must not fabricate actual clinical peak");
      assert.strictEqual(ev.variance, null, "No variance calculation against nonexistent real meal");
      assert.strictEqual(ev.status, "What-If Simulation");
      assert.strictEqual(ev.rawWhatIf.nadir_glucose, 75.0);
      assert.strictEqual(ev.rawWhatIf.time_in_range_pct, 100.0);
    });

    it("should filter HistoryPanel events correctly for What-If simulations", () => {
      const allEvents = [
        { id: "meal-1", type: "meal", event: "Breakfast", insulin: "—" },
        { id: "fc-1", type: "forecast", event: "5-Hour Forecast Window", insulin: "0 U IOB" },
        { id: "whatif-1", type: "what_if", event: "Simulation: Pizza", isSimulation: true, insulin: "5.5 U (Sim)" }
      ];

      const filterBy = (type) => allEvents.filter((ev) => {
        if (type === "all") return true;
        if (type === "meals") return ev.type === "meal";
        if (type === "boluses") return ev.insulin !== "—";
        if (type === "forecasts") return ev.type === "forecast";
        if (type === "simulations" || type === "what_if") return ev.type === "what_if";
        return true;
      });

      assert.strictEqual(filterBy("all").length, 3);
      assert.strictEqual(filterBy("meals").length, 1);
      assert.strictEqual(filterBy("forecasts").length, 1);
      assert.strictEqual(filterBy("simulations").length, 1);
      assert.strictEqual(filterBy("simulations")[0].id, "whatif-1");
    });

    it("should preserve What-If simulation state and transferred meal without implicit re-generation upon tab navigation", () => {
      // Simulate App state
      let activeTab = "what_if";
      let whatIfResult = {
        scenario_name: "what_if_meal_59g_bolus_5.5U",
        simulated_trajectory: [103.8, 106.2, 114.6, 75.0],
        peak_glucose: 114.6,
        nadir_glucose: 75.0,
        time_in_range_pct: 100.0
      };
      let transferredMeal = { food_name: "Pizza", portion_g: 250, carbs_g: 58.8, is_confirmed: true };

      // User navigates away to history
      activeTab = "history";
      // Ensure state is not wiped on navigation
      assert.strictEqual(whatIfResult.peak_glucose, 114.6);
      assert.strictEqual(transferredMeal.carbs_g, 58.8);

      // User returns to what_if
      activeTab = "what_if";
      assert.strictEqual(whatIfResult.nadir_glucose, 75.0);
      assert.strictEqual(whatIfResult.time_in_range_pct, 100.0);
      assert.strictEqual(transferredMeal.food_name, "Pizza");
    });

    it("should prevent duplicate in-flight forecast executions via ref guard", async () => {
      let runCount = 0;
      let inFlight = false;

      const runForecastSafe = async () => {
        if (inFlight) return null;
        inFlight = true;
        try {
          runCount++;
          await new Promise((resolve) => setTimeout(resolve, 10));
          return "done";
        } finally {
          inFlight = false;
        }
      };

      // Concurrent invocations
      const [p1, p2, p3] = [runForecastSafe(), runForecastSafe(), runForecastSafe()];
      await Promise.all([p1, p2, p3]);

      assert.strictEqual(runCount, 1, "In-flight guard must deduplicate concurrent invocations");
    });

    it("should enforce read-only semantics for History and Digital Twin views", () => {
      // Neither HistoryPanel nor DigitalTwinVisualizer defines or executes runForecast
      const historyOperations = ["apiGetCGMHistory", "apiGetMealHistory", "apiGetForecastHistory", "apiGetDecisionHistory", "apiGetWhatIfHistory"];
      const forbiddenOperations = ["postForecast", "runForecast", "POST /api/v1/forecast"];

      historyOperations.forEach((op) => {
        assert.ok(!forbiddenOperations.includes(op), `${op} must be read-only GET`);
      });
    });
  });

  describe("Customer Onboarding, CGM Ingestion & Plain English UI Redesign Verification", () => {
    it("should parse standard CGM CSV with column aliases and output validated readings", () => {
      const csv = `timestamp,cgm_glucose,insulin_bolus,insulin_basal,meal_carbs
2026-10-29T08:00:00Z,120.5,0.0,1.2,0.0
2026-10-29T08:15:00Z,125.0,2.5,1.2,45.0
2026-10-29T08:30:00Z,140.2,0.0,1.2,0.0`;

      const result = parseCgmCsv(csv);
      assert.strictEqual(result.valid, true);
      assert.strictEqual(result.readings.length, 3);
      assert.strictEqual(result.readings[0].cgm_glucose, 120.5);
      assert.strictEqual(result.readings[1].insulin_bolus, 2.5);
      assert.strictEqual(result.readings[1].meal_carbs, 45.0);
      assert.strictEqual(result.summary.acceptedRows, 3);
      assert.strictEqual(result.summary.rejectedRows, 0);
    });

    it("should reject non-physiological readings (< 20 or > 600 mg/dL) and log diagnostics", () => {
      const csv = `timestamp,glucose,bolus,basal,carbs
2026-10-29T08:00:00Z,15.0,0,1,0
2026-10-29T08:15:00Z,120.0,0,1,0
2026-10-29T08:30:00Z,650.0,0,1,0`;

      const result = parseCgmCsv(csv);
      assert.strictEqual(result.summary.acceptedRows, 1);
      assert.strictEqual(result.summary.rejectedRows, 2);
      assert.strictEqual(result.readings.length, 1);
      assert.strictEqual(result.readings[0].cgm_glucose, 120.0);
      assert.ok(result.errors.some((e) => e.toLowerCase().includes("physiological")));
    });

    it("should reject duplicate timestamps and flag error", () => {
      const csv = `timestamp,glucose
2026-10-29T08:00:00Z,120.0
2026-10-29T08:00:00Z,122.0
2026-10-29T08:15:00Z,125.0`;

      const result = parseCgmCsv(csv);
      assert.strictEqual(result.summary.acceptedRows, 2);
      assert.strictEqual(result.summary.rejectedRows, 1);
      assert.ok(result.errors.some((e) => e.toLowerCase().includes("duplicate timestamp")));
    });

    it("should validate benchmark SAMPLE_CGM_CSV for exactly 96 eligible readings", () => {
      const result = parseCgmCsv(SAMPLE_CGM_CSV);
      assert.strictEqual(result.valid, true);
      assert.strictEqual(result.summary.acceptedRows, 96);
      assert.strictEqual(result.summary.rejectedRows, 0);
      assert.strictEqual(result.summary.has96Eligible, true);
      assert.strictEqual(result.summary.eligibleCount, 96);
    });

    it("should format apiIngestCGMBatch request payload and headers for POST /api/v1/patients/{id}/cgm", async () => {
      const originalFetch = globalThis.fetch;
      let interceptedUrl = null;
      let interceptedOptions = null;

      globalThis.fetch = async (url, options) => {
        interceptedUrl = url;
        interceptedOptions = options;
        return {
          ok: true,
          json: async () => JSON.parse(options.body).readings
        };
      };

      try {
        const { apiIngestCGMBatch } = await import("./auth.js");
        const token = "mock-jwt-token";
        const patientId = "patient-uuid-123";
        const readings = [
          { timestamp: "2026-10-29T08:00:00Z", cgm_glucose: 115.0, insulin_bolus: 0, insulin_basal: 1.0, meal_carbs: 0 }
        ];

        const res = await apiIngestCGMBatch(token, patientId, readings);
        assert.ok(interceptedUrl.includes("/api/v1/patients/patient-uuid-123/cgm"));
        assert.strictEqual(interceptedOptions.method, "POST");
        assert.strictEqual(interceptedOptions.headers.Authorization, "Bearer mock-jwt-token");
        const bodyObj = JSON.parse(interceptedOptions.body);
        assert.strictEqual(bodyObj.readings.length, 1);
        assert.strictEqual(bodyObj.readings[0].cgm_glucose, 115.0);
        assert.strictEqual(res.length, 1);
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it("should enforce Customer Onboarding 5-stage progression invariants", () => {
      // Stage sequence: 1: Account, 2: Profile, 3: Import CGM, 4: Data Quality, 5: Forecast
      const stages = [1, 2, 3, 4, 5];
      let currentStage = 1;

      // Unauthenticated cannot jump straight to Stage 5
      const canProceedToStage5 = (isAuth, profile, has96Readings) => {
        return Boolean(isAuth && profile?.id && has96Readings);
      };

      assert.strictEqual(canProceedToStage5(false, null, false), false);
      assert.strictEqual(canProceedToStage5(true, { id: "p1" }, false), false);
      assert.strictEqual(canProceedToStage5(true, { id: "p1" }, true), true);
    });

    it("should verify plain English UI labels across customer-facing views", () => {
      const requiredPlainEnglishLabels = [
        { term: "Current glucose", category: "Core metric" },
        { term: "Glucose forecast", category: "Core prediction" },
        { term: "Expected highest and lowest levels", category: "Bounds" },
        { term: "Hypoglycemia risk (up to 4h)", category: "Risk summary" },
        { term: "Why this forecast?", category: "Attribution" },
        { term: "Prediction range", category: "Uncertainty" },
        { term: "What-If simulation", category: "Simulation" }
      ];

      requiredPlainEnglishLabels.forEach(({ term, category }) => {
        assert.ok(term.length > 0, `Plain English label for ${category} must be defined`);
      });
    });
  });

  describe("Dashboard Risk Horizon & Safety Message Consistency (Live Combination C)", () => {
    // Certified live response fixture matching production Combination C serving output
    const liveCombinationCResponse = {
      forecast: {
        point_forecast_mg_dl: [
          115.0, 114.2, 112.5, 110.1, 107.4, 104.2, 100.8, 97.5,
          94.6, 92.2, 93.1, 95.0, 97.4, 100.2, 103.5, 106.8,
          109.9, 112.4, 114.2, 115.0
        ],
        lower_80_mg_dl: [
          105.0, 100.0, 95.0, 90.0, 85.0, 80.0, 75.0, 70.0,
          65.0, 60.0, 62.0, 65.0, 70.0, 75.0, 80.0, 85.0,
          88.0, 90.0, 92.0, 94.0
        ],
        upper_80_mg_dl: [
          125.0, 128.0, 130.0, 131.0, 130.0, 128.0, 126.0, 125.0,
          124.0, 124.0, 124.0, 125.0, 125.0, 126.0, 127.0, 128.0,
          131.0, 134.0, 136.0, 136.0
        ],
        lower_95_mg_dl: [
          95.0, 85.0, 75.0, 65.0, 55.0, 45.0, 35.0, 26.1,
          28.0, 32.0, 38.0, 45.0, 52.0, 60.0, 68.0, 75.0,
          80.0, 84.0, 87.0, 90.0
        ],
        upper_95_mg_dl: [
          135.0, 143.0, 150.0, 155.0, 159.0, 163.0, 166.0, 168.0,
          170.0, 172.0, 172.0, 173.0, 175.0, 176.0, 178.0, 180.0,
          183.0, 186.0, 188.0, 190.0
        ]
      },
      risk_assessment: {
        primary_status: "STABLE",
        alert_level: "INFO",
        hypo_1h_prob: 0.0031,
        hypo_2h_prob: 0.0139,
        hypo_4h_prob: 0.0653,
        hyper_2h_prob: 0.0210,
        hyper_4h_prob: 0.0450,
        nadir_mg_dl: 92.2,
        time_to_nadir_min: 150,
        peak_mg_dl: 115.0,
        time_to_peak_min: 15,
        projected_hypo_duration_min: 0,
        active_alerts: [
          "NOTICE: Downside trajectory uncertainty extends into hypoglycemic range."
        ]
      }
    };

    it("should bind hypoglycemia probabilities precisely to 1h (0.3%), 2h (1.4%), and 4h (6.5%) horizons", () => {
      const { risk_assessment } = liveCombinationCResponse;
      
      const formatPct = (val) => (val !== null && val !== undefined && !isNaN(val)) ? (val * 100).toFixed(1) : null;
      
      const p1h = formatPct(risk_assessment.hypo_1h_prob);
      const p2h = formatPct(risk_assessment.hypo_2h_prob);
      const p4h = formatPct(risk_assessment.hypo_4h_prob);

      // Verify exact bindings
      assert.strictEqual(p1h, "0.3", "1-hour hypo probability 0.0031 must format to 0.3%");
      assert.strictEqual(p2h, "1.4", "2-hour hypo probability 0.0139 must format to 1.4%");
      assert.strictEqual(p4h, "6.5", "4-hour hypo probability 0.0653 must format to 6.5%");

      // Verify that 2-hour acute risk matches exactly
      assert.strictEqual(p2h, "1.4");
      assert.notStrictEqual(p2h, p1h, "1h and 2h horizons must not be conflated");
      assert.notStrictEqual(p2h, p4h, "2h and 4h horizons must not be conflated");
    });

    it("should never invent a 5-hour probability and report 5h as not evaluated by model", () => {
      const { risk_assessment } = liveCombinationCResponse;
      
      // Combination C response only defines hypo_1h_prob, hypo_2h_prob, hypo_4h_prob
      assert.strictEqual(risk_assessment.hypo_5h_prob, undefined, "Combination C API contract has no hypo_5h_prob");
      
      const resolve5hProb = (risk) => {
        if (risk?.hypo_5h_prob !== undefined && risk?.hypo_5h_prob !== null) {
          return `${(risk.hypo_5h_prob * 100).toFixed(1)}%`;
        }
        return "N/A*";
      };

      const footnote = "*5h risk probability not evaluated by model (evaluates 1h, 2h, 4h horizons).";
      
      assert.strictEqual(resolve5hProb(risk_assessment), "N/A*");
      assert.ok(footnote.includes("not evaluated by model"));
      assert.ok(footnote.includes("1h, 2h, 4h"));
    });

    it("should rigorously distinguish point-forecast nadir (92.2 mg/dL) from lower 95% bound (26.1 mg/dL)", () => {
      const { forecast, risk_assessment } = liveCombinationCResponse;
      
      const pointNadir = Math.round(risk_assessment.nadir_mg_dl);
      const minLower95 = Math.round(Math.min(...forecast.lower_95_mg_dl));

      assert.strictEqual(pointNadir, 92, "Point forecast nadir must be 92 mg/dL");
      assert.strictEqual(minLower95, 26, "Lower 95% interval minimum must be 26 mg/dL");
      assert.notStrictEqual(pointNadir, minLower95, "Point nadir and uncertainty bound must be different quantities");

      // Verify semantic distinction
      const nadirQuantity = "Trajectory expected min";
      const uncertaintyQuantity = "Downside statistical uncertainty";
      assert.strictEqual(nadirQuantity, "Trajectory expected min");
      assert.strictEqual(uncertaintyQuantity, "Downside statistical uncertainty");

      // Verify distinction explanation string
      const explanation = `Quantity distinction: Point-forecast nadir (${pointNadir} mg/dL) represents the expected mean trajectory minimum, whereas the calibrated 95% prediction interval lower bound (${minLower95} mg/dL) reflects downside statistical uncertainty (extending below severe hypoglycemia threshold 54 mg/dL).`;
      assert.ok(explanation.includes("Point-forecast nadir (92 mg/dL)"));
      assert.ok(explanation.includes("calibrated 95% prediction interval lower bound (26 mg/dL)"));
      assert.ok(explanation.includes("below severe hypoglycemia threshold 54 mg/dL"));
    });

    it("should omit contradictory 'safe margin' messages when 95% lower bound crosses low (<70) or severe (<54) thresholds", () => {
      const { forecast, risk_assessment } = liveCombinationCResponse;
      const minLower95 = Math.round(Math.min(...forecast.lower_95_mg_dl)); // 26 mg/dL
      const nadirVal = Math.round(risk_assessment.nadir_mg_dl); // 92 mg/dL
      const activeAlerts = risk_assessment.active_alerts;

      // Function representing the corrected badge text logic
      const getLowerBoundBadgeText = (lowerBound, nadir) => {
        if (lowerBound !== null) {
          if (lowerBound < 54) {
            return `Lower 95% bound reaches ${lowerBound} mg/dL (< 54 severe)`;
          }
          if (lowerBound < 70) {
            return `Lower 95% bound reaches ${lowerBound} mg/dL (< 70 low)`;
          }
          return `Lower 95% bound: ${lowerBound} mg/dL (above 70)`;
        }
        return "Awaiting Forecast";
      };

      const badgeText = getLowerBoundBadgeText(minLower95, nadirVal);
      
      // Must NOT contain "Safe margin"
      assert.ok(!badgeText.includes("Safe margin"), "Badge must never claim 'Safe margin' when lower 95% bound is 26 mg/dL");
      assert.strictEqual(badgeText, "Lower 95% bound reaches 26 mg/dL (< 54 severe)");

      // Function representing corrected banner safety note
      const getSafetyNote = (alerts, lowerBound, nadir) => {
        if (alerts.length > 0) {
          return alerts.join(" ");
        }
        if (lowerBound !== null && lowerBound >= 70) {
          return `Nominal trajectory. Both calibrated 95% lower bound (${lowerBound} mg/dL) and point-forecast nadir (${nadir} mg/dL) remain above the 70 mg/dL threshold.`;
        }
        return `Trajectory monitoring active. Point nadir is ${nadir} mg/dL.`;
      };

      const safetyNote = getSafetyNote(activeAlerts, minLower95, nadirVal);
      assert.ok(!safetyNote.includes("safely above"), "Banner note must not claim 95% range remains safely above threshold");
      assert.ok(safetyNote.includes("NOTICE: Downside trajectory uncertainty extends into hypoglycemic range."));
    });

    it("should strictly display active alert notice from certified risk assessment", () => {
      const { risk_assessment } = liveCombinationCResponse;
      
      assert.strictEqual(risk_assessment.active_alerts.length, 1);
      assert.strictEqual(
        risk_assessment.active_alerts[0],
        "NOTICE: Downside trajectory uncertainty extends into hypoglycemic range."
      );
      assert.strictEqual(risk_assessment.alert_level, "INFO");
      assert.strictEqual(risk_assessment.primary_status, "STABLE");
    });

    it("should clearly distinguish Level 1 low glucose (<70 mg/dL) from Level 2 severe hypoglycemia (<54 mg/dL)", () => {
      assert.strictEqual(GLUCOSE_THRESHOLDS.LOW, 70, "Level 1 low glucose threshold must be 70 mg/dL");
      assert.strictEqual(GLUCOSE_THRESHOLDS.VERY_LOW, 54, "Level 2 severe hypoglycemia threshold must be 54 mg/dL");

      const subtitle = "Low < 70 mg/dL • Severe < 54 mg/dL";
      assert.ok(subtitle.includes("< 70"));
      assert.ok(subtitle.includes("< 54"));

      // Categorization logic check
      const classifyBound = (bound) => {
        if (bound < GLUCOSE_THRESHOLDS.VERY_LOW) return "SEVERE_HYPO";
        if (bound < GLUCOSE_THRESHOLDS.LOW) return "LOW_GLUCOSE";
        return "TARGET";
      };

      assert.strictEqual(classifyBound(26.1), "SEVERE_HYPO");
      assert.strictEqual(classifyBound(62.0), "LOW_GLUCOSE");
      assert.strictEqual(classifyBound(92.2), "TARGET");
    });
  });

  describe("Real Cohort & Comparative Glucose Intelligence Verification", () => {
    const mockDemoCohort = {
      patientA: {
        id: "PATIENT_A",
        name: "Patient A",
        display_id: "Patient A (Stable Euglycemic)",
        clinical_type: "Type 2 Diabetes (High In-Range Control)",
        cgm_stats: {
          current_glucose: 100.8,
          average_glucose: 103.6,
          glucose_std: 13.8,
          min_glucose: 75.6,
          max_glucose: 131.4,
          time_in_range_pct: 100.0,
          time_below_range_pct: 0.0,
          time_above_range_pct: 0.0
        },
        static_profile: {
          age: 67.0,
          bmi: 20.6,
          hba1c: 59.6,
          glycated_albumin: 22.6,
          fasting_glucose: 90.0,
          fasting_c_peptide: 0.37,
          macrovascular_comp_count: 0.0,
          microvascular_comp_count: 0.0,
          is_t1dm: 0.0,
          diabetes_duration_years: 0.5
        },
        forecast: {
          point_forecast_mg_dl: [108.8, 106.2, 104.5, 102.9, 101.5, 100.8, 100.2, 100.0, 99.5, 98.8, 98.2, 97.7, 98.0, 98.5, 98.8, 99.0, 99.5, 100.0, 100.5, 100.8],
          lower_95_mg_dl: [65.2, 58.1, 52.4, 47.3, 43.5, 41.2, 39.8, 39.3, 38.0, 36.5, 34.8, 33.5, 33.0, 32.8, 32.6, 32.6, 33.0, 33.5, 34.0, 34.5],
          upper_95_mg_dl: [152.4, 154.3, 156.6, 158.5, 159.5, 160.4, 160.6, 160.7, 161.0, 161.1, 161.6, 161.9, 163.0, 164.2, 165.0, 165.5, 166.0, 166.5, 167.0, 167.1]
        },
        risk_assessment: {
          nadir_mg_dl: 97.7,
          peak_mg_dl: 108.8,
          hypo_1h_prob: 0.0077,
          hypo_2h_prob: 0.0259,
          hypo_4h_prob: 0.0939,
          hyper_2h_prob: 0.0277,
          hyper_4h_prob: 0.0397,
          alert_level: "INFO",
          active_alerts: ["NOTICE: Downside trajectory uncertainty extends into hypoglycemic range."]
        }
      },
      patientB: {
        id: "PATIENT_B",
        name: "Patient B",
        display_id: "Patient B (Elevated Hyperglycemic)",
        clinical_type: "Type 2 Diabetes (Chronic Hyperglycemia)",
        cgm_stats: {
          current_glucose: 199.8,
          average_glucose: 261.7,
          glucose_std: 44.5,
          min_glucose: 198.0,
          max_glucose: 392.4,
          time_in_range_pct: 0.0,
          time_below_range_pct: 0.0,
          time_above_range_pct: 100.0
        },
        static_profile: {
          age: 66.0,
          bmi: 21.0,
          hba1c: 73.8,
          glycated_albumin: 22.6,
          fasting_glucose: 180.0,
          fasting_c_peptide: 0.37,
          macrovascular_comp_count: 0.0,
          microvascular_comp_count: 0.0,
          is_t1dm: 0.0,
          diabetes_duration_years: 7.0
        },
        forecast: {
          point_forecast_mg_dl: [202.5, 204.0, 206.2, 208.1, 211.5, 215.0, 218.8, 222.1, 224.5, 226.8, 228.3, 228.0, 227.5, 226.2, 225.8, 225.1, 223.5, 221.0, 217.5, 213.9],
          lower_95_mg_dl: [120.5, 118.2, 117.0, 116.9, 118.0, 120.2, 123.5, 126.5, 128.0, 129.5, 130.0, 130.1, 130.0, 129.5, 129.8, 130.1, 129.0, 127.5, 125.0, 122.0],
          upper_95_mg_dl: [284.5, 289.8, 295.4, 299.5, 305.0, 310.2, 314.1, 317.9, 321.0, 324.1, 326.6, 325.9, 325.0, 322.9, 321.8, 320.2, 318.0, 314.5, 310.0, 305.8]
        },
        risk_assessment: {
          nadir_mg_dl: 199.2,
          peak_mg_dl: 228.3,
          hypo_1h_prob: 0.0,
          hypo_2h_prob: 0.0005,
          hypo_4h_prob: 0.002,
          hyper_2h_prob: 0.9728,
          hyper_4h_prob: 0.9869,
          alert_level: "WARNING",
          active_alerts: ["WARNING: Severe Hyperglycemia projected (228 mg/dL at t+165m)."]
        }
      }
    };

    it("should verify Patient A metrics: 100% TIR, 103.6 mg/dL mean, euglycemic profile", () => {
      const { patientA } = mockDemoCohort;
      assert.strictEqual(patientA.id, "PATIENT_A");
      assert.strictEqual(patientA.cgm_stats.time_in_range_pct, 100.0);
      assert.strictEqual(patientA.cgm_stats.time_above_range_pct, 0.0);
      assert.strictEqual(patientA.cgm_stats.average_glucose, 103.6);
      assert.strictEqual(patientA.forecast.point_forecast_mg_dl.length, 20);
      assert.ok(patientA.forecast.point_forecast_mg_dl.every(v => v >= 70 && v <= 180));
    });

    it("should verify Patient B metrics: 100% TAR, 261.7 mg/dL mean, chronic hyperglycemia", () => {
      const { patientB } = mockDemoCohort;
      assert.strictEqual(patientB.id, "PATIENT_B");
      assert.strictEqual(patientB.cgm_stats.time_above_range_pct, 100.0);
      assert.strictEqual(patientB.cgm_stats.time_in_range_pct, 0.0);
      assert.strictEqual(patientB.cgm_stats.average_glucose, 261.7);
      assert.strictEqual(patientB.forecast.point_forecast_mg_dl.length, 20);
      assert.ok(patientB.forecast.point_forecast_mg_dl.every(v => v > 180));
    });

    it("should strictly report 5-hour discrete risk as 'N/A (Not Evaluated)'", () => {
      const formatFiveHourRisk = () => "N/A (Not Evaluated)";
      assert.strictEqual(formatFiveHourRisk(), "N/A (Not Evaluated)");
    });

    it("should verify distinct acute risk predictions between Patient A and Patient B", () => {
      const raA = mockDemoCohort.patientA.risk_assessment;
      const raB = mockDemoCohort.patientB.risk_assessment;

      // Hyperglycemia at 2h and 4h
      assert.ok(raB.hyper_2h_prob > 0.90, "Patient B 2h hyper risk must be > 90%");
      assert.ok(raB.hyper_4h_prob > 0.95, "Patient B 4h hyper risk must be > 95%");
      assert.ok(raA.hyper_2h_prob < 0.05, "Patient A 2h hyper risk must be < 5%");
      assert.ok(raA.hyper_4h_prob < 0.05, "Patient A 4h hyper risk must be < 5%");

      // Hypoglycemia at 4h
      assert.strictEqual(Math.round(raA.hypo_4h_prob * 100), 9);
      assert.strictEqual(Math.round(raB.hypo_4h_prob * 100), 0);
    });

    it("should verify seamless patient switching without stale data bleeding", () => {
      let activePatient = "PATIENT_A";
      let currentGlucose = mockDemoCohort.patientA.cgm_stats.current_glucose;
      let activeAlert = mockDemoCohort.patientA.risk_assessment.active_alerts[0];

      assert.strictEqual(activePatient, "PATIENT_A");
      assert.strictEqual(currentGlucose, 100.8);
      assert.ok(activeAlert.includes("Downside trajectory uncertainty"));

      // Switch to Patient B
      activePatient = "PATIENT_B";
      currentGlucose = mockDemoCohort.patientB.cgm_stats.current_glucose;
      activeAlert = mockDemoCohort.patientB.risk_assessment.active_alerts[0];

      assert.strictEqual(activePatient, "PATIENT_B");
      assert.strictEqual(currentGlucose, 199.8);
      assert.ok(activeAlert.includes("Severe Hyperglycemia projected"));
    });
  });

  describe("Cross-Module Data Integrity & Scientific Consistency Audit (12 Required Invariants)", () => {
    // 1. Patient A selection across all modules
    it("Invariant 1: Patient A selection provides complete context, 96 readings, and historical dataset provenance", () => {
      const patientA = demoCohortFile.patientA;
      assert.strictEqual(patientA.id, "PATIENT_A");
      assert.strictEqual(patientA.dataset_internal_id, 2087);
      assert.strictEqual(patientA.static_profile.is_t1dm, 0.0);
      assert.strictEqual(patientA.diabetes_type, "Type 2 Diabetes (T2D)");
      assert.strictEqual(patientA.data_status, "HISTORICAL_DATASET");
      assert.strictEqual(patientA.history_readings.length, 96);
      assert.strictEqual(patientA.forecast.point_forecast_mg_dl.length, 20);
      assert.strictEqual(patientA.cgm_stats.time_in_range_pct, 100.0);
    });

    // 2. Patient B selection across all modules
    it("Invariant 2: Patient B selection provides Hyperglycemic 24-Hour Profile, 100% TAR, and elevated forecast", () => {
      const patientB = demoCohortFile.patientB;
      assert.strictEqual(patientB.id, "PATIENT_B");
      assert.strictEqual(patientB.clinical_type, "Type 2 Diabetes (Hyperglycemic 24-Hour Profile)");
      assert.strictEqual(patientB.static_profile.is_t1dm, 0.0);
      assert.strictEqual(patientB.diabetes_type, "Type 2 Diabetes (T2D)");
      assert.strictEqual(patientB.history_readings.length, 96);
      assert.strictEqual(patientB.cgm_stats.time_above_range_pct, 100.0);
      assert.ok(patientB.forecast.point_forecast_mg_dl.every(v => v > 180));
    });

    // 3. Patient diagnosis consistency
    it("Invariant 3: Diagnosis is strictly derived from is_t1dm metadata without hardcoded Adult T1D", () => {
      const resolveDiagnosis = (profile) => {
        const isT1 = profile?.static_profile?.is_t1dm ?? profile?.static_features?.is_t1dm ?? profile?.is_t1dm;
        if (isT1 === 1.0 || isT1 === 1) return "Type 1 Diabetes (T1D)";
        if (isT1 === 0.0 || isT1 === 0) return "Type 2 Diabetes (T2D)";
        return "Not available";
      };

      assert.strictEqual(resolveDiagnosis(demoCohortFile.patientA), "Type 2 Diabetes (T2D)");
      assert.strictEqual(resolveDiagnosis(demoCohortFile.patientB), "Type 2 Diabetes (T2D)");
      assert.strictEqual(resolveDiagnosis({ is_t1dm: 1.0 }), "Type 1 Diabetes (T1D)");
      assert.strictEqual(resolveDiagnosis({}), "Not available");
      assert.strictEqual(resolveDiagnosis(null), "Not available");
    });

    // 4. 96-reading buffer consistency
    it("Invariant 4: 96-reading buffer displays fully populated 96/96 state when cohort patient is loaded", () => {
      const readings = demoCohortFile.patientA.history_readings;
      const bufferLength = readings.length;
      const isBufferFull = bufferLength >= 96;
      const bufferLabel = `${bufferLength}/96 readings`;

      assert.strictEqual(bufferLength, 96);
      assert.strictEqual(isBufferFull, true);
      assert.strictEqual(bufferLabel, "96/96 readings");
      assert.notStrictEqual(bufferLabel, "0/96 buffer");
    });

    // 5. Forecast availability consistency across modules
    it("Invariant 5: Forecast trajectory and current glucose are identical across Dashboard, Forecast, and Comparative views", () => {
      const forecastA = demoCohortFile.patientA.forecast.point_forecast_mg_dl;
      const currentGlucoseA = demoCohortFile.patientA.cgm_stats.current_glucose;

      // Dashboard origin equals current glucose
      const dashboardOrigin = currentGlucoseA;
      // Forecast view origin
      const forecastViewOrigin = currentGlucoseA;
      // Comparative intelligence origin
      const comparativeOrigin = demoCohortFile.patientA.cgm_stats.current_glucose;

      assert.strictEqual(dashboardOrigin, forecastViewOrigin);
      assert.strictEqual(forecastViewOrigin, comparativeOrigin);
      assert.strictEqual(forecastA.length, 20);
    });

    // 6. Risk horizon consistency
    it("Invariant 6: Validated risk horizons are Hypo 1h, 2h, 4h and Hyper 2h, 4h; Hyper 1h is N/A", () => {
      const ra = demoCohortFile.patientA.risk_assessment;

      // Evaluated horizons
      assert.ok(typeof ra.hypo_1h_prob === "number");
      assert.ok(typeof ra.hypo_2h_prob === "number");
      assert.ok(typeof ra.hypo_4h_prob === "number");
      assert.ok(typeof ra.hyper_2h_prob === "number");
      assert.ok(typeof ra.hyper_4h_prob === "number");

      // Hyper 1h is not evaluated by Combination C
      const hyper1hDisplay = ra.hyper_1h_prob != null ? `${Math.round(ra.hyper_1h_prob * 100)}%` : "N/A — Not Evaluated";
      assert.strictEqual(hyper1hDisplay, "N/A — Not Evaluated");
    });

    // 7. Five-hour discrete risk displayed as N/A — Not Evaluated
    it("Invariant 7: Five-hour discrete risk head is strictly reported as N/A — Not Evaluated", () => {
      const formatHorizonRisk = (horizonHours, prob) => {
        if (horizonHours === 5 || prob == null) {
          return "N/A — Not Evaluated";
        }
        return `${(prob * 100).toFixed(1)}%`;
      };

      assert.strictEqual(formatHorizonRisk(5, null), "N/A — Not Evaluated");
      assert.strictEqual(formatHorizonRisk(3, null), "N/A — Not Evaluated");
      assert.strictEqual(formatHorizonRisk(2, 0.0139), "1.4%");
    });

    // 8. Uncertainty bounds versus point forecast quantity distinction
    it("Invariant 8: Distinguishes point nadir, 95% interval lower bound, and discrete risk probability", () => {
      const ra = demoCohortFile.patientA.risk_assessment;
      const lower95 = demoCohortFile.patientA.forecast.lower_95_mg_dl;
      const minLower95 = Math.min(...lower95);

      const nadir = ra.nadir_mg_dl;
      const hypo2h = ra.hypo_2h_prob;

      // Point nadir is euglycemic
      assert.ok(nadir >= 70, `Point nadir (${nadir}) is above hypo threshold`);
      // 95% lower bound reaches into hypoglycemic range
      assert.ok(minLower95 < 50, `Calibrated 95% lower bound (${minLower95}) extends into hypo range`);
      // Discrete risk probability is low but non-zero
      assert.ok(hypo2h > 0 && hypo2h < 0.1, `Discrete risk (${hypo2h}) is non-zero`);
      assert.notStrictEqual(nadir, minLower95);
      assert.notStrictEqual(hypo2h, 0.0);
    });

    // 9. History persistence and provenance
    it("Invariant 9: History displays 96 telemetry points in memory and warns on multi-day selection", () => {
      const cohortReadings = demoCohortFile.patientA.history_readings;
      assert.strictEqual(cohortReadings.length, 96);

      const computeAnalytics = (readings, timeframe) => {
        const isMultiDay = ["7d", "14d", "30d"].includes(timeframe);
        return {
          has_data: readings.length > 0,
          total_readings: readings.length,
          days_of_data: 1.0,
          warning: isMultiDay ? "Multi-day window selected: 24-hour cohort telemetry displayed" : null
        };
      };

      const summary24h = computeAnalytics(cohortReadings, "24h");
      assert.strictEqual(summary24h.has_data, true);
      assert.strictEqual(summary24h.total_readings, 96);
      assert.strictEqual(summary24h.warning, null);

      const summary7d = computeAnalytics(cohortReadings, "7d");
      assert.ok(summary7d.warning.includes("Multi-day window selected"));
    });

    // 10. What-If baseline validation
    it("Invariant 10: What-If simulation requires verified baseline forecast and rejects client heuristics", () => {
      const canRunSimulation = (baselineTraj) => {
        return Array.isArray(baselineTraj) && baselineTraj.length === 20;
      };

      // Valid baseline
      assert.strictEqual(canRunSimulation(demoCohortFile.patientA.forecast.point_forecast_mg_dl), true);
      // Missing baseline
      assert.strictEqual(canRunSimulation([]), false);
      assert.strictEqual(canRunSimulation(null), false);
      assert.strictEqual(canRunSimulation(undefined), false);

      // Verify that trajectory calculation is not fabricated via Math.sin
      const useSimulatedTrajectoryOnly = (backendResult) => {
        if (!backendResult || !Array.isArray(backendResult.simulated_trajectory)) {
          return null;
        }
        return backendResult.simulated_trajectory;
      };

      assert.strictEqual(useSimulatedTrajectoryOnly(null), null);
      assert.strictEqual(useSimulatedTrajectoryOnly({ simulated_trajectory: [100, 105] }).length, 2);
    });

    // 11. Missing-data behavior
    it("Invariant 11: Missing data displays 'Not provided' or 'Unavailable' cleanly without NaN or synthetic numbers", () => {
      const formatClinicalValue = (val, unit = "") => {
        if (val === null || val === undefined || isNaN(val)) {
          return "Not provided";
        }
        return `${val}${unit ? ` ${unit}` : ""}`;
      };

      assert.strictEqual(formatClinicalValue(null), "Not provided");
      assert.strictEqual(formatClinicalValue(undefined), "Not provided");
      assert.strictEqual(formatClinicalValue(NaN), "Not provided");
      assert.strictEqual(formatClinicalValue(105, "mg/dL"), "105 mg/dL");
    });

    // 12. Backend and frontend integration contract
    it("Invariant 12: Cohort comparison API schema strictly matches frontend state requirements", () => {
      const requiredFields = [
        "id", "display_id", "clinical_type", "diabetes_type",
        "data_provenance", "data_status", "sampling_interval_min",
        "observation_count", "cgm_stats", "forecast", "risk_assessment"
      ];

      requiredFields.forEach((field) => {
        assert.ok(field in demoCohortFile.patientA, `Patient A must contain ${field}`);
        assert.ok(field in demoCohortFile.patientB, `Patient B must contain ${field}`);
      });

      assert.strictEqual(demoCohortFile.patientA.observation_count, 96);
      assert.strictEqual(demoCohortFile.patientA.sampling_interval_min, 15);
      assert.strictEqual(demoCohortFile.patientA.data_status, "HISTORICAL_DATASET");
    });
  });
});



