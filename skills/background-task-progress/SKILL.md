---
name: background-task-progress
description: Run long-running commands in the background without blocking the foreground LLM session, answer user questions while tasks run, and report incremental progress on demand or at scheduled intervals across Bash (macOS/Linux) and PowerShell/pwsh (Windows) (后台执行耗时任务、避免前台会话阻塞、支持对话期间随时查询任务状态、以及在用户无交互时按指定时间间隔自动汇报进度). Use whenever the user runs a slow build, test suite, download, or script and wants the session to stay responsive or report progress periodically.
---

# Background Task Execution & Progress Reporting

## Core Rules

1. **Never block the foreground tool call**: Launch long-running tasks in the background so the initial tool call returns within 1–2 seconds.
2. **Never loop until completion inside a single shell call**: An LLM can only emit visible progress text *between* tool calls. Running an unbounded wait loop inside one tool call freezes the turn until completion and outputs zero intermediate updates.
3. **Prefer native background tools first, then shell-specific detached fallback**:
   - **Native host tools** (e.g., `run_in_background: true` + `job_output` / `BashOutput` / `job_kill`): Use them directly when available.
   - **Shell fallback**: Each tool call runs in a fresh process—never rely on in-memory shell variables (`$BG_PID`, `$job`) persisting across tool calls. Always print and reuse literal `<BG_PID>` and `<LOG_FILE>` values, and detach standard pipes so the tool runner does not hang waiting for EOF.
   - **Note on embedded Bash interpreters on Windows** (e.g., `mvdan/sh`): Builtin `nohup` or `ps` may not exist; if native `run_in_background` is unavailable on Windows, invoke `pwsh -NoProfile -Command ...` or `powershell -NoProfile -Command ...`.

## 1. Launch Detached & Verify Startup

### Bash (macOS / Linux / Git Bash)

Use a backgrounded command group `{ ...; } &` with `trap '' HUP` rather than `sh -c '...'` so single and double quotes inside `<command>` do not need escaping:

```bash
LOG_FILE="${TMPDIR:-/tmp}/bg_task_$(date +%s)_$$.log"
{ trap '' HUP; <command>; printf '\n__EXIT_CODE=%s\n' "$?"; } </dev/null >"$LOG_FILE" 2>&1 &
BG_PID=$!
printf 'BG_PID=%s\nLOG_FILE=%s\n' "$BG_PID" "$LOG_FILE"
sleep 1
ps -p "$BG_PID" -o pid,%cpu,etime,state,comm || true
tail -n 10 "$LOG_FILE" 2>/dev/null || true
```

### PowerShell / `pwsh` (Windows / Cross-Platform)

Do **not** use `Start-Job` (jobs die when the tool call's PowerShell session exits). Encode the command with `[Convert]::ToBase64String`, pass `-WorkingDirectory $PWD.Path` so relative paths resolve in the current project, and check both `$?` and `$LASTEXITCODE` (PowerShell cmdlets do not set `$LASTEXITCODE`):

```powershell
$LogFile = Join-Path ([System.IO.Path]::GetTempPath()) "bg_task_$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())_$PID.log"
$Script = { $global:LASTEXITCODE = 0; <command>; $ec = if (-not $?) { if ($LASTEXITCODE) { $LASTEXITCODE } else { 1 } } else { $LASTEXITCODE }; Write-Output "`n__EXIT_CODE=$ec" }.ToString()
$Encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Script))
$p = Start-Process -FilePath "pwsh" -WorkingDirectory $PWD.Path -ArgumentList "-NoProfile", "-EncodedCommand", $Encoded -RedirectStandardOutput $LogFile -RedirectStandardError "$LogFile.err" -WindowStyle Hidden -PassThru
Write-Output "BG_PID=$($p.Id)`nLOG_FILE=$LogFile"
Start-Sleep -Seconds 1
Get-Process -Id $p.Id -ErrorAction SilentlyContinue | Select-Object Id, CPU, ProcessName
Get-Content $LogFile, "$LogFile.err" -Tail 10 -ErrorAction SilentlyContinue
```
*(If `pwsh` is not installed on Windows, substitute `"powershell"` in `-FilePath`.)*

## 2. Two Progress Reporting Patterns

### Pattern A: Interactive Mode (Keep Foreground Open for Q&A)

Use when the user wants to keep chatting or working on other tasks while the job runs:

1. Start the task in the background and report `BG_PID` / `shell_id` and `LOG_FILE` in 1–2 lines.
2. **End the turn immediately** so the user prompt stays free.
3. Whenever the user sends a follow-up message (even on an unrelated topic), answer their question and piggyback a non-blocking status check:
   - **Native**: `job_output` (`wait: false`)
   - **Bash**: `ps -p <BG_PID> -o pid,%cpu,etime || true; tail -n 15 "<LOG_FILE>"`
   - **PowerShell**: `Get-Process -Id <BG_PID> -ErrorAction SilentlyContinue | Select-Object Id,CPU; Get-Content "<LOG_FILE>","<LOG_FILE>.err" -Tail 15 -ErrorAction SilentlyContinue`

### Pattern B: Scheduled Auto-Report Mode (Periodic Updates When Idle)

Use when the user asks for automatic progress reports every `N` seconds (default `15s`–`30s` if unspecified) while not interacting:

1. Start the task in the background.
2. Execute **one bounded wait + check per tool call** (substituting literal `<BG_PID>` and `<LOG_FILE>`):
   - **Bash**:
     ```bash
     for _ in $(seq 1 15); do kill -0 <BG_PID> 2>/dev/null || break; sleep 1; done
     ps -p <BG_PID> -o pid,%cpu,etime,state,comm || true
     tail -n 20 "<LOG_FILE>"
     ```
   - **PowerShell / `pwsh`**:
     ```powershell
     $p = Get-Process -Id <BG_PID> -ErrorAction SilentlyContinue
     if ($p) { $null = $p.WaitForExit(15000) }
     if ($p -and -not $p.HasExited) { $p | Select-Object Id, CPU, ProcessName } else { Write-Output "EXITED" }
     Get-Content "<LOG_FILE>", "<LOG_FILE>.err" -Tail 20 -ErrorAction SilentlyContinue
     ```
   - **Native `run_in_background`**: Run `sleep 15` (or `Start-Sleep 15`) followed by non-blocking `job_output`.
3. Emit a concise 1–3 line progress update to the user:
   - `[Running | 01m15s | PID 48210] Latest milestone...`
   - If log output has not changed but the process is still alive, report that it is actively running (`CPU` / `etime`) rather than assuming it hung.
   - When the process exits, check `__EXIT_CODE=` at the end of `<LOG_FILE>` to report success (`0`) or failure (`!= 0`).
4. Immediately invoke the next bounded check tool call and repeat until the process exits (if the task is still running after 20 ticks and the user has not requested indefinite polling, pause and ask whether to continue polling).
5. Because the task runs in an independent OS process, if the user interrupts (`Ctrl+C` / `Esc`) to ask a question, the background job continues unharmed. Answer their question and resume or switch to Pattern A as requested.
6. **Stopping or cleaning up**: To cancel a running task when requested, use native `job_kill`, Bash `pkill -TERM -P <BG_PID> 2>/dev/null || true; kill -TERM <BG_PID>`, or PowerShell `taskkill /T /F /PID <BG_PID>` (`Stop-Process` does not kill child process trees). Remove temporary `<LOG_FILE>` files once the user no longer needs the output.
