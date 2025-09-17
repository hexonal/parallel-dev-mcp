# Parallel Dev MCP - Claude Code Hooks & TMUX Integration PRD

## 1. Overview
- Objective: Deliver a unified Claude Code hooks toolkit that orchestrates tmux-based master/child sessions, FastMCP 2.x services, and a Flask control plane so that parallel development sessions can self-manage, communicate, and report status through MCP resources.
- Scope: Master session lifecycle management, child session creation and observability, TMUX command automation, web endpoints for inter-session messaging, and persistent metadata (git plus worktree) tracking.
- Out of Scope: FastMCP core server implementation, Claude Code IDE behavior changes, or cross-host session federation.

## 2. System Context
- Runtime: All hooks run inside tmux sessions. If tmux is unavailable, hooks terminate immediately.
- Primary stack: tmux plus FastMCP >= 2.x, Flask (web control plane), and Claude Code hook scripts.
- Control surfaces:
  - Flask web service that intermediates hook POST and GET requests.
  - Claude Code hook scripts attached to master and child sessions.
  - MCP resource store (for example `@mcp.resource`) for persistent state.

## 3. Key Definitions
- Master session: tmux session named `{PROJECT_PREFIX}_master`. Owns shared resources, runs Flask server, exposes status.
- Child session: tmux session named `{PROJECT_PREFIX}_child_{taskId}`. Handles individual task execution.
- Session ID file: `session_id.txt` at project root that records the master session Claude session id when available.
- Worktree directory: `${PROJECT_ROOT}/worktree/{taskId}` directory that maps each child to a git worktree checkout and branch.

## 4. Assumptions and Dependencies
- tmux commands (`tmux has-session`, `tmux new-session`, `tmux send-keys`, `tmux list-sessions`, and similar) are available and permitted.
- Git repository already initialized at project root; `git remote get-url` and `git rev-parse --abbrev-ref HEAD` succeed.
- Claude Code hooks receive structured payloads compatible with FastMCP 2.x hook contract.
- MCP resource storage API is accessible for read and write operations from hooks.

## 5. Environment Variables
All hooks honor configuration supplied through the MCP server definition (see `mcp.json` pattern).

| Name | Purpose | Notes |
| ---- | ------- | ----- |
| `PROJECT_PREFIX` | tmux namespace prefix | Must match tmux session names. Master is `{PROJECT_PREFIX}_master`; child is `{PROJECT_PREFIX}_child_{taskId}`. |
| `DANGEROUSLY_SKIP_PERMISSIONS` | propagate into Claude CLI invocation | When set truthy, final command uses `--dangerously-skip-permissions`. |
| `MCP_CONFIG_PATH` | path to `.mcp.json` | Used when spawning Claude CLI: `claude --dangerously-skip-permissions --mcp-config .mcp.json`. |
| `WEB_PORT` | Flask port for master web service | Only the master session may bind and listen. Child sessions read it for requests. |

Example MCP server stub:
```json
"taskmaster-ai": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "--package=task-master-ai", "task-master-ai"],
  "env": {
    "NODE_ENV": "production",
    "PROJECT_PREFIX": "parallel_demo",
    "MCP_CONFIG_PATH": ".mcp.json",
    "WEB_PORT": "5500"
  }
}
```

## 6. High-Level Architecture
1. Master Session Responsibilities
   - Launch Flask server (web control plane) on `WEB_PORT`.
   - Bind Claude session id to `session_id.txt` (poll every 2 seconds until the first bind).
   - Persist git remote and branch metadata to MCP resource cache (single source of truth for worktrees).
   - Ensure `worktree/` directory exists.
   - Discover and monitor child sessions through `tmux list-sessions` every 5 seconds, syncing summary into MCP resources.
   - Handle 5-hour limit resets by scheduling tmux messages per `tmux_web_service.py` logic.
   - Manage prompt templates from `.parallel-dev-mcp/master.txt` when available.

2. Child Session Responsibilities
   - Never mutate `session_id.txt`.
   - Register with master via `/msg/health` and `/msg/report` calls.
   - Report health every 15 seconds: execution state, idle indicator, git dirty flag, tmux pane busy indicator, Claude execution flag.
   - On creation, auto-create `worktree/{taskId}` and checkout dedicated branch.
   - Use `.parallel-dev-mcp/child.txt` prompt template if present; otherwise send raw message.

3. Flask Web Service
   - Exposes `/msg/send`, `/msg/health`, `/msg/report` for child to master communication.
   - Persists status and reports into MCP resources.
   - Applies tmux limit handling, auto `hi` handshake, and session filtering per `tmux_web_service.py` reference.

4. Claude Code Hook Scripts
   - Wrap tmux interactions, environment validations, and HTTP requests.
   - Master hook bootstraps services; child hook focuses on health reporting and execution orchestration.

5. Logging
   - All hooks and services log under `.parallel-dev-mcp/logs/*.log` with rotation policy to be defined.

## 7. Functional Requirements

### 7.1 Session Bootstrap and Identification
- Detect current tmux session id upfront (reuse logic from `examples/hooks/web_message_sender.py`).
- Master session detection rules:
  - If tmux session name exactly matches `{PROJECT_PREFIX}_master`, treat as master.
  - Write Claude `session_id` to `session_id.txt` only when file is missing or empty.
- Child sessions skip any attempt to touch `session_id.txt`.

### 7.2 Flask Web Endpoints (master only)
- `/msg/send`: Accepts payload `{ "message": str, "taskId": str?, "sessionId": str? }`; forwards to target tmux session (default master) while respecting rate-limit safeguards.
- `/msg/health`: Records health payload from child (timestamped) and returns aggregated status.
- `/msg/report`: Persists status snapshots (task progress, completion state, diagnostics) into `@mcp.resource` for retrieval.
- `/health`: Basic readiness probe.
- Implement limit-handling scheduler mirroring `tmux_web_service.py` (detect "5-hour limit reached" and schedule continuation message).

### 7.3 Master Session Binding and Git Metadata
- Poll `session_id.txt` existence every 2 seconds until master Claude session id is acquired; once bound, cease polling.
- On master hook start, capture:
  - `git remote get-url --push origin` (or default remote) as repo URL.
  - `git rev-parse --abbrev-ref HEAD` as base branch.
- Persist metadata and session binding into MCP resource store for downstream tools.

### 7.4 Worktree Management
- Ensure `worktree/` directory exists under project root during master initialization.
- For each child `taskId`, create `worktree/{taskId}` via `git worktree add` and checkout branch naming convention (for example `{base_branch}-{taskId}` or configurable).
- Child hook automatically changes directory into its worktree directory.

### 7.5 Child Session Lifecycle
- Creation flow:
  1. Master executes `tmux new-session -d -s {PROJECT_PREFIX}_child_{taskId}`.
  2. Immediately send "hi" via tmux to validate session responsiveness.
  3. Prepare worktree directory and branch (see section 7.4).
  4. Launch Claude CLI with required flags and env (respecting `DANGEROUSLY_SKIP_PERMISSIONS` and `MCP_CONFIG_PATH`).
- Runtime:
  - Every 15 seconds, call `/msg/health` with payload containing:
    - `taskId`, `sessionId`, `isExecuting` (Claude running), `isIdle`, `hasUncommittedChanges`, `tmuxPaneBusy`.
  - Emit progress updates through `/msg/report` with structured status (started, running, blocked, done, notes, artifacts, etc.).

### 7.6 Master Session Child Management
- Every 5 seconds, run `tmux list-sessions` and filter names starting with `{PROJECT_PREFIX}_child_`.
- Sync list to MCP resource store including derived metadata (taskId, status, last health ping, git branch).
- Provide CLI or API to check child health and escalate missing heartbeats.

### 7.7 Claude CLI Invocation
- Compose command: `claude [--dangerously-skip-permissions?] --mcp-config {MCP_CONFIG_PATH}`.
- Only master triggers CLI spawn for new sessions; children inherit environment.
- Validate `claude` binary availability; log and abort gracefully if missing.

### 7.8 Prompt Template Handling
- On startup, ensure `.parallel-dev-mcp/` directory exists.
- Master:
  - If `.parallel-dev-mcp/master.txt` exists, load template and send once to master session; otherwise skip silently.
- Child:
  - If `.parallel-dev-mcp/child.txt` exists, merge template into outgoing message (for example placeholder substitution with task metadata); otherwise use default message.

### 7.9 Session Status Queries and Shutdown
- Provide commands to:
  - Check existence of tmux sessions (master and children).
  - Determine whether Claude processes are active within sessions (for example via tmux pane text or process inspection).
- Implement graceful shutdown sequence: broadcast notice, terminate Claude CLI, kill tmux session, update MCP resources, clear worktree state if required.

### 7.10 Logging and Observability
- Store structured logs under `.parallel-dev-mcp/logs/{role}-{date}.log`.
- Include timestamp, session role, event type, message, optional payload snippet.
- Provide log rotation policy (size-based or daily).

## 8. Non-Functional Requirements
- Reliability: Master must recover from hook restart without losing child metadata (read from MCP resources and filesystem).
- Performance: Health checks (15 seconds) and session discovery (5 seconds) should be asynchronous to avoid blocking main hook execution.
- Security: Reject non-master attempts to bind session id; only accept child reports matching known `{PROJECT_PREFIX}` namespace.
- Configurability: Allow overriding polling intervals via environment variables or config constants.
- Telemetry: Ensure HTTP endpoints return actionable status codes and structured JSON for troubleshooting.

## 9. Open Questions
1. How should child worktree branch naming be parameterized? (Current assumption: `{base_branch}-{taskId}`.)
2. Should `/msg/report` support attachments or artifact links, and if so how are they stored in MCP resources?
3. What is the retention strategy for logs and MCP resource snapshots?
4. Do we need backoff or retry for tmux command failures or network glitches between sessions?
5. Should master auto-restart stalled child sessions based on health timeout thresholds?

## 10. Milestones
1. Phase 1: Implement master Flask service plus session binding plus MCP persistence.
2. Phase 2: Deliver child session bootstrap and health reporting.
3. Phase 3: Add git worktree integration and prompt templates.
4. Phase 4: Harden for rate limits, logging, and lifecycle commands.

