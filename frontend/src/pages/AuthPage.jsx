import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useBackendHealth } from "../hooks/useBackendHealth";

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const health = useBackendHealth();
  const { user, loading, signIn, signUp } = useAuth();

  const [authMode, setAuthMode] = useState("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname || "/dashboard";

  useEffect(() => {
    setError(null);
  }, [authMode]);

  if (loading) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <h1>Loading your workspace...</h1>
        </section>
      </main>
    );
  }

  if (user) {
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (authMode === "register") {
        await signUp({
          email: authEmail,
          password: authPassword,
          fullName: authName,
        });
      } else {
        await signIn({ email: authEmail, password: authPassword });
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Auth failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="auth-shell">
      <section className="landing-panel">
        <p className="eyebrow">MCP Quick</p>
        <h1>Benchmark agents, track runs, and improve reliability.</h1>
        <p>
          Sign in to manage your run history, inspect detailed traces, and monitor
          performance trends per provider and model.
        </p>
        <div className="status-pill">Backend: {health}</div>
      </section>

      <section className="auth-card">
        <div className="auth-switch">
          <button
            type="button"
            className={authMode === "login" ? "active" : ""}
            onClick={() => setAuthMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={authMode === "register" ? "active" : ""}
            onClick={() => setAuthMode("register")}
          >
            Register
          </button>
        </div>

        <form className="run-form" onSubmit={handleSubmit}>
          {authMode === "register" ? (
            <label>
              Full Name
              <input
                value={authName}
                onChange={(event) => setAuthName(event.target.value)}
                placeholder="Optional"
              />
            </label>
          ) : null}

          <label>
            Email
            <input
              type="email"
              value={authEmail}
              onChange={(event) => setAuthEmail(event.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={authPassword}
              onChange={(event) => setAuthPassword(event.target.value)}
              minLength={authMode === "register" ? 8 : 1}
              required
            />
          </label>

          <button type="submit" disabled={submitting}>
            {submitting
              ? "Please wait..."
              : authMode === "register"
                ? "Create Account"
                : "Sign In"}
          </button>
        </form>

        {error ? <p className="error">Error: {error}</p> : null}
      </section>
    </main>
  );
}
