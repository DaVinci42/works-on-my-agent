# Validation Scope

## Public test material

The evaluation prompts in `evals.json` use explicitly labeled synthetic fixtures and contain no machine identifiers, personal paths, or live session logs.

## Completed checks

- `SKILL.md` stays well below the 500-line limit with zero external script or reference file dependencies, covering Tier 1 async subagent dispatch (`agent_dispatch`), Tier 2 native background shells (`run_in_background`), and Tier 3 detached Bash / PowerShell (`pwsh` / `powershell`) fallbacks.
- Embedded Bash snippets pass `bash -n` syntax validation.
- Four synthetic evaluation scenarios in `evals/evals.json` pass `jq empty` validation.
- Sanitization scan confirmed zero personal `/Users/<username>` paths, UUIDs, or private key headers.
