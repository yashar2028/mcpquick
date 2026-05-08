import { Link } from "react-router-dom";

export default function ResourcesPage() {
  return (
    <section className="stack">
      <article className="panel">
        <h2>Resources</h2>
        <p className="muted">
          Helpful links and references to support your MCP Quick workflow.
        </p>
      </article>

      <div className="link-list">
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
          <Link to="/">Home guide</Link>
          <p>Step-by-step overview of the evaluation workflow.</p>
        </div>
        <div className="link-card">
          <Link to="/faq">FAQ</Link>
          <p>Common questions about runs, scoring, and MCP support.</p>
        </div>
        <div className="link-card">
          <Link to="/contact">Contact support</Link>
          <p>Reach the team for workflow help and integrations.</p>
        </div>
      </div>
    </section>
  );
}
