import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="shell">
      <section className="panel">
        <h2>Page Not Found</h2>
        <p>The page you requested does not exist.</p>
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
