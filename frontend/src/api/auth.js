/**
 * GlucoShield Authentication & Persistence REST API Client
 */

const API_BASE = "";

export async function apiRegister(email, password, fullName) {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName || null
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Registration failed (${res.status})` }));
    throw new Error(err.detail || "Registration failed");
  }

  return await res.json();
}

export async function apiLogin(email, password) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Login failed (${res.status})` }));
    throw new Error(err.detail || "Invalid credentials");
  }

  return await res.json();
}

export async function apiGetMe(token) {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { "Authorization": `Bearer ${token}` }
  });

  if (!res.ok) {
    throw new Error(`Session expired (${res.status})`);
  }

  return await res.json();
}

export async function apiGetMyPatient(token) {
  const res = await fetch(`${API_BASE}/api/v1/patients/me`, {
    headers: { "Authorization": `Bearer ${token}` }
  });

  if (!res.ok) {
    throw new Error(`Failed to load patient profile (${res.status})`);
  }

  return await res.json();
}

export async function apiUpdatePatient(token, patientId, profileData) {
  const payload = {
    age: profileData.age !== undefined ? Number(profileData.age) : undefined,
    bmi: profileData.bmi !== undefined ? Number(profileData.bmi) : undefined,
    diabetes_duration_years: profileData.diabetes_duration_years !== undefined ? Number(profileData.diabetes_duration_years) : undefined,
    hba1c: profileData.hba1c !== undefined ? Number(profileData.hba1c) : undefined,
    glycated_albumin: profileData.glycated_albumin !== undefined ? Number(profileData.glycated_albumin) : undefined,
    fasting_glucose: profileData.fasting_glucose !== undefined ? Number(profileData.fasting_glucose) : undefined,
    fasting_c_peptide: profileData.fasting_c_peptide !== undefined ? Number(profileData.fasting_c_peptide) : undefined,
    macrovascular_comp_count: profileData.macrovascular_comp_count !== undefined ? Number(profileData.macrovascular_comp_count) : undefined,
    microvascular_comp_count: profileData.microvascular_comp_count !== undefined ? Number(profileData.microvascular_comp_count) : undefined,
    is_t1dm: profileData.is_t1dm !== undefined ? Number(profileData.is_t1dm) : undefined
  };

  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Profile update failed (${res.status})` }));
    throw new Error(err.detail || "Profile update failed");
  }

  return await res.json();
}

export async function apiGetCGMHistory(token, patientId, limit = 96) {
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/cgm?limit=${limit}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function apiIngestCGMBatch(token, patientId, readings) {
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/cgm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ readings })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `CGM ingestion failed (${res.status})`);
  }
  return await res.json();
}

export async function apiGetMealHistory(token, patientId, limit = 20) {
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/meals?limit=${limit}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function apiGetForecastHistory(token, patientId, limit = 10) {
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/forecasts?limit=${limit}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function apiGetDecisionHistory(token, patientId, limit = 10) {
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/decisions?limit=${limit}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function apiGetWhatIfHistory(token, patientId, limit = 20) {
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/what-if?limit=${limit}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) return [];
  return await res.json();
}

