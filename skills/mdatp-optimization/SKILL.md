---
name: mdatp-optimization
description: >-
  Help macOS users reduce Microsoft Defender for Endpoint (mdatp) overhead, diagnose high wdavdaemon / wdavdaemon_enterprise / wdavdaemon_unprivileged CPU or fan noise during slow builds or file-heavy workloads, apply performance-profiles, maintain scoped path exclusions, and minimize optional diagnostic reporting and automatic sample submission where policy permits (包括 macOS Defender CPU 占用高、风扇狂转、编译与文件读写卡顿排查、排除项与隐私遥测优化).
  Verify actual settings and changes, use low-overhead diagnostics, and preserve required protection policies.
compatibility: macOS with Microsoft Defender for Endpoint and the mdatp CLI. Some operations require administrator privileges or organizational authorization.
---

# Microsoft Defender Performance Optimization (macOS)

## Core Boundaries

- **Read-only by default**: Editing this skill never authorizes host changes. Apply changes only when requested (testing/applying privacy settings authorizes those supported changes), and explain security/privacy tradeoffs concisely.
- **Separate protection layers**: Distinguish AV (`mdatp exclusion`), EDR (`mdatp edr exclusion`), behavior monitoring, DLP, and network protection (`com.microsoft.wdav.netext`). AV exclusions never suppress EDR Endpoint Security (`AUTH_EXEC`/`AUTH_OPEN`), DLP, or socket-level network blocks (e.g., `Errno 57: Socket is not connected` on package registries).
- **Respect policy (explicit & implicit)**: Respect `[managed]` markers, MDM, and tamper protection. Some settings (such as `data-loss-prevention` or `scan-after-definition-update`) can reject local changes even without a `[managed]` label. Never stop security daemons, change protected permissions, or bypass policy; if `sudo` is blocked by the runner, provide commands for the user's terminal.
- **Verification discipline**: Capture the immediate exit status (`printf 'change_exit_status=%s\n' "$?"`) before running verification queries—`healthy: true` proves product health, not that a change succeeded or reduced CPU.
- **Low-overhead & privacy-first**: Filter device/org IDs before output reaches the assistant; redact private paths/secrets; never enable persistent verbose logging, create/upload support bundles, or delete files without authorization.

## 1. Read-Only Baseline

Run only queries relevant to the user's symptom (builds -> `performance-profiles` + event sources; file sync -> hot paths + AV exclusions; periodic spikes -> `mdatp scan list` + `scheduled-scan` / `scan-after-definition-update`):

```bash
set -o pipefail
mdatp version
mdatp health | /usr/bin/awk '/^(healthy|health_issues|cloud_enabled|cloud_diagnostic_enabled|cloud_automatic_sample_submission_consent|real_time_protection_enabled|behavior_monitoring|tamper_protection|data_loss_prevention_status|managed_by) +:/'
mdatp scan list
mdatp exclusion list
mdatp edr exclusion list all
mdatp performance-profiles list-available
mdatp performance-profiles list-applied
mdatp performance-profiles suggestions
```

`set -o pipefail` prevents `awk` from masking `mdatp` failures; if output is empty, inspect the upstream error. Check process CPU (`100%` on macOS ≈ 1 logical core; ignore sample 1 of `top` and record system idle %):

```bash
ps -axo pid,ppid,%cpu,etime,comm -r | head -n 25
top -l 4 -s 3 -pid <PID> -stats pid,command,cpu,time,threads
```

## 2. Workload & Bounded Event Diagnostics

```bash
mdatp diagnostic event-provider-statistics
mdatp diagnostic real-time-protection-statistics
mdatp diagnostic behavior-monitoring-statistics
```

- `No Data` means statistics collection is disabled/unavailable, not that scanning is absent; compare counter deltas across a workload run rather than lifetime totals.
- Check `/Library/Application Support/Microsoft/Defender/wdavdiag` size in read-only mode for stale multi-hundred-MB `.zip` diagnostic bundles; report storage waste without deleting unauthorized.
- **Bounded `hot-event-sources` (zero worktree residue)**: Leaf diagnostic commands (`hot-event-sources`, `antivirus-engine-pool-content`) run continuously even with `--help` and write `hot_event_source_<UUID>.txt` containing full paths into `$PWD` on exit. Always isolate in a temp directory, bound to ~10s, stop only that PID, and clean up immediately:
  ```bash
  DIAG_TMP="$(mktemp -d "${TMPDIR:-/tmp}/mdatp_hot.XXXXXX")"
  ( cd "$DIAG_TMP" && mdatp diagnostic hot-event-sources >out.log 2>&1 ) &
  DIAG_PID=$!
  sleep 10
  kill -INT "$DIAG_PID" 2>/dev/null || true
  wait "$DIAG_PID" 2>/dev/null || true
  tail -n 30 "$DIAG_TMP"/out.log "$DIAG_TMP"/hot_event_source_*.txt 2>/dev/null || true
  rm -rf "$DIAG_TMP"
  ```
  *(Redact sensitive local paths before sharing; enable extra `config *-statistics` only with user authorization and restore original values afterward.)*

## 3. Built-In Performance Profiles

Inspect `list-available`, `list-applied`, and `suggestions` first (review `suggestions` scope rather than blindly running `apply-suggestions`; skip already-applied profiles and record only newly added ones for rollback; see [references/configuration.md](references/configuration.md) for common profile names):

```bash
mdatp performance-profiles apply --name <exact-profile-name>
printf 'change_exit_status=%s\n' "$?"
mdatp performance-profiles list-applied
mdatp health --field healthy
```

- To roll back, run `mdatp performance-profiles remove --name <added-profile>` (preserving pre-existing profiles) and recheck after policy sync/upgrades.
- **Conditional environment notes** (apply only when detected):
  - **Python**: No generic `python`/`python3` profile exists; if `list-available` lacks a requested name, report it rather than substituting `jetbrains-pycharm-tree` or adding unsafe broad interpreter exclusions.
  - **Custom stores (`/nix`, `/opt/homebrew`, `/opt/local`)**: Built-in profiles may match Apple signing IDs or standard paths rather than store paths; see [references/exclusions.md](references/exclusions.md) for symlink resolution and `/nix/store` AV-vs-EDR boundaries.

## 4. Scoped AV Exclusions & EDR Boundaries

Require hotspot evidence, user authorization, parent-directory deduplication, tilde expansion (`"$HOME/..."`, never quoted `"~/..."`), and symlink inspection (full rules and file/extension/process syntax in [references/exclusions.md](references/exclusions.md)):

- **CLI gotcha**: Use `folder` or `file` with an expanded absolute path—`mdatp exclusion path add` fails with `Unrecognized command 'path'` (`paths` exists only under read-only `mdatp edr exclusion list paths`):
  ```bash
  mdatp exclusion folder add --path "/absolute/project/build"
  printf 'change_exit_status=%s\n' "$?"
  mdatp exclusion list
  mdatp health --field healthy
  ```
  *(Use `folder remove --path ...` to remove authorized entries.)*
- **EDR**: Query `mdatp edr exclusion list {all,processes,paths,extensions}`. Local CLI has **no** `mdatp edr exclusion add` command—never invent one or edit protected plists; custom EDR exclusions require MDM/Intune.

## 5. Performance Verification

Compare identical authorized workloads (same inputs, cache state, concurrency, power, clean vs. incremental mode) over 30–60s samples, recording Defender CPU mean/peak, system idle %, event sources, and unchanged protection flags. Without comparable before/after runs (or if CPU dropped simply because system idle rose), state: `"Configuration applied; performance benefit not verified."` `maximum-on-demand-scan-threads` affects on-demand scans only—there is no real-time/EDR CPU cap.

## 6. Optional Reporting & Privacy Controls

Separate optional diagnostics (`cloud-diagnostic`) and automatic sample submission (`cloud-automatic-sample-submission`) from core `cloud` protection and EDR security telemetry: disabling optional reporting never yields zero telemetry or guaranteed CPU gains, and core `cloud`/EDR/behavior-monitoring/DLP must never be disabled as substitutes.

Record original semantic values first (e.g., `cloud_automatic_sample_submission_consent` may be `all`, which CLI re-enabling cannot always restore), then apply authorized changes one by one:

```bash
mdatp health --field cloud_diagnostic_enabled
mdatp health --field cloud_automatic_sample_submission_consent
mdatp config cloud-diagnostic --value disabled
printf 'change_exit_status=%s\n' "$?"
mdatp health --field cloud_diagnostic_enabled
mdatp health --field healthy
```
*(Repeat analogously for `mdatp config cloud-automatic-sample-submission --value disabled` and `cloud_automatic_sample_submission_consent` when authorized.)*

On non-zero exit or `This setting is managed by your organization`, stop attempts on that setting, report the rejection (with prior value, `change_exit_status`, resulting value, `healthy`, and only the privilege level actually tested), and invent no rollback for unchanged settings.

## References & History Evolution

- [references/configuration.md](references/configuration.md): Full `mdatp` CLI/config inventory and candidate `performance-profiles` table.
- [references/exclusions.md](references/exclusions.md): Path/symlink normalization, file/extension/process exclusions, and optional Nix/Homebrew store notes.
- `bash scripts/collect-history-signals.sh`: Read-only sanitized local history extractor used when evolving this skill.
