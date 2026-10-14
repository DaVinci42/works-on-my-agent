---
name: mdatp-optimization
description: Help macOS users reduce Microsoft Defender for Endpoint (mdatp) overhead, diagnose high wdavdaemon / wdavdaemon_enterprise / wdavdaemon_unprivileged CPU or fan noise during slow builds or file-heavy workloads, apply performance-profiles, maintain scoped path exclusions, and minimize optional diagnostic reporting and automatic sample submission where policy permits (包括 macOS Defender CPU 占用高、风扇狂转、编译与文件读写卡顿排查、排除项与隐私遥测优化). Verify actual settings and changes, use low-overhead diagnostics, and preserve required protection policies.
compatibility: macOS with Microsoft Defender for Endpoint and the mdatp CLI. Some operations require administrator privileges or organizational authorization.
---

# Microsoft Defender Performance Optimization

## User-facing priorities

Prioritize a responsive machine, low-overhead diagnosis, and minimal optional data sharing. Start with existing local counters and short process samples. Do not enable persistent verbose logging, additional collection, or support uploads by default. Explain proposed changes in terms of user benefit, security or privacy tradeoffs, and measured outcomes, rather than presenting an enterprise policy checklist.

A request to edit this skill does not authorize changing the machine. A request to test or apply privacy settings does authorize the specified supported changes; report what actually persisted. Read the privacy section below before making claims about telemetry controls.

## Boundaries

- **Read-only by default**: Keep diagnosis and explanations read-only. Apply changes only when requested, and explain that profiles and exclusions may reduce monitoring coverage.
- **Layer separation**: Distinguish antivirus (AV), endpoint detection and response (EDR), behavior monitoring, and data loss prevention (DLP). `mdatp exclusion` only manages AV; it does not exclude EDR or DLP. Process names alone do not identify every source of CPU time.
- **Scoped configuration**: Check the installed version and available commands first. Prefer profiles for toolchains the user actually uses rather than enabling every language or broad IDE process-tree exclusions by default.
- **Policy & privilege respect**: Respect `[managed]` settings. Administrator privileges do not guarantee permission to override policy. Do not bypass MDM or tamper protection, stop security services, or change protected file permissions.
- **Verification discipline**: Always capture the immediate exit status of any changing command (`printf 'change_exit_status=%s\n' "$?"`) before running verification queries. Treat `healthy: true` as product health, not proof that a change succeeded, matched a workload, or reduced CPU.
- **Privacy & sanitization**: Redact organization IDs, device IDs, credentials, and sensitive paths before output reaches the assistant. Do not upload support bundles, start scans, stop builds, or clear caches without authorization.
- **Portability**: Respond in the user's language. Keep installation paths and machine-specific assumptions out of this skill.

## Choose the investigation scope

- **Compilation, tests, or dependency installation**: Inspect workload profiles (`performance-profiles`) and live event sources.
- **Indexing, synchronization, or file-heavy tasks**: Identify the actual hot paths before considering scoped AV exclusions.
- **Periodic spikes**: Inspect on-demand scans (`mdatp scan list`) and scheduling (`scheduled-scan`, `scan-after-definition-update`) rather than assuming real-time protection is responsible.

## 1. Establish a read-only baseline

Run only the queries relevant to the user's request, not the entire checklist automatically:

```bash
set -o pipefail
command -v mdatp
mdatp version
mdatp health | /usr/bin/awk '/^(healthy|health_issues|cloud_enabled|cloud_diagnostic_enabled|cloud_automatic_sample_submission_consent|real_time_protection_enabled|behavior_monitoring|tamper_protection|data_loss_prevention_status|managed_by) +:/'
mdatp scan list
mdatp exclusion list
mdatp edr exclusion list all
mdatp performance-profiles list-available
mdatp performance-profiles list-applied
mdatp performance-profiles suggestions
```

The `awk` filter retains management markers while omitting device and organization identifiers before output reaches the assistant. Using `set -o pipefail` ensures an upstream `mdatp` failure is not masked by `awk`; if filtered output is empty, inspect the upstream error rather than assuming healthy or disabled protection. Exclusion lists, scan records, process lists, and event sources can still reveal private paths; redact or aggregate locally when needed.

If an interface is unavailable, inspect its parent menu and continue with supported diagnostics. Do not install or upgrade software just to obtain a missing command.

```bash
ps -axo pid,ppid,%cpu,etime,comm -r
```

Identify Defender's main (`wdavdaemon`), enterprise (`wdavdaemon_enterprise`), and unprivileged (`wdavdaemon_unprivileged`) processes alongside the workload's processes. Trace parents with `ps -p PID -o pid,ppid,%cpu,etime,args` when needed (redact secrets in arguments).

Sample a specific process (`PID`):

```bash
top -l 4 -s 3 -pid PID -stats pid,command,cpu,time,threads
```

On macOS, 100% process CPU represents roughly one logical core; adding process percentages does not produce a whole-machine percentage. Ignore the initial zero-CPU sample from `top`, and record system idle time, build phase, and concurrency.

## 2. Identify the workload

```bash
mdatp diagnostic event-provider-statistics
mdatp diagnostic real-time-protection-statistics
mdatp diagnostic behavior-monitoring-statistics
```

- `No Data` means statistics collection is unavailable or disabled, not that scanning is absent.
- An empty `mdatp scan list` does not rule out real-time scanning.
- Event and dropped-message counters may cover the service's lifetime; compare increments across a workload run before attributing them to current activity.
- Logs commonly reside in `/Library/Logs/Microsoft/mdatp`. Previously generated diagnostic bundles (`mdatp diagnostic create`) can accumulate hundreds of megabytes per `.zip` in `/Library/Application Support/Microsoft/Defender/wdavdiag`. Inspect directory size in read-only mode and report stale bundle storage to the user; do not delete bundles or change protected directory permissions without authorization.

When live sources are needed, run `mdatp diagnostic hot-event-sources` for a bounded 10 to 30 seconds using the runner's background-job controls or a verified timeout utility, cap retained output, and stop only the diagnostic process you started.

**Gotchas**:
- Diagnostic leaf commands such as `hot-event-sources` and `antivirus-engine-pool-content` start continuous monitoring immediately, even when passed `--help`. Inspect the parent `mdatp diagnostic` menu first and bound execution.
- When `hot-event-sources` terminates (on SIGINT/SIGTERM), it writes a `hot_event_source_<UUID>.txt` report containing full local paths into the current working directory. Run it from a temporary directory or delete generated `hot_event_source_*.txt` files immediately so private paths are never left in a Git worktree.

Enable additional statistics (`config real-time-protection-statistics`, `behavior-monitoring-statistics`, or `collect-scanned-files-per-process`) only with user authorization for collection overhead. Verify accepted arguments, record original values, and restore only temporary diagnostic changes introduced for the investigation.

## 3. Apply built-in performance profiles

Inspect available, applied, and product-suggested profiles before making changes. Review the scope of `mdatp performance-profiles suggestions` rather than blindly running `apply-suggestions`.

```bash
mdatp performance-profiles list-available
mdatp performance-profiles list-applied
mdatp performance-profiles suggestions
mdatp performance-profiles apply --name rust
printf 'change_exit_status=%s\n' "$?"
mdatp performance-profiles list-applied
mdatp health --field healthy
```

Replace `rust` with an exact name from `list-available`. Skip profiles already present in `list-applied` and record only newly added profiles for rollback.

Candidate profile names to check in `list-available` (not a guaranteed catalog; names do not establish exact path, signature, or child-process matching rules):

| Candidate workload | Profile names |
|---|---|
| Rust | `rust` |
| Xcode toolchain | `xcode` |
| Code signing | `codesign` |
| Make and Unix build tools | `make-tree`, `unix-utils` |
| Git and GitHub CLI | `git`, `github-cli` |
| .NET | `dotnet-build` |
| Java compiler | `openjdk-javac` |
| Android Studio | `android-studio` |
| Go workloads | `google-golang`, `mason-golang`, `sap-golang` (do not assume interchangeability) |
| Node.js and package tools | `node`, `pnpm`, `volta` |
| Containers and virtualization | `docker`, `homebrew-podman`, `podman-desktop`, `macos-container` |
| Ruby | `ruby` |
| Flutter / Dart | `flutter-dart` |
| AI coding CLIs and IDEs | `claude-code-cli`, `openai-codex`, `open-code`, `cursor`, `vscode` |

Tree-oriented profiles affect multiple executables and are not CPU limiters; explain their monitoring coverage impact. If elevation is required and the runner prohibits `sudo`, report the restriction and provide commands for the user's terminal rather than bypassing it.

When removal is requested, preserve pre-existing profiles unless their removal was also authorized:

```bash
mdatp performance-profiles remove --name rust
printf 'change_exit_status=%s\n' "$?"
mdatp performance-profiles list-applied
mdatp health --field healthy
```

Recheck after upgrades, restarts, or policy synchronization, as local changes may not persist.

### Optional environment-specific notes

Apply the subsections below **only** when the user's request or local process/event evidence involves that environment:

- **Python**: Do not assume a generic `python` or version-specific (`python3`) performance profile exists. Query `list-available` instead of guessing names. If a request returns `Profile name not found in available profiles`, report the unsupported name rather than substituting `jetbrains-pycharm-tree` (which is specific to PyCharm) or adding broad interpreter exclusions. Interpreters execute dependency installation scripts and arbitrary code; an AV exclusion named `python` also does not prove matching for version-suffixed interpreters.
- **Custom package managers and non-standard prefixes (e.g., Homebrew, Nix / `nix-darwin`, MacPorts)**: Built-in profiles may match by Apple signing ID or standard system paths rather than custom store or cellar paths (`/opt/homebrew`, `/nix/store`). If the machine uses Nix or similar immutable store layouts, see the optional section in [references/exclusions.md](references/exclusions.md) for symlink resolution and AV-vs-EDR store boundaries.

## 4. Maintain AV exclusions and respect EDR boundaries

Add an AV exclusion only when evidence points to AV overhead, the user authorizes it, and the scope is justified. Prefer specific generated-output directories over home directories or entire source trees. Check for existing parent-directory coverage first (for example, adding `/absolute/project/build/cache` when `/absolute/project/build` is already excluded adds no scope).

**CLI syntax note**: The top-level AV exclusion interface uses `folder` or `file` (`mdatp exclusion folder add --path ...` / `mdatp exclusion file add --path ...`), **not** `mdatp exclusion path add` (which fails with `Unrecognized command 'path'`; `paths` is only a read-only subcommand under `mdatp edr exclusion list paths`). Always pass an expanded absolute path rather than `./`.

```bash
mdatp exclusion list
mdatp exclusion folder add --path "/absolute/project/build"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

When removal is requested:

```bash
mdatp exclusion folder remove --path "/absolute/project/build"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

For path normalization (tilde expansion, symlinks), file/extension/process exclusions, and maintenance rules, read [references/exclusions.md](references/exclusions.md).

Inspect the EDR exclusion menu where supported:

```bash
mdatp edr exclusion list all
mdatp edr exclusion list processes
mdatp edr exclusion list paths
mdatp edr exclusion list extensions
```

Do not invent `mdatp edr exclusion add` or undocumented plist keys. Built-in performance profiles use a separate interface and can succeed even when custom EDR exclusions have no local add command. Use the organization's management process for custom EDR exclusions.

## 5. Verify performance, not just configuration

1. Record sanitized versions, profiles, exclusions, and protection status before and after changes.
2. Compare identical authorized workloads with the same inputs, cache state, concurrency, power conditions, and clean/incremental build mode.
3. Sample each state for at least 30 to 60 seconds when possible; report duration, Defender CPU mean and peak, system idle time, and event sources.
4. Confirm after each change that real-time protection, behavior monitoring, tamper protection, and DLP did not change unexpectedly.
5. Without comparable measurements, report: `"Configuration applied; performance benefit not verified."` A workload becoming idle (e.g., system idle rising while CPU drops) is not evidence that profiles reduced overhead.
6. For persistent unexplained overhead, provide sanitized evidence (version, time window, toolchain, configuration, metrics) to organizational IT or Microsoft support rather than continually broadening exclusions.

Do not assume a global CPU ceiling exists for real-time protection or EDR. `maximum-on-demand-scan-threads` controls only on-demand scan threads; do not apply Windows-specific scan CPU settings to macOS.

## 6. Minimize optional reporting, where policy permits

Distinguish optional diagnostic reporting (`cloud-diagnostic`), automatic file sample submission (`cloud-automatic-sample-submission`), cloud-delivered protection (`cloud`), and EDR security telemetry. Disabling optional diagnostics does not produce zero telemetry, and disabling automatic samples may affect cloud-assisted investigation or detection. Never disable cloud protection, behavior monitoring, EDR, or DLP as a substitute for optional reporting controls, and do not promise a CPU reduction from telemetry changes without measurement.

Inspect current values and local help first:

```bash
mdatp health --field cloud_diagnostic_enabled
mdatp health --field cloud_automatic_sample_submission_consent
mdatp config cloud-diagnostic --help
mdatp config cloud-automatic-sample-submission --help
```

When authorized to reduce optional reporting, apply one setting at a time and check both the command exit status and the resulting health field:

```bash
mdatp config cloud-diagnostic --value disabled
printf 'change_exit_status=%s\n' "$?"
mdatp health --field cloud_diagnostic_enabled
mdatp health --field healthy
```

Automatic sample submission is a separate authorized change:

```bash
mdatp config cloud-automatic-sample-submission --value disabled
printf 'change_exit_status=%s\n' "$?"
mdatp health --field cloud_automatic_sample_submission_consent
mdatp health --field healthy
```

If a command returns a non-zero exit status or `This setting is managed by your organization`, stop attempts on that setting and report the policy rejection. Report only the privilege level actually tested; do not claim administrator execution was tested when it was not.

Record the original semantic health value (for example, `cloud_automatic_sample_submission_consent` may report `all` rather than `enabled`), as re-enabling via CLI later may not restore a previous managed or custom consent state.

### Interpret the result

For each attempted change, report:
- Prior value
- Command exit status (`change_exit_status`)
- Resulting value
- Protection health (`healthy`)

If a command is rejected and the value is unchanged, report that no change occurred and do not invent a rollback step. Report privacy changes separately from performance changes.

## Reference and output

Read [references/configuration.md](references/configuration.md) for the full configuration and administrative command inventory. When evolving this skill from local operator history, run `bash scripts/collect-history-signals.sh` to extract sanitized command shapes, active toolchains, and diagnostic bundle sizes without exposing private paths. Summarize confirmed evidence, successful and rejected changes, protection status, whether performance was measured comparably, and any remaining access or verification limits.
