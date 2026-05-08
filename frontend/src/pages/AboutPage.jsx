import { Link } from "react-router-dom";

export default function AboutPage() {
  return (
    <section className="stack">
      <article className="panel">
        <h2>About MCP Quick</h2>
        <p>
          MCP Quick is an agent evaluation platform designed to run LLM models
          inside a nix sandbox while integrating MCP servers. It helps teams
          compare providers, validate reliability, and inspect detailed reports
          without changing their backend workflows.
        </p>
        <p className="muted">
          Use it to standardize prompts, measure runtime performance, and keep a
          full audit trail of every run.
        </p>
      </article>

      <section className="grid two-col">
        <article className="panel">
          <h3>Core capabilities</h3>
          <ul className="checklist">
            <li>Prompt-based evaluations with configurable step limits.</li>
            <li>External MCP servers with repo-based configuration.</li>
            <li>Detailed run reports and sandbox logs.</li>
            <li>Provider and model comparisons over time.</li>
          </ul>
        </article>
        <article className="panel">
          <h3>Why it matters</h3>
          <p>
            Consistent evaluation helps you choose the right model, find
            regressions early, and keep production agents reliable.
          </p>
          <Link className="text-link" to="/faq">
            Read the FAQ
          </Link>
        </article>
      </section>
    </section>
  );
}
