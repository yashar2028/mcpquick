# Platform Architecture Plan

## Goal
Build a FastAPI + React platform where users bring their own LLM credentials, execute prompt-driven tasks, and receive:
- A weighted performance rating
- Granular metric breakdown
- Human-readable execution logs

The platform must isolate user execution strongly and be ready for future GitHub MCP server onboarding.

## Scope Boundaries
- In scope now: user-run architecture, run pipeline, scoring, isolation contracts.
- Out of scope now: platform-level deployment Dockerization (can be added later).

## Core Principles
1. Control-plane and execution-plane separation.
2. Session-only provider API key handling (never persisted).
3. Per-run isolation with Nix-based reproducible runtime profile.
4. External GitHub MCP (when enabled later) must run in the same isolated per-run boundary as the user LLM loop.

## High-Level Architecture

### Control Plane (FastAPI)
Responsibilities:
- Accept run requests
- Validate policy and feature flags
- Persist run state and event logs
- Schedule isolated execution
- Compute and return score reports

Key components:
- Run API endpoints
- Run and event persistence
- Scoring service
- Worker queue/scheduler abstraction

### Execution Plane (Sandbox Worker)
Responsibilities:
- Start isolated run environment
- Execute model/tool loop
- Emit structured events
- Enforce policy controls and limits
- Return metrics and artifacts

Isolation baseline:
- Per-run sandbox boundary
- Pinned Nix runtime profile
- Strict time/resource/network controls
- Ephemeral writable workspace

## v1 Data Model
- evaluation_runs
  - provider, model, prompt
  - status lifecycle (queued, running, completed, failed)
  - sandbox_profile
  - external MCP request metadata
  - score fields and summarized metrics
  - token/cost/latency aggregates
- run_events
  - event_type, message, payload
  - step index and timestamp

## v1 API Surface
- POST /v1/runs
  - Create run and queue execution
- GET /v1/runs
  - List runs
- GET /v1/runs/{run_id}
  - Fetch run details
- GET /v1/runs/{run_id}/events
  - Fetch ordered execution events
- GET /v1/runs/{run_id}/report
  - Fetch final score and recommendations

## Scoring Model (Weighted Scorecard)
Composite score:
score = sum(weight_i * metric_i)

Recommended v1 default weights:
- task_success: 0.35
- tool_correctness: 0.25
- latency_efficiency: 0.10
- cost_efficiency: 0.10
- step_efficiency: 0.10
- reliability_recovery: 0.10

Task success source in v1:
- Judge-model based scoring with rubric constraints and explicit uncertainty handling.

## External MCP GitHub Support (Designed, Disabled in v1)
Feature flag remains OFF in v1.

Future pipeline when enabled:
1. Clone and validate repository
2. Check compatibility against supported MCP profile/template
3. Build in isolated builder environment
4. Produce signed runnable artifact
5. Execute artifact only inside the same per-run sandbox boundary as LLM execution

## Security and Policy
- Session-only API keys:
  - accepted per request
  - never written to DB
  - scrubbed from memory after run completion/failure
- Prevent untrusted execution on control-plane host.
- Add payload/step/timeout/rate limits.

## Implementation Phases
1. Foundation: entities, schemas, run APIs, scoring module, worker scaffold.
2. Isolation hardening: real sandbox broker and limit enforcement.
3. Evaluation maturity: judge-model integration and richer metrics.
4. UX: live run timeline and score dashboard in React.
5. Scale and ops: queue fairness, observability, and SLOs.

## Immediate Next Technical Milestones
1. Add Alembic migration for run tables.
2. Replace mock worker execution with real sandbox orchestration adapter.
3. Add event streaming endpoint (SSE/WebSocket) for live frontend updates.
4. Add auth and tenant-level quotas.
