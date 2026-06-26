import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="shell">
      <section className="panel not-found">
        <p className="eyebrow">404</p>
        <h2>Page not found</h2>
        <p className="muted">The page you requested does not exist.</p>
        <div className="inline-actions">
          <Link className="text-link" to="/">
            Back to home
          </Link>
          <Link className="text-link" to="/resources">
            Resources
          </Link>
        </div>
      </section>
    </main>
  );
}
