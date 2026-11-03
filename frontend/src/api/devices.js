/**
 * GlucoShield Mobile & Device Integration API Client (Phase 17)
 */

const API_BASE = "";

function getAuthHeaders() {
  const token = localStorage.getItem("glucoshield_token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchConnectedDevices() {
  const res = await fetch(`${API_BASE}/api/v1/devices`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch connected devices (${res.status})`);
  }
  return await res.json();
}

export async function registerDevice(payload) {
  const res = await fetch(`${API_BASE}/api/v1/devices/register`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || "Failed to register device");
  }
  return await res.json();
}

export async function syncDeviceData(payload) {
  const res = await fetch(`${API_BASE}/api/v1/devices/sync`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || "Device sync failed");
  }
  return await res.json();
}

export async function logManualEvent(payload) {
  const res = await fetch(`${API_BASE}/api/v1/devices/events/manual`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || "Failed to log mobile event");
  }
  return await res.json();
}

export async function disconnectDevice(deviceId) {
  const res = await fetch(`${API_BASE}/api/v1/devices/${deviceId}/disconnect`, {
    method: "POST",
    headers: getAuthHeaders()
  });
  if (!res.ok) {
    throw new Error("Failed to disconnect device");
  }
  return await res.json();
}

export async function fetchCausalContext(originIso = null) {
  const url = originIso
    ? `${API_BASE}/api/v1/devices/causal-context?forecast_origin=${encodeURIComponent(originIso)}`
    : `${API_BASE}/api/v1/devices/causal-context`;
  const res = await fetch(url, {
    headers: getAuthHeaders()
  });
  if (!res.ok) {
    throw new Error("Failed to fetch causal context");
  }
  return await res.json();
}
