import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useBackendHealth } from "../hooks/useBackendHealth";

export default function AppLayout() {
  const health = useBackendHealth();
  const navigate = useNavigate();
  const { user, signOut } = useAuth();

  const handleLogout = () => {
    signOut();
    navigate("/auth", { replace: true });
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">MCP Quick Platform</p>
          <h1>Welcome back, {user?.full_name || user?.email}</h1>
        </div>
        <div className="topbar-actions">
          <span className="status-pill">Backend: {health}</span>
          <button type="button" className="danger ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <nav className="main-nav">
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/runs/new">New Run</NavLink>
        <NavLink to="/runs">Run History</NavLink>
        <NavLink to="/profile">Profile</NavLink>
      </nav>

      <Outlet />
    </main>
  );
}
