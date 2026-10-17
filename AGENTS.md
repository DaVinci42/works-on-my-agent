# AGENTS.md

## Repository Overview

`works-on-my-agent` is a collection of portable AI agent skills. There is no application runtime, package manager, or build system at the repository root; the primary artifacts are structured Markdown skill definitions, reference guides, and synthetic evaluation fixtures under `skills/`.

## Architecture & Directory Structure

Each skill is self-contained in `skills/<skill-name>/`:

```text
skills/
  <skill-name>/
    SKILL.md          # Required: YAML frontmatter + core workflow instructions (<500 lines)
    references/       # Optional: Deep-dive reference tables and topic guides loaded on demand
    evals/            # Optional: Synthetic test cases (evals.json) and validation notes (validation.md)
    scripts/          # Optional: Helper scripts bundled with the skill
    assets/           # Optional: Templates or static files bundled with the skill
```

When adding or removing a skill, update the skills table in `README.md`.

### Current Skills

- **`crush-copilot-delegate`** (`skills/crush-copilot-delegate/`): Delegates bounded tasks through Crush using cached, account-discovered GitHub Copilot candidates; keeps planning and verification in the parent model.
- **`background-task-progress`** (`skills/background-task-progress/`): Runs long-running commands detached in the background across Bash and PowerShell (`pwsh`) so the foreground LLM session stays responsive for user Q&A, and supports both on-demand status piggybacking and bounded scheduled progress reporting.
- **`mdatp-optimization`** (`skills/mdatp-optimization/`): Guides macOS users through diagnosing Microsoft Defender for Endpoint (`mdatp` / `wdavdaemon`) CPU overhead, applying built-in performance profiles, managing scoped exclusions, and minimizing optional diagnostic reporting/sample submission within organizational policy boundaries.

## Skill Authoring & Modification Conventions

1. **Frontmatter & Line Limits**:
   - Every `SKILL.md` starts with YAML frontmatter containing `name` (matching the directory name), `description` (clear trigger conditions and scope), and optional `compatibility`.
   - Keep `SKILL.md` under 500 lines. Prefer lean, zero-dependency instructions in `SKILL.md` that leverage native agent tools and standard shell primitives before introducing custom wrapper scripts (`scripts/`) or extra reference files (`references/`).

2. **Edit vs. Execution Boundary**:
   - Editing or validating a skill in this repository **does not** authorize running system-modifying commands (such as `mdatp config`, `mdatp exclusion`, or `mdatp performance-profiles apply`) on the host machine.

3. **Portability & Sanitization Rules (Strict)**:
   - Never commit real machine identifiers, organization IDs, UUIDs, personal absolute paths (e.g., `/Users/<username>/...`), actual organization policy states, private exclusion lists, session logs, or generated diagnostic bundles.
   - Use clearly placeholder paths like `/absolute/project/build` or `"$HOME/project/build"` in documentation and examples.
   - All evaluation scenarios in `evals/evals.json` must use explicitly labeled synthetic fixtures (`fixture_note`) and offline reasoning prompts unless safe, isolated mock execution is specified.

4. **Shell Snippet Conventions in Skills**:
   - Capture and display the exit status of state-changing commands immediately (`printf 'change_exit_status=%s\n' "$?"`) before running subsequent verification commands (such as `mdatp health --field healthy`), so a passing health check does not mask a rejected configuration change.
   - Never assume in-memory shell variables (`$PID`, `$$`, `$job`) or session-bound background jobs (such as PowerShell `Start-Job`) persist across separate agent tool calls; print and reuse literal identifiers/paths and detach standard pipes (`</dev/null >"$LOG_FILE" 2>&1 &` or `Start-Process -PassThru`).
   - Avoid fragile nested quote wrapping (`sh -c '<command>'` or `pwsh -Command "<command>"`) in command templates; use Bash command groups (`{ ...; }`) or PowerShell `-EncodedCommand` so arbitrary user commands containing quotes do not break.
   - Filter sensitive device/org identifiers locally before output reaches the assistant (e.g., filtering `mdatp health` with `/usr/bin/awk`).
   - Do not assume leaf CLI subcommands exit on `--help` (for example, some `mdatp diagnostic` leaf commands start continuous monitoring immediately).

## Validation & Quality Checks

Because this repository consists of Markdown, JSON, and embedded Bash snippets, validate changes using static checks rather than executing host-mutating commands:

```bash
# 1. Validate evals JSON syntax and structure
jq empty skills/*/evals/evals.json

# 2. Check line count of SKILL.md files (must remain < 500 lines)
wc -l skills/*/SKILL.md

# 3. Scan for accidental personal paths, UUIDs, or private key headers before committing
rg -n '(/Users/[A-Za-z0-9._-]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|BEGIN [A-Z ]*PRIVATE KEY)' README.md AGENTS.md skills/
```

When modifying bash code blocks inside Markdown files or scripts, syntax-check them with `bash -n` rather than executing host-mutating commands directly.

For every added or modified Python file, require passing `ruff check`, `ruff format --check`, and `basedpyright` with zero errors or warnings. Run these checks on the affected skill directory, including its Python evaluation fixtures, and run its offline unit tests. Fix annotations and code rather than suppressing diagnostics or weakening checker settings.

## Evolving Skills from Operator History

When asked to update `mdatp-optimization` based on local usage history:
1. Run `bash skills/mdatp-optimization/scripts/collect-history-signals.sh` (read-only, automatically sanitizes `/Users/<user>`, `/nix/store/<hash>-`, and UUIDs).
2. Separate **universal macOS `mdatp` mechanics** from **environment-specific habits**:
   - **Universal mechanics** (belong in main `SKILL.md` workflow): CLI subcommand syntax gotchas (`exclusion folder/file` vs `path`), diagnostic side effects (`hot_event_source_<UUID>.txt`, stale `.zip` bundles in `wdavdiag`), and built-in `performance-profiles` catalog updates.
   - **User/environment-specific setups** (belong in optional branches or `references/`): Specialized toolchains or directory layouts (such as Nix / `nix-darwin`, custom package managers, or specific app log paths) must be framed as conditional branches ("only when detected/applicable") rather than assumed defaults for every macOS user.
3. Re-run all validation checks above and sync to `~/.agents/skills/mdatp-optimization/`.
