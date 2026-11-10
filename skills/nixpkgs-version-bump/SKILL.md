---
name: nixpkgs-version-bump
description: Automate Nixpkgs package version updates from a GitHub issue or package request through local verification and PR preparation (自动完成 Nixpkgs 软件包版本更新：解析 Issue、查重 Open PR、查看 nixpkgs-update 日志、同步 upstream/master、运行 nix-update、本地修复沙盒与测试失败、运行 nixfmt 和 nixpkgs-review 验证，并生成包含 Resolves #ISSUE 与模板的 PR 草稿). Use whenever the user shares a NixOS/nixpkgs update issue link, asks to bump a package in a local nixpkgs checkout, or wants to fix a failing r-ryantm / nixpkgs-update bump and prepare an upstream PR.
---

# Nixpkgs Package Version Bump & PR Preparation

## Core Rules

1. **Default to the latest version**: Run `nix-update --commit <pkg>` without `--version` unless a specific version is requested.
2. **Never auto-run `git push` or `gh pr create`**: To prevent using the wrong GitHub account, only output the prepared PR body and push / `gh pr create --draft` commands for the user to run.
3. **Single commit with disclosure**: Keep one `<pkg>: <old> -> <new>` commit on the branch (committed **before** `nixpkgs-review rev HEAD`), with `Changelog:` / `Diff:` links and `Assisted-by: <Tool> (<Model>)` trailer (no emojis).
4. **Link issues with `Resolves #<ISSUE>`**: Prepend `Resolves #<ISSUE>` (and `Fix: <log-url>` if fixing a `nixpkgs-update` failure) to `.github/PULL_REQUEST_TEMPLATE.md` verbatim.

## Workflow

### 1. Pre-check Issue, Open PRs & Update Logs

1. **Parse issue**: Read `https://github.com/NixOS/nixpkgs/issues/<ISSUE>` (`fetch` or `gh issue view`) to get `<pkg>` and context.
2. **Check duplicate PRs**: Search `https://github.com/NixOS/nixpkgs/pulls?q=is%3Apr%20is%3Aopen%20in%3Atitle%20%22<pkg>%3A%22`. Stop if an open PR already updates `<pkg>`.
3. **Check bot logs**: Fetch `https://nixpkgs-update-logs.nixos.org/<pkg>/` and read the **last** log URL to see prior `nixpkgs-update` failure details.

### 2. Sync `upstream/master` & Create Branch

Expand `gprum` explicitly (shell aliases do not load in non-interactive subshells):

```bash
git status --porcelain
git checkout master
git pull --rebase upstream master
git checkout -b "update-<pkg>"
```

### 3. Update & Fix Locally

```bash
nix-update --commit "<pkg>"
printf 'nix_update_exit_status=%s\n' "$?"
```

If `nix-update` or the build fails, fix the package and verify:

- **Patches / build inputs**: Drop upstreamed patches, refresh conflicting ones, and check upstream build/license changes (e.g., `bsl11` in sub-crates).
- **Sandbox tests (fix environment before skipping)**:
  - Darwin localhost bind denied -> `__darwinAllowLocalNetworking = true;`
  - Unwritable `$HOME` -> `writableTmpDirAsHomeHook` in `nativeCheckInputs`
  - Hardcoded `/bin` or `/usr/bin` -> `substituteInPlace ... --replace-fail` with `lib.getExe'`
  - Flaky concurrency -> `checkPhaseThreadLimitHook`
  - Skip specific tests (`disabledTests` / `cargoTestFlags`) only as a documented last resort.
- **Format, sandbox build & smoke test**:
  ```bash
  nixfmt --check <modified-nix-files>
  nix-build --option sandbox true -A "<pkg>"
  ./result/bin/<binary-name> --version || ./result/bin/<binary-name> --help
  ```
  *(Add `--arg config '{ allowUnfree = true; }'` if unfree.)*

### 4. Finalize Commit & Run `nixpkgs-review`

If `nix-update --commit` failed before committing, run `nix-update --commit --version=skip "<pkg>"` (or `git commit`) after fixing, then `--amend` to ensure `git log upstream/master..HEAD` has a single commit:

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

### 5. Prepare PR Material (Do Not Push or Create PR Automatically)

1. Read `.github/PULL_REQUEST_TEMPLATE.md` from the local checkout and keep all HTML comments and sections verbatim.
2. Prepend `Resolves #<ISSUE>`, `Fix: <nixpkgs-update-log-url>` (when applicable), `Changelog:` / `Diff:`, brief fix notes, and `Assisted-by: <Tool> (<Model>)` at the top; check `[x]` only for verified items.
3. Save the body to `"${TMPDIR:-/tmp}/nixpkgs-pr-<pkg>.md"`, display it, check `gh auth status`, and output the commands for the user:

```bash
gh auth status
git push -u origin "update-<pkg>"
gh pr create --repo NixOS/nixpkgs --draft \
  --head "<github-user>:update-<pkg>" \
  --base master \
  --title "<pkg>: <old-version> -> <new-version>" \
  --body-file "${TMPDIR:-/tmp}/nixpkgs-pr-<pkg>.md"
```
