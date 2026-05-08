import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const navLinks = [
  { to: "/", label: "Home", end: true, icon: "H" },
  { to: "/about", label: "About", icon: "A" },
  { to: "/resources", label: "Resources", icon: "R" },
  { to: "/faq", label: "FAQ", icon: "F" },
  { to: "/contact", label: "Contact", icon: "C" },
];

const getPublicTitle = (path) => {
  if (path === "/") return "Home Guide";
  if (path === "/about") return "About";
  if (path === "/resources") return "Resources";
  if (path === "/faq") return "FAQ";
  if (path === "/contact") return "Contact";
  return "Welcome";
};

export default function PublicLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const pageTitle = getPublicTitle(location.pathname);
  const showIntro = location.pathname !== "/";

  return (
    <div className="public-shell">
      <header className="site-header">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <p className="brand-name">MCP Quick</p>
            <span className="brand-subtitle">Sandboxed agent runs</span>
          </div>
        </div>

        <nav className="site-nav">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `site-nav-link${isActive ? " active" : ""}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="site-actions">
          <a
            className="ghost-link"
            href="https://registry.modelcontextprotocol.io/"
            target="_blank"
            rel="noreferrer"
          >
            MCP Registry
          </a>
          <NavLink className="primary-link" to={user ? "/dashboard" : "/auth"}>
            {user ? "Open console" : "Sign in"}
          </NavLink>
        </div>
      </header>

      {showIntro ? (
        <section className="page-hero">
          <div>
            <p className="eyebrow">MCP Quick</p>
            <h1>{pageTitle}</h1>
            <p className="muted">
              A fast path to launch, score, and compare MCP-enabled agent runs.
            </p>
          </div>
          <div className="page-hero-card">
            <p>Need access?</p>
            <h3>Get to a run in minutes.</h3>
            <NavLink className="primary-link" to={user ? "/dashboard" : "/auth"}>
              {user ? "Go to dashboard" : "Create an account"}
            </NavLink>
          </div>
        </section>
      ) : null}

      <main className="public-main">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div>
          <p>Sandboxed evals for MCP-ready teams.</p>
          <span className="muted">Built for repeatable, safe experiments.</span>
        </div>
        <div className="footer-links">
          <a
            className="text-link"
            href="https://registry.modelcontextprotocol.io/"
            target="_blank"
            rel="noreferrer"
          >
            MCP Registry
          </a>
          <NavLink className="text-link" to="/contact">
            Contact
          </NavLink>
        </div>
      </footer>
    </div>
  );
}
