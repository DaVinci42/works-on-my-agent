# Validation Scope

## Public test material

The evaluation prompts use explicitly labeled synthetic fixtures. They do not contain real device versions, organization policy states, exclusion inventories, test dates, process IDs, or measured performance results.

The skill and references describe procedures and example commands, not a successful optimization of a particular machine. Command availability, privileges, matching behavior, and effective configuration require verification on the user's installation.

## Completed checks

- Skill YAML metadata and naming passed the skill-creator format validator.
- Local Markdown references resolve, code fences are balanced, and the main skill remains below 500 lines.
- Bash examples passed syntax checking without executing real configuration changes.
- Seven synthetic scenarios have unique IDs and four assertions each. This validates the fixture structure, not independent model behavior.
- Synthetic checks verified that the selected health filter removes device identifiers while retaining relevant health fields and management markers.
- A mocked configuration failure remained visible through its recorded change exit status even when later health queries succeeded.
- Targeted publication checks cover personal absolute paths, UUID-shaped identifiers, private-key headers, obsolete session-reference names, and removed device-specific facts. Such checks are not a comprehensive secret scanner.

## Evaluation expectations

1. Diagnose high CPU without changing settings; distinguish missing statistics from absent scanning.
2. Reject unsupported profile names rather than inventing configuration or bypassing managed policy.
3. Preserve existing profiles and avoid attributing workload-driven CPU changes to an optimization.
4. Resolve path syntax and symlinks, inspect parent coverage, and prefer scoped exclusions over global extensions.
5. Report policy-rejected privacy changes as unsuccessful; distinguish optional reporting from security telemetry.
6. Minimize data before sharing and preserve change exit status independently from health verification.

## Limits

Static checks, mocked commands, and manual review do not establish independent agent evaluation results, effective exclusion matching, runtime compatibility, lower CPU use, or elimination of telemetry. No comparable-workload performance benchmark or independent with-skill versus baseline evaluation is claimed.

Keep real diagnostic output and private evaluation artifacts out of the public repository. Publish only synthetic or explicitly reviewed aggregate evidence.
