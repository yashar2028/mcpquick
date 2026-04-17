import { useAuth } from "../context/AuthContext";
import { formatDateTime } from "../utils/formatters";

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <section className="panel">
      <h2>Profile</h2>
      <div className="status-block">
        <p>User ID: {user?.id}</p>
        <p>Email: {user?.email}</p>
        <p>Full Name: {user?.full_name || "-"}</p>
        <p>Joined At: {formatDateTime(user?.created_at)}</p>
      </div>
    </section>
  );
}
