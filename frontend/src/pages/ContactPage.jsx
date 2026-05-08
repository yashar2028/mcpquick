export default function ContactPage() {
  return (
    <section className="stack">
      <article className="panel">
        <h2>Contact</h2>
        <p className="muted">
          Reach out for onboarding, access requests, or MCP troubleshooting.
        </p>
        <div className="contact-grid">
          <div className="info-card">
            <h3>Support</h3>
            <p>support@mcpquick.local</p>
          </div>
          <div className="info-card">
            <h3>Product feedback</h3>
            <p>product@mcpquick.local</p>
          </div>
        </div>
      </article>
    </section>
  );
}
