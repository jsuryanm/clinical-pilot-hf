# LLM Wiki — schema and conventions

> OWNER: Person A. Person B reads wiki pages from the Discharge and Clerical
> agents; Person C reads them from the Handover agent. Schema is **frozen on
> Day 0** like `app/contracts.py` — additive changes only.

## Folders

```
wiki/
├── conditions/   # one page per clinical condition (e.g. hypertension.md)
├── drugs/        # one page per drug (e.g. amlodipine.md)
├── patients/     # one page per patient — GITIGNORED, synthetic-only in repo
└── protocols/    # SOPs (e.g. shift_handover.md, discharge_workflow.md)
```

## Page schema (frontmatter)

Every page **must** carry this YAML frontmatter:

```yaml
---
type: condition | drug | patient | protocol
id: <kebab-case-unique-within-folder>
title: <human-readable>
last_updated: 2026-05-26
source: <url or citation>   # for conditions / drugs / protocols
supersedes: []              # list of page ids this page replaces
cross_refs:                 # other wiki pages this page links to
  - conditions/hypertension
  - drugs/amlodipine
---
```

## Required sections

| Page type | Required sections (in order) |
|---|---|
| `condition` | `Summary`, `Current Guideline`, `Diagnostic Criteria`, `Treatment`, `Drug Interactions`, `Red Flags` |
| `drug` | `Summary`, `Indications`, `Dosing`, `Interactions`, `Adverse Effects`, `Pregnancy/Lactation` |
| `patient` | `Demographics`, `Active Problems`, `Medications`, `Allergies`, `Encounter History` |
| `protocol` | `Purpose`, `Trigger`, `Steps`, `Owner`, `Last Review` |

## Cross-reference syntax

Use `[[folder/id]]` for wiki-internal links. Example:

> Patient is on `[[drugs/amlodipine]]` for `[[conditions/hypertension]]`.

The Wiki Maintenance Agent's lint pass flags any cross-ref whose target does
not exist.

## Versioning

Pages live in this git repo. The Documentation Agent commits to a `wiki-history`
branch on every approved update — this is the clinical audit trail (DPDPA-aligned).

## Never commit real PHI

`wiki/patients/*` is gitignored except for `.gitkeep`. Sample synthetic patient
pages should live under `wiki/patients/_examples/`.
