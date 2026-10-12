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

## #13 — Permission set includes Account and Contact object access
- Date: 2026-10-11
- Status: Decided
- Context: Dry run failed: "Permission Read Signal__c depends on permission(s): Read Account". A master-detail child's object permissions require at least the same access on the parent.
- Decision: Add Account and Contact read/create/edit to Signal_Pipeline_Admin; set Signal__c View All to false so it doesn't require View All on Account.
- Why: Makes the permission set self-contained, so it also works for a future least-privilege integration user, not just the System Administrator.

## #14 — Seller switched from GPU cloud to Flozero (sales comp SaaS)
- Date: 2026-10-12
- Status: Decided (supersedes the GPU cloud framing in the original plan)
- Context: The first framing was a fictional GPU cloud selling to AI/ML startups. Phase 1 had not started, so switching costs only a few schema field changes.
- Options considered: Keep GPU cloud; switch to a B2B SaaS RevOps tool (comp / CPQ / planning, Everstage category).
- Decision: Fictional seller **Flozero** — "Commissions on autopilot. Zero spreadsheets, zero disputes." Lead product is sales comp (ICM); CPQ and quota/territory planning are expansion modules.
- Why: The buyer (RevOps, Sales Ops, Finance) matches the builder's own domain, so signals and messaging come from real experience; richer public signals (sales hiring, new CRO, comp-analyst job posts naming Excel or incumbent tools); CPQ ties into the quote-to-cash deal desk project; strong fit for GTM ops roles at RevOps-tool vendors.
- Name check: "Payce" was considered and rejected — it is an existing payroll product (Ramco Payce). "Flozero" returned no existing company or product.
- Trade-off accepted: GPU-specific Salesforce fields must be replaced and redeployed (Changes 2–6).

## #15 — Schema swapped from GPU fields to Flozero fields
- Date: 2026-10-12
- Status: Decided
- Context: Decision #14 changed the seller; four parts of the schema were GPU-specific.
- Decision:
  - `Current_Compute_Provider__c` (text) → `Incumbent_Comp_Tool__c` (picklist: Spreadsheets, Xactly, CaptivateIQ, Varicent, Spiff, QuotaPath, Everstage, Performio, In-house build, Other, Unknown). CPQ and planning tools go into the existing append-only `Tech_Stack__c`.
  - `Open_ML_Roles_Count__c` → `Open_RevOps_Roles_Count__c` + `Open_Sales_Roles_Count__c`.
  - Signal picklists (`Primary_Signal__c`, `Signal_Type__c`): Hiring RevOps, Sales Team Growth, Funding, Leadership Change, Competitor Mention, Other.
  - `Persona__c`: Head of RevOps, Sales Ops / Comp Manager, CRO / VP Sales, CFO / VP Finance, Other.
- Why: How an account pays commissions today decides the pitch (greenfield vs displacement vs in-house), so it's a reportable picklist rather than free text; Clay normalizes values before write-back (see #6). Sales hiring is tracked separately from RevOps hiring because it measures comp-plan load, not buyer intent.
- How: Old fields removed with a destructive-changes manifest (`salesforce/destructive/`), then a normal deploy; one script (`scripts/apply_flozero_schema.sh`) runs both, verifies, commits and pushes.
- Trade-off accepted: The two signal picklists duplicate their values; a Global Value Set would keep them in sync but isn't worth the extra migration now.

## #16 — Flozero ICP
- Date: 2026-10-12
- Status: Decided
- Decision: B2B companies with 20–300 quota-carrying reps (proxy: 100–2,000 employees + open sales roles), Series B–D or profitable private, **Salesforce CRM only**, US + Canada. Competitor users are in the ICP as displacement targets at lower priority. Hard exclusions: competitors, no quota-carrying sales, >5,000 employees, staffing agencies, confirmed non-Salesforce CRM. Unknown CRM is scored and flagged, not excluded.
- Why: The rep band is where spreadsheet comp breaks but enterprise ICM hasn't locked in. Salesforce-only keeps the integration story clean. Exclusions run before contact enrichment to save Clay credits.
- Trade-off accepted: Excludes HubSpot-CRM mid-market accounts; revisit if account volume is too thin in Phase 2.

## #17 — Five signal types, pain language as a bonus
- Date: 2026-10-12
- Status: Decided
- Decision: Hiring RevOps, Sales Team Growth, Funding, Leadership Change, Competitor Mention (+ Other). Pain language in job posts ("commissions in Excel", "implement an ICM tool") is a bonus inside Hiring RevOps, not a separate type. Comp planning season is campaign timing, not an account score.
- Why: Matches the deployed picklists (no redeploy); the role that names the pain scores highest.

## #18 — Credit budget: ~20 curated accounts, signals captured without Clay
- Date: 2026-10-12
- Status: Decided
- Context: Clay free plan is 100 data credits/month; failed lookups still cost credits.
- Decision: ~20 hand-picked accounts covering every tier and edge case (competitor user, unknown CRM, an exclusion). All signals come from free sources (job feeds, funding CSV, leadership changes seeded by hand). Clay credits go to contacts + verified emails (Tier A, then B), then firmographic gaps; prototype on 3 accounts first; keep a ~20% reserve; never enrich Tier C or excluded accounts past firmographics.
- Why: A small deliberate test set exercises every pipeline path and leaves enough credits to enrich each account properly instead of thinly.
- Trade-off accepted: Not a realistic lead volume; the README frames the 20 as a test set and explains how it scales on a paid plan.

## #19 — Scoring weights: Fit 30 + Intent 70
- Date: 2026-10-12
- Status: Decided
- Decision: Fit (headcount 8, funding 8, incumbent tool 10, Salesforce confirmed 4) + Intent (Hiring RevOps 20/25, +10 pain bonus; Sales Team Growth 10/15/20; Funding 20; new CRO/VP Sales/VP RevOps 20; new CFO 13; Competitor Mention 5; Other 5), strongest instance per type, capped at 100.
- Why: Fit can't reach Tier B alone, so every prioritized account has a real signal. The comp-analyst post with pain language is the strongest signal because it proves the pain. CFO vs CRO-level weighted 40:60 (13 vs 20) — CFOs care about comp accuracy and audit, but the CRO / RevOps leader usually chooses the tool. Competitor users get 3 fit points vs 10 for spreadsheets, making displacement lower priority by design.

## #20 — Signal decay: events fade, states are re-measured
- Date: 2026-10-12
- Status: Decided
- Decision: Hiring RevOps full 0–45 days / half 46–90 / expires >90; a closed posting keeps half points for 30 days after close. Funding and Leadership Change full 0–90 / half 91–180 / expire >180. Sales Team Growth and Competitor Mention are state signals re-measured every run. Half points round half up.
- Why: Matches typical hiring, funding and new-leader timelines; the closed-posting grace period catches the new hire who is likely to look for a comp tool; re-scoring every run makes tiers drop on their own as signals age.

## #21 — Tiers, SLAs and routing guardrails
- Date: 2026-10-12
- Status: Decided
- Decision: Tier A = score ≥ 60 with at least one full-strength signal (task next business day, High; rationale + Gmail draft). Tier B = 35–59, or ≥ 60 with only decayed signals (task in 3 business days, Normal; rationale, no draft). Tier C = < 35 (no task; re-scored every run). One open automation task per account per reason; promotions create a task at the new SLA, demotions add nothing.
- Why: The freshness rule keeps stale accounts out of Tier A; drafts only for Tier A keep the demo focused; task dedupe mirrors the record-level idempotency keys.

## #22 — Fictional sales team: 2 AEs + 3 BDRs, territory routing
- Date: 2026-10-12
- Status: Decided
- Context: Routing needs real owners. The Developer Edition org has 2 free full Salesforce licenses, 6 free Salesforce Platform licenses and 1 free Salesforce Integration license.
- Decision: 5 fictional users — AEs Maya Chen (West) and Priya Raman (Central + East) on Salesforce licenses; BDRs Lucas Romero (West), Daniel Okafor (Central) and Hannah Brooks (East) on Platform licenses. AE owns the Account by HQ state/province; Tier A/B tasks go to the territory BDR; unknown location → RevOps "Fix territory" task. Mapping in `salesforce/territories.csv`; users created by `scripts/create_sales_team.sh` (re-runnable). Emails use the reserved `.example` domain. The Integration license is kept for the n8n API user in Phase 4.
- Why: Fits the license pool exactly; AEs need full licenses for Opportunities later (BDR→AE handoff), BDRs only need Accounts, Contacts, Tasks and Signal__c. Territory routing mirrors how outbound teams split work and ties into Flozero's territory-planning module.
- Trade-off accepted: Territories are unbalanced (Priya covers two); left as-is for a 20-account test set — rebalancing is a natural follow-up story.

## #23 — Reference scorer and worked examples close Phase 1
- Date: 2026-10-12
- Status: Decided
- Decision: `clay/scoring_reference.py` implements the full spec (fit, intent, decay, freshness, tiers, primary-signal tie-break) and is the source of truth the Phase 3 Clay formula must match. Seven fictional sample accounts all land on their intended tiers. Accepted outcomes: a competitor user actively selecting a tool can reach Tier A (sample 3, 61); an unknown incumbent can keep a new-CRO account in Tier B (sample 2, 55). Primary-signal ties break Hiring RevOps → Leadership Change → Funding → Sales Team Growth → Competitor Mention → Other.
- Why: Testing the rules in code before building them in Clay catches design flaws cheaply and gives Phase 3 an exact target.
