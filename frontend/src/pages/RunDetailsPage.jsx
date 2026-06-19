import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  deleteRun,
  getRun,
  getRunEvents,
  getRunInstructionFile,
  getRunLogs,
  getRunReport,
  retryRun,
} from "../api/runsApi";
import { useAuth } from "../context/AuthContext";
import { formatFileSize, formatPayload, formatScore } from "../utils/formatters";

export default function RunDetailsPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();

  const [run, setRun] = useState(null);
  const [events, setEvents] = useState([]);
  const [report, setReport] = useState(null);
  const [logs, setLogs] = useState(null);
  const [instructionFileContents, setInstructionFileContents] = useState({});
  const [visibleInstructionFileIds, setVisibleInstructionFileIds] = useState([]);
  const [loadingInstructionFileId, setLoadingInstructionFileId] = useState(null);
  const [retryApiKey, setRetryApiKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const runInProgress = useMemo(() => {
    if (!run) {
      return false;
    }
    return run.status === "queued" || run.status === "running";
  }, [run]);

  const loadRunBundle = useCallback(async () => {
    if (!runId) {
      return;
    }

    setError(null);

    const [runData, eventsData] = await Promise.all([
      getRun(token, runId),
      getRunEvents(token, runId, 250),
    ]);

    setRun(runData);
    setEvents(eventsData);

    if (runData.status === "completed") {
      const reportData = await getRunReport(token, runId);
      setReport(reportData);
      setLogs(null);
      return;
    }

    if (runData.status === "failed") {
      const logsData = await getRunLogs(token, runId);
      setLogs(logsData);
      setReport(null);
      return;
    }

    setReport(null);
    setLogs(null);
  }, [token, runId]);

  useEffect(() => {
    let mounted = true;

    async function loadInitial() {
      try {
        setLoading(true);
        await loadRunBundle();
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

    loadInitial();

    return () => {
      mounted = false;
    };
  }, [loadRunBundle]);

  useEffect(() => {
    if (!runInProgress) {
      return undefined;
    }

    const timer = setInterval(async () => {
      try {
        await loadRunBundle();
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      }
    }, 1500);

    return () => clearInterval(timer);
  }, [runInProgress, loadRunBundle]);

  useEffect(() => {
    setInstructionFileContents({});
    setVisibleInstructionFileIds([]);
    setLoadingInstructionFileId(null);
  }, [runId]);

  const handleDelete = async () => {
    if (!runId) {
      return;
    }

    try {
      await deleteRun(token, runId);
      navigate("/runs", { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleRetry = async () => {
    if (!retryApiKey.trim()) {
      return;
    }

    try {
      const retry = await retryRun(token, runId, retryApiKey);
      setRetryApiKey("");
      navigate(`/runs/${retry.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const toggleInstructionFileContent = async (fileId) => {
    if (!runId) {
      return;
    }

    if (visibleInstructionFileIds.includes(fileId)) {
      setVisibleInstructionFileIds((current) =>
        current.filter((item) => item !== fileId)
      );
      return;
    }

    if (!instructionFileContents[fileId]) {
      try {
        setLoadingInstructionFileId(fileId);
        const contentResponse = await getRunInstructionFile(token, runId, fileId);
        setInstructionFileContents((current) => ({
          ...current,
          [fileId]: contentResponse,
        }));
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
        return;
      } finally {
        setLoadingInstructionFileId(null);
      }
    }

    setVisibleInstructionFileIds((current) => [...current, fileId]);
  };

  const parseJudgeReport = (reportValue) => {
    const extractRaw = (value) => {
      if (typeof value === "string") {
        return value.trim();
      }
      if (value && typeof value === "object") {
        if (typeof value.raw === "string") {
          return value.raw.trim();
        }
        if (typeof value.text === "string") {
          return value.text.trim();
        }
      }
      return "";
    };

    if (!reportValue) {
      return null;
    }

    if (reportValue && typeof reportValue === "object") {
      const hasStructuredFields =
        "achieved" in reportValue ||
        "summary" in reportValue ||
        "tools_used" in reportValue ||
        "notes" in reportValue;
      if (hasStructuredFields) {
        return reportValue;
      }
    }

    const raw = extractRaw(reportValue);
    if (!raw) {
      return reportValue;
    }

    const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
    const candidate = fenceMatch ? fenceMatch[1] : raw;
    const start = candidate.indexOf("{");
    const end = candidate.lastIndexOf("}");
    const jsonText = start >= 0 && end > start ? candidate.slice(start, end + 1) : candidate;

    try {
      const parsed = JSON.parse(jsonText);
      if (parsed && typeof parsed === "object") {
        return parsed;
      }
    } catch (err) {
      return reportValue;
    }

    return reportValue;
  };

  return (
    <section className="panel stack">
      <div className="section-header">
        <h2>Run Details</h2>
        <Link className="text-link" to="/runs">
          Back to runs
        </Link>
      </div>

      {loading ? (
        <p>Loading run...</p>
      ) : !run ? (
        <p>Run not found.</p>
      ) : (
        <>
          <div className="status-block">
            <p>Run ID: {run.id}</p>
            <p>Status: {run.status}</p>
            <p>Prompt: {run.prompt}</p>
            <p>Latency: {run.latency_ms ? `${run.latency_ms} ms` : "-"}</p>
            <p>
              Tokens: {run.token_input} in / {run.token_output} out
            </p>
            <p>Estimated Cost: ${run.estimated_cost_usd}</p>
            <p>Score: {formatScore(run.total_score)}</p>
            {run.external_mcp_enabled ? (
              <>
                {(() => {
                  const repos = Array.isArray(run.mcp_config?.repos)
                    ? run.mcp_config.repos
                    : run.requested_external_mcp_url
                    ? [
                        {
                          repo_url: run.requested_external_mcp_url,
                          server_path: run.mcp_config?.server_path || "server.json",
                        },
                      ]
                    : [];

                  return repos.length ? (
                    <div className="stack">
                      {repos.map((repo, index) => (
                        <div key={`mcp-repo-${index}`}>
                          {repo.server_json ? (
                            <>
                              <p>MCP Repo: inline server.json</p>
                              <p>
                                MCP server.json: inline
                                {typeof repo.server_json?.name === "string"
                                  ? ` (${repo.server_json.name})`
                                  : ""}
                              </p>
                            </>
                          ) : (
                            <>
                              <p>MCP Repo: {repo.repo_url}</p>
                              <p>
                                MCP server.json: {repo.server_path || "server.json"}
                              </p>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p>MCP Repo: -</p>
                  );
                })()}
                <p>
                  MCP failure policy: {run.mcp_config?.failure_policy || "fail"}
                </p>
              </>
            ) : null}
            {Array.isArray(run.instruction_files) && run.instruction_files.length ? (
              <div className="stack">
                <p>
                  Instruction files used during execution: {run.instruction_files.length}
                  {" "}
                  ({formatFileSize(
                    run.instruction_files.reduce(
                      (acc, file) => acc + Number(file.size_bytes || 0),
                      0
                    )
                  )}
                  )
                </p>
                <ul className="instruction-file-list">
                  {run.instruction_files
                    .slice()
                    .sort((a, b) => a.upload_order - b.upload_order)
                    .map((file) => {
                      const isVisible = visibleInstructionFileIds.includes(file.id);
                      const contentPayload = instructionFileContents[file.id];
                      const isLoading = loadingInstructionFileId === file.id;

                      return (
                        <li key={file.id} className="instruction-file-item">
                          <div className="instruction-file-head">
                            <div>
                              <strong>
                                {file.upload_order + 1}. {file.filename}
                              </strong>
                              <p className="muted">
                                {formatFileSize(file.size_bytes)} | sha256: {file.content_sha256}
                              </p>
                            </div>
                            <button
                              type="button"
                              disabled={isLoading}
                              onClick={() => toggleInstructionFileContent(file.id)}
                            >
                              {isLoading
                                ? "Loading..."
                                : isVisible
                                ? "Hide Content"
                                : "View Content"}
                            </button>
                          </div>
                          {isVisible && contentPayload ? (
                            <pre className="instruction-file-preview">
                              {contentPayload.content}
                            </pre>
                          ) : null}
                        </li>
                      );
                    })}
                </ul>
              </div>
            ) : (
              <p>Instruction files used during execution: none</p>
            )}
            {run.status === "failed" ? (
              <p className="status-error">
                Failure Reason: {run.error_message || "Unknown error"}
              </p>
            ) : null}
          </div>

          <div className="inline-actions">
            <button type="button" className="danger" onClick={handleDelete}>
              Delete Run
            </button>
          </div>

          <div className="retry-box">
            <label>
              Retry with new API Key
              <input
                type="password"
                value={retryApiKey}
                onChange={(event) => setRetryApiKey(event.target.value)}
                placeholder="Paste key for retry"
              />
            </label>
            <button type="button" disabled={!retryApiKey.trim()} onClick={handleRetry}>
              Retry Run
            </button>
          </div>

          <section>
            <h3>Timeline</h3>
            {!events.length ? (
              <p>No events yet.</p>
            ) : (
              <ul className="events">
                {events.map((item) => (
                  <li key={item.id}>
                    <strong>{item.event_type}</strong>
                    <span>{item.message}</span>
                    {formatPayload(item.payload) ? (
                      <details>
                        <summary>details</summary>
                        <pre>{formatPayload(item.payload)}</pre>
                      </details>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h3>Sandbox Logs</h3>
            {!logs ? (
              <p>Logs appear automatically for failed runs.</p>
            ) : (
              <div className="logs-grid">
                <div>
                  <h4>stderr tail</h4>
                  <pre className="log-box">{logs.stderr_tail || "(empty)"}</pre>
                </div>
                <div>
                  <h4>stdout tail</h4>
                  <pre className="log-box">{logs.stdout_tail || "(empty)"}</pre>
                </div>
              </div>
            )}
          </section>

          <section>
            <h3>Report</h3>
            {!report && run.status !== "failed" ? (
              <p>Report appears when run completes.</p>
            ) : run.status === "failed" ? (
              <p>Run failed before report generation.</p>
            ) : (
              <div className="report">
                <p>Total Score: {formatScore(report.total_score)}</p>
                <p>{report.evaluation_summary}</p>
                <ul>
                  {Object.entries(report.metrics).map(([name, value]) => (
                    <li key={name}>
                      {name}: {formatScore(value)}
                    </li>
                  ))}
                </ul>
                {report.judge_report ? (
                  <div className="stack">
                    <h4>Judge Report</h4>
                    {report.judge_model ? (
                      <p>Judge model: {report.judge_model}</p>
                    ) : null}
                    {(() => {
                      const judgeReport = parseJudgeReport(report.judge_report);
                      const toolsUsed = Array.isArray(judgeReport?.tools_used)
                        ? judgeReport.tools_used
                        : [];

                      if (
                        judgeReport &&
                        ("summary" in judgeReport || "achieved" in judgeReport)
                      ) {
                        return (
                          <div className="stack">
                            {typeof judgeReport.summary === "string" ? (
                              <p>{judgeReport.summary}</p>
                            ) : null}
                            {typeof judgeReport.achieved === "boolean" ? (
                              <p>
                                Achieved: {judgeReport.achieved ? "Yes" : "No"}
                              </p>
                            ) : null}
                            <div>
                              <p>Tools used:</p>
                              {!toolsUsed.length ? (
                                <p>(none)</p>
                              ) : (
                                <ul>
                                  {toolsUsed.map((tool, index) => (
                                    <li key={`judge-tool-${index}`}>
                                      {tool?.name || "(unnamed tool)"}
                                      {tool?.input_summary
                                        ? ` — ${tool.input_summary}`
                                        : ""}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                            {typeof judgeReport.notes === "string" ? (
                              <p>{judgeReport.notes}</p>
                            ) : null}
                          </div>
                        );
                      }

                      return <pre>{formatPayload(report.judge_report)}</pre>;
                    })()}
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </>
      )}

      {error ? <p className="error">Error: {error}</p> : null}
    </section>
  );
}
