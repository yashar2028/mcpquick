import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getCurrentUser, loginUser, registerUser } from "../api/authApi";
import { AUTH_STORAGE_KEY } from "../constants";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(
    () => window.localStorage.getItem(AUTH_STORAGE_KEY) || ""
  );
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    let mounted = true;

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
