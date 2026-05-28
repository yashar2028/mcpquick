import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function HomePage() {
  const { user } = useAuth();

  return (
    <section className="home-stack">
      <section className="hero-split">
        <div className="hero-copy stagger">
          <p className="eyebrow">MCP Quick</p>
          <h1>Run agent evaluations in a sandboxed MCP stack.</h1>
          <p className="muted">
            Launch structured runs, compare provider behavior, and keep every
            trace reproducible without retooling your backend.
          </p>
          <div className="hero-actions">
            <Link className="primary-link" to={user ? "/runs/new" : "/auth"}>
              {user ? "Start a run" : "Sign in to start"}
            </Link>
            <Link className="ghost-link" to="/about">
              How it works
            </Link>
          </div>
          <div className="hero-metrics">
            <div className="metric-card">
              <span>Sandboxed runs</span>
              <strong>Isolated + repeatable</strong>
            </div>
            <div className="metric-card">
              <span>Provider coverage</span>
              <strong>OpenAI, Anthropic</strong>
            </div>
          </div>
        </div>
        <div className="hero-panel">
          <div className="hero-panel-inner">
            <h3>What teams ship faster</h3>
            <ul className="checklist">
              <li>Run prompts across providers with consistent constraints.</li>
              <li>Attach MCP servers for tool-augmented evaluations.</li>
              <li>Review scores, reports, and trace timelines.</li>
              <li>Track reliability trends across runs.</li>
            </ul>
            <div className="hero-panel-footer">
              <span className="status-pill">Live dashboards</span>
              <span className="status-pill">Run retries</span>
            </div>
          </div>
        </div>
      </section>

      <section className="logo-row">
        <span className="muted">Built for teams shipping MCP-ready agents</span>
        <div className="logo-pill">Sandboxed</div>
        <div className="logo-pill">Traceable</div>
        <div className="logo-pill">Repeatable</div>
        <div className="logo-pill">Auditable</div>
      </section>

      <section className="feature-grid">
        <article className="feature-card">
          <h3>Provider control</h3>
          <p>
            Route prompts across models with a single run spec, then compare
            latency, cost, and reliability.
          </p>
        </article>
        <article className="feature-card">
          <h3>MCP-ready pipelines</h3>
          <p>
            Attach MCP repos or streamable endpoints, then keep tool calling
            policy consistent across runs.
          </p>
        </article>
        <article className="feature-card">
          <h3>Execution clarity</h3>
          <p>
            Inspect run timelines, logs, and scoring breakdowns without digging
            through raw sandbox output.
          </p>
        </article>
      </section>

      <section className="panel workflow-panel">
        <div className="section-header">
          <h2>User guide</h2>
          <Link className="text-link" to="/resources">
            Resources
          </Link>
        </div>
        <div className="step-grid">
          <div className="step-card">
            <span className="step-index">01</span>
            <h3>Configure the run</h3>
            <p>
              Pick provider, model, and steps. Add a session API key for the
              sandbox.
            </p>
          </div>
          <div className="step-card">
            <span className="step-index">02</span>
            <h3>Attach MCP servers</h3>
            <p>
              Connect MCP repos or endpoints, then define the prompt and
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
      </section>

      <section className="spotlight">
        <div>
          <h2>Make every run explain itself.</h2>
          <p className="muted">
            MCP Quick preserves run context, tool traces, and scoring so the next
            iteration is guided by data instead of guesswork.
          </p>
          <div className="inline-actions">
            <Link className="text-link" to="/runs">
              View run history
            </Link>
            <Link className="text-link" to="/faq">
              Read the FAQ
            </Link>
          </div>
        </div>
        <div className="spotlight-card">
          <h3>Quick links</h3>
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
              <Link to="/contact">Contact support</Link>
              <p>Talk to the MCP Quick team about onboarding.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="cta-band">
        <div>
          <h2>Ready to launch your first MCP run?</h2>
          <p className="muted">
            Start with a single prompt and expand into multi-tool evaluations.
          </p>
        </div>
        <Link className="primary-link" to={user ? "/runs/new" : "/auth"}>
          {user ? "Create a run" : "Sign in"}
        </Link>
      </section>
    </section>
  );
}
