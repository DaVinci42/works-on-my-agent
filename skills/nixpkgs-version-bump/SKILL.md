---
name: nixpkgs-version-bump
description: >-
  Automate Nixpkgs package version updates from a GitHub issue or package request through local verification and Draft PR preparation (自动完成 Nixpkgs 软件包版本更新：解析 Issue、查重 Open PR、查看 nixpkgs-update 日志、同步 upstream/master、运行 nix-update、修复沙盒测试、nixfmt 与 nixpkgs-review 验证，并生成含 Resolves #ISSUE 与模板的 PR 草稿).
  Use whenever the user shares a NixOS/nixpkgs update issue link, asks to bump a package in a local nixpkgs checkout, or wants to fix a failing r-ryantm / nixpkgs-update bump and prepare an upstream PR.
---

# Nixpkgs Package Version Bump & PR Preparation

## Core Rules

1. **Default to the latest version**: Run `nix-update --commit <pkg>` without `--version` unless a specific version is requested.
2. **Never auto-run `git push` or `gh pr create`**: Prevent wrong-account mistakes—only output the prepared PR body and `gh auth status` + push + `gh pr create --draft` commands for the user.
3. **Single commit with disclosure**: Squash update and fixups into one `<pkg>: <old> -> <new>` commit **before** `nixpkgs-review rev HEAD`, including `Changelog:` / `Diff:` links and `Assisted-by: <Tool> (<Model>)` trailer (no emojis).
4. **Preserve PR template verbatim**: Prepend `Resolves #<ISSUE>` (and `Fix: <log-url>` when fixing a bot failure) above `.github/PULL_REQUEST_TEMPLATE.md` without removing HTML comments or sections; check `[x]` only for verified items.

## Workflow

### 1. Pre-check Issue, Duplicate PRs & Bot Logs (Run in Parallel)

1. **Issue**: `gh issue view <ISSUE> -R NixOS/nixpkgs` (fallback to `fetch` if `gh` is unavailable).
2. **Duplicate open PRs**: `gh pr list -R NixOS/nixpkgs --state open --search "<pkg>: in:title"`. Stop and report if an open PR already updates `<pkg>`.
3. **Bot logs**: Fetch `https://nixpkgs-update-logs.nixos.org/<pkg>/` and read the **last** log entry to inspect prior `nixpkgs-update` failure causes.

### 2. Sync `upstream/master` & Create Branch

Expand `gprum` explicitly (shell aliases do not load in non-interactive subshells):

```bash
git status --porcelain
git checkout master
git pull --rebase upstream master
git checkout -b "update-<pkg>"
```

### 3. Update, Triage & Verify Locally

For slow builds (`nix-update`, `nix-build`, `nixpkgs-review`), offload execution via `agent_dispatch` (with raised `auto_background_after`) when available so the foreground session never `sleep`-polls.

```bash
nix-update --commit "<pkg>"
printf 'nix_update_exit_status=%s\n' "$?"
```

If `nix-update`, source fetching, or `checkPhase` fails:

- **Host network vs. package bugs**: Socket errors like `Errno 57: Socket is not connected` on `files.pythonhosted.org` / `registry.npmjs.org` indicate local macOS endpoint-security network filtering (e.g., Defender `netext`), not a broken Nix expression—do not rewrite valid fetchers to work around host blocks.
- **Patches & licenses**: Drop upstreamed patches, refresh conflicting ones, and audit workspace sub-crates for new licenses (e.g., `bsl11` marks a package unfree).
- **Sandbox tests (repair environment before skipping)**:
  - Darwin localhost bind denied -> `__darwinAllowLocalNetworking = true;`
  - Unwritable `$HOME` -> `writableTmpDirAsHomeHook` in `nativeCheckInputs`
  - Hardcoded `/bin` or `/usr/bin` -> `substituteInPlace ... --replace-fail` with `lib.getExe'` (`patchShebangs` only rewrites `#!`)
  - Local service or concurrency issues -> `redisTestHook` / `postgresqlTestHook` / `memcachedTestHook`, or `checkPhaseThreadLimitHook`
  - Skip narrow failing tests (`disabledTests` / `cargoTestFlags`) only as a documented last resort.
- **Format, sandbox build & smoke test**:
  ```bash
  nixfmt --check <modified-nix-files>
  nix-build --option sandbox true -A "<pkg>"
  ./result/bin/<binary-name> --version || ./result/bin/<binary-name> --help
  ```
  *(Add `--arg config '{ allowUnfree = true; }'` if unfree; cached Linux outputs do not verify Darwin.)*

### 4. Squash Commit & Run `nixpkgs-review`

If `nix-update --commit` failed before committing, run `nix-update --commit --version=skip "<pkg>"` (or `git commit`), then `--amend` so `git log upstream/master..HEAD` has exactly one commit:

```bash
git add -u
git commit --amend -m "$(cat <<'EOF'
<pkg>: <old-version> -> <new-version>

Changelog: <changelog-url>
Diff: https://github.com/<owner>/<repo>/compare/<old-tag>...<new-tag>

Assisted-by: <Tool> (<Model>)
EOF
)"
nixpkgs-review rev HEAD --no-shell
```

### 5. Prepare PR Material (Never Push or Create PR Automatically)

1. Read `.github/PULL_REQUEST_TEMPLATE.md` verbatim from the local checkout.
2. Prepend `Resolves #<ISSUE>`, `Fix: <nixpkgs-update-log-url>` (if applicable), `Changelog:` / `Diff:`, concise fix notes, and `Assisted-by: <Tool> (<Model>)`; check `[x]` only for completed checks.
3. Write to `"${TMPDIR:-/tmp}/nixpkgs-pr-<pkg>.md"`, display the body, run `gh auth status`, and output the commands for the user:

```bash
gh auth status
git push -u origin "update-<pkg>"
gh pr create --repo NixOS/nixpkgs --draft \
  --head "<github-user>:update-<pkg>" \
  --base master \
  --title "<pkg>: <old-version> -> <new-version>" \
  --body-file "${TMPDIR:-/tmp}/nixpkgs-pr-<pkg>.md"
```
