# Salesforce Schema — Signal-to-Pipeline

Every field Clay enriches has a home in Salesforce, an owner, and a write rule.
Create these before connecting Clay or n8n.

## Write rules

| Rule | Meaning | Used for |
|---|---|---|
| **Match key** | Used to find the record on upsert; never overwritten | `Domain__c`, `Email_Key__c`, `Signal_Key__c` |
| **Fill if blank** | Written only when the Salesforce field is empty, so rep edits survive | Stable firmographics, names, URLs |
| **Overwrite if newer** | Written when the enriched value has a newer `Enrichment_Date__c` | Data that goes stale (title, headcount, funding) |
| **Always overwrite** | System-owned; Salesforce value is never authoritative | Scores, tiers, signals, statuses |
| **Append** | New values added to existing text, deduplicated | Tech stack |

Completeness rule: every enriched field ends up **populated** or explained by
`Enrichment_Status__c` + `Missing_Fields__c`. A blank field with no status is a defect.

---

## Account

| Label | API name | Type | Write rule | Source |
|---|---|---|---|---|
| Account Name | `Name` (standard) | Text | Fill if blank | Clay company enrichment |
| Domain | `Domain__c` | Text(255), **External ID, Unique** (case-insensitive) | Match key | Normalized input domain (lowercase, no `www.`, no protocol) |
| Website | `Website` (standard) | URL | Fill if blank | Clay |
| Enriched Industry | `Enriched_Industry__c` | Text(255) | Fill if blank | Clay (see decision #6 — not the standard Industry picklist) |
| Employees | `NumberOfEmployees` (standard) | Number | Overwrite if newer | Clay |
| Employee Range | `Employee_Range__c` | Picklist: 1-50, 51-200, 201-500, 501-1000, 1001+ | Overwrite if newer | Clay formula from headcount |
| Billing City / Country | `BillingCity`, `BillingCountry` (standard) | Address | Fill if blank | Clay HQ location |
| LinkedIn Company URL | `LinkedIn_Company_URL__c` | URL | Fill if blank | Clay |
| Funding Stage | `Funding_Stage__c` | Picklist: Seed, Series A, Series B, Series C, Series D, Series E+, Public, Unknown | Overwrite if newer | Funding seed CSV / Clay |
| Last Funding Amount | `Last_Funding_Amount__c` | Currency(16,0) | Overwrite if newer | Funding seed CSV / Clay |
| Last Funding Date | `Last_Funding_Date__c` | Date | Overwrite if newer | Funding seed CSV / Clay |
| Tech Stack | `Tech_Stack__c` | Long Text Area(5000) | Append | Clay tech enrichment + job-post parsing |
| Current Compute Provider | `Current_Compute_Provider__c` | Text(255) | Overwrite if newer | Job-post parsing |
| Open ML Roles | `Open_ML_Roles_Count__c` | Number(4,0) | Always overwrite | Apify job scrape |
| Signal Score | `Signal_Score__c` | Number(3,0) | Always overwrite | Clay scoring formula |
| Signal Tier | `Signal_Tier__c` | Picklist: A, B, C | Always overwrite | Clay (A ≥ 60, B 35–59, C < 35) |
| Primary Signal | `Primary_Signal__c` | Picklist: Hiring ML Infra, Funding, Leadership Change, Competitor Mention, Other | Always overwrite | Highest-weighted active signal |
| Signal Source URL | `Signal_Source_URL__c` | URL | Always overwrite | Signals table |
| Last Signal Date | `Last_Signal_Date__c` | Date | Always overwrite | Signals table |
| Enrichment Status | `Enrichment_Status__c` | Picklist: Complete, Partial, Not Attempted, Failed | Always overwrite | Clay metadata / n8n |
| Missing Fields | `Missing_Fields__c` | Text(255) | Always overwrite | n8n completeness check (semicolon-separated) |
| Enrichment Date | `Enrichment_Date__c` | Date/Time | Always overwrite | Clay run timestamp |
| Enrichment Credits Used | `Enrichment_Credits_Used__c` | Number(6,1) | Always overwrite | Clay credit tracking column |

**Required for "Complete":** Name, Domain__c, Enriched_Industry__c, NumberOfEmployees,
BillingCountry, Funding_Stage__c, Signal_Score__c, Signal_Tier__c, Primary_Signal__c.

---

## Contact

| Label | API name | Type | Write rule | Source |
|---|---|---|---|---|
| Email Key | `Email_Key__c` | Text(255), **External ID, Unique** (case-insensitive) | Match key | Lowercased, trimmed email (standard Email can't be an external ID) |
| Email | `Email` (standard) | Email | Fill if blank | Clay waterfall email finder |
| Email Verification | `Email_Verification_Status__c` | Picklist: Valid, Catch-all, Invalid, Unknown | Always overwrite | Clay verifier |
| First / Last Name | `FirstName`, `LastName` (standard) | Text | Fill if blank | Clay person enrichment |
| Title | `Title` (standard) | Text | Overwrite if newer | Clay |
| Persona | `Persona__c` | Picklist: ML Infra Lead, Head of AI/ML, CTO / VP Eng, Founder / CEO, Other | Always overwrite | Clay formula from title |
| Seniority | `Seniority__c` | Picklist: C-Level, VP, Director, Manager, IC | Overwrite if newer | Clay |
| LinkedIn URL | `LinkedIn_URL__c` | URL | Fill if blank | Clay |
| Mailing City / Country | `MailingCity`, `MailingCountry` (standard) | Address | Fill if blank | Clay |
| Account | `AccountId` (standard) | Lookup(Account) | Set on create; corrected if mismatched | Upsert via `Account.Domain__c` external ID reference |
| Why Now Rationale | `Why_Now_Rationale__c` | Long Text Area(2000) | Always overwrite | Claude (MCP step) |
| Outreach Status | `Outreach_Status__c` | Picklist: Not Started, Drafted, Sent, Replied, Meeting Booked, Disqualified | Workflow-controlled | n8n / Claude |
| Enrichment Status | `Enrichment_Status__c` | Picklist: Complete, Partial, Not Attempted, Failed | Always overwrite | n8n |
| Missing Fields | `Missing_Fields__c` | Text(255) | Always overwrite | n8n |
| Enrichment Date | `Enrichment_Date__c` | Date/Time | Always overwrite | Clay |

**Required for "Complete":** Email (Valid or Catch-all), FirstName, LastName, Title,
Persona__c, Seniority__c, AccountId.

---

## Signal__c (custom object)

Keeps the full signal history per account; the Account fields above hold only the current summary.

| Label | API name | Type | Notes |
|---|---|---|---|
| Signal Name | `Name` | Auto Number `SIG-{00000}` | |
| Account | `Account__c` | Master-Detail(Account) | Rolls up to the account; deleted with it |
| Signal Key | `Signal_Key__c` | Text(255), **External ID, Unique** | `domain|signal_type|signal_date` — makes re-runs idempotent |
| Signal Type | `Signal_Type__c` | Picklist (same values as `Primary_Signal__c`) | |
| Signal Date | `Signal_Date__c` | Date | |
| Points | `Points__c` | Number(3,0) | Weight at time of capture |
| Source URL | `Source_URL__c` | URL | |
| Detail | `Detail__c` | Text Area(255) | e.g. "Hiring: Senior ML Infrastructure Engineer" |

Optional rollup on Account: `Active_Signal_Count__c` = COUNT of Signal__c where Signal_Date__c in the last 30 days
(use a scheduled flow or calculate in Clay if rollup filters on date aren't allowed).

---

## Task (standard) — created by automation

| Field | Value |
|---|---|
| `Subject` | `Tier A – {Primary_Signal__c} – {Account Name}` |
| `WhatId` | Account |
| `WhoId` | Contact |
| `OwnerId` | Account owner |
| `ActivityDate` | Today + 1 (Tier A SLA) |
| `Priority` | High (A) / Normal (B) |
| `Description` | `Why_Now_Rationale__c` + signal source URL |
| `Type` | Email |
| `Created_By_Automation__c` | Activity custom field, Checkbox = true (lets reports separate automated vs. manual tasks) |
| `Automation_Reason__c` | Activity custom field, Picklist: Tier A Outreach, Manual Research Needed |

Partial-enrichment Tier A records get a **Manual Research Needed** task instead of an email draft.

---

## Reports to build later (Phase 6)

- Account fill rate by field (Enrichment_Status__c × Missing_Fields__c)
- Contacts without Account (target: 0)
- Duplicate check: Accounts grouped by Domain__c with count > 1 (target: 0)
- Tier A task SLA: tasks where CompletedDateTime ≤ ActivityDate
- Signals by type and month
