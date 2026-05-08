import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function HomePage() {
  const { user } = useAuth();

  return (
    <section className="stack">
      <article className="panel hero">
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Home Guide</p>
            <h2>Benchmark LLM agents in a nix sandbox with MCP.</h2>
            <p className="muted">
              Run structured evaluations, compare provider performance, and
              inspect sandboxed traces without changing your backend setup.
            </p>
            <div className="hero-actions">
              <Link className="primary-link" to={user ? "/runs/new" : "/auth"}>
                {user ? "Start a run" : "Sign in to start"}
              </Link>
              <Link className="text-link" to="/about">
                How it works
              </Link>
            </div>
          </div>
          <div className="hero-card">
            <h3>What you can do</h3>
            <ul className="checklist">
              <li>Run prompts across providers with consistent constraints.</li>
              <li>Attach MCP servers for tool-augmented evaluations.</li>
              <li>Review scores, reports, and trace timelines.</li>
              <li>Track reliability trends across runs.</li>
            </ul>
          </div>
        </div>
      </article>

      <article className="panel">
        <div className="section-header">
          <h2>User Guide</h2>
          <Link className="text-link" to="/resources">
            Resources
          </Link>
        </div>
        <div className="guide-steps">
          <div className="step-card">
            <span className="step-index">01</span>
            <h3>Configure the run</h3>
            <p>
              Choose provider, model, and max steps. Add your API key for this
              session.
            </p>
          </div>
          <div className="step-card">
            <span className="step-index">02</span>
            <h3>Attach MCP servers</h3>
            <p>
              Add MCP repos or streamable endpoints, then define the prompt and
              safeguards.
            </p>
          </div>
          <div className="step-card">
            <span className="step-index">03</span>
            <h3>Review the report</h3>
            <p>
              Inspect scores, latency, and logs to understand quality and
              failures.
            </p>
          </div>
        </div>
      </article>

      <section className="grid two-col info-grid">
        <article className="panel info-card">
          <h3>Sandboxed execution</h3>
          <p>
            Runs execute inside a nix-based sandbox to keep evaluations isolated
            and reproducible.
          </p>
        </article>
        <article className="panel info-card">
          <h3>Actionable scoring</h3>
          <p>
            Reports include a consolidated score plus metric breakdowns for
            quick comparisons.
          </p>
        </article>
        <article className="panel info-card">
          <h3>Provider tracking</h3>
          <p>
            Compare provider and model performance across your run history with
            consistent baselines.
          </p>
        </article>
        <article className="panel info-card">
          <h3>MCP registry access</h3>
          <p>
            Browse MCP servers and choose the right integrations for each
            evaluation.
          </p>
        </article>
      </section>

      <article className="panel">
        <h2>Quick Links</h2>
        <div className="link-list">
          <div className="link-card">
            <a
              href="https://registry.modelcontextprotocol.io/"
              target="_blank"
              rel="noreferrer"
            >
              MCP Registry
            </a>
            <p>Browse MCP servers, tools, and transports.</p>
          </div>
          <div className="link-card">
            <Link to="/runs">Run history</Link>
            <p>Review past evaluations and retry runs.</p>
          </div>
          <div className="link-card">
            <Link to="/faq">FAQ</Link>
            <p>Answers to common workflow questions.</p>
          </div>
        </div>
      </article>
    </section>
  );
}
