import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getDashboardSummary } from "../api/dashboardApi";
import { listRuns } from "../api/runsApi";
import { useAuth } from "../context/AuthContext";
import { formatDateTime, formatScore } from "../utils/formatters";

const RECENT_RUNS_LIMIT = 5;

export default function ProfilePage() {
  const { user, token } = useAuth();
  const [summary, setSummary] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(null);
  const [runsError, setRunsError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const getErrorMessage = (error, fallback) =>
      error?.response?.data?.detail || error?.message || fallback;

    async function loadProfileData() {
      setLoading(true);
      setSummaryError(null);
      setRunsError(null);

      const [summaryResult, runsResult] = await Promise.allSettled([
        getDashboardSummary(token),
        listRuns(token, { limit: RECENT_RUNS_LIMIT, offset: 0 }),
      ]);

      if (!mounted) {
        return;
      }

      if (summaryResult.status === "fulfilled") {
        setSummary(summaryResult.value);
      } else {
        setSummary(null);
        setSummaryError(
          getErrorMessage(summaryResult.reason, "Unable to load activity snapshot.")
        );
      }

      if (runsResult.status === "fulfilled") {
        setRecentRuns(runsResult.value.items || []);
      } else {
        setRecentRuns([]);
        setRunsError(
          getErrorMessage(runsResult.reason, "Unable to load recent runs.")
        );
      }

      setLoading(false);
    }

    loadProfileData();

    return () => {
      mounted = false;
    };
  }, [token]);

  const topUsage = useMemo(() => {
    if (!summary?.provider_model_usage?.length) {
      return null;
    }

    return [...summary.provider_model_usage].sort(
      (a, b) => (b.run_count || 0) - (a.run_count || 0)
    )[0];
  }, [summary]);

  const recentRunVolume = useMemo(() => {
    if (!summary?.runs_over_time?.length) {
      return null;
    }

    return summary.runs_over_time
      .slice(-7)
      .reduce((total, item) => total + (item.count || 0), 0);
  }, [summary]);

  return (
    <section className="stack">
      <article className="panel profile-header">
        <div>
          <h2>Profile</h2>
          <p className="muted">Account details and recent activity.</p>
        </div>
        <div className="inline-actions">
          <Link className="text-link" to="/runs/new">
            Start a run
          </Link>
          <Link className="text-link" to="/runs">
            View run history
          </Link>
        </div>
      </article>

      <section className="grid two-col profile-grid">
        <article className="panel">
          <h3>Account</h3>
          <div className="status-block">
            <p>User ID: {user?.id}</p>
            <p>Email: {user?.email}</p>
            <p>Full Name: {user?.full_name || "-"}</p>
            <p>Joined At: {formatDateTime(user?.created_at)}</p>
          </div>
        </article>

        <article className="panel">
          <h3>Activity snapshot</h3>
          {loading ? (
            <p>Loading activity...</p>
          ) : summaryError ? (
            <p className="error">Error: {summaryError}</p>
          ) : (
            <div className="summary-grid">
              <div className="summary-item">
                <span>Latest run</span>
                <strong>{formatDateTime(summary?.latest_run_at)}</strong>
              </div>
              <div className="summary-item">
                <span>Top provider/model</span>
                <strong>
                  {topUsage
                    ? `${topUsage.provider} / ${topUsage.model}`
                    : "-"}
                </strong>
              </div>
              <div className="summary-item">
                <span>Top avg score</span>
                <strong>
                  {topUsage ? formatScore(topUsage.avg_score) : "-"}
                </strong>
              </div>
              <div className="summary-item">
                <span>Recent 7-day runs</span>
                <strong>{recentRunVolume ?? "-"}</strong>
              </div>
            </div>
          )}
        </article>
      </section>

      <article className="panel">
        <div className="section-header">
          <h3>Recent runs</h3>
          <Link className="text-link" to="/runs">
            View all
          </Link>
        </div>
        {loading ? (
          <p>Loading recent runs...</p>
        ) : runsError ? (
          <p className="error">Error: {runsError}</p>
        ) : !recentRuns.length ? (
          <p>No runs yet.</p>
        ) : (
          <ul className="run-list compact">
            {recentRuns.map((item) => (
              <li key={item.id}>
                <Link to={`/runs/${item.id}`} className="run-list-link">
                  <strong>{item.provider}</strong>
                  <span>{item.model}</span>
                  <span>{item.status}</span>
                  <span>{formatDateTime(item.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
