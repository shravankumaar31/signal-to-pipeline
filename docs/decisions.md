# Decisions Log

Every judgment call, with the reasoning. Add an entry whenever you pick between two reasonable options,
work around a tool limit, or fix a data-quality problem.

**Template**

```
## #N — <short title>
- Date:
- Status: Proposed | Decided | Superseded by #M
- Context: what forced a choice
- Options considered:
- Decision:
- Why:
- Trade-off accepted:
```

---

## #1 — Salesforce as the CRM
- Date: 2026-10-11
- Status: Decided
- Context: Project needs a CRM for enriched accounts, contacts, signals and automated tasks.
- Options considered: HubSpot (reuses deal desk portal), Salesforce.
- Decision: Salesforce.
- Why: Matches the CRM named in most target RevOps / Sales Ops job descriptions; external ID upserts and custom objects make the data model explicit.
- Trade-off accepted: The funnel won't connect natively to the HubSpot deal desk project.

## #2 — Developer Edition org
- Date: 2026-10-11
- Status: Proposed
- Context: Need API access for n8n upserts and the MCP connector. The earlier Starter Suite trial expires; Developer Edition has a 5MB data storage cap that blocked the 7,375-opportunity analytics project.
- Decision: Use a fresh Developer Edition org.
- Why: Free, doesn't expire, API enabled. This project holds ~50 accounts, ~150 contacts and a few hundred signal/task records — well under 5MB (most records count ~2KB each).
- Trade-off accepted: Storage cap means no bulk historical data in this org.

## #3 — Clay connects via webhooks, not MCP
- Date: 2026-10-11
- Status: Decided
- Context: The "Clay MCP" servers found are for clay.earth (a personal CRM) or a community server that stores browser session cookies.
- Decision: Clay → HTTP/webhook → n8n → Salesforce. MCP is used only for Salesforce and Gmail.
- Why: Uses supported integration paths; no credential cookies stored on disk.
- Trade-off accepted: One extra hop (n8n) in the pipeline.

## #4 — Drafts to a test inbox, no live sends
- Date: 2026-10-11
- Status: Decided
- Decision: Claude writes outreach as Gmail drafts addressed to a test inbox.
- Why: Proves the automation without cold-emailing real people from a portfolio project (CAN-SPAM, deliverability, reputation of personal domain).
- Trade-off accepted: No real reply-rate data; reply/meeting statuses are simulated.

## #5 — Field ownership write rules
- Date: 2026-10-11
- Status: Decided
- Decision: Every enriched field has one rule — Match key, Fill if blank, Overwrite if newer, Always overwrite, or Append (see `salesforce_schema.md`).
- Why: Stops enrichment from overwriting corrections reps make by hand, while keeping scores and signals current.

## #6 — Custom text field for industry
- Date: 2026-10-11
- Status: Decided
- Context: Clay returns free-text industries that won't match the standard Industry picklist values, which would fail or silently drop on upsert.
- Decision: Write to `Enriched_Industry__c` (text). Map to the standard picklist later with a lookup table if reporting needs it.

## #7 — `Email_Key__c` as the contact external ID
- Date: 2026-10-11
- Status: Decided
- Context: The standard Contact Email field can't be marked as an external ID.
- Decision: Custom unique, case-insensitive `Email_Key__c` holding the lowercased, trimmed email; used for upserts.

## #8 — `Signal__c` custom object for signal history
- Date: 2026-10-11
- Status: Decided
- Decision: Store each signal as its own record (master-detail to Account) with an idempotent `Signal_Key__c`; keep only the current summary on Account.
- Why: Preserves history for reporting and score decay; re-running the pipeline can't create duplicate signals.

## #9 — Partial Tier A records get a research task, not an email
- Date: 2026-10-11
- Status: Decided
- Decision: If a Tier A contact is missing required fields, create a "Manual Research Needed" task instead of drafting outreach.
- Why: Avoids personalizing on incomplete data; makes data gaps visible to reps and in reports.

## #10 — Base pipeline first, rep-facing features after
- Date: 2026-10-11
- Status: Decided
- Context: Brainstormed BDR, AE and RevOps features (account briefs, reply triage, meeting prep, signal feedback loop).
- Decision: Finish Phases 0–6 before adding any of them; they're tracked in the README backlog.
- Why: Every rep-facing feature reads from the enriched Salesforce data. If the foundation (dedupe, write rules, completeness) is shaky, each feature inherits the problem.
- Trade-off accepted: The demo is less flashy until the base ships.

## #11 — Salesforce schema deployed as metadata, not built by hand
- Date: 2026-10-11
- Status: Decided
- Context: 38 custom fields, a custom object and field-level security take ~45 minutes to click through Setup, and a hand-built schema can't be reproduced in a new org.
- Decision: Define everything in `force-app/` (Salesforce DX format) and deploy with `sf project deploy start`; access granted through the `Signal_Pipeline_Admin` permission set. Page layouts stay manual so the deploy can't overwrite standard layouts.
- Why: Repeatable, version-controlled schema ("metadata as code"); a new org is one command away.
- Trade-off accepted: Requires installing the Salesforce CLI.

## #12 — Plain-text picklist values
- Date: 2026-10-11
- Status: Decided
- Context: The signal picklist value "Hiring – ML Infra" contained an en dash, which is easy to mistype in n8n mappings and Clay formulas and would fail a restricted picklist.
- Decision: Use "Hiring ML Infra"; keep all picklist API values plain ASCII.
