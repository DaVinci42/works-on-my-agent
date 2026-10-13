# Exclusion Selection and Maintenance

## Separate the protection layers

`mdatp exclusion` manages antivirus exclusions. It does not establish that EDR, behavior monitoring, or DLP will ignore the same activity. Check `mdatp edr exclusion list all` separately when supported. Do not interpret an empty custom exclusion list as absence of internal filtering.

An exclusion is a security tradeoff, not a CPU limit. Use it only for an identified source of overhead with user authorization and organizational approval where required.

## Choose the narrowest suitable scope

| Type | Candidate use | Main concern |
|---|---|---|
| Folder path | A specific generated-output or cache directory identified in diagnostics | Everything matching the folder exclusion may lose AV scanning coverage |
| File path | One verified file causing repeated scanning | Future contents at that path may also be excluded |
| Extension | A justified file class when path scoping is insufficient | Can affect matching files outside the intended project |
| Process | A specific executable workload with verified matching semantics | May affect scanning associated with the process, not merely its executable file |
| Performance profile | A supported workload preset | Internal matching and protection-layer effects need separate verification |

Prefer an exact path over a system-wide extension or interpreter exclusion. Build folders such as `build`, `target`, or a particular project's DerivedData directory are candidates for investigation, not automatic recommendations. Package caches, virtual environments, and dependency folders can contain executable third-party code.

Avoid broad defaults such as the filesystem root, an entire home directory, Downloads, all temporary files, all Python processes, or all shell processes.

## Inspect and normalize paths

1. Run `mdatp exclusion list` and identify duplicate or already-covered paths before adding anything.
2. Check that the proposed path exists and belongs to the intended workload. An absent path can be valid for future output, but confirm that intent rather than silently accepting a typo.
3. Use quoted absolute paths. `"~/project/build"` contains a literal tilde in a shell; use `"$HOME/project/build"` or a fully expanded path.
4. Inspect symlinks. Record the user-facing path and resolved target; do not assume Defender treats both identically or add both without evidence.
5. Prefer the path observed in diagnostics. Do not assume wildcard, case-sensitivity, recursion, or child-process inheritance rules from another platform or version.
6. Check for an existing parent exclusion. A child exclusion normally adds no scope when the parent already covers it. Verify matching if events suggest otherwise; events may come from a different protection layer.

If Python 3 is already available, use this read-only check after substituting the intended path. Otherwise use the available filesystem inspection tools; do not install Python solely for this check:

```bash
python3 -c 'import pathlib, sys; path = pathlib.Path(sys.argv[1]).expanduser(); print("absolute:", path.absolute()); print("resolved:", path.resolve()); print("exists:", path.exists()); print("directory:", path.is_dir())' "$HOME/project/build"
```

Do not create a directory merely to justify an exclusion. A path check does not verify Defender matching.

## Folder and file commands

Verify the following argument forms through local CLI help before use. These are separate examples, not a script to execute as a batch. Read the printed change status separately from later verification results; automated callers must retain it and handle failures explicitly.

Inspect current exclusions:

```bash
mdatp exclusion list
```

Add an authorized directory exclusion, then verify configuration and health:

```bash
mdatp exclusion folder add --path "/absolute/project/build"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

Remove that exact directory exclusion only when requested:

```bash
mdatp exclusion folder remove --path "/absolute/project/build"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

For one specific file:

```bash
mdatp exclusion file add --path "/absolute/project/build/artifact.bin"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

Its corresponding removal:

```bash
mdatp exclusion file remove --path "/absolute/project/build/artifact.bin"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

Commands may require administrator privileges. First try the permitted local interface; do not assume all changes require elevation or that elevation overrides managed policy.

## Extension and process exclusions

Check local help for `mdatp exclusion extension add --name` and `remove --name`. Verify the required extension representation, including whether a leading dot is required, before adding one. Use the exact representation reported in the list when removing an existing entry. Avoid global source-code or executable-extension exclusions as a default.

The process interface may support `--path` or `--name`; verify both the accepted arguments and their matching behavior. Inspect current help before using it; prefer a specific executable path when supported and appropriate, but do not promise that this excludes only the executable file or all descendants.

A `python` process-name exclusion does not prove matching for `python3` or version-suffixed interpreter names. Do not add every version as a substitute for a nonexistent performance profile. Interpreters and build tools can execute untrusted dependency scripts.

## Verify and maintain

- Record each exclusion's type, exact value, reason, owner, date, and review or expiry date outside public reports when it contains private paths.
- Check exit status and the resulting list after every change. A success message alone is insufficient evidence of effective matching.
- Verify health and protection states, then compare the same workload. `healthy: true` does not certify unchanged security coverage or reduced CPU.
- Do not test exclusions with malware or introduce unsafe test artifacts. Escalate uncertain matching through the supported diagnostic or management process.
- If AV exclusions exist but CPU remains high, investigate EDR, DLP, behavior monitoring, and non-Defender workload changes before broadening the scope.
- Review stale paths after project moves, toolchain upgrades, or cache relocation. Remove entries only with authorization; preserve pre-existing settings during rollback.
- Recheck after policy synchronization or restart. If a managed rule reappears, work through the policy owner rather than repeatedly deleting it.

If the installed EDR exclusion interface only exposes queries, do not invent an EDR add command or plist payload. Built-in performance profiles are a separate interface and do not establish arbitrary local EDR configuration support.
