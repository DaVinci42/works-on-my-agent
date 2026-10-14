# Configuration Inventory

## Scope

This inventory maps macOS Microsoft Defender for Endpoint (`mdatp`) CLI areas to their diagnostic and optimization roles. Inspect `mdatp --help` and `mdatp config` on the target machine to confirm available subcommands and flags. Do not run leaf diagnostic commands (`hot-event-sources`, `antivirus-engine-pool-content`) with `--help`, as they start continuous monitoring immediately; inspect the parent `mdatp diagnostic` menu instead.

Names in the configuration column are subcommands under `mdatp config` unless marked as top-level.

## User-facing configuration areas

| Category | Configuration or command | Purpose and limits |
|---|---|---|
| Version and health | Top-level `version`, `health` | Inspect selected health and protection fields; filter device and org identifiers before sharing |
| Performance profiles | Top-level `performance-profiles list-available/list-applied/apply/remove` | Select supported workload presets; not arbitrary language names or a CPU ceiling |
| Performance suggestions | Top-level `performance-profiles suggestions/apply-suggestions` | Inspect product-generated suggestions first; review scope before applying |
| AV exclusions | Top-level `exclusion folder/file/extension/process`, `exclusion list` | Maintain justified AV exclusions; verify matching, parent coverage, and permissions |
| Optional reporting | `cloud-diagnostic`, `cloud-automatic-sample-submission` | Manage optional diagnostics and automatic sample submission separately from security telemetry |
| Scan scheduling | `scheduled-scan`, `scan-after-definition-update` | Check whether scheduled scans overlap the user's workload before adjusting |
| On-demand scan load | `maximum-on-demand-scan-threads`, `scan-archives` | Controls on-demand scan concurrency/archive scanning only; does not cap real-time or EDR CPU |
| Diagnostic collection | `real-time-protection-statistics`, `behavior-monitoring-statistics`, `collect-scanned-files-per-process`, `antivirus-engine-pool-content-monitoring` | Prefer existing counters; authorize and bound extra collection, then restore original values |
| Log retention | `log-rotation-parameters`; top-level `log` | Manage local log storage; does not reduce CPU or disable remote reporting |
| Security intelligence | `automatic-definitions-update`; top-level `definitions` | Manage virus definitions; definition updates do not upgrade the application binary |
| Network and proxy | `proxy`; top-level `connectivity` | Diagnose connectivity without disabling protection |

## Protection and administrative areas

Use these interfaces to understand policy boundaries and active protection layers, not as a checklist of features to disable for performance:

| Category | Configuration or command | Boundary |
|---|---|---|
| EDR management | Top-level `edr exclusion/early-preview/group-ids/tag` | Query `edr exclusion list`; local CLI has no custom `edr exclusion add` command |
| Real-time protection | `real-time-protection`, `passive-mode` | Core protection state; never disable as a routine performance fix |
| Behavior monitoring | `behavior-monitoring` | Separate from file scanning and optional diagnostic reporting |
| Cloud protection | `cloud`, `cloud-pin-certificate-thumbs` | Detection and certificate validation; never disable as a substitute for optional reporting controls |
| Network protection | `network-protection`; same top-level command | Security enforcement, separate from proxy settings |
| Data loss prevention | `data-loss-prevention`; same top-level command | Separate protection layer; AV exclusions do not apply to DLP |
| Device and tamper protection | `device-control`, `tamper-protection` | Enforced by organizational policy; do not attempt to bypass |
| File hashes | `enable-file-hash-computation` | Verify purpose and policy impact before considering changes |
| Manual scans | Top-level `scan list/quick/full/custom/cancel` | `scan list` is read-only; other subcommands start or cancel scans and require authorization |
| Support diagnostics | Top-level `diagnostic` (`create`, `upload`, `perf-trace`, statistics, `hot-event-sources`) | Do not create or upload support bundles without explicit authorization; check `/Library/Application Support/Microsoft/Defender/wdavdiag` for large stale `.zip` bundles |
| Other interfaces | Top-level `threat`, `device-control`, `system-extension`, `end-user`, `notice` | Threat handling, system extensions, and notices; inspect local help as needed |

## Change verification checklist

1. Record the original setting value privately before modifying anything.
2. Execute one authorized change at a time and capture `change_exit_status` immediately.
3. Re-query the target field and `mdatp health --field healthy` to confirm persistence and health.
4. Preserve pre-existing settings during rollback and re-verify after MDM policy sync.
