# Validation Scope

## Public test material

The evaluation prompts in `evals.json` use explicitly labeled synthetic fixtures and contain no machine identifiers, personal paths, or live session logs.

## Completed checks

- `SKILL.md` stays well below the 500-line limit with zero external script or reference file dependencies, covering both Bash and PowerShell (`pwsh` / `powershell`).
- Embedded Bash snippets pass `bash -n` syntax validation.
- Three synthetic evaluation scenarios in `evals/evals.json` pass `jq empty` validation.
- Sanitization scan confirmed zero personal `/Users/<username>` paths, UUIDs, or private key headers.
