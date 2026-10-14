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

## #24 — Real companies, company-level data public, people data private
- Date: 2026-10-12
- Status: Decided
- Decision: The ~20 accounts are real companies sourced from live public job posts and news. Company names, domains, job post URLs and funding / leadership news go in `data/raw/*.csv` and Salesforce. Contact names and emails (Clay, Phase 3) live only in the private Salesforce dev org — the data CSVs are gitignored. Outreach is Gmail drafts to a test inbox only. No companies are excluded by preference.
- Why: Clay can only enrich real domains, and real job posts make every signal verifiable by a reviewer. Keeping people's details out of the public repo is the line between a credible demo and publishing personal data.

## #25 — Apify for job signals: two actors, title filters, spend capped
- Date: 2026-10-12
- Status: Decided
- Context: The plan was Apify for job scraping. Free-tier behaviour found while running it: `bovi/greenhouse-lever-ashby-job-scraper` report mode processed only the first company per run, and job mode capped runs at 10 results. `wickfeed/ats-job-aggregator` has no such cap, but its keyword filter also matches job descriptions — "Compensation" matched pay boilerplate in almost every posting, so the run hit its $0.50 charge cap after 501 jobs.
- Decision: Comp / commission roles from `bovi` with a title-only filter (few results, full descriptions). Open sales-role counts from `wickfeed`. Every run carries a `maxTotalChargeUsd` cap. Next time, `wickfeed` keywords must be title-specific phrases only (never "Compensation").
- Result: 17 boards captured for ~$0.58 total. Raw output in `data/raw/job_signals_2026-10-12.csv` with run IDs in `data/raw/SOURCES.md`. Several search-result postings (Tines analyst, Tailscale, Chainguard, Perforce comp roles) had already closed — the live feed is the source of truth.
- Also: `.gitignore` changed so company-level CSVs are committed and only contact files are ignored (applies #24).

## #26 — Sourcing filter: spreadsheet-only + recently funded (ICP unchanged)
- Date: 2026-10-12
- Status: Decided (a first draft wrongly changed the ICP; reverted the same day)
- Context: The first Apify pass showed most companies hiring comp analysts already run an ICM tool — displacement deals.
- Decision: The ICP (#16) and weights (#19) stay exactly as defined. Phase 2 **sourcing** is filtered to companies that (1) still run commissions on spreadsheets and (2) announced a Series B–D round in the last ~90 days. "About to be funded" isn't publicly observable, so recent funding is the proxy. Competitor users remain in the ICP and can still enter the set as edge cases.
- Why: Filters what we look for, not how we score — the scoring model stays general while the test set leans toward Flozero's best story (greenfield, fresh budget).
- Example: sample 8 (250 employees, Series B 25 days ago, spreadsheets, Salesforce, 8 open sales roles) scores 60 → Tier A with no comp hire yet.

## #27 — Geography is judged by legal HQ
- Date: 2026-10-12
- Status: Decided
- Context: Several sourced companies (Metaview, Tines) were founded abroad but run US go-to-market teams.
- Decision: The US + Canada rule uses the company's legal / listed HQ country. Legal HQ outside US + Canada is a hard exclusion. Tines (LinkedIn HQ: Boston) stays in; Metaview (London) is kept in the set as the non-US-HQ exclusion test case.
- Why: Legal HQ is one unambiguous field Clay can return; "where the US team sits" is a judgment call that can't be automated. Territory routing also needs a single HQ state/province.
- Trade-off accepted: Some foreign-HQ companies with large US sales teams are excluded.

## #28 — Funding outside B–D: Series E+ scored, Series A and below capped at Tier C
- Date: 2026-10-12
- Status: Decided
- Context: Gong (Series E) has the strongest signal in batch 1 — two comp roles citing an ICM platform migration. Flai (Series A) has explicit spreadsheet pain but is early.
- Decision: Series E and later are scored with 0 funding points (no exclusion), so strong intent can still carry them to Tier A — Gong scores 66 → A. Series A and earlier are scored normally but capped at Tier C (no task, no credits), so the signal is kept on the watch list — Flai scores 58 → C (capped).
- Why: A late-stage company mid-migration is a live deal and shouldn't be hidden; an early company with real pain is worth watching but not worth rep time yet. Capping instead of excluding keeps the signal history for when it raises a Series B.
- Trade-off accepted: Series E+ gets no fit credit for funding, so it needs intent to compensate.

## #29 — Score LinkedIn headcount bands when no exact count exists
- Date: 2026-10-12
- Status: Decided
- Context: LinkedIn shows bands (e.g. 1,001–5,000), and those bands don't line up with the spec's 100 / 1,000 / 2,000 cut-offs.
- Decision: An exact headcount uses the original rule. When only a band is known: 201–500 and 501–1,000 → 8; 51–200 and 1,001–5,000 → 4; 11–50 → 0; 5,001+ → excluded.
- Why: Gives every band a deterministic score Clay can reproduce, and errs toward partial credit for bands that straddle the ICP edge.

## #30 — Under 100 employees capped at Tier C (same floor as Series A)
- Date: 2026-10-12
- Status: Decided
- Context: Flow Engineering (LinkedIn 11–50, $50M Series B, first Head of RevOps) scored 63 → Tier A, even though the ICP says teams that small can still run comp in spreadsheets.
- Decision: Extend the #28 floor: under 100 employees (exact count, or LinkedIn band 1–10 / 11–50) is scored but capped at Tier C. The 51–200 band is not capped. Flow Engineering → C (capped).
- Why: Keeps Tier A consistent with the ICP's own reasoning; one "below-ICP floor" rule covers both funding and size.
- Trade-off accepted: Fewer Tier A accounts in batch 1 (Gong, Notion), and a just-funded company's band may lag its real size — re-scored every run, so it graduates when LinkedIn catches up.

## #31 — Public companies scored like Series E+ (0 funding points, not excluded)
- Date: 2026-10-12
- Status: Decided
- Context: Ibotta (NYSE: IBTA) was sourced, and the ICP's funding rule (Series B–D or profitable private) didn't say what to do with public companies.
- Decision: Public companies are scored with 0 funding points and are not excluded, same as Series E+ (#28). PE-owned companies count as "profitable private" (5 points).
- Why: One consistent rule for everything outside the B–D band; a public company with a strong comp signal (e.g. SOX-driven commission audits) is still a real buyer.
- Trade-off accepted: Public companies need strong intent to reach Tier B.

## #32 — Social pain signals deferred to the backlog
- Date: 2026-10-12
- Status: Deferred (post base build)
- Context: A founder in the Clay community described a tool that finds buying signals in public conversations (Reddit, LinkedIn, forums, Slack, Discord) instead of funding / hiring. Our hardest sourcing gap is proving a company still runs commissions in spreadsheets, and a post like "month-end commissions in Excel are killing me" proves it directly.
- Decision: Don't adopt the tool or add the signal to the base build. Log it as a future improvement: a "Pain Post" signal type, sourced from public forums only, scored as "Other" (5) until we measure how often a post can be mapped to an account, then re-weighted (potentially above a comp job post, since it proves the pain).
- Why: The base build is account-based; social posts are person-level and often anonymous, so account mapping is the unproven step. Several sources (private Slack / Discord communities) forbid scraping members' messages, which conflicts with our data policy (#24).
- Revisit when: Phases 0–6 ship. Test on public forums first (e.g. r/salesops, r/revops), measure the post → account match rate, and only then decide on weight and tooling.

## #33 — Cut 5 no-signal accounts; backfill with spreadsheet + just-funded companies
- Date: 2026-10-12
- Status: Decided
- Context: After Steps 4–5 the 22 leads scored 3 A / 4 B / 12 C / 3 Excluded. Five Tier C accounts had no live signal or only open sales roles, and no Tier A account runs commissions in spreadsheets — Flozero's best story (sample 8) had no real account.
- Decision: Cut Ibotta, Perforce, BlueCat, Outreach (no live signals) and 1Password (largest, single weak signal). 17 remain. Backfill 3 accounts that are spreadsheet-only, raised a Series B/C in the last ~90 days, 100+ employees, legal HQ in US/Canada — sourced two ways: recent funding news, and a capped Apify pass over job boards.
- Why: Dead-weight Tier C rows add no test coverage; the public-company and PE-owned rules are already covered by samples and Bazaarvoice. The backfill fills the missing "greenfield Tier A" path.

## #34 — Test set locked: 21 accounts (5 A / 6 B / 7 C / 3 Excluded)
- Date: 2026-10-12
- Status: Decided
- Context: Step 3 screened the 22 scraped leads, Steps 4–5 added funding and leadership signals, #33 cut 5 and backfilled from both routes (Apify comp-role scan across 500 boards + recent funding news). All four backfill candidates were kept (Keeper Security, Confido, Numeral, Ema); firmographics verified on LinkedIn.
- Decision: The Phase 3 test set is the 21 accounts in `data/processed/account_set_preview.csv`, produced by `clay/final_set_preview.py`. Tier A: Keeper Security 77, Sierra 71, Gong 66, Notion 63, Confido 61. Tier B: Tines, Numeral, Semperis, Socure, Bazaarvoice, Ema. Tier C: Flow Engineering, Flai, Outmarket (all capped), DoiT, Chainguard, Solink, Tailscale. Excluded: Metaview (HQ), Clipboard Health (staffing), Ambrook (HubSpot).
- Coverage: every path the taxonomy asks for — strong A, B, C, competitor users (Tines, Semperis, Notion, Bazaarvoice), unknown CRM, three different exclusions, both floor caps, a Canadian account (Tailscale, Solink), Series E+ and PE-owned accounts, and a decay demo (Notion drops A → B on Oct 16).
- Known gap: no account is *proven* to run commissions on spreadsheets — Keeper is closest (no ICM tool named, Excel/Sheets + macros, "automate manual commission processes") but stays "Unknown" under the explicit-language rule. Phase 3 enrichment is the next chance to confirm it.
- Credit plan: Clay contact spend on 5 Tier A first, then 6 Tier B — 11 accounts, within the ~80 usable credits after the 20% reserve.

## #35 — Fix: Competitor Mention was missing from 5 accounts' scores
- Date: 2026-10-13
- Status: Resolved
- Context: Building the Clay import (one column per signal) exposed that Tines, Semperis, Gong, Notion and Bazaarvoice have a live job post naming a comp tool, but the Phase 2 preview never added the Competitor Mention signal (+5, state signal while the posting is live).
- Decision: Added it. Gong 66 → 71, Notion 63 → 68, Tines 48 → 53, Semperis 46 → 51, Bazaarvoice 41 → 46. No tier changed. Tailscale, Chainguard and Perforce named tools only in closed posts, so they correctly get nothing. `account_set_preview.csv` and `clay_import_accounts.csv` regenerated.
- Why it slipped: Phase 2 recorded the tool in `tools_named` (for `Incumbent_Comp_Tool__c`) but treated it only as a fit input, not also as an intent signal.
- Lesson: flat, one-column-per-signal inputs make missing signals visible — the Clay table uses that shape.


## #36 — Scoring lives in Clay as 15 formula columns, validated row-for-row
- Date: 2026-10-13
- Status: Decided
- Context: Option of moving scoring to n8n (single JS copy, daily decay) was considered; the user chose to keep scoring in Clay.
- Decision: 15 formula columns (Exclusion → Pts × 6 → Fresh Signal → Fit → Intent → Score → Below ICP Floor → Signal Tier → Primary Signal → Score Check), source in `clay/clay_formulas_v2.json`, paste guide in `clay/CLAY_FORMULAS.md`, tested by `clay/test_clay_formulas_v2.js`. In Clay, Score Check = OK on all 21 rows (2026-10-13).
- What we learned about Clay formulas:
  - Pasted `{{Column}}` / `{{/Column}}` text never links to a column; only `/`-inserted chips do. So each formula is an arrow function with all columns passed as the last arguments (`COL1..n`) — one chip per column, all in one place.
  - The checker rejects assignments (`=`), rest params and destructuring; arrow functions, ternaries, `??`, `.reduce` and object-literal lookups are fine.
  - The AI formula generator repeatedly inverted "is not empty" checks (leading `!`) — generated formulas must be reviewed, which is why we paste tested code instead.
  - The generator's preview runs on sample data, not table rows — validate on saved columns only.
- Trade-off accepted: Clay formulas only recompute when a row re-runs, so decay (e.g. Notion A → B on Oct 16) needs a scheduled re-run — to solve in Phase 4. Two copies of the scoring logic (Python reference + Clay JS) are kept in sync by the Score Check column and the Node test.

## #37 — HQ = US / Canada operating hub when one exists (supersedes #27)
- Date: 2026-10-13
- Status: Decided (supersedes #27)
- Context: Clay company enrichment returned Tines → Dublin, IE (LinkedIn check said Boston) and Metaview → San Francisco, US (we had London and excluded it).
- Decision: When a company has a US or Canadian hub, it counts as US / Canada for the ICP and for territory routing (the hub's state / province). Tines stays in (Boston, MA). Metaview comes back in (San Francisco, CA): Series C, 51–200, Finance Manager role at half points + 14 sales roles → 42, Tier B, primary Sales Team Growth. Test set is now 5 A / 7 B / 7 C / 2 Excluded.
- Why: Flozero sells to the go-to-market team, which sits in the US hub; a foreign legal entity doesn't change who buys. The non-US-HQ exclusion stays tested by scorer sample 10.
- Trade-off accepted: "Has a US hub" is a judgment call that Clay can't return directly — Clay's Country field reflects the primary LinkedIn location, so conflicts are resolved by a human.

## #38 — Headcount: hand-verified value wins; Clay count is a flagged cross-check
- Date: 2026-10-13
- Status: Decided
- Context: Clay's Employee Count and Size band disagreed with each other and with the LinkedIn check: Notion 7,137 (band 501–1,000 — would trip the over-5,000 exclusion), Confido Size 11–50 vs count 114 (Size would cap it at Tier C), Flai 29 vs 51–200, Ema 311 vs 51–200, Outmarket 60 vs 11–50. Gong 3,587 agreed with everything.
- Decision: Score from the hand-verified headcount (imported Employees / Employee Band). Clay's count goes to a `Headcount Conflict` column that flags disagreement (outside the verified band, or under ½ / over 2× an exact count) for human review. Never score from Clay's Size band.
- Why: Clay's count appears to include people who merely list the company on LinkedIn (inflates community-heavy brands like Notion), and Size bands go stale after fast growth. One automated number would have wrongly excluded Notion or capped Confido.
- In production (no human check): a flagged row keeps the last verified value and gets a "Manual Research Needed" reason instead of silently changing tier.
- Cost: Enrich company on 21 rows = 10.5 credits (0.5 / row, as listed). Balance 189.5.

## #39 — CRM detection with BuiltWith; HubSpot website tools alone ≠ HubSpot CRM
- Date: 2026-10-13
- Status: Decided
- Context: 10 non-excluded accounts had CRM = Unknown (0 fit points). Tested BuiltWith "Find technology stack" (1 credit/row) with a keyword filter (Salesforce, HubSpot, Pardot, Marketo, Dynamics, Zoho, Pipedrive), first on 3 rows including a known-Salesforce control (Keeper), then on the remaining 8 — 11 credits total, balance 178.5.
- Result: Salesforce detected at Tailscale, DoiT, Solink, Socure, Numeral (plus the Keeper control). HubSpot website tools only at Flow Engineering, Metaview, Chainguard, Outmarket, Ema. Evidence in `data/raw/crm_detection_2026-10-13.csv`.
- Decision: `CRM Final` = imported CRM when known; else Salesforce if core Salesforce tech is detected (My Salesforce, Salesforce SPF, Pardot…; not Commerce Cloud, Tableau, MuleSoft, Heroku, Slack, Marketing Cloud or Audience Studio); else Unknown. HubSpot website tools alone stay Unknown with a "Verify CRM" flag — not an exclusion (option a).
- Why: BuiltWith sees website tags, not the CRM; HubSpot forms / analytics sit on top of Salesforce at many companies (Numeral, Tailscale and DoiT all show both). Excluding 5 accounts on indirect evidence would contradict "only a confirmed non-Salesforce CRM excludes".
- Impact: +4 fit for 5 accounts. DoiT 33 → 37 and Solink 31 → 35 move C → B; Tailscale 29 → 33, Socure 43 → 47, Numeral 47 → 51. Test set now 5 A / 9 B / 5 C / 2 Excluded.


## #40 — Two Clay tables: accounts (one row per company) and contacts (one row per person)
- Date: 2026-10-14
- Status: Decided
- Context: The accounts table reached 71 columns, and contacts were going to be flattened into it one person per account.
- Decision: New table `clay_contacts_v1`, filled from `clay_accounts_v1` by *Send table data* in "send row for each item in a list" mode, using the Find contacts `people` list. Account columns sent: Account Name, Domain (join key), HQ Country, Signal Tier, Score, Primary Signal, Primary Contact LinkedIn. "Update existing rows on re-run" is ON, so a re-send refreshes rows without duplicating them. Auto-run is OFF, and the run condition is Primary Contact Idx ≥ 0.
- Primary contact: Clay formulas can't compare rows, so the accounts table chooses the primary (`Primary Contact Idx` → `Primary Contact LinkedIn`). The contacts table flags it with `Is Primary` = its own LinkedIn URL matches the account's primary (lower-cased, trailing slash ignored).
- Why: Matches Salesforce (Account vs Contact objects), allows a 2nd Tier A contact later, and lets email enrichment run per person, only where Is Primary and Tier is A/B. Reuses the people already found, with no new search.
- Lesson: Clay's formula checker also rejects `typeof`; use `Array.isArray(v) ? v : []`.
- Formulas: `clay/contact_formulas_v3.json`, `clay/CLAY_CONTACT_FORMULAS.md` (v1/v2 superseded).
