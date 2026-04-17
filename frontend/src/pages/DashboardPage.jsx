import { useEffect, useState } from "react";

import { getDashboardSummary } from "../api/dashboardApi";
import { useAuth } from "../context/AuthContext";
import { formatDateTime, formatPercent, formatScore } from "../utils/formatters";

export default function DashboardPage() {
  const { token } = useAuth();

  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadDashboard() {
      setLoading(true);
      setError(null);
      try {
        const summary = await getDashboardSummary(token);
        if (mounted) {
          setDashboard(summary);
        }
      } catch (err) {
        if (mounted) {
          setError(err.response?.data?.detail || err.message);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      mounted = false;
    };
  }, [token]);

  return (
    <section className="stack">
      <article className="panel">
        <h2>Key Metrics</h2>
        {loading ? (
          <p>Loading dashboard...</p>
        ) : error ? (
          <p className="error">Error: {error}</p>
        ) : (
          <div className="stats-grid">
            <div className="stat-card">
              <span>Total Runs</span>
              <strong>{dashboard.total_runs}</strong>
            </div>
            <div className="stat-card">
              <span>Success Rate</span>
              <strong>{formatPercent(dashboard.success_rate)}</strong>
            </div>
            <div className="stat-card">
              <span>Average Latency</span>
              <strong>
                {dashboard.average_latency_ms
                  ? `${dashboard.average_latency_ms} ms`
                  : "-"}
              </strong>
            </div>
            <div className="stat-card">
              <span>Latest Run</span>
              <strong>{formatDateTime(dashboard.latest_run_at)}</strong>
            </div>
          </div>
        )}
      </article>

      <section className="grid two-col">
        <article className="panel">
          <h2>Runs Over Time</h2>
          {!dashboard?.runs_over_time?.length ? (
            <p>No runs yet.</p>
          ) : (
            <div className="bars">
              {dashboard.runs_over_time.map((item) => (
                <div key={item.date} className="bar-row">
                  <span>{item.date}</span>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${Math.max(
                          8,
                          (item.count /
                            Math.max(
                              ...dashboard.runs_over_time.map((it) => it.count),
                              1
                            )) *
                            100
                        )}%`,
                      }}
                    />
                  </div>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel">
          <h2>Provider / Model Usage</h2>
          {!dashboard?.provider_model_usage?.length ? (
            <p>No usage yet.</p>
          ) : (
            <div className="table-like">
              {dashboard.provider_model_usage.map((item) => (
                <div key={`${item.provider}-${item.model}`} className="table-row">
                  <div>
                    <strong>{item.provider}</strong>
                    <p>{item.model}</p>
                  </div>
                  <div>
                    <span>Runs: {item.run_count}</span>
                    <span>Avg Score: {formatScore(item.avg_score)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </section>
  );
}
