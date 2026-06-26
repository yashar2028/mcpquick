export default function ContactPage() {
  return (
    <section className="stack">
      <article className="panel contact-hero">
        <div>
          <p className="eyebrow">Contact</p>
          <h2>Talk to the MCP Quick team.</h2>
          <p className="muted">
            Reach out for onboarding, access requests, or MCP troubleshooting.
          </p>
        </div>
        <div className="contact-card">
          <h3>Response time</h3>
          <p>Weekdays, 9am to 5pm PT</p>
          <span className="status-pill">Support SLA: 24h</span>
        </div>
      </article>
      <div className="contact-grid">
        <div className="info-card">
          <h3>Support</h3>
          <p>yashar.najafi@stud.th-deg.de</p>
        </div>
        <div className="info-card">
          <h3>Product feedback</h3>
          <p>yashar.najafi@stud.th-deg.de</p>
        </div>
        <div className="info-card">
          <h3>Partnerships</h3>
          <p>yashar.najafi@stud.th-deg.de</p>
        </div>
        <div className="info-card">
          <h3>Security</h3>
          <p>yashar.najafi@stud.th-deg.de</p>
        </div>
      </div>
    </section>
  );
}
