import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  deleteRun,
  getRun,
  getRunEvents,
  getRunLogs,
  getRunReport,
  retryRun,
} from "../api/runsApi";
import { useAuth } from "../context/AuthContext";
import { formatPayload, formatScore } from "../utils/formatters";

export default function RunDetailsPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();

  const [run, setRun] = useState(null);
  const [events, setEvents] = useState([]);
  const [report, setReport] = useState(null);
  const [logs, setLogs] = useState(null);
  const [retryApiKey, setRetryApiKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const runInProgress = useMemo(() => {
    if (!run) {
      return false;
    }
    return run.status === "queued" || run.status === "running";
  }, [run]);

  const loadRunBundle = useCallback(async () => {
    if (!runId) {
      return;
    }

    setError(null);

    const [runData, eventsData] = await Promise.all([
      getRun(token, runId),
      getRunEvents(token, runId, 250),
    ]);

    setRun(runData);
    setEvents(eventsData);

    if (runData.status === "completed") {
      const reportData = await getRunReport(token, runId);
      setReport(reportData);
      setLogs(null);
      return;
    }

    if (runData.status === "failed") {
      const logsData = await getRunLogs(token, runId);
      setLogs(logsData);
      setReport(null);
      return;
    }

    setReport(null);
    setLogs(null);
  }, [token, runId]);

  useEffect(() => {
    let mounted = true;

    async function loadInitial() {
      try {
        setLoading(true);
        await loadRunBundle();
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

    loadInitial();

    return () => {
      mounted = false;
    };
  }, [loadRunBundle]);

  useEffect(() => {
    if (!runInProgress) {
      return undefined;
    }

    const timer = setInterval(async () => {
      try {
        await loadRunBundle();
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      }
    }, 1500);

    return () => clearInterval(timer);
  }, [runInProgress, loadRunBundle]);

  const handleDelete = async () => {
    if (!runId) {
      return;
    }

    try {
      await deleteRun(token, runId);
      navigate("/runs", { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleRetry = async () => {
    if (!retryApiKey.trim()) {
      return;
    }

    try {
      const retry = await retryRun(token, runId, retryApiKey);
      setRetryApiKey("");
      navigate(`/runs/${retry.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <section className="panel stack">
      <div className="section-header">
        <h2>Run Details</h2>
        <Link className="text-link" to="/runs">
          Back to runs
        </Link>
      </div>

      {loading ? (
        <p>Loading run...</p>
      ) : !run ? (
        <p>Run not found.</p>
      ) : (
        <>
          <div className="status-block">
            <p>Run ID: {run.id}</p>
            <p>Status: {run.status}</p>
            <p>Prompt: {run.prompt}</p>
            <p>Latency: {run.latency_ms ? `${run.latency_ms} ms` : "-"}</p>
            <p>
              Tokens: {run.token_input} in / {run.token_output} out
            </p>
            <p>Estimated Cost: ${run.estimated_cost_usd}</p>
            <p>Score: {formatScore(run.total_score)}</p>
            {run.status === "failed" ? (
              <p className="status-error">
                Failure Reason: {run.error_message || "Unknown error"}
              </p>
            ) : null}
          </div>

          <div className="inline-actions">
            <button type="button" className="danger" onClick={handleDelete}>
              Delete Run
            </button>
          </div>

          <div className="retry-box">
            <label>
              Retry with new API Key
              <input
                type="password"
                value={retryApiKey}
                onChange={(event) => setRetryApiKey(event.target.value)}
                placeholder="Paste key for retry"
              />
            </label>
            <button type="button" disabled={!retryApiKey.trim()} onClick={handleRetry}>
              Retry Run
            </button>
          </div>

          <section>
            <h3>Timeline</h3>
            {!events.length ? (
              <p>No events yet.</p>
            ) : (
              <ul className="events">
                {events.map((item) => (
                  <li key={item.id}>
                    <strong>{item.event_type}</strong>
                    <span>{item.message}</span>
                    {formatPayload(item.payload) ? (
                      <details>
                        <summary>details</summary>
                        <pre>{formatPayload(item.payload)}</pre>
                      </details>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h3>Sandbox Logs</h3>
            {!logs ? (
              <p>Logs appear automatically for failed runs.</p>
            ) : (
              <div className="logs-grid">
                <div>
                  <h4>stderr tail</h4>
                  <pre className="log-box">{logs.stderr_tail || "(empty)"}</pre>
                </div>
                <div>
                  <h4>stdout tail</h4>
                  <pre className="log-box">{logs.stdout_tail || "(empty)"}</pre>
                </div>
              </div>
            )}
          </section>

          <section>
            <h3>Report</h3>
            {!report && run.status !== "failed" ? (
              <p>Report appears when run completes.</p>
            ) : run.status === "failed" ? (
              <p>Run failed before report generation.</p>
            ) : (
              <div className="report">
                <p>Total Score: {formatScore(report.total_score)}</p>
                <p>{report.evaluation_summary}</p>
                <ul>
                  {Object.entries(report.metrics).map(([name, value]) => (
                    <li key={name}>
                      {name}: {formatScore(value)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </>
      )}

      {error ? <p className="error">Error: {error}</p> : null}
    </section>
  );
}
