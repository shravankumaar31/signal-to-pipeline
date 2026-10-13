# Raw data sources — 2026-10-12

| File | Source | Apify runs |
|---|---|---|
| `job_signals_2026-10-12.csv` | Public Greenhouse / Lever / Ashby job feeds via Apify | `bovi/greenhouse-lever-ashby-job-scraper` (title filters "Compensation", "Commission"): OsRUQfUULu9zA4vls, 7jPHaKavVNwaee62W · `wickfeed/ats-job-aggregator` (sales-role counts): zPpKGfE4meHTsl8MD · recently funded boards (all jobs, no keyword filter): nlaNa24CQNuhVQTCf |

Notes
- `open_sales_roles` counts open AE / Account Manager / SDR / BDR / Business Development titles (collections and
  technical account managers excluded). `sales_count_complete = N` means the board had more matching jobs than
  the run returned, so the count is a lower bound.
- `pain_language = Y` only for explicit evidence: commissions run in spreadsheets, or an ICM tool being
  implemented / selected / migrated.

Funding sources for the recently funded pass: parsers.substack.com weekly funding report (Oct 6, 2026), postround.substack.com Series A activity (week of Oct 4, 2026), saasrise.com This Week in SaaS (Aug 4–10, 2026).

## Funding and leadership signals (Steps 4–5, 2026-10-12)

- `funding_signals_2026-10-12.csv` — latest primary round per account from public announcements (web search + article fetch). Only rounds in the last 180 days score; older rounds are kept to set `Funding_Stage__c`. Secondary / tender sales are recorded but never count as a Funding signal.
- `leadership_signals_2026-10-12.csv` — CRO / VP Sales / VP RevOps / CFO changes from company press pages and press wires. Only the role level and date are used for scoring; names stay in the linked source.
- Firmographics (HQ, LinkedIn employee band) verified by hand on LinkedIn.

## Backfill (decision #33, 2026-10-13 UTC)

- Apify `wickfeed/ats-job-aggregator`, preset `starter-500`, title-phrase keywords (Commission/Commissions Analyst, Manager, Accountant, Specialist; Incentive / Sales Compensation Analyst), posted after 2026-08-01, 3 per board — run `S6086XH2ywxr050wX`, 4 jobs (KnowBe4, Keeper Security, New Relic, Collibra), ~$0.004. Only Keeper names no ICM tool.
- Apify `wickfeed/ats-job-aggregator` on 10 candidate boards (Keeper + recent Series B/C from funding news) for sales / RevOps / finance roles — run `E678elELbq7jju8Fe`, 95 jobs, ~$0.10.
- Funding news: TechCrunch, Insurance Journal, vcbacked.co, nosh.com (Confido), Seedtable (Numeral).

## Phase 2 close-out

- Backfill rows (Keeper Security, Confido, Numeral, Ema) added to `job_signals_2026-10-12.csv` and `funding_signals_2026-10-12.csv` so the raw CSVs, not the preview scripts, are the source of truth.
- `data/processed/clay_import_accounts.csv` — one row per account for the Phase 3 Clay import: domain (Salesforce match key), HQ city / region / country (territory routing), band, funding, CRM, incumbent, and the expected tier / score / primary signal from `clay/final_set_preview.py` (the Clay formula must reproduce them). All 21 domains verified by hand (Confido, Ema, Flai checked on their websites).
