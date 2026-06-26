import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { createRun } from "../api/runsApi";
import { MODEL_OPTIONS, PROVIDER_OPTIONS } from "../constants";
import { useAuth } from "../context/AuthContext";
import { formatFileSize } from "../utils/formatters";

const MAX_INSTRUCTION_FILES = 10;
const MAX_INSTRUCTION_FILE_BYTES = 100 * 1024;
const MAX_INSTRUCTION_FILES_TOTAL_BYTES = 500 * 1024;
const ALLOWED_INSTRUCTION_EXTENSIONS = [".md", ".txt"];

export default function NewRunPage() {
  const navigate = useNavigate();
  const { token } = useAuth();

  const defaultProvider = PROVIDER_OPTIONS[0]?.value ?? "anthropic";
  const defaultModel = MODEL_OPTIONS[defaultProvider]?.[0] ?? "";

  const [prompt, setPrompt] = useState(
    "Summarize the task and propose a safe 3-step execution plan before running tools."
  );
  const [provider, setProvider] = useState(defaultProvider);
  const [model, setModel] = useState(defaultModel);
  const [apiKey, setApiKey] = useState("");
  const [maxSteps, setMaxSteps] = useState(20);
  const [enableExternalMcp, setEnableExternalMcp] = useState(false);
  const [mcpRepos, setMcpRepos] = useState([
    {
      source: "repo",
      repoUrl: "",
      serverPath: "server.json",
      envText: "",
      headersText: "",
      transport: "stdio",
      serverJsonText: "",
    },
  ]);
  const [mcpFailOnError, setMcpFailOnError] = useState(true);
  const [instructionFiles, setInstructionFiles] = useState([]);
  const [previewInstructionFileId, setPreviewInstructionFileId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const modelOptions = MODEL_OPTIONS[provider] ?? [];

  const handleProviderChange = (event) => {
    const nextProvider = event.target.value;
    const nextModels = MODEL_OPTIONS[nextProvider] ?? [];

    setProvider(nextProvider);
    if (!nextModels.includes(model)) {
      setModel(nextModels[0] ?? "");
    }
    if (nextProvider !== "anthropic") {
      setEnableExternalMcp(false);
    }
  };

  const updateRepo = (index, patch) => {
    setMcpRepos((current) =>
      current.map((repo, i) => (i === index ? { ...repo, ...patch } : repo))
    );
  };

  const addRepo = () => {
    setMcpRepos((current) => [
      ...current,
      {
        source: "repo",
        repoUrl: "",
        serverPath: "server.json",
        envText: "",
        headersText: "",
        transport: "stdio",
        serverJsonText: "",
      },
    ]);
  };

  const removeRepo = (index) => {
    setMcpRepos((current) => current.filter((_, i) => i !== index));
  };

  const parseKeyValueLines = (text, label) => {
    const entries = {};
    const invalid = [];
    const lines = text.split("\n");

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return;
      }
      const idx = trimmed.indexOf("=");
      if (idx <= 0) {
        invalid.push(trimmed);
        return;
      }
      const key = trimmed.slice(0, idx).trim();
      const value = trimmed.slice(idx + 1).trim();
      if (!key) {
        invalid.push(trimmed);
        return;
      }
      entries[key] = value;
    });

    if (invalid.length) {
      throw new Error(`MCP ${label} lines must be KEY=VALUE`);
    }

    return entries;
  };

  const toUtf8Bytes = (text) => new TextEncoder().encode(text).length;

  const validateInstructionFilename = (name) => {
    const lower = name.toLowerCase();
    return ALLOWED_INSTRUCTION_EXTENSIONS.some((extension) =>
      lower.endsWith(extension)
    );
  };

  const handleInstructionFileChange = async (event) => {
    const selectedFiles = Array.from(event.target.files ?? []);
    if (!selectedFiles.length) {
      return;
    }

    try {
      const nextCount = instructionFiles.length + selectedFiles.length;
      if (nextCount > MAX_INSTRUCTION_FILES) {
        throw new Error(
          `You can upload up to ${MAX_INSTRUCTION_FILES} instruction files.`
        );
      }

      const nextEntries = [];
      for (const selectedFile of selectedFiles) {
        if (!validateInstructionFilename(selectedFile.name)) {
          throw new Error(
            `${selectedFile.name}: only .md or .txt instruction files are allowed.`
          );
        }

        const content = await selectedFile.text();
        const sizeBytes = toUtf8Bytes(content);
        if (sizeBytes > MAX_INSTRUCTION_FILE_BYTES) {
          throw new Error(
            `${selectedFile.name}: file exceeds ${formatFileSize(
              MAX_INSTRUCTION_FILE_BYTES
            )}.`
          );
        }

        nextEntries.push({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
          filename: selectedFile.name,
          content,
          sizeBytes,
        });
      }

      const totalBytes =
        instructionFiles.reduce((acc, item) => acc + item.sizeBytes, 0) +
        nextEntries.reduce((acc, item) => acc + item.sizeBytes, 0);
      if (totalBytes > MAX_INSTRUCTION_FILES_TOTAL_BYTES) {
        throw new Error(
          `Instruction files exceed total limit of ${formatFileSize(
            MAX_INSTRUCTION_FILES_TOTAL_BYTES
          )}.`
        );
      }

      setInstructionFiles((current) => [...current, ...nextEntries]);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      event.target.value = "";
    }
  };

  const removeInstructionFile = (fileId) => {
    setInstructionFiles((current) => current.filter((item) => item.id !== fileId));
    if (previewInstructionFileId === fileId) {
      setPreviewInstructionFileId(null);
    }
  };

  const instructionFilesTotalBytes = instructionFiles.reduce(
    (acc, item) => acc + item.sizeBytes,
    0
  );

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    let parsedRepos = [];
    try {
      parsedRepos = mcpRepos
        .filter((repo) =>
          repo.source === "inline"
            ? repo.serverJsonText.trim()
            : repo.repoUrl.trim()
        )
        .map((repo, index) => {
          const hasEnv = repo.envText.trim().length > 0;
          const hasHeaders = repo.headersText.trim().length > 0;
          const transport = repo.transport || "stdio";
          const isInline = repo.source === "inline";

          if (transport === "stdio" && hasHeaders) {
            throw new Error(
              `Repo ${index + 1}: headers are only valid for streamable-http.`
            );
          }
          if (transport === "streamable-http" && hasEnv) {
            throw new Error(`Repo ${index + 1}: env is only valid for stdio.`);
          }

          if (isInline) {
            let serverJson = null;
            try {
              serverJson = JSON.parse(repo.serverJsonText);
            } catch (err) {
              throw new Error(
                `Repo ${index + 1}: server.json must be valid JSON.`
              );
            }
            if (!serverJson || typeof serverJson !== "object" || Array.isArray(serverJson)) {
              throw new Error(
                `Repo ${index + 1}: server.json must be a JSON object.`
              );
            }

            return {
              server_json: serverJson,
              env: transport === "stdio" ? parseKeyValueLines(repo.envText, "env") : {},
              headers:
                transport === "streamable-http"
                  ? parseKeyValueLines(repo.headersText, "headers")
                  : {},
            };
          }

          return {
            repo_url: repo.repoUrl.trim(),
            server_path: repo.serverPath.trim() || "server.json",
            env: transport === "stdio" ? parseKeyValueLines(repo.envText, "env") : {},
            headers:
              transport === "streamable-http"
                ? parseKeyValueLines(repo.headersText, "headers")
                : {},
          };
        });
    } catch (err) {
      setError(err.message);
      return;
    }

    if (enableExternalMcp && !parsedRepos.length) {
      setError("Add at least one MCP repo to continue.");
      return;
    }

    try {
      setSubmitting(true);
      const run = await createRun(token, {
        prompt,
        provider,
        model,
        api_key: apiKey,
        max_steps: Number(maxSteps),
        enable_external_mcp: enableExternalMcp,
        external_mcp_url: null,
        mcp_repos: enableExternalMcp ? parsedRepos : [],
        mcp_failure_policy: mcpFailOnError ? "fail" : "continue",
        instruction_files: instructionFiles.map((file) => ({
          filename: file.filename,
          content: file.content,
        })),
      });
      setApiKey("");
      navigate(`/runs/${run.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="panel">
      <h2>Create New Run</h2>

      <form className="run-form" onSubmit={handleSubmit}>
        <label>
          Prompt
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={6}
            required
          />
          <span className="hint">
            The exact instruction sent to the provider inside the sandbox.
          </span>
        </label>

        <div className="row">
          <label>
            Provider
            <select value={provider} onChange={handleProviderChange} required>
              {PROVIDER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <span className="hint">Select the API vendor for this run.</span>
          </label>

          <label>
            Model
            <select
              value={model}
              onChange={(event) => setModel(event.target.value)}
              required
            >
              {modelOptions.map((modelName) => (
                <option key={modelName} value={modelName}>
                  {modelName}
                </option>
              ))}
            </select>
            <span className="hint">
              Pick a model version, including cheaper tiers for testing.
            </span>
          </label>

          <label>
            Max Steps
            <input
              type="number"
              min={1}
              max={200}
              value={maxSteps}
              onChange={(event) => setMaxSteps(event.target.value)}
              required
            />
            <span className="hint">
              Upper bound for tool steps. In v1 it only affects scoring via
              step-efficiency, while execution is single-step.
            </span>
          </label>
        </div>

        <label>
          API Key (session-only)
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="Paste provider key"
            required
          />
          <span className="hint">
            Stored in memory for this run only. It is never persisted.
          </span>
        </label>

        <section className="instruction-files-panel">
          <div className="section-header">
            <h3>Instruction Files</h3>
            <p className="muted">
              {instructionFiles.length} / {MAX_INSTRUCTION_FILES} files
            </p>
          </div>

          <label>
            Upload .md or .txt files
            <input
              type="file"
              accept=".md,.txt,text/plain"
              multiple
              onChange={handleInstructionFileChange}
            />
            <span className="hint">
              Max {formatFileSize(MAX_INSTRUCTION_FILE_BYTES)} per file, total {" "}
              {formatFileSize(MAX_INSTRUCTION_FILES_TOTAL_BYTES)}.
            </span>
          </label>

          <p className="hint">
            Total uploaded size: {formatFileSize(instructionFilesTotalBytes)}
          </p>

          {!instructionFiles.length ? (
            <p className="muted">No instruction files uploaded yet.</p>
          ) : (
            <ul className="instruction-file-list">
              {instructionFiles.map((file, index) => {
                const isPreviewOpen = previewInstructionFileId === file.id;
                return (
                  <li key={file.id} className="instruction-file-item">
                    <div className="instruction-file-head">
                      <div>
                        <strong>
                          {index + 1}. {file.filename}
                        </strong>
                        <p className="muted">{formatFileSize(file.sizeBytes)}</p>
                      </div>
                      <div className="inline-actions">
                        <button
                          type="button"
                          onClick={() =>
                            setPreviewInstructionFileId((current) =>
                              current === file.id ? null : file.id
                            )
                          }
                        >
                          {isPreviewOpen ? "Hide Preview" : "Preview"}
                        </button>
                        <button
                          type="button"
                          className="danger ghost"
                          onClick={() => removeInstructionFile(file.id)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                    {isPreviewOpen ? (
                      <pre className="instruction-file-preview">{file.content}</pre>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <label className="check-row">
          <input
            type="checkbox"
            checked={enableExternalMcp}
            onChange={(event) => setEnableExternalMcp(event.target.checked)}
            disabled={provider !== "anthropic"}
          />
          Enable MCP server
        </label>

        {provider !== "anthropic" ? (
          <span className="hint">
            MCP tool calling supports Anthropic only in v1.
          </span>
        ) : null}

        {enableExternalMcp ? (
          <div className="stack">
            {mcpRepos.map((repo, index) => (
              <div key={`mcp-repo-${index}`} className="stack">
                <label>
                  MCP source
                  <select
                    value={repo.source}
                    onChange={(event) =>
                      updateRepo(index, { source: event.target.value })
                    }
                  >
                    <option value="repo">GitHub repo</option>
                    <option value="inline">Inline server.json</option>
                  </select>
                  <span className="hint">
                    Use a repo URL or paste server.json directly.
                  </span>
                </label>

                <label>
                  Transport
                  <select
                    value={repo.transport}
                    onChange={(event) =>
                      updateRepo(index, { transport: event.target.value })
                    }
                  >
                    <option value="stdio">stdio (npm package)</option>
                    <option value="streamable-http">streamable-http</option>
                  </select>
                  <span className="hint">
                    Determines whether env or headers are used.
                  </span>
                </label>

                {repo.source === "repo" ? (
                  <>
                    <label>
                      MCP Repo URL
                      <input
                        type="url"
                        value={repo.repoUrl}
                        onChange={(event) =>
                          updateRepo(index, { repoUrl: event.target.value })
                        }
                        placeholder="https://github.com/org/repo"
                        required={enableExternalMcp && repo.source === "repo"}
                      />
                      <span className="hint">Public repo containing server.json.</span>
                    </label>

                    <label>
                      server.json path
                      <input
                        value={repo.serverPath}
                        onChange={(event) =>
                          updateRepo(index, { serverPath: event.target.value })
                        }
                        placeholder="server.json"
                        required={enableExternalMcp && repo.source === "repo"}
                      />
                      <span className="hint">Relative to repo root.</span>
                    </label>
                  </>
                ) : (
                  <label>
                    server.json content
                    <textarea
                      value={repo.serverJsonText}
                      onChange={(event) =>
                        updateRepo(index, { serverJsonText: event.target.value })
                      }
                      rows={6}
                      placeholder={`{\n  "name": "my-mcp",\n  "packages": [...]\n}`}
                      required={enableExternalMcp && repo.source === "inline"}
                    />
                    <span className="hint">Paste the full server.json payload.</span>
                  </label>
                )}

                {repo.transport === "stdio" ? (
                  <label>
                    MCP env (KEY=VALUE per line)
                    <textarea
                      value={repo.envText}
                      onChange={(event) =>
                        updateRepo(index, { envText: event.target.value })
                      }
                      rows={3}
                      placeholder="KEY=VALUE"
                    />
                    <span className="hint">
                      Used for stdio packages (environmentVariables).
                    </span>
                  </label>
                ) : (
                  <label>
                    MCP headers (KEY=VALUE per line)
                    <textarea
                      value={repo.headersText}
                      onChange={(event) =>
                        updateRepo(index, { headersText: event.target.value })
                      }
                      rows={3}
                      placeholder="Authorization=Bearer ..."
                    />
                    <span className="hint">
                      Used for streamable-http remotes (headers).
                    </span>
                  </label>
                )}

                {mcpRepos.length > 1 ? (
                  <button type="button" onClick={() => removeRepo(index)}>
                    Remove Repo
                  </button>
                ) : null}
              </div>
            ))}

            <button type="button" onClick={addRepo}>
              Add MCP Repo
            </button>
          </div>
        ) : null}

        <label className="check-row">
          <input
            type="checkbox"
            checked={mcpFailOnError}
            onChange={(event) => setMcpFailOnError(event.target.checked)}
            disabled={!enableExternalMcp}
          />
          Fail run if MCP server fails to start
        </label>

        <button type="submit" disabled={submitting || !apiKey.trim()}>
          {submitting ? "Submitting..." : "Start Run"}
        </button>
      </form>

      {error ? <p className="error">Error: {error}</p> : null}
    </section>
  );
}
