---
name: nixpkgs-version-bump
description: >-
  Automate Nixpkgs package version updates from a GitHub issue or package request through local verification, Draft PR preparation, and user-authorized post-Eval nixpkgs-review-gha multi-platform CI triggering (自动完成 Nixpkgs 软件包版本更新：解析 Issue、查重 Open PR、查看 nixpkgs-update 日志、评估目标软件包支持的平台、同步 upstream/master、运行 nix-update、修复沙盒测试、nixfmt 与 nixpkgs-review 验证、准备 Draft PR；仅在用户明确授权时，等 PR Eval CI 通过后按支持平台触发 nixpkgs-review-gha review.yml 且始终排除 x86_64-darwin).
  Use whenever the user shares a NixOS/nixpkgs update issue link, asks to bump a package in a local nixpkgs checkout, wants to fix a failing r-ryantm / nixpkgs-update bump and prepare an upstream PR, or asks to run remote multi-platform nixpkgs-review GitHub Actions after PR evaluation passes.
---

# Nixpkgs Package Version Bump & PR Preparation

## Core Rules

1. **Default to the latest version**: Run `nix-update --commit <pkg>` without `--version` unless a specific version is requested.
2. **Require explicit authorization for remote GitHub actions (`git push`, `gh pr create`, `gh workflow run`)**: Prevent wrong-account mistakes and unintended CI runs—output the prepared PR body and `gh auth status` + push + `gh pr create --draft` (and optional `gh workflow run review.yml`) commands first; never execute push, PR creation, or `nixpkgs-review-gha` workflow dispatch unless the user explicitly authorizes it.
3. **Single commit with disclosure**: Squash update and fixups into one `<pkg>: <old> -> <new>` commit **before** `nixpkgs-review rev HEAD`, including `Changelog:` / `Diff:` links and `Assisted-by: <Tool> (<Model>)` trailer (no emojis).
4. **Preserve PR template verbatim**: Prepend `Resolves #<ISSUE>` (and `Fix: <log-url>` when fixing a bot failure) above `.github/PULL_REQUEST_TEMPLATE.md` without removing HTML comments or sections; check `[x]` only for verified items.
5. **Respect package platforms & never run `x86_64-darwin`**: Inspect `meta.platforms` / `meta.badPlatforms` via `lib.meta.availableOn`, skip local builds if unsupported on the host, and **always set `x86_64-darwin=no`** when preparing or dispatching `nixpkgs-review-gha`.

## Workflow

### 1. Pre-check Issue, Duplicate PRs, Bot Logs & Supported Platforms (Run in Parallel)

1. **Issue**: `gh issue view <ISSUE> -R NixOS/nixpkgs` (fallback to `fetch` if `gh` is unavailable).
2. **Duplicate open PRs**: `gh pr list -R NixOS/nixpkgs --state open --search "<pkg>: in:title"`. Stop and report if an open PR already updates `<pkg>`.
3. **Bot logs**: Fetch `https://nixpkgs-update-logs.nixos.org/<pkg>/` and read the **last** log entry to inspect prior `nixpkgs-update` failure causes.
4. **Supported platforms**: Evaluate candidate CI platforms (`x86_64-linux`, `aarch64-linux`, `aarch64-darwin`) so local builds and remote `nixpkgs-review-gha` runs match what `<pkg>` actually supports:
   ```bash
   nix eval --impure --json --expr '
     let pkgs = import ./. {}; p = pkgs.<pkg>; in {
       platforms = p.meta.platforms or null;
       badPlatforms = p.meta.badPlatforms or [];
       supported = builtins.listToAttrs (map (s: {
         name = s;
         value = pkgs.lib.meta.availableOn { system = s; } p;
       }) [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" ]);
     }'
   ```

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

### 6. Post-PR (Explicit User Authorization Required): Wait for Eval CI & Trigger `nixpkgs-review-gha`

**Never trigger `nixpkgs-review-gha` automatically.** Wait for explicit user authorization (e.g., asking to trigger the review Action or confirming after the PR is opened). Once authorized and `<github-user>/nixpkgs-review-gha` is available (resolve `<github-user>` from `gh api user --jq .login` or `git remote get-url origin`):

1. **Re-verify `<pkg>` platform support** on the final commit (in case the update modified `meta.platforms` or `meta.badPlatforms`), mapping supported systems to workflow inputs:
   - `x86_64-linux`: `true` if supported, else `false`
   - `aarch64-linux`: `true` if supported, else `false`
   - `x86_64-darwin`: **`no` (always disabled—never run Intel macOS)**
   - `aarch64-darwin`: `yes_sandbox_relaxed` if supported, else `no`
   *(If zero of the 3 remaining platforms are supported, skip workflow dispatch and report why.)*
2. **Wait asynchronously via `agent_dispatch`** (never `sleep`-poll in the foreground turn):
   - Inside the subagent, poll `gh pr checks <PR> -R NixOS/nixpkgs --json name,state,bucket` every 20s (with `auto_background_after: 600` + `job_output(..., wait: true)`).
   - Abort and report immediately if any `Eval` check fails or cancels (`bucket` in `fail` / `cancel`).
   - Proceed once `Eval Summary` reaches `SUCCESS` (or all `Eval / *` checks finish with `pass` / `skipping` and `Eval / compare` is `SUCCESS`).
3. **Dispatch `review.yml` and confirm matrix jobs**:
   ```bash
   gh workflow run review.yml -R "<github-user>/nixpkgs-review-gha" \
     -f pr="<PR>" \
     -f x86_64-linux="<true|false>" \
     -f aarch64-linux="<true|false>" \
     -f x86_64-darwin=no \
     -f aarch64-darwin="<yes_sandbox_relaxed|no>"
   printf 'workflow_dispatch_exit_status=%s\n' "$?"
   gh run list -R "<github-user>/nixpkgs-review-gha" -w review.yml -L 3 --json databaseId,displayTitle,status,url
   ```
   Wait inside the subagent until `prepare` finishes, verify the expected `review (<system>)` jobs spawned (at most 3, never `x86_64-darwin`), and return the run URL.

