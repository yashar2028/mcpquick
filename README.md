# MCP Quick

MCP Quick is a full-stack app for launching, tracking, and reviewing sandboxed model evaluations in an MCP-oriented workflow. The backend queues isolated runs, records timelines, stores uploaded instruction files, computes deterministic score toegether with a judgemnt on response, and exposes run artifacts and reports. The frontend provides a public landing experience plus authenticated pages for dashboards, run creation, history, and run details.

- Create evaluation runs with a prompt, provider, model, API key, max steps, and optional instruction files.
- Attach MCP repos or inline MCP server definitions for tool-augmented runs.
- Inspect run timelines, logs, final scorecards, and downloadable artifacts.
- Review dashboard aggregates such as run totals, success rate, latency, and provider/model usage.

## Stack

- Frontend: React 19, Vite, React Router, Axios.
- Backend: FastAPI, SQLAlchemy async, Alembic, PostgreSQL.
- Sandbox runtime: Nix-first execution with a local subprocess fallback for development when enabled.
- Providers: OpenAI and Anthropic/Claude are exposed in the current UI and backend runtime.

## Repository Layout

`frontend/` contains the Vite app and the public/authenticated UI.
`backend/` contains the FastAPI app, data models, workers, sandbox runtime, and migrations.
`scripts/run.sh` starts the backend and database.
`docker_run.sh` wraps Docker Compose. Run using this script will change port visibilities to public in backend and frontend images (needed for run in Codespaces)

## Run

Start the app with Docker Compose:

```bash
./docker_run.sh up --build
```

Run backend and database separately:

```bash
./scripts/run.sh
```

Run the frontend separately:

```bash
cd frontend
npm install
npm run dev
```

## Development Notes

Install the pre-commit hooks with:

```bash
pre-commit install
```

### Windows Setup Options for Local run

Option 1: install Nix directly and keep:

```env
SANDBOX_COMMAND_PREFIX=
SANDBOX_NIX_BINARY=nix
```

Option 2: run the backend directly inside WSL and install Poetry + Nix there. This keeps the backend process and sandbox process in one environment.

```env
SANDBOX_COMMAND_PREFIX=wsl.exe
SANDBOX_NIX_BINARY=nix
```

## Backend Overview

The backend exposes these core areas:

- `POST /v1/auth/register`, `POST /v1/auth/login`, `GET /v1/auth/me` for authentication.
- `GET /v1/dashboard/summary` for run aggregates.
- `POST /v1/runs` to create a run.
- `GET /v1/runs` to list runs with filtering and pagination.
- `GET /v1/runs/{run_id}` to fetch run details.
- `GET /v1/runs/{run_id}/events` for the timeline.
- `GET /v1/runs/{run_id}/logs` for stdout/stderr tails.
- `GET /v1/runs/{run_id}/report` for the final scorecard.
- `GET /v1/runs/{run_id}/artifacts.zip` for downloadable artifacts.
- `POST /v1/runs/{run_id}/retry` to rerun with a fresh API key.
- `DELETE /v1/runs/{run_id}` to remove a run.

The run worker stores provider keys only for the active session, executes the sandboxed model call, computes a weighted score from deterministic metrics, and persists events plus the final report that also includes a judge report.


## Contributers
[Yashar Najafi](https://github.com/yashar2028)

[Sina Najafi](https://github.com/SinaNajafi1)

[Youssef Daoud ](https://github.com/MrHowtz)

[Sepehr Hajimokhtar](https://github.com/sepehrmokhtar)

[Parnian Taji](https://github.com/ParnianTj)