import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listRuns } from "../api/runsApi";
import { HISTORY_PAGE_SIZE } from "../constants";
import { useAuth } from "../context/AuthContext";
import { formatDateTime } from "../utils/formatters";

export default function RunsPage() {
  const { token } = useAuth();

  const [historyProvider, setHistoryProvider] = useState("");
  const [historyStatus, setHistoryStatus] = useState("");
  const [historySearch, setHistorySearch] = useState("");
  const [historyFromDate, setHistoryFromDate] = useState("");
  const [historyToDate, setHistoryToDate] = useState("");
  const [historyOffset, setHistoryOffset] = useState(0);

  const [runs, setRuns] = useState([]);
  const [runsTotal, setRunsTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadRuns() {
      setLoading(true);
      setError(null);
      try {
        const response = await listRuns(token, {
          limit: HISTORY_PAGE_SIZE,
          offset: historyOffset,
          provider: historyProvider || undefined,
          status: historyStatus || undefined,
          search: historySearch || undefined,
          created_after: historyFromDate || undefined,
          created_before: historyToDate || undefined,
        });

        if (mounted) {
          setRuns(response.items || []);
          setRunsTotal(response.total || 0);
        }
      } catch (err) {
        if (mounted) {
          setError(err.response?.data?.detail || err.message);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadRuns();

    return () => {
      mounted = false;
    };
  }, [
    token,
    historyOffset,
    historyProvider,
    historyStatus,
    historySearch,
    historyFromDate,
    historyToDate,
  ]);

  const totalPages = Math.max(1, Math.ceil(runsTotal / HISTORY_PAGE_SIZE));
  const currentPage = Math.floor(historyOffset / HISTORY_PAGE_SIZE) + 1;

  const resetOffset = () => setHistoryOffset(0);

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Run History</h2>
        <Link className="text-link" to="/runs/new">
          Create New Run
        </Link>
      </div>

      <div className="filters">
        <input
          placeholder="Search prompt"
          value={historySearch}
          onChange={(event) => {
            setHistorySearch(event.target.value);
            resetOffset();
          }}
        />
        <input
          placeholder="Provider"
          value={historyProvider}
          onChange={(event) => {
            setHistoryProvider(event.target.value);
            resetOffset();
          }}
        />
        <select
          value={historyStatus}
          onChange={(event) => {
            setHistoryStatus(event.target.value);
            resetOffset();
          }}
        >
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <input
          type="date"
          value={historyFromDate}
          onChange={(event) => {
            setHistoryFromDate(event.target.value);
            resetOffset();
          }}
        />
        <input
          type="date"
          value={historyToDate}
          onChange={(event) => {
            setHistoryToDate(event.target.value);
            resetOffset();
          }}
        />
      </div>

      {loading ? (
        <p>Loading runs...</p>
      ) : error ? (
        <p className="error">Error: {error}</p>
      ) : !runs.length ? (
        <p>No runs found.</p>
      ) : (
        <ul className="run-list">
          {runs.map((item) => (
            <li key={item.id}>
              <Link to={`/runs/${item.id}`} className="run-list-link">
                <strong>{item.provider}</strong>
                <span>{item.model}</span>
                <span>{item.status}</span>
                <span>{formatDateTime(item.created_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <div className="pagination">
        <button
          type="button"
          disabled={historyOffset === 0}
          onClick={() => setHistoryOffset((prev) => Math.max(0, prev - HISTORY_PAGE_SIZE))}
        >
          Previous
        </button>
        <span>
          Page {currentPage} / {totalPages}
        </span>
        <button
          type="button"
          disabled={historyOffset + HISTORY_PAGE_SIZE >= runsTotal}
          onClick={() => setHistoryOffset((prev) => prev + HISTORY_PAGE_SIZE)}
        >
          Next
        </button>
      </div>
    </section>
  );
}
