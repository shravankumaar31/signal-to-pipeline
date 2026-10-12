# Signal-to-Pipeline Engine

Capture buying signals, enrich and score accounts in Clay, write every field back to Salesforce
with explicit ownership rules, and use Claude via MCP to draft "why now" outreach and create rep tasks.

**Fictional seller:** a GPU cloud provider
**ICP:** Series B–D AI/ML startups training models

> Status: Phase 0 — setup

## Architecture

```
Signal sources ──► Clay table ──► n8n ──► Salesforce
(Apify job scrape,  (enrich, score,  (webhook,     ▲
 funding CSV,        tier, dedupe)    upsert,      │ MCP: read Tier A,
 seed list)                           routing)     │ create Tasks
                                         │         │
                                         ▼         │
                                   Claude via MCP ─┘
                                   (why-now rationale,
                                    Gmail drafts to test inbox)
```

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Setup: repo, Salesforce org, schema, Clay, n8n | In progress |
| 1 | ICP and signal taxonomy with weights | Not started |
| 2 | Signal capture (Apify job scrape, funding CSV) | Not started |
| 3 | Enrichment and scoring in Clay | Not started |
| 3.5 | Field mapping and write-back rules | Spec done (`docs/salesforce_schema.md`) |
| 4 | Salesforce upserts and tier routing via n8n | Not started |
| 5 | Claude + MCP: rationale, drafts, tasks | Not started |
| 6 | Reporting, completeness checks, README polish | Not started |

## Backlog (after the base build ships)

Rep-facing features layered on once Phases 0–6 are stable:

- Account brief + daily priority list (BDR)
- Reply triage + re-engagement dates (BDR)
- Pre-meeting brief from calendar events (AE)
- Signal feedback loop: meeting rate by signal type → recalibrate weights (RevOps)
- Later: buying committee mapping, job-change alerts, post-call updates, BDR→AE handoff summary, deal risk alerts

## Repo layout

```
docs/        schema, decisions log, signal taxonomy, findings
data/raw/    seed lists, scraped signals (gitignored if they contain personal data)
data/processed/
clay/        table column specs and scoring formulas
n8n/         exported workflow JSON
prompts/     Claude prompts / skill for the MCP step
force-app/   Salesforce metadata: fields, Signal__c object, tab, permission set
salesforce/  DEPLOY.md (CLI deploy), manual setup checklist, report definitions
screenshots/
```

## Key docs

- `docs/salesforce_schema.md` — every field, its type, source and write rule
- `docs/decisions.md` — every judgment call and why

## Data and outreach policy

- Outreach is drafted to a test inbox only; nothing is sent to real prospects.
- Contact data in this repo is synthetic or limited to public business information.
