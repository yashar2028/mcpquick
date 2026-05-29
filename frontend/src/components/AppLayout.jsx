import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BookOpen,
  History,
  LayoutDashboard,
  PlusCircle,
  User,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { useBackendHealth } from "../hooks/useBackendHealth";

const getRouteTitle = (path) => {
  if (path === "/dashboard") return "Dashboard";
  if (path === "/runs/new") return "New Run";
  if (path === "/runs") return "Run History";
  if (path.startsWith("/runs/")) return "Run Details";
  if (path === "/profile") return "Profile";
  if (path === "/resources") return "Resources";
  return "Workspace";
};

export default function AppLayout() {
  const health = useBackendHealth();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const displayName = user?.full_name || user?.email || "User";
  const initial = displayName.trim().charAt(0).toUpperCase() || "U";
  const routeTitle = getRouteTitle(location.pathname);

  const handleLogout = () => {
    signOut();
    navigate("/auth", { replace: true });
  };

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <p className="brand-name">MCP Quick</p>
            <span className="brand-subtitle">Agent console</span>
          </div>
        </div>

        <NavLink className="primary-link" to="/runs/new">
          <PlusCircle size={16} aria-hidden />
          New run
        </NavLink>

        <nav className="sidebar-nav">
          <div className="nav-section">
            <p className="nav-label">Main</p>
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">
                <LayoutDashboard size={16} aria-hidden />
              </span>
              <span>Dashboard</span>
            </NavLink>
          </div>

          <div className="nav-section">
            <p className="nav-label">Runs</p>
            <NavLink
              to="/runs/new"
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">
                <PlusCircle size={16} aria-hidden />
              </span>
              <span>New Run</span>
            </NavLink>
            <NavLink
              to="/runs"
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">
                <History size={16} aria-hidden />
              </span>
              <span>Run History</span>
            </NavLink>
          </div>

          <div className="nav-section">
            <p className="nav-label">Account</p>
            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">
                <User size={16} aria-hidden />
              </span>
              <span>Profile</span>
            </NavLink>
            <NavLink
              to="/resources"
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">
                <BookOpen size={16} aria-hidden />
              </span>
              <span>Resources</span>
            </NavLink>
          </div>
        </nav>

        <div className="sidebar-foot">
          <span className="status-pill">Backend: {health}</span>
          <span className="muted">Status updates every 10s</span>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div>
            <h1 className="topbar-title">{routeTitle}</h1>
            <p className="topbar-sub">Welcome back, {displayName}</p>
          </div>
          <div className="topbar-actions">
            <div className="user-pill">
              <span className="user-initial">{initial}</span>
              <span className="user-name">{displayName}</span>
            </div>
            <button type="button" className="danger ghost" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </header>

        <div className="app-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
