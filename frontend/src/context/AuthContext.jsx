import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import { getCurrentUser, loginUser, registerUser } from "../api/authApi";
import { AUTH_STORAGE_KEY } from "../constants";

const AuthContext = createContext(null);

const decodeBase64Url = (value) => {
  if (!value) {
    return null;
  }
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  try {
    return JSON.parse(window.atob(padded));
  } catch {
    return null;
  }
};

const getTokenExpiry = (token) => {
  if (!token) {
    return null;
  }
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }
  const payload = decodeBase64Url(parts[1]);
  if (!payload || typeof payload.exp !== "number") {
    return null;
  }
  return payload.exp * 1000;
};

export function AuthProvider({ children }) {
  const [token, setToken] = useState(
    () => window.localStorage.getItem(AUTH_STORAGE_KEY) || ""
  );
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));
  const logoutTimerRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const expiresAt = getTokenExpiry(token);
    if (token && expiresAt && expiresAt <= Date.now()) {
      setToken("");
      setUser(null);
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
      setLoading(false);
      return () => {
        mounted = false;
      };
    }

    async function loadUser() {
      if (!token) {
        if (mounted) {
          setUser(null);
          setLoading(false);
        }
        return;
      }

      try {
        const me = await getCurrentUser(token);
        if (mounted) {
          setUser(me);
        }
      } catch {
        if (mounted) {
          setToken("");
          setUser(null);
          window.localStorage.removeItem(AUTH_STORAGE_KEY);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadUser();

    return () => {
      mounted = false;
    };
  }, [token]);

  useEffect(() => {
    if (logoutTimerRef.current) {
      window.clearTimeout(logoutTimerRef.current);
      logoutTimerRef.current = null;
    }

    if (!token) {
      return undefined;
    }

    const expiresAt = getTokenExpiry(token);
    if (!expiresAt) {
      return undefined;
    }

    const delay = Math.max(0, expiresAt - Date.now());
    logoutTimerRef.current = window.setTimeout(() => {
      setToken("");
      setUser(null);
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
    }, delay);

    return () => {
      if (logoutTimerRef.current) {
        window.clearTimeout(logoutTimerRef.current);
        logoutTimerRef.current = null;
      }
    };
  }, [token]);

  const signIn = async ({ email, password }) => {
    const response = await loginUser({ email, password });
    setToken(response.access_token);
    setUser(response.user);
    window.localStorage.setItem(AUTH_STORAGE_KEY, response.access_token);
    return response.user;
  };

  const signUp = async ({ email, password, fullName }) => {
    const response = await registerUser({
      email,
      password,
      full_name: fullName || null,
    });
    setToken(response.access_token);
    setUser(response.user);
    window.localStorage.setItem(AUTH_STORAGE_KEY, response.access_token);
    return response.user;
  };

  const signOut = () => {
    setToken("");
    setUser(null);
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  };

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      signIn,
      signUp,
      signOut,
    }),
    [token, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
