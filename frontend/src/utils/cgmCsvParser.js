/**
 * GlucoShield CGM CSV Ingestion Parser & Validator
 * =================================================
 * Validates, normalizes, and previews continuous glucose monitoring data from CSV.
 * Supported columns:
 *   - timestamp (or date_time, time): ISO-8601 or YYYY-MM-DD HH:MM[:SS]
 *   - cgm_glucose (or glucose, glucose_mg_dl, value): numeric between 20 and 600 mg/dL
 *   - insulin_bolus (or bolus): numeric units (optional, default 0.0)
 *   - insulin_basal (or basal): numeric units/hr (optional, default 0.0)
 *   - meal_carbs (or carbs, carbohydrates): numeric grams (optional, default 0.0)
 */

export const SAMPLE_CGM_CSV = `timestamp,cgm_glucose,insulin_bolus,insulin_basal,meal_carbs
2026-10-28T00:00:00,118.0,0.0,0.5,0.0
2026-10-28T00:15:00,116.0,0.0,0.5,0.0
2026-10-28T00:30:00,115.0,0.0,0.5,0.0
2026-10-28T00:45:00,117.0,0.0,0.5,0.0
2026-10-28T01:00:00,119.0,0.0,0.5,0.0
2026-10-28T01:15:00,121.0,0.0,0.5,0.0
2026-10-28T01:30:00,120.0,0.0,0.5,0.0
2026-10-28T01:45:00,118.0,0.0,0.5,0.0
2026-10-28T02:00:00,117.0,0.0,0.5,0.0
2026-10-28T02:15:00,116.0,0.0,0.5,0.0
2026-10-28T02:30:00,115.0,0.0,0.5,0.0
2026-10-28T02:45:00,114.0,0.0,0.5,0.0
2026-10-28T03:00:00,116.0,0.0,0.5,0.0
2026-10-28T03:15:00,118.0,0.0,0.5,0.0
2026-10-28T03:30:00,119.0,0.0,0.5,0.0
2026-10-28T03:45:00,121.0,0.0,0.5,0.0
2026-10-28T04:00:00,122.0,0.0,0.5,0.0
2026-10-28T04:15:00,120.0,0.0,0.5,0.0
2026-10-28T04:30:00,118.0,0.0,0.5,0.0
2026-10-28T04:45:00,117.0,0.0,0.5,0.0
2026-10-28T05:00:00,115.0,0.0,0.5,0.0
2026-10-28T05:15:00,114.0,0.0,0.5,0.0
2026-10-28T05:30:00,116.0,0.0,0.5,0.0
2026-10-28T05:45:00,118.0,0.0,0.5,0.0
2026-10-28T06:00:00,122.0,0.0,0.5,0.0
2026-10-28T06:15:00,125.0,0.0,0.5,0.0
2026-10-28T06:30:00,128.0,0.0,0.5,0.0
2026-10-28T06:45:00,130.0,0.0,0.5,0.0
2026-10-28T07:00:00,132.0,0.0,0.5,0.0
2026-10-28T07:15:00,135.0,4.0,0.5,45.0
2026-10-28T07:30:00,148.0,0.0,0.5,0.0
2026-10-28T07:45:00,162.0,0.0,0.5,0.0
2026-10-28T08:00:00,170.0,0.0,0.5,0.0
2026-10-28T08:15:00,165.0,0.0,0.5,0.0
2026-10-28T08:30:00,154.0,0.0,0.5,0.0
2026-10-28T08:45:00,142.0,0.0,0.5,0.0
2026-10-28T09:00:00,135.0,0.0,0.5,0.0
2026-10-28T09:15:00,128.0,0.0,0.5,0.0
2026-10-28T09:30:00,124.0,0.0,0.5,0.0
2026-10-28T09:45:00,121.0,0.0,0.5,0.0
2026-10-28T10:00:00,119.0,0.0,0.5,0.0
2026-10-28T10:15:00,118.0,0.0,0.5,0.0
2026-10-28T10:30:00,117.0,0.0,0.5,0.0
2026-10-28T10:45:00,116.0,0.0,0.5,0.0
2026-10-28T11:00:00,118.0,0.0,0.5,0.0
2026-10-28T11:15:00,120.0,0.0,0.5,0.0
2026-10-28T11:30:00,122.0,0.0,0.5,0.0
2026-10-28T11:45:00,124.0,0.0,0.5,0.0
2026-10-28T12:00:00,125.0,0.0,0.5,0.0
2026-10-28T12:15:00,126.0,5.0,0.5,60.0
2026-10-28T12:30:00,140.0,0.0,0.5,0.0
2026-10-28T12:45:00,158.0,0.0,0.5,0.0
2026-10-28T13:00:00,166.0,0.0,0.5,0.0
2026-10-28T13:15:00,160.0,0.0,0.5,0.0
2026-10-28T13:30:00,148.0,0.0,0.5,0.0
2026-10-28T13:45:00,136.0,0.0,0.5,0.0
2026-10-28T14:00:00,128.0,0.0,0.5,0.0
2026-10-28T14:15:00,122.0,0.0,0.5,0.0
2026-10-28T14:30:00,118.0,0.0,0.5,0.0
2026-10-28T14:45:00,116.0,0.0,0.5,0.0
2026-10-28T15:00:00,115.0,0.0,0.5,0.0
2026-10-28T15:15:00,114.0,0.0,0.5,0.0
2026-10-28T15:30:00,116.0,0.0,0.5,0.0
2026-10-28T15:45:00,118.0,0.0,0.5,0.0
2026-10-28T16:00:00,120.0,0.0,0.5,0.0
2026-10-28T16:15:00,122.0,0.0,0.5,0.0
2026-10-28T16:30:00,121.0,0.0,0.5,0.0
2026-10-28T16:45:00,119.0,0.0,0.5,0.0
2026-10-28T17:00:00,118.0,0.0,0.5,0.0
2026-10-28T17:15:00,117.0,0.0,0.5,0.0
2026-10-28T17:30:00,116.0,0.0,0.5,0.0
2026-10-28T17:45:00,115.0,0.0,0.5,0.0
2026-10-28T18:00:00,116.0,0.0,0.5,0.0
2026-10-28T18:15:00,118.0,0.0,0.5,0.0
2026-10-28T18:30:00,120.0,0.0,0.5,0.0
2026-10-28T18:45:00,122.0,0.0,0.5,0.0
2026-10-28T19:00:00,124.0,4.5,0.5,50.0
2026-10-28T19:15:00,138.0,0.0,0.5,0.0
2026-10-28T19:30:00,152.0,0.0,0.5,0.0
2026-10-28T19:45:00,160.0,0.0,0.5,0.0
2026-10-28T20:00:00,155.0,0.0,0.5,0.0
2026-10-28T20:15:00,144.0,0.0,0.5,0.0
2026-10-28T20:30:00,136.0,0.0,0.5,0.0
2026-10-28T20:45:00,128.0,0.0,0.5,0.0
2026-10-28T21:00:00,122.0,0.0,0.5,0.0
2026-10-28T21:15:00,119.0,0.0,0.5,0.0
2026-10-28T21:30:00,117.0,0.0,0.5,0.0
2026-10-28T21:45:00,116.0,0.0,0.5,0.0
2026-10-28T22:00:00,115.0,0.0,0.5,0.0
2026-10-28T22:15:00,114.0,0.0,0.5,0.0
2026-10-28T22:30:00,115.0,0.0,0.5,0.0
2026-10-28T22:45:00,116.0,0.0,0.5,0.0
2026-10-28T23:00:00,117.0,0.0,0.5,0.0
2026-10-28T23:15:00,118.0,0.0,0.5,0.0
2026-10-28T23:30:00,119.0,0.0,0.5,0.0
2026-10-28T23:45:00,117.0,0.0,0.5,0.0`;

/**
 * Parses raw CSV text into a structured, validated array of CGM observations.
 * Returns { valid: boolean, readings: [], errors: [], summary: {} }
 */
export function parseCgmCsv(csvText) {
  if (!csvText || typeof csvText !== "string" || !csvText.trim()) {
    return {
      valid: false,
      readings: [],
      errors: ["CSV file is empty or contains no readable text."],
      summary: { totalRows: 0, acceptedRows: 0, rejectedRows: 0, eligibleCount: 0 }
    };
  }

  const lines = csvText.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length < 2) {
    return {
      valid: false,
      readings: [],
      errors: ["CSV file must contain a header row and at least one data row."],
      summary: { totalRows: 0, acceptedRows: 0, rejectedRows: 0, eligibleCount: 0 }
    };
  }

  // Parse header
  const headers = lines[0].split(",").map(h => h.trim().toLowerCase().replace(/['"]/g, ""));
  
  // Find column indices with alias support
  const timeIdx = headers.findIndex(h => ["timestamp", "time", "date_time", "datetime", "date"].includes(h));
  const glucoseIdx = headers.findIndex(h => ["cgm_glucose", "glucose", "glucose_mg_dl", "value", "sensor_glucose"].includes(h));
  const bolusIdx = headers.findIndex(h => ["insulin_bolus", "bolus", "bolus_insulin", "insulin"].includes(h));
  const basalIdx = headers.findIndex(h => ["insulin_basal", "basal", "basal_rate", "basal_insulin"].includes(h));
  const carbsIdx = headers.findIndex(h => ["meal_carbs", "carbs", "carbohydrates", "cho"].includes(h));

  if (timeIdx === -1) {
    return {
      valid: false,
      readings: [],
      errors: ["Missing required header column for timestamp ('timestamp', 'date_time', or 'time')."],
      summary: { totalRows: lines.length - 1, acceptedRows: 0, rejectedRows: lines.length - 1, eligibleCount: 0 }
    };
  }

  if (glucoseIdx === -1) {
    return {
      valid: false,
      readings: [],
      errors: ["Missing required header column for glucose ('cgm_glucose', 'glucose', or 'glucose_mg_dl')."],
      summary: { totalRows: lines.length - 1, acceptedRows: 0, rejectedRows: lines.length - 1, eligibleCount: 0 }
    };
  }

  const parsedReadings = [];
  const errors = [];
  const seenTimestamps = new Set();

  for (let i = 1; i < lines.length; i++) {
    const rowNum = i + 1;
    const cols = lines[i].split(",").map(c => c.trim().replace(/['"]/g, ""));
    
    if (cols.length < 2) {
      errors.push(`Row ${rowNum}: malformed line with insufficient columns.`);
      continue;
    }

    const rawTime = cols[timeIdx];
    const rawGlucose = cols[glucoseIdx];

    // Validate timestamp
    const dateObj = new Date(rawTime);
    if (isNaN(dateObj.getTime())) {
      errors.push(`Row ${rowNum}: invalid timestamp format '${rawTime}'. Must be ISO-8601 or YYYY-MM-DD HH:MM.`);
      continue;
    }

    const isoTimestamp = dateObj.toISOString();

    // Check duplicate timestamp
    if (seenTimestamps.has(isoTimestamp)) {
      errors.push(`Row ${rowNum}: duplicate timestamp '${isoTimestamp}'.`);
      continue;
    }
    seenTimestamps.add(isoTimestamp);

    // Validate glucose
    const numGlucose = Number(rawGlucose);
    if (!Number.isFinite(numGlucose) || isNaN(numGlucose)) {
      errors.push(`Row ${rowNum}: invalid non-numeric glucose value '${rawGlucose}'.`);
      continue;
    }

    if (numGlucose < 20.0 || numGlucose > 600.0) {
      errors.push(`Row ${rowNum}: glucose ${numGlucose} mg/dL out of physiological clinical range (20–600 mg/dL).`);
      continue;
    }

    // Optional fields
    let bolus = 0.0;
    if (bolusIdx !== -1 && cols[bolusIdx]) {
      const b = Number(cols[bolusIdx]);
      if (Number.isFinite(b) && b >= 0 && b <= 50.0) bolus = b;
    }

    let basal = 0.0;
    if (basalIdx !== -1 && cols[basalIdx]) {
      const b = Number(cols[basalIdx]);
      if (Number.isFinite(b) && b >= 0 && b <= 20.0) basal = b;
    }

    let carbs = 0.0;
    if (carbsIdx !== -1 && cols[carbsIdx]) {
      const c = Number(cols[carbsIdx]);
      if (Number.isFinite(c) && c >= 0 && c <= 300.0) carbs = c;
    }

    parsedReadings.push({
      timestamp: isoTimestamp,
      cgm_glucose: Math.round(numGlucose * 10) / 10,
      insulin_bolus: Math.round(bolus * 10) / 10,
      insulin_basal: Math.round(basal * 100) / 100,
      meal_carbs: Math.round(carbs * 10) / 10
    });
  }

  // Sort chronologically
  parsedReadings.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const totalRows = lines.length - 1;
  const acceptedRows = parsedReadings.length;
  const rejectedRows = totalRows - acceptedRows;
  const isChronological = true; // explicitly sorted
  const eligibleCount = acceptedRows;

  return {
    valid: acceptedRows > 0,
    readings: parsedReadings,
    errors,
    summary: {
      totalRows,
      acceptedRows,
      rejectedRows,
      eligibleCount,
      has96Eligible: eligibleCount >= 96,
      dateRange: acceptedRows > 0 ? {
        start: parsedReadings[0].timestamp,
        end: parsedReadings[parsedReadings.length - 1].timestamp
      } : null
    }
  };
}
