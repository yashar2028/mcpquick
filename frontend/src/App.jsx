import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function formatScore(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${Math.round(value * 100)} / 100`;
}

function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  const [prompt, setPrompt] = useState(
    "Summarize the task and propose a safe 3-step execution plan before running tools."
  );
  const [provider, setProvider] = useState("claude");
  const [model, setModel] = useState("claude-sonnet");
  const [apiKey, setApiKey] = useState("");
  const [maxSteps, setMaxSteps] = useState(20);
  const [submitting, setSubmitting] = useState(false);

  const [run, setRun] = useState(null);
  const [events, setEvents] = useState([]);
  const [report, setReport] = useState(null);

  const runInProgress = useMemo(() => {
    if (!run) {
      return false;
    }
    return run.status === "queued" || run.status === "running";
  }, [run]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/health`);
        setHealth(response.data.status);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingHealth(false);
      }
    };

    checkHealth();
  }, []);

  useEffect(() => {
    if (!run || !runInProgress) {
      return undefined;
    }

    const interval = setInterval(async () => {
      try {
        const [runResponse, eventsResponse] = await Promise.all([
          axios.get(`${API_BASE_URL}/v1/runs/${run.id}`),
          axios.get(`${API_BASE_URL}/v1/runs/${run.id}/events`, {
            params: { limit: 250 },
          }),
        ]);
        setRun(runResponse.data);
        setEvents(eventsResponse.data);

        if (runResponse.data.status === "completed") {
          const reportResponse = await axios.get(
            `${API_BASE_URL}/v1/runs/${run.id}/report`
          );
          setReport(reportResponse.data);
        }
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      }
    }, 1300);

    return () => clearInterval(interval);
  }, [run, runInProgress]);

  const handleSubmitRun = async (event) => {
    event.preventDefault();
    setError(null);
    setReport(null);
    setEvents([]);

    try {
      setSubmitting(true);
      const response = await axios.post(`${API_BASE_URL}/v1/runs`, {
        prompt,
        provider,
        model,
        api_key: apiKey,
        max_steps: Number(maxSteps),
        enable_external_mcp: false,
        external_mcp_url: null,
      });

      setRun(response.data);
      setApiKey("");
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="shell">
      <header className="hero">
        <p className="eyebrow">MCP Quick</p>
        <h1>LLM Evaluation Sandbox</h1>
        <p>
          Submit a run, track event-level logs, and inspect weighted scoring in one view.
        </p>
      </header>

      <section className="panel">
        <h2>Platform Health</h2>
        {loadingHealth ? <p>Checking backend...</p> : <p>Status: {health || "unreachable"}</p>}
      </section>

      <section className="panel">
        <h2>Run Prompt</h2>
        <form className="run-form" onSubmit={handleSubmitRun}>
          <label>
            Prompt
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={6}
              required
            />
          </label>

          <div className="row">
            <label>
              Provider
              <input value={provider} onChange={(e) => setProvider(e.target.value)} required />
            </label>

            <label>
              Model
              <input value={model} onChange={(e) => setModel(e.target.value)} required />
            </label>

            <label>
              Max Steps
              <input
                type="number"
                min={1}
                max={200}
                value={maxSteps}
                onChange={(e) => setMaxSteps(e.target.value)}
                required
              />
            </label>
          </div>

          <label>
            API Key (session-only)
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="paste provider key"
              required
            />
          </label>

          <button type="submit" disabled={submitting || !apiKey.trim()}>
            {submitting ? "Submitting..." : "Start Run"}
          </button>
        </form>
      </section>

      <section className="grid">
        <article className="panel">
          <h2>Run Status</h2>
          {!run ? (
            <p>No run submitted yet.</p>
          ) : (
            <div className="status-block">
              <p>Run ID: {run.id}</p>
              <p>Status: {run.status}</p>
              <p>Sandbox: {run.sandbox_profile}</p>
              <p>Latency: {run.latency_ms ? `${run.latency_ms} ms` : "-"}</p>
              <p>
                Tokens: {run.token_input} in / {run.token_output} out
              </p>
              <p>Estimated Cost: ${run.estimated_cost_usd}</p>
              <p>Score: {formatScore(run.total_score)}</p>
            </div>
          )}
        </article>

        <article className="panel">
          <h2>Execution Timeline</h2>
          {!events.length ? (
            <p>No events yet.</p>
          ) : (
            <ul className="events">
              {events.map((item) => (
                <li key={item.id}>
                  <strong>{item.event_type}</strong>
                  <span>{item.message}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>

      <section className="panel">
        <h2>Final Report</h2>
        {!report ? (
          <p>Report will appear when run completes.</p>
        ) : (
          <div className="report">
            <p>Total Score: {formatScore(report.total_score)}</p>
            <p>{report.evaluation_summary}</p>
            <h3>Metrics</h3>
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

      {error ? <p className="error">Error: {error}</p> : null}
    </main>
  );
}

export default App;