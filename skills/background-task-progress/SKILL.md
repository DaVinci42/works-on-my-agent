---
name: background-task-progress
description: >-
  Run slow commands in the background without foreground `sleep` blocking, wake automatically via async subagents (`agent_dispatch`), and check progress on demand across Crush/subagent hosts, Bash, and PowerShell (`pwsh`) (后台跑耗时构建/测试/下载、零前台 sleep 阻塞、subagent 跑完自动唤醒、边跑边聊随时查状态).
  Use for slow builds/tests (`nix-build`, `nixpkgs-review`, `cargo`, `pytest`, `npm/pnpm`), downloads, migrations, dev servers, auto-backgrounded `shell_id` jobs, or "run in background / notify when done / 后台跑 / 边跑边聊 / 跑完叫我".
---

# Background Task Execution & Progress

## Core Rules

1. **Zero foreground `sleep` by default**: Never call `sleep`, `Start-Sleep`, `WaitForExit`, or `job_output(wait: true)` in the main session to wait on or poll a task. Finish unblocked work and **end your turn immediately** to free the user prompt.
2. **Never loop until completion inside one foreground shell call**: Unbounded waits freeze the turn and emit zero intermediate output.
3. **Dispatch matrix (pick highest available tier)**:

| Scenario | Mechanism | Post-Launch Action |
|---|---|---|
| **Finite slow task or milestone wait** (build, test, download, "notify when ready") on subagent host | **Tier 1**: `agent_dispatch` | Report subagent name; **end turn immediately** (`<subagent-report>` wakes you automatically). |
| **Persistent daemon** (server, watcher) or finite task without `agent_dispatch` | **Tier 2**: `run_in_background: true` | Report `shell_id`; **end turn immediately** (never append `&` or call immediate `job_output`). |
| **Command auto-backgrounded on timeout** (returned `shell_id`) | **Tier 2 takeover** | Do **not** start a foreground `sleep` loop; finish unrelated work, report `shell_id`, and **end turn**. |
| **Minimal host** (no `agent_dispatch`, no `run_in_background`) | **Tier 3**: Detached OS process | Print literal `BG_PID` + `LOG_FILE`, detach stdio pipes, and **end turn**. |

## 1. Launch

### Tier 1: Async Subagent (`agent_dispatch`)

- Set `label` (e.g., `cargo-test`), `access` (`"read"` unless editing files; keep concurrent `"write"` scopes and build locks like `target/` or Nix/Gradle locks strictly disjoint), and optionally a lightweight `model` with minimal `reasoning` (`off` / `low`) for pure command execution + log summarization.
- **Subagent prompt template** (handle `auto_background_after` inside the subagent so >60s commands do not return prematurely):
  ```text
  Working directory: <abs_cwd>
  Run: <command>
  Set `auto_background_after: 600` on `bash`; if it still auto-backgrounds and returns a `shell_id`, call `job_output(shell_id, wait: true)` until completion (`wait: true` is allowed inside this isolated subagent).
  Return concise exit status, duration, artifact paths, and key error lines only.
  ```
- After `agent_dispatch`, **never** call `sleep` or `agent_status` to wait—end your turn. Subagents survive user interrupts and follow-up messages.

### Tier 2: Native Background Shell (`run_in_background: true`)

- Call `bash` with `run_in_background: true` (no trailing `&`, no startup `sleep`, no immediate `job_output`).

### Tier 3: Detached OS Process Fallback (No Tier 1 / Tier 2)

Never rely on in-memory shell variables (`$BG_PID`, `$job`) across tool calls; print and reuse literal `<BG_PID>` and `<LOG_FILE>`. On Windows embedded Bash (`mvdan/sh`) where `nohup`/`ps` may be missing, invoke `pwsh` / `powershell`.

- **Bash** (command group avoids nested quote escaping; closed stdio prevents runner hang):
  ```bash
  LOG_FILE="${TMPDIR:-/tmp}/bg_task_$(date +%s)_$$.log"
  { trap '' HUP; <command>; printf '\n__EXIT_CODE=%s\n' "$?"; } </dev/null >"$LOG_FILE" 2>&1 &
  BG_PID=$!
  printf 'BG_PID=%s\nLOG_FILE=%s\n' "$BG_PID" "$LOG_FILE"
  ps -p "$BG_PID" -o pid,%cpu,etime,state,comm || true
  ```
- **PowerShell / `pwsh`** (never use session-bound `Start-Job`; substitute `"powershell"` if `pwsh` is absent):
  ```powershell
  $LogFile = Join-Path ([System.IO.Path]::GetTempPath()) "bg_task_$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())_$PID.log"
  $Script = { $global:LASTEXITCODE = 0; <command>; $ec = if (-not $?) { if ($LASTEXITCODE) { $LASTEXITCODE } else { 1 } } else { $LASTEXITCODE }; Write-Output "`n__EXIT_CODE=$ec" }.ToString()
  $Encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Script))
  $p = Start-Process -FilePath "pwsh" -WorkingDirectory $PWD.Path -ArgumentList "-NoProfile", "-EncodedCommand", $Encoded -RedirectStandardOutput $LogFile -RedirectStandardError "$LogFile.err" -WindowStyle Hidden -PassThru
  Write-Output "BG_PID=$($p.Id)`nLOG_FILE=$LogFile"
  Get-Process -Id $p.Id -ErrorAction SilentlyContinue | Select-Object Id, CPU, ProcessName
  ```

## 2. Progress & Control

### Default: Event-Driven / On-Demand (Zero Polling)

- **While running**: If the user asks a question or checks progress, answer and run **one non-blocking check** (then end turn again—never enter a `sleep` loop):
  - **Tier 1**: `agent_status(label: "<subagent-name>")`; steer via `agent_send`
  - **Tier 2**: `job_output(shell_id: "<shell_id>", wait: false)`
  - **Tier 3 Bash**: `ps -p <BG_PID> -o pid,%cpu,etime || true; tail -n 15 "<LOG_FILE>"`
  - **Tier 3 PowerShell**: `Get-Process -Id <BG_PID> -ErrorAction SilentlyContinue | Select-Object Id,CPU; Get-Content "<LOG_FILE>","<LOG_FILE>.err" -Tail 15 -ErrorAction SilentlyContinue`
- **On completion (Tier 1)**: `<subagent-report>` wakes you in a new turn; summarize results and continue dependent steps.

### Opt-In Only: Fixed-Interval Chat Ticker

Use **only** when the user explicitly requests periodic chat messages every `N` seconds (default `15s`–`30s`). Milestone waits (*"tell me when port 8080 is up"*) belong in **Tier 1 `agent_dispatch`**, not foreground ticks.

1. Launch via Tier 2 or Tier 3 so user interrupts (`Ctrl+C` / `Esc`) do not kill the job.
2. Execute **one bounded wait + check per tool call** (max 20 ticks before asking to continue; if interrupted for Q&A, answer and revert to Default mode unless asked to resume ticking):
   - **Tier 2**: `sleep <N>` (or `Start-Sleep -Seconds <N>`), then `job_output(wait: false)`.
   - **Tier 3 Bash**: `for _ in $(seq 1 15); do kill -0 <BG_PID> 2>/dev/null || break; sleep 1; done; ps -p <BG_PID> -o pid,%cpu,etime,state,comm || true; tail -n 20 "<LOG_FILE>"`
   - **Tier 3 PowerShell**: `$p = Get-Process -Id <BG_PID> -ErrorAction SilentlyContinue; if ($p) { $null = $p.WaitForExit(15000) }; if ($p -and -not $p.HasExited) { $p | Select-Object Id,CPU,ProcessName } else { "EXITED" }; Get-Content "<LOG_FILE>","<LOG_FILE>.err" -Tail 20 -ErrorAction SilentlyContinue`
3. Report `[Running | <etime>]` (note active `CPU`/`etime` when logs are quiet) or final `__EXIT_CODE=`.

## 3. Stop & Cleanup

- **Tier 1**: `agent_stop(label: "<subagent-name>", reason: "...")` (clean up any detached OS processes the subagent spawned).
- **Tier 2**: `job_kill(shell_id: "<shell_id>")`.
- **Tier 3**: Bash `pkill -TERM -P <BG_PID> 2>/dev/null || true; kill -TERM <BG_PID>`; PowerShell `taskkill /T /F /PID <BG_PID>`; delete temporary `<LOG_FILE>` when done.
