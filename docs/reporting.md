# Phase 6 — Reports and dashboard (built by hand in Salesforce)

Folder: **Signal-to-Pipeline** (Reports tab → New Folder). Save every report there, then build one dashboard from them.
Each report lists the numbers it should show after the first load (2026-10-14/15), so the build doubles as a data check.

## Report types to use
| Report type | Where it comes from |
|---|---|
| Accounts | standard |
| Accounts with Signals | auto-created for the `Signal__c` master-detail (needs "Allow Reports" on Signal__c — already on) |
| Contacts & Accounts | standard |
| Tasks and Events | standard (`Created_By_Automation__c`, `Automation_Reason__c` appear as Activity fields) |

## Reports

### R1 · Accounts by Tier and Primary Signal
- Type: Accounts. Filters: Show **All accounts**; `Signal Tier` not equal to (blank).
- Group rows: Signal Tier. Group columns: Primary Signal. Columns: Account Name, Signal Score, Last Signal Date, Incumbent Comp Tool, Enrichment Status.
- Chart: stacked bar (x = Signal Tier, stack = Primary Signal).
- **Expect 19 accounts:** A = 5 (all Hiring RevOps) · B = 9 (Hiring RevOps 3, Sales Team Growth 3, Funding 3) · C = 5 (Hiring RevOps 2, Sales Team Growth 2, Funding 1).

### R2 · Signals by Type
- Type: Accounts with Signals. Filters: All accounts; Signal Date = All time (switch to Last 90 days on the dashboard later).
- Group rows: Signal Type. Columns: Account Name, Signal Date, Points, Detail, Source URL. Summarize: Points (Sum, Average).
- Chart: horizontal bar of record count by Signal Type.
- **Expect 38 signals:** Sales Team Growth 13 · Hiring RevOps 11 · Funding 7 · Competitor Mention 5 · Leadership Change 1 · Other 1.

### R3 · Automated Tasks by Reason and Status
- Type: Tasks and Events. Filters: `Created By Automation` = True; Date: All time.
- Group rows: Automation Reason. Group columns: Status. Columns: Subject, Due Date, Priority, Related To, Name (contact), Assigned.
- Chart: donut by Automation Reason.
- **Expect 14 tasks, all Not Started:** Tier A Outreach 5 (High, due 10/15) · Tier B Outreach 8 (Normal, due 10/19) · LinkedIn Outreach 1.

### R4 · Tier A SLA — overdue automated tasks
- Type: Tasks and Events. Filters: `Created By Automation` = True; Priority = High; Status not equal to Completed; Due Date less than TODAY.
- Columns: Subject, Due Date, Related To, Assigned. No grouping.
- **Expect 0 today (10/15); 5 from 10/16 if nobody works them.** This is the "did reps act on Tier A within a day" check.

### R5 · Outreach Funnel by Persona
- Type: Contacts & Accounts. Filters: `Outreach Status` not equal to (blank).
- Group rows: Outreach Status. Group columns: Persona. Columns: Account Name, Title, Email Verification Status, Seniority.
- Chart: funnel or horizontal bar on Outreach Status (order Not Started → Drafted → Sent → Replied → Meeting Booked).
- **Expect 14 contacts:** Drafted 13 · Not Started 1 (Socure, LinkedIn path). Persona: Head of RevOps 10 · Sales Ops / Comp Manager 2 · CRO / VP Sales 2.

### R6 · Data Completeness — Accounts
- Type: Accounts. Filters: `Enrichment Status` = Partial.
- Columns: Account Name, Signal Tier, Missing Fields, Employee Range, Enrichment Date.
- **Expect 4:** Notion (A), Ema (B), Flai (C), Outmarket (C), all "NumberOfEmployees; Verify headcount" (+ "Verify CRM" for Ema, Outmarket).
- Tip: also run it with `Missing Fields` contains "Verify CRM" → 5 accounts (Flow Engineering, Metaview, Chainguard, Outmarket, Ema).

### R7 · Data Completeness — Contacts
- Type: Contacts & Accounts. Filters: `Enrichment Status` = Partial.
- Columns: Account Name, Title, Missing Fields, Email Verification Status.
- **Expect 1:** Socure, Missing Fields = Email.

## Dashboard · "Signal-to-Pipeline"
| Row | Component | Source | Expect |
|---|---|---|---|
| 1 | Metric: Tier A accounts | R1 filtered to Tier = A (or a summary report) | 5 |
| 1 | Metric: Open automated tasks | R3 (Status ≠ Completed) | 14 |
| 1 | Metric: Contacts drafted | R5 (Outreach Status = Drafted) | 13 |
| 1 | Metric: Partial records | R6 + R7 | 4 + 1 |
| 2 | Stacked bar: Accounts by Tier × Primary Signal | R1 | 5 / 9 / 5 |
| 2 | Bar: Signals by Type | R2 | 38 |
| 3 | Donut: Tasks by Automation Reason | R3 | 5 / 8 / 1 |
| 3 | Funnel: Outreach Status | R5 | 13 / 1 |
| 4 | Table: Tier A SLA overdue | R4 | 0 today |
| 4 | Table: Partial accounts | R6 | 4 |

Running user: set the dashboard to run as yourself (Dev org). Add a dashboard filter on Signal Tier if wanted.

## After building
Take screenshots of the dashboard and each report chart into `screenshots/` (no contact names visible — use the dashboard and R1/R2/R3, or hide the Name column) for the README.
