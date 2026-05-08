import { Link } from "react-router-dom";

export default function ResourcesPage() {
  return (
    <section className="stack">
      <article className="panel resource-hero">
        <div>
          <p className="eyebrow">Resources</p>
          <h2>Everything you need to orchestrate MCP evaluations.</h2>
          <p className="muted">
            Curated links and guides to keep your MCP Quick workflow moving.
          </p>
        </div>
        <div className="resource-card">
          <h3>Getting started</h3>
          <p>
            Review the step-by-step guide, then jump into your first evaluation.
          </p>
          <Link className="text-link" to="/">
            Open the guide
          </Link>
        </div>
      </article>

      <div className="resource-grid">
        <div className="link-card">
          <a
            href="https://registry.modelcontextprotocol.io/"
            target="_blank"
            rel="noreferrer"
          >
            MCP Registry
          </a>
          <p>Browse MCP servers, tool specs, and transports.</p>
        </div>
        <div className="link-card">
          <Link to="/faq">FAQ</Link>
          <p>Common questions about runs, scoring, and MCP support.</p>
        </div>
        <div className="link-card">
          <Link to="/contact">Contact support</Link>
          <p>Reach the team for workflow help and integrations.</p>
        </div>
        <div className="link-card">
          <Link to="/runs">Run history</Link>
          <p>Inspect completed evaluations and rerun experiments.</p>
        </div>
      </div>
    </section>
  );
}
