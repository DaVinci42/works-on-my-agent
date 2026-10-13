---
name: mdatp-optimization
description: Help macOS users reduce Microsoft Defender for Endpoint overhead, diagnose high wdavdaemon CPU, and minimize optional diagnostic reporting and automatic sample submission where policy permits. Use for slow builds or file-heavy workloads, path exclusions and allowlists, performance-profiles, privacy or telemetry preferences, and maintenance. Verify actual settings and changes, use low-overhead diagnostics, and preserve required protection policies.
compatibility: macOS with Microsoft Defender for Endpoint and the mdatp CLI. Some operations require administrator privileges or organizational authorization.
---

# Microsoft Defender Performance Optimization

## User-facing priorities

Prioritize a responsive machine, low-overhead diagnosis, and minimal optional data sharing. Start with existing local counters and short process samples. Do not enable persistent verbose logging, additional collection, or support uploads by default. Explain proposed changes in terms of user benefit, security or privacy tradeoffs, and measured outcomes, rather than presenting an enterprise policy checklist.

A request to edit this skill does not authorize changing the machine. A request to test or apply privacy settings does authorize the specified supported changes; report what actually persisted. Read the privacy section below before making claims about telemetry controls.

## Boundaries

- Keep diagnosis and explanations read-only. Apply changes only when requested, and explain that profiles and exclusions may reduce monitoring coverage.
- Check the installed version and available commands. Command availability and behavior can vary by release and policy.
- Distinguish antivirus (AV), endpoint detection and response (EDR), behavior monitoring, and data loss prevention (DLP). AV exclusions do not imply EDR or DLP exclusions. Process names alone do not identify every source of CPU time.
- Prefer profiles for toolchains the user actually uses. Do not enable every language or broad IDE process-tree exclusions by default.
- Respect `[managed]` settings. Administrator privileges do not guarantee permission to override policy. Do not bypass MDM or tamper protection, stop security services, or change protected file permissions.
- Treat `healthy: true` as product health, not proof that exclusions preserve detection coverage.
- Do not upload support bundles, start scans, stop builds, or clear caches without authorization. Redact organization IDs, device IDs, credentials, and sensitive paths.
- Respond in the user's language. Keep installation paths and machine-specific assumptions out of this portable skill.

## Choose the investigation scope

For compilation, tests, or dependency installation, inspect workload profiles and event sources. For indexing, synchronization, or other file-heavy tasks, identify the actual hot paths before considering exclusions. For periodic spikes, inspect on-demand scans and scheduling rather than assuming real-time protection is responsible. Use the configuration inventory for supported categories, not as a list of settings to change wholesale.

## 1. Establish a read-only baseline

```bash
command -v mdatp
mdatp version
mdatp health | /usr/bin/awk '/^(healthy|health_issues|cloud_enabled|cloud_diagnostic_enabled|cloud_automatic_sample_submission_consent|real_time_protection_enabled|behavior_monitoring|tamper_protection|data_loss_prevention_status|managed_by) +:/'
mdatp scan list
mdatp exclusion list
mdatp edr exclusion list all
mdatp performance-profiles list-available
mdatp performance-profiles list-applied
```

Run only the queries relevant to the user's request, not the entire checklist automatically. The health filter retains management markers while omitting device identifiers before output reaches the assistant. Exclusion lists, scan records, process lists, and event sources can still reveal private paths or applications; inspect locally and redact or aggregate before sharing when needed. A pipeline's final exit status does not prove that `mdatp` succeeded; empty filtered output requires checking the upstream error, not assuming healthy or disabled protection.

If an interface is unavailable, inspect its parent menu and continue with supported diagnostics. Do not install or upgrade software just to obtain a missing command.

```bash
ps -axo pid,ppid,%cpu,etime,comm -r
```

Identify Defender's main, enterprise, and unprivileged processes and the workload's processes. Trace parents with `ps -p PID -o pid,ppid,%cpu,etime,args` when needed. Arguments can contain secrets; do not publish them indiscriminately.

Replace `PID` with a current process ID:

```bash
top -l 4 -s 3 -pid PID -stats pid,command,cpu,time,threads
```

On macOS, 100% process CPU represents roughly one logical core. Adding process percentages does not produce a whole-machine percentage. Ignore the initial zero-CPU sample from `top`. Record system idle time, build phase, and concurrency too.

## 2. Identify the workload

```bash
mdatp diagnostic event-provider-statistics
mdatp diagnostic real-time-protection-statistics
mdatp diagnostic behavior-monitoring-statistics
```

- `No Data` means statistics are unavailable, not that scanning is absent.
- An empty scan list does not rule out real-time scanning.
- Event and dropped-message counters may cover the service's lifetime. Compare increments before attributing them to current activity.
- Logs commonly reside in `/Library/Logs/Microsoft/mdatp`. Report access restrictions instead of changing permissions.

Use `mdatp diagnostic hot-event-sources` for a bounded 10 to 30 seconds when live sources are needed. Use the runner's background-job controls or a verified timeout utility, cap retained output, and stop only the diagnostic process you started.

Diagnostic leaf commands, including `hot-event-sources` and `antivirus-engine-pool-content`, may start continuous monitoring rather than display help. Inspect the `mdatp diagnostic` parent menu first and bound execution; do not assume leaf-command `--help` exits immediately.

Enable additional statistics only with authorization for collection overhead. Verify arguments for `config real-time-protection-statistics`, `behavior-monitoring-statistics`, or `collect-scanned-files-per-process`. Record original values and restore only temporary diagnostic changes introduced for this investigation.

## 3. Apply built-in performance profiles

```bash
mdatp performance-profiles list-available
mdatp performance-profiles list-applied
mdatp performance-profiles apply --name rust
printf 'change_exit_status=%s\n' "$?"
mdatp performance-profiles list-applied
mdatp health --field healthy
```

Replace `rust` with an exact name from the current available list. Check the printed change exit status, success message, and applied list after each change. These snippets display errors for interactive review; automation must capture the change status and branch on failure rather than returning the status of the final health check. Skip profiles already present and record additions for a user-requested rollback.

The following names are candidates to check in the current available list, not a guaranteed catalog. Names suggest workloads; they do not establish executable-path, signature, or child-process matching rules. Consult documentation or state that matching remains unverified.

| Candidate workload | Profile names |
|---|---|
| Rust | `rust` |
| Xcode toolchain | `xcode` |
| Make build trees | `make-tree` |
| .NET | `dotnet-build` |
| Java compiler | `openjdk-javac` |
| Android Studio | `android-studio` |
| Go-related workloads | `google-golang`, `mason-golang`, `sap-golang`; do not assume interchangeability |
| Node.js and package tools | `node`, `pnpm`, `volta` |
| Ruby | `ruby` |
| Flutter / Dart | `flutter-dart` |

Tree-oriented profiles can affect more than one executable. Explain the coverage impact. They are not CPU limiters, and successful application does not prove a custom toolchain installation matches their rules.

Profile application may or may not require elevation depending on the installed version and policy. Use only permitted elevation mechanisms. If the runner prohibits `sudo`, report the restriction and provide instructions for the user's terminal when appropriate; do not bypass it.

When removal is requested:

```bash
mdatp performance-profiles remove --name rust
printf 'change_exit_status=%s\n' "$?"
mdatp performance-profiles list-applied
mdatp health --field healthy
```

Preserve pre-existing settings unless removal is authorized. Recheck after upgrades, restarts, or policy synchronization; local settings may not persist.

### Python

Do not assume a generic `python` or version-specific Python performance profile exists. Query the available list instead of repeatedly guessing names. If a request returns `Profile name not found in available profiles`, report the unsupported name rather than adding a broad exclusion as a substitute.

If listed, `jetbrains-pycharm-tree` is a PyCharm candidate, not a generic Python profile. An AV exclusion named `python` does not prove it matches a version-suffixed interpreter. Do not automatically exclude every interpreter: interpreters execute dependency installation scripts and arbitrary code.

## 4. Maintain AV exclusions and respect EDR boundaries

Add an AV exclusion only when evidence points to AV overhead, the user authorizes it, and the scope is justified. Prefer necessary generated-output directories over home directories or entire source trees.

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

For path selection, file exclusions, extension exclusions, process exclusions, and maintenance checks, read [references/exclusions.md](references/exclusions.md). Its commands are examples to execute only after authorization. Verify arguments locally. Do not invent wildcard, recursive, process-name, or child-process inheritance semantics. Changes may require privileges.

Check for existing parent-directory exclusions. For example, adding `/absolute/project/build/cache` when `/absolute/project/build` already covers it adds no scope. These are illustrative paths, not recommended defaults. Do not remove existing exclusions without authorization.

Inspect the EDR exclusion menu. Where supported, these commands query exclusions:

```bash
mdatp edr exclusion list all
mdatp edr exclusion list processes
mdatp edr exclusion list paths
mdatp edr exclusion list extensions
```

Do not invent `edr exclusion add` or undocumented plist keys. Built-in profile application can succeed even when custom EDR exclusions have no local add command. Profile rules and affected protection layers still require verification. Use the organization's supported management process for custom managed exclusions.

## 5. Verify performance, not just configuration

1. Record versions, profiles, exclusions, and protection status before and after changes. Retain only necessary, sanitized data.
2. Compare identical authorized workloads with the same inputs, cache state, concurrency, and power conditions. For builds, also preserve code, dependency versions, and clean/incremental mode. Do not clear caches or rerun expensive work without permission.
3. Sample each state for at least 30 to 60 seconds when possible. Prefer repeated comparable builds; report duration, Defender CPU mean and peak, system idle time, and event sources.
4. Verify the applied list and health immediately after each change. Check that real-time protection, behavior monitoring, tamper protection, and DLP did not change unexpectedly.
5. Without comparable measurements, report: "Configuration applied; performance benefit not verified." A build becoming idle is not evidence that profiles reduced CPU.
6. For persistent unexplained overhead, provide sanitized version, time window, toolchain, configuration, and performance evidence to organizational IT or Microsoft support. Do not keep broadening exclusions to conceal the issue.

Do not assume a general CPU ceiling exists for real-time protection or EDR. If available, `maximum-on-demand-scan-threads` controls only on-demand scan threads; check local help for accepted values. It is not a global CPU limit. Do not apply Windows-specific scan CPU settings to macOS.

## 6. Minimize optional reporting, where policy permits

Distinguish optional diagnostic reporting, automatic file sample submission, cloud-delivered protection, and EDR security telemetry. They are not one switch. Disabling optional diagnostics does not establish zero telemetry; disabling automatic samples can reduce data sharing but may affect cloud-assisted investigation or detection. Do not turn off cloud protection, behavior monitoring, EDR, or DLP as a substitute for optional reporting controls, and do not promise a CPU improvement without measurement.

Inspect the current values and management markers locally. Share only relevant, sanitized health fields with the user; do not upload raw health output or logs. Data passed to an assistant or its provider is still data disclosure even when no support bundle is uploaded.

```bash
mdatp health --field cloud_diagnostic_enabled
mdatp health --field cloud_automatic_sample_submission_consent
mdatp config cloud-diagnostic --help
mdatp config cloud-automatic-sample-submission --help
```

Verify that local help lists `enabled` and `disabled` for both commands before using the examples. When the user authorizes reducing optional reporting, try one setting at a time and immediately check the exit status and resulting health field:

```bash
mdatp config cloud-diagnostic --value disabled
printf 'change_exit_status=%s\n' "$?"
mdatp health --field cloud_diagnostic_enabled
mdatp health --field healthy
```

Automatic sample submission is a separate, authorized change:

```bash
mdatp config cloud-automatic-sample-submission --value disabled
printf 'change_exit_status=%s\n' "$?"
mdatp health --field cloud_automatic_sample_submission_consent
mdatp health --field healthy
```

Do not infer success from valid syntax. If the command says `This setting is managed by your organization`, stop attempts on that setting and explain the policy boundary. Do not bypass management or retry through protected files. A permissions error without a policy rejection is a different condition; use only authorized, permitted elevation mechanisms. Report only the privilege level actually tested; do not claim an administrator attempt occurred when it did not.

Record the original semantic value, not just the CLI argument. The sample-consent health field can report `all` rather than `enabled`. Do not assume enabling later restores an arbitrary previous managed or consent state. Preserve successful user-requested privacy changes unless reversal is requested; restore temporary diagnostic collection only when its original value is known.

### Interpret the result

For each attempted change, report the prior value, command exit status, resulting value, and whether protection remained healthy. If a command is rejected and the value is unchanged, report no successful change and do not invent a rollback requirement. If a command succeeds, verify its resulting value and recheck after policy synchronization when relevant.

Permission to apply performance profiles does not imply permission to change reporting or sample-submission policy. Report privacy changes separately from performance changes and list any required organizational action without presenting it as a completed local optimization.

## Reference and output

Read [references/configuration.md](references/configuration.md) for the configuration inventory. Examples are illustrative, not records of a particular device or guarantees about the installed version.

Report confirmed evidence, successful and failed changes, protection status, whether performance was measured comparably, and remaining access or verification limits. Do not invent community findings or promise an unmeasured improvement.
