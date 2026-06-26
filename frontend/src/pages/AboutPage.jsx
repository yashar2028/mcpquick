import { Link } from "react-router-dom";

export default function AboutPage() {
  return (
    <section className="stack">
      <section className="panel about-hero">
        <div>
          <p className="eyebrow">About MCP Quick</p>
          <h2>Evaluation infrastructure built for MCP-first agents.</h2>
          <p>
            MCP Quick runs LLM models inside a nix sandbox while integrating MCP
            servers. It helps teams compare providers, validate reliability, and
            inspect detailed reports without changing their backend workflows.
          </p>
          <p className="muted">
            Standardize prompts, measure runtime performance, and keep a full
            audit trail of every run.
          </p>
          <Link className="text-link" to="/faq">
            Read the FAQ
          </Link>
        </div>
        <div className="about-card">
          <h3>At a glance</h3>
          <ul className="checklist">
            <li>Sandboxed execution with repeatable configs.</li>
            <li>MCP repo or streamable endpoint support.</li>
            <li>Scorecards with trace visibility.</li>
            <li>Provider and model comparisons over time.</li>
          </ul>
        </div>
      </section>

      <section className="feature-grid">
        <article className="feature-card">
          <h3>Reliable baselines</h3>
          <p>
            Keep evaluations steady with consistent prompts, step limits, and
            policy settings across every run.
          </p>
        </article>
        <article className="feature-card">
          <h3>Traceable pipelines</h3>
          <p>
            Capture tool calls, event timelines, and sandbox output to debug
            failures faster.
          </p>
        </article>
        <article className="feature-card">
          <h3>Operational clarity</h3>
          <p>
            Compare providers and models with metrics that highlight cost,
            latency, and reliability.
          </p>
        </article>
      </section>
    </section>
  );
}
