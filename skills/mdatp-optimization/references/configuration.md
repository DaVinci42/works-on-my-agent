# Configuration Inventory

## Scope

This inventory is a navigation aid for macOS Microsoft Defender for Endpoint, not a complete cross-platform specification. Discover supported commands and accepted values on the installed release. Examples do not describe a particular device, organization, or measured performance result.

Inspect `mdatp --help` and `mdatp config`, then the relevant submenu. Do not execute changes merely to enumerate settings. Help may return a nonzero status; some diagnostic leaf commands can start monitoring even with `--help`.

Names in the configuration column are subcommands under `mdatp config` unless marked as top-level. Presence in this inventory does not guarantee availability or permission to modify a setting.

## User-facing configuration areas

| Category | Configuration or command | Purpose and limits |
|---|---|---|
| Version and health | Top-level `version`, `health` | Inspect selected health and protection fields; filter device identifiers before sharing |
| Performance profiles | Top-level `performance-profiles list-available/list-applied/apply/remove` | Select supported workload presets; not arbitrary language names or a CPU ceiling |
| Performance suggestions | Top-level `performance-profiles suggestions/apply-suggestions` | Inspect suggestions if enabled; review scope before applying |
| AV exclusions | Top-level `exclusion folder/file/extension/process`, `exclusion list` | Maintain justified exclusions; verify matching, existing coverage, and permissions |
| Optional reporting | `cloud-diagnostic`, `cloud-automatic-sample-submission` | Review optional diagnostics and automatic samples separately from security telemetry |
| Scan scheduling | `scheduled-scan`, `scan-after-definition-update` | Establish whether scheduled work overlaps the user's workload before adjusting |
| On-demand scan load | `maximum-on-demand-scan-threads`, `scan-archives` | Does not cap real-time or EDR CPU; changing scan coverage has security consequences |
| Diagnostic collection | `real-time-protection-statistics`, `behavior-monitoring-statistics`, `collect-scanned-files-per-process`, `antivirus-engine-pool-content-monitoring` | Prefer existing data; authorize and bound extra collection, then restore temporary changes |
| Log retention | `log-rotation-parameters`; top-level `log` | Manage local log storage; not proof of reduced CPU or disabled remote reporting |
| Security intelligence | `automatic-definitions-update`; top-level `definitions` | Keep definitions current; definition updates do not upgrade the application |
| Network and proxy | `proxy`; top-level `connectivity` | Diagnose connectivity without treating high CPU as grounds to disable protection |

## Protection and administrative areas

These interfaces help distinguish policy boundaries from user-facing optimization. They are not a checklist of features to disable.

| Category | Configuration or command | Boundary |
|---|---|---|
| EDR management | Top-level `edr exclusion/early-preview/group-ids/tag` | Inspect supported exclusion queries; do not invent custom local add commands |
| Real-time protection | `real-time-protection`, `passive-mode` | Changes protection behavior, not a routine performance optimization |
| Behavior monitoring | `behavior-monitoring` | Separate from file scanning and optional diagnostic reporting |
| Cloud protection | `cloud`, `cloud-pin-certificate-thumbs` | Detection and certificate validation; not substitutes for optional reporting controls |
| Network protection | `network-protection`; same top-level command | Security functionality, not merely proxy configuration |
| Data loss prevention | `data-loss-prevention`; same top-level command | Separate protection layer; AV exclusions do not establish DLP exclusions |
| Device and tamper protection | `device-control`, `tamper-protection` | Respect organizational policy and authorized management |
| File hashes | `enable-file-hash-computation` | Verify purpose and impact before considering a change |
| Manual scans | Top-level `scan list/quick/full/custom/cancel` | Commands other than list start or cancel work; require appropriate authorization |
| Support diagnostics | Top-level `diagnostic`, including statistics, hot sources, `perf-trace`, `create`, `upload` | Do not create or upload support bundles by default |
| Other interfaces | Top-level `threat`, `device-control`, `system-extension`, `end-user`, `notice` | Threat handling, devices, extensions, and user management; inspect local help |

## Maintenance

Managed policy can reject or supersede local changes. Administrator privileges do not guarantee an override. Follow the organization's supported software management process for application updates.

Before a change, record the relevant original value privately. After each authorized change, retain its exit status, query the resulting value, and check protection health. Preserve pre-existing settings during rollback and recheck after policy synchronization.

Do not publish actual exclusion lists, device identifiers, organization policy states, raw diagnostic logs, or support bundles as examples. Use clearly labeled synthetic fixtures in evaluation material.

For unresolved overhead, compare identical workloads rather than broadening global interpreter exclusions. Keep configuration success separate from effective matching and measured performance improvement.
