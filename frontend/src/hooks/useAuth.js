import { useState, useEffect, useCallback } from "react";
import { apiLogin, apiRegister, apiGetMe, apiGetMyPatient } from "../api/auth";

export function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem("glucoshield_token") || null);
  const [user, setUser] = useState(null);
  const [patientProfile, setPatientProfile] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Initialize session on mount
  const initSession = useCallback(async (authToken) => {
    if (!authToken) {
      setUser(null);
      setPatientProfile(null);
      setAuthLoading(false);
      return;
    }

    try {
      setAuthLoading(true);
      const userData = await apiGetMe(authToken);
      setUser(userData);
      const patientData = await apiGetMyPatient(authToken);
      setPatientProfile(patientData);
      setAuthError(null);
    } catch (err) {
      console.warn("[Auth] Session invalid or expired:", err.message);
      localStorage.removeItem("glucoshield_token");
      setToken(null);
      setUser(null);
      setPatientProfile(null);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    initSession(token);
  }, [token, initSession]);

  const login = async (email, password) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const data = await apiLogin(email, password);
      localStorage.setItem("glucoshield_token", data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      const patient = await apiGetMyPatient(data.access_token);
      setPatientProfile(patient);
      return data;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    } finally {
      setAuthLoading(false);
    }
  };

  const register = async (email, password, fullName) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const data = await apiRegister(email, password, fullName);
      localStorage.setItem("glucoshield_token", data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      const patient = await apiGetMyPatient(data.access_token);
      setPatientProfile(patient);
      return data;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    } finally {
      setAuthLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("glucoshield_token");
    setToken(null);
    setUser(null);
    setPatientProfile(null);
    setAuthError(null);
  };

  return {
    isAuthenticated: !!token && !!user,
    token,
    user,
    patientProfile,
    setPatientProfile,
    authLoading,
    authError,
    setAuthError,
    login,
    register,
    logout
  };
}
