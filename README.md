# Signal-to-Pipeline Engine

Capture buying signals, enrich and score accounts in Clay, write every field back to Salesforce
with explicit ownership rules, and use Claude via MCP to draft "why now" outreach and create rep tasks.

**Fictional seller:** **Flozero** — *Commissions on autopilot. Zero spreadsheets, zero disputes.*
Sales compensation (ICM) platform; CPQ and quota/territory planning are expansion modules.
**ICP:** B2B companies with 20–300 quota-carrying reps, Series B–D, Salesforce CRM, US + Canada (`docs/signal_taxonomy.md`)

> Flozero is a fictional company created for this portfolio project. Real tools named in this repo
> (e.g. comp, CPQ and planning vendors) appear only as data — competitor or incumbent signals.

> Status: Phase 3 — enrichment and scoring in Clay (Phases 0–2 complete)

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
| 0 | Setup: repo, Salesforce org, schema, sales team, Clay | Done (n8n hosting open) |
| 1 | ICP and signal taxonomy with weights | Done (`docs/signal_taxonomy.md`) |
| 2 | Signal capture (Apify job scrape, funding CSV, leadership seed) | Done — 21-account test set (`data/processed/account_set_preview.csv`) |
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
- Social pain signals: public forum / community posts describing comp pain (e.g. "commissions in Excel"), mapped to an account → new "Pain Post" signal type (decision #32)
- Later: buying committee mapping, job-change alerts, post-call updates, BDR→AE handoff summary, deal risk alerts

## Repo layout

```
docs/        schema, decisions log, signal taxonomy, findings
data/raw/    seed lists, scraped signals (gitignored if they contain personal data)
data/processed/
clay/        scoring_reference.py (source of truth for scores) + Clay column specs
n8n/         exported workflow JSON
prompts/     Claude prompts / skill for the MCP step
scripts/     one-shot scripts: schema changes, sales team setup
force-app/   Salesforce metadata: fields, Signal__c object, tab, permission set
salesforce/  DEPLOY.md (CLI deploy), manual setup checklist, report definitions
screenshots/
```

## Key docs

- `docs/salesforce_schema.md` — every field, its type, source and write rule
- `docs/decisions.md` — every judgment call and why
- `docs/signal_taxonomy.md` — ICP, signals, weights, decay, tiers, routing, worked examples
- `salesforce/sales_team.csv`, `salesforce/territories.csv` — fictional reps and territory routing

## Data and outreach policy

- Outreach is drafted to a test inbox only; nothing is sent to real prospects.
- Accounts are real companies; only company-level public information (domains, job post URLs, funding and
  leadership news) is committed. Contact names and emails live only in the private Salesforce dev org.
