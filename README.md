# Works on My Agent

Personal agent skills. They work on my agent. Yours may need instructions.

## Skills

| Skill | Purpose |
|---|---|
| [mdatp-optimization](skills/mdatp-optimization/SKILL.md) | Diagnose Microsoft Defender performance on macOS, maintain scoped exclusions, and minimize optional reporting where policy permits. |

## Repository layout

```text
skills/
  mdatp-optimization/
    SKILL.md
    references/
    evals/
  another-skill/
    SKILL.md
```

Each skill lives in its own directory under `skills/`. `SKILL.md` defines its scope and workflow. Optional `references/`, `scripts/`, `assets/`, and `evals/` directories keep supporting material together. `another-skill` illustrates where future skills belong; it is not included yet.

## Use

Configure your agent to discover this repository's `skills/` directory, or install individual skill directories using your agent's supported mechanism. Cloning the repository alone does not register its skills.

Read a skill before enabling it. Configuration-changing steps require authorization. Examples are illustrative; verify command support and policy permissions on your installation.

## Maintenance

Keep skills portable, document command requirements and limitations, and distinguish static checks from executed behavior tests. Use explicitly labeled synthetic evaluation fixtures. Do not commit credentials, machine identifiers, actual organization policy states, private exclusion inventories, session logs, or generated diagnostic bundles.
