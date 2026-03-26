import { useEffect, useState } from "react";
import axios from "axios";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";

function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await axios.get("http://localhost:8000/health");
        setHealth(response.data.status);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank" rel="noreferrer">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank" rel="noreferrer">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>YWHealth Integration Platform</h1>
      <div className="card">
        <h2>Backend Status</h2>
        {loading ? (
          <p>🔄 Checking backend health...</p>
        ) : health ? (
          <div style={{ color: "green" }}>
            Backend health: <strong>{health}</strong>
          </div>
        ) : (
          <div style={{ color: "red" }}>
            Backend error: <strong>{error}</strong>
          </div>
        )}
      </div>
      <p className="read-the-docs">
        Backend: http://localhost:8000 | Frontend: http://localhost:5173
      </p>
    </>
  );
}

export default App;