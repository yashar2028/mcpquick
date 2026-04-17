import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="shell">
      <section className="panel">
        <h2>Page Not Found</h2>
        <p>The page you requested does not exist.</p>
        <Link className="text-link" to="/dashboard">
          Go to dashboard
        </Link>
      </section>
    </main>
  );
}
