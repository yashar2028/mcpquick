import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { createRun } from "../api/runsApi";
import { useAuth } from "../context/AuthContext";

export default function NewRunPage() {
  const navigate = useNavigate();
  const { token } = useAuth();

  const [prompt, setPrompt] = useState(
    "Summarize the task and propose a safe 3-step execution plan before running tools."
  );
  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("claude-3-5-sonnet-latest");
  const [apiKey, setApiKey] = useState("");
  const [maxSteps, setMaxSteps] = useState(20);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    try {
      setSubmitting(true);
      const run = await createRun(token, {
        prompt,
        provider,
        model,
        api_key: apiKey,
        max_steps: Number(maxSteps),
        enable_external_mcp: false,
        external_mcp_url: null,
      });
      setApiKey("");
      navigate(`/runs/${run.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="panel">
      <h2>Create New Run</h2>

      <form className="run-form" onSubmit={handleSubmit}>
        <label>
          Prompt
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={6}
            required
          />
        </label>

        <div className="row">
          <label>
            Provider
            <input
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
              required
            />
          </label>

          <label>
            Model
            <input
              value={model}
              onChange={(event) => setModel(event.target.value)}
              required
            />
          </label>

          <label>
            Max Steps
            <input
              type="number"
              min={1}
              max={200}
              value={maxSteps}
              onChange={(event) => setMaxSteps(event.target.value)}
              required
            />
          </label>
        </div>

        <label>
          API Key (session-only)
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="Paste provider key"
            required
          />
        </label>

        <button type="submit" disabled={submitting || !apiKey.trim()}>
          {submitting ? "Submitting..." : "Start Run"}
        </button>
      </form>

      {error ? <p className="error">Error: {error}</p> : null}
    </section>
  );
}
