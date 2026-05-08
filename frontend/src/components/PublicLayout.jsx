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

  return (
    <div className="app-shell public-shell">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <p className="brand-name">MCP Quick</p>
            <span className="brand-subtitle">Public guide</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">
            <p className="nav-label">Explore</p>
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `nav-link${isActive ? " active" : ""}`
                }
              >
                <span className="nav-icon">{link.icon}</span>
                <span>{link.label}</span>
              </NavLink>
            ))}
          </div>
        </nav>

        <div className="sidebar-foot">
          <a
            className="text-link"
            href="https://registry.modelcontextprotocol.io/"
            target="_blank"
            rel="noreferrer"
          >
            MCP Registry
          </a>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div>
            <h1 className="topbar-title">{pageTitle}</h1>
            <p className="topbar-sub">
              A minimal guide to MCP-enabled evaluation workflows.
            </p>
          </div>
          <div className="topbar-actions">
            <NavLink className="primary-link" to={user ? "/dashboard" : "/auth"}>
              {user ? "Go to dashboard" : "Sign in"}
            </NavLink>
          </div>
        </header>

        <Outlet />

        <footer className="public-footer">
          <span>Sandboxed evals for MCP-enabled agents.</span>
          <a
            className="text-link"
            href="https://registry.modelcontextprotocol.io/"
            target="_blank"
            rel="noreferrer"
          >
            MCP Registry
          </a>
        </footer>
      </div>
    </div>
  );
}
