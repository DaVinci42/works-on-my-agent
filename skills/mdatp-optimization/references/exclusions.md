# Exclusion Selection and Maintenance

## Separate the protection layers

`mdatp exclusion` manages antivirus (AV) exclusions only; it does not exclude EDR, behavior monitoring, or DLP. Query `mdatp edr exclusion list all` separately when supported, and do not treat an empty custom exclusion list as proof that no internal rules apply.

## Choose the narrowest suitable scope

| Type | Candidate use | Main concern |
|---|---|---|
| Folder path | A specific generated-output or cache directory identified in diagnostics | Everything matching the folder exclusion loses AV scanning coverage |
| File path | One verified file causing repeated scanning | Future contents written to that path are also excluded |
| Extension | A justified file class when path scoping is insufficient | Affects matching files across the entire system |
| Process | A specific executable workload with verified matching semantics | May exclude scanning performed on behalf of the process, not just its binary |
| Performance profile | A supported workload preset | Internal matching and protection-layer coverage require verification |

Prefer an exact path over a system-wide extension or interpreter exclusion. Build folders (`build`, `target`, project-specific `DerivedData`) are candidates for investigation after hotspot confirmation, whereas package caches, virtual environments, and dependency directories can contain untrusted third-party executables. Avoid broad exclusions such as `/`, `$HOME`, `Downloads`, `/tmp`, all Python processes, or all shell processes.

## Inspect and normalize paths

1. Run `mdatp exclusion list` to check for duplicates or existing parent-directory coverage before adding anything.
2. Confirm whether the target path exists and belongs to the intended workload (if pre-creating an exclusion for future build output, confirm the exact path intent rather than accepting a typo).
3. Expand tildes before passing quoted paths: `"~/project/build"` keeps a literal tilde in Bash; use `"$HOME/project/build"` or a fully expanded absolute path.
4. Resolve symlinks and record both the user-facing symlink path and resolved target. Do not assume Defender treats both identically or exclude both without evidence from event sources.
5. Prefer the exact path observed in `hot-event-sources` rather than assuming wildcard, case-sensitivity, recursion, or child-process inheritance semantics.

If `python3` is already installed, use this read-only snippet to inspect tilde expansion and symlink resolution (do not install Python solely for this check):

```bash
python3 -c 'import pathlib, sys; path = pathlib.Path(sys.argv[1]).expanduser(); print("absolute:", path.absolute()); print("resolved:", path.resolve()); print("exists:", path.exists()); print("directory:", path.is_dir())' "$HOME/project/build"
```

## Folder and file commands

Verify supported flags via local CLI help before executing authorized changes, and always capture `change_exit_status` immediately before running verification commands.

Inspect current AV exclusions:

```bash
mdatp exclusion list
```

Add an authorized directory exclusion:

```bash
mdatp exclusion folder add --path "/absolute/project/build"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

Remove an authorized directory exclusion:

```bash
mdatp exclusion folder remove --path "/absolute/project/build"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

Add an authorized single-file exclusion:

```bash
mdatp exclusion file add --path "/absolute/project/build/artifact.bin"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

Remove an authorized single-file exclusion:

```bash
mdatp exclusion file remove --path "/absolute/project/build/artifact.bin"
printf 'change_exit_status=%s\n' "$?"
mdatp exclusion list
mdatp health --field healthy
```

## Extension and process exclusions

- **Extensions**: Check `mdatp exclusion extension add --help` and `remove --help` to confirm whether a leading dot is expected. When removing an entry, match the exact string shown in `mdatp exclusion list`.
- **Processes**: Check `mdatp exclusion process add --help` for `--path` vs. `--name` support. Prefer `--path` for a specific binary when supported. A `--name python` exclusion does not guarantee matching for `python3` or version-suffixed binaries (`python3.12`), and broad interpreter exclusions are unsafe because interpreters execute dependency scripts.

## Optional branch: Non-standard package stores (Nix / `nix-darwin`, Homebrew, MacPorts)

Consult this section only when diagnostics or user context show activity under custom package prefixes (such as `/nix`, `/opt/homebrew`, or `/opt/local`):

- **No built-in `nix` profile**: `mdatp performance-profiles list-available` has no generic `nix` profile. Applying related built-in profiles (`git`, `unix-utils`, `codesign`, `make-tree`) can help, but verify via `hot-event-sources` whether non-standard store binaries actually match those profiles.
- **AV vs. EDR on `/nix/store`**: Excluding `/nix`, `"$HOME/.cache/nix"`, or `nix-daemon` in `mdatp exclusion` only reduces AV file scanning during package unpacking/realization; it does not suppress EDR Endpoint Security (`AUTH_EXEC` / `AUTH_OPEN`) events on `/nix/store/<hash>-...` paths.
- **Symlinked environments and secret mounts**: On `nix-darwin` or similar declarative setups, paths like `/run/current-system` or `/etc/profiles/...` are symlink chains into `/nix/store`. Check whether `/nix` already covers the resolved target before adding redundant AV exclusions, and never exclude transient secret mounts (e.g., `/private/var/run/agenix.d` or `sops-nix`) without explicit security review.

## Verify and maintain

- Record each exclusion's type, exact value, reason, owner, and review date privately (redact private paths in shared reports).
- Verify `change_exit_status`, the updated `mdatp exclusion list`, and `mdatp health --field healthy` after every change, then benchmark against an identical workload.
- Never test exclusions using malware samples or unsafe artifacts.
- If AV exclusions are present but `wdavdaemon` or `wdavdaemon_enterprise` CPU remains high, inspect EDR (`mdatp edr exclusion list all`), behavior monitoring, DLP, and live `hot-event-sources` rather than widening AV folder exclusions.
- Prune stale paths after project moves or toolchain upgrades only with user authorization, and preserve pre-existing rules during rollback.
- Recheck after policy sync or reboot; if a `[managed]` rule reverts or reappears, coordinate with the policy administrator rather than repeatedly deleting it.
