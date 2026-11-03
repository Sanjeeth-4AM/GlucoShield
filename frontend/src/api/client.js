/**
 * GlucoShield Centralized REST API Client
 */

const API_BASE = ""; // Relative path relies on Vite proxy or same-origin FastAPI host

function getAuthHeaders() {
  const token = localStorage.getItem("glucoshield_token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    if (!res.ok) {
      throw new Error(`Health check failed with HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn("[API Client] Backend health check unreachable:", err.message);
    return null;
  }
}

export async function fetchForecast(payload) {
  const res = await fetch(`${API_BASE}/api/v1/forecast`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(errData.detail || `Forecast request failed (${res.status})`);
  }

  return await res.json();
}

export async function fetchWhatIf(payload) {
  const res = await fetch(`${API_BASE}/api/v1/what-if`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(errData.detail || `What-If simulation failed (${res.status})`);
  }

  return await res.json();
}

export async function fetchFoodAnalyze(payload) {
  const res = await fetch(`${API_BASE}/api/v1/food/analyze`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(errData.detail || `Food analysis failed (${res.status})`);
  }

  return await res.json();
}

export async function fetchFullFlow(payload) {
  const res = await fetch(`${API_BASE}/api/v1/decision/full-flow`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(errData.detail || `Full-flow decision request failed (${res.status})`);
  }

  return await res.json();
}

export async function fetchCohortDemoPatients() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/cohort/demo-patients`);
    if (!res.ok) {
      throw new Error(`Demo patients request failed (${res.status})`);
    }
    return await res.json();
  } catch (err) {
    console.warn("[API Client] fetchCohortDemoPatients failed:", err.message);
    return null;
  }
}

export async function fetchCohortComparison() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/cohort/comparison`);
    if (!res.ok) {
      throw new Error(`Cohort comparison request failed (${res.status})`);
    }
    return await res.json();
  } catch (err) {
    console.warn("[API Client] fetchCohortComparison failed:", err.message);
    return null;
  }
}
