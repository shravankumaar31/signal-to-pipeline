# Signal Taxonomy — Flozero

The spec for who we target, which buying signals count, how they're scored, and how scores become tiers.
Clay's scoring formula (Phase 3) and n8n's routing (Phase 4) implement exactly what's written here.

**Seller:** Flozero — *Commissions on autopilot. Zero spreadsheets, zero disputes.*
Lead product: sales compensation (ICM). Expansion: CPQ, quota and territory planning.

---

## 1. ICP

The question the ICP answers: **who has enough comp complexity to feel the pain, but isn't big enough
to already be locked into an enterprise tool?**

| Dimension | Rule | Why |
|---|---|---|
| Company type | B2B companies with quota-carrying sales teams (SaaS, fintech, B2B services) | No quota-carrying reps, no commission problem |
| Sales team size | 20–300 quota-carrying reps | Under 20, spreadsheets still work; over 300 is enterprise, usually already on an enterprise ICM tool with long cycles |
| Headcount (proxy) | 100–2,000 employees | Rep count is hard to get directly; headcount plus open sales roles stands in for it |
| Funding stage | Series B–D, or profitable private | Post-B is when sales scales and the first RevOps / comp hire happens |
| CRM | **Salesforce only** | Flozero's integration story for this project; detected from `Tech_Stack__c` |
| Geography | US + Canada | One market; California's written-commission-agreement requirement adds a compliance angle |
| Incumbent comp tool | Spreadsheets, in-house, **or a competitor** | Competitor users are in the ICP as displacement targets, at lower priority than spreadsheet users (weighted in section 3) |

### Hard exclusions (never scored, never enriched past firmographics)

| Exclusion | Detected by |
|---|---|
| Competitors: comp, CPQ and planning vendors | Domain on a maintained competitor list |
| No quota-carrying sales (product-led only, consumer) | No sales roles open and none on the team |
| Over 5,000 employees | Headcount |
| Staffing / recruiting agencies | Industry |
| CRM is confirmed **not** Salesforce (e.g. HubSpot) | `Tech_Stack__c` |

**Unknown CRM is not an exclusion.** If the CRM can't be detected, the account is scored and
`Missing_Fields__c` records it, so a rep can confirm instead of the account silently disappearing.

Exclusions run **before** contact enrichment, so excluded accounts never spend contact-finding credits.

---

## 2. Signals

A signal counts only if it is **public, detectable, and has an obvious "why now."**
Values match the `Primary_Signal__c` / `Signal_Type__c` picklists.

| Signal | Trigger | Why it means "buy now" | Source (credit cost) |
|---|---|---|---|
| **Hiring RevOps** | Open role: comp / commissions analyst or manager, incentive compensation, RevOps or Sales Ops manager | Building or overloading the comp function; the new hire's first project is often "fix commissions" | Public job feeds (Greenhouse, Lever, Ashby) or Apify job scrape — **no Clay credits** |
| ↳ *Pain-language bonus* | The posting says e.g. "manage commissions in Excel", "reconcile payouts", "implement / select an ICM tool" | Direct evidence of the problem Flozero solves | Same job post text — **no Clay credits** |
| **Sales Team Growth** | 5+ open quota-carrying roles (AE, SDR/BDR, AM) | More reps → more plans, accelerators and disputes | Same job scrape → `Open_Sales_Roles_Count__c` — **no Clay credits** |
| **Funding** | New round in the last ~6 months | New money is spent on sales headcount | Hand-built funding CSV from public announcements — **no Clay credits** |
| **Leadership Change** | New CRO, VP Sales, VP RevOps or CFO in the last ~90 days | New leaders redesign comp in their first 1–2 quarters | **Seeded by hand** from LinkedIn / press — **no Clay credits** |
| **Competitor Mention** | A job post names a comp tool (Xactly, CaptivateIQ, …) | Sets `Incumbent_Comp_Tool__c`; flags a displacement play. Low intent on its own | Same job post text — **no Clay credits** |

Pain language is a bonus inside **Hiring RevOps**, not its own type, so the schema stays unchanged and the
role that names the pain scores highest.

**Not a scored signal — comp planning season.** Most companies redesign comp in Q4 for a January fiscal year.
It applies to every account at once, so it sets campaign timing, not account scores.

### Credit policy (Clay free plan: 100 data credits / month)

Signals are captured **without Clay**. Clay credits are reserved for what only Clay does well: finding the
right contact and a verified email.

1. **Small, curated account set: ~20 accounts**, hand-picked to cover every path — strong Tier A, Tier B,
   Tier C, a competitor user, an unknown-CRM account, and at least one exclusion (e.g. HubSpot CRM).
   Treated as a test set, not a lead list.
2. **Prototype on 3 accounts first.** Measure real credits per column on one row before running any column
   on all rows; record it in `Enrichment_Credits_Used__c`.
3. **Spend order:** primary contact + verified email for Tier A, then Tier B → firmographic gaps that
   free sources couldn't fill → a second contact for Tier A only if credits remain.
4. **Never spend on** excluded or Tier C accounts beyond firmographics.
5. **Keep a ~20% reserve** for re-runs and fixes; stop and review if the reserve is touched.

## 3. Weights

**Score = Fit (max 30) + Intent (max 70), capped at 100.** Fit alone can't reach Tier B (35), so every
prioritized account has at least one real signal.

### Fit — max 30: is this a good account?

| Factor | Points |
|---|---|
| Headcount 200–1,000 (sweet spot) / 100–199 or 1,001–2,000 | 8 / 4 |
| Funding: Series B or C / Series D / profitable private / other | 8 / 6 / 5 / 0 |
| Incumbent comp tool: Spreadsheets / In-house build / Unknown / competitor or Other | 10 / 8 / 5 / 3 |
| CRM: Salesforce confirmed / unknown | 4 / 0 |

### Intent — max 70: is now the time?

Only the **strongest instance per signal type** counts (three open RevOps roles don't triple the points).

| Signal | Points |
|---|---|
| Hiring RevOps: general RevOps / Sales Ops role | 20 |
| Hiring RevOps: comp-specific role (comp or commissions analyst, ICM) | 25 |
| ↳ Pain-language bonus | +10 (comp role with pain language = **35, the single strongest signal**) |
| Sales Team Growth: 5–9 / 10–19 / 20+ open sales roles | 10 / 15 / 20 |
| Funding | 20 |
| Leadership Change: new CRO, VP Sales or VP RevOps | 20 |
| Leadership Change: new CFO | 13 (≈ 60:40 split vs. CRO-level) |
| Competitor Mention | 5 |
| Other | 5 |

Why the comp-analyst post with pain language is strongest: it's the only signal that **proves** the pain
instead of implying it.

## 4. Decay

Two kinds of signal:
- **Event signals** happen once (a funding round, a new CRO) and fade with age.
- **State signals** describe right now (sales roles open today) and don't decay — they're re-measured every run.

| Signal | Kind | Full points | Half points | Expires |
|---|---|---|---|---|
| Hiring RevOps (+ pain bonus) | Event (posting date) | 0–45 days | 46–90 days | > 90 days |
| ↳ posting closed | — | — | 30 days after close | 30 days after close |
| Funding | Event (announcement date) | 0–90 days | 91–180 days | > 180 days |
| Leadership Change | Event (start date) | 0–90 days | 91–180 days | > 180 days |
| Sales Team Growth | State | Current count, every run | — | When roles close |
| Competitor Mention | State | While the posting is live | — | When the posting closes (`Incumbent_Comp_Tool__c` keeps its value) |

Rules:
- Half points round **half up** (a 25-point comp role at day 60 → 13).
- A closed posting keeps half points for 30 days after it closes: a closed role usually means someone was
  hired, and that new hire is often the person who goes looking for a comp tool.
- Every run re-scores every signal at its current value, so accounts move **down** tiers on their own as
  signals age — reps never chase stale "hot" accounts.

Why these windows: most roles fill or get re-posted within ~6 weeks; post-funding sales hiring starts within
a quarter; new CROs usually redesign comp in their first quarter.

## 5. Tiers and routing

### Tiers

| Tier | Rule | Meaning |
|---|---|---|
| **A** | Score ≥ 60 **and** at least one signal still at full points | Act now |
| **B** | Score 35–59, or ≥ 60 with every signal already decayed | Work this week |
| **C** | Score < 35 | Watch; no rep time yet |
| Excluded | Fails an ICP hard exclusion | Never scored or enriched |

The **freshness rule** stops an account reaching Tier A on several half-decayed signals: if nothing is
fresh, it isn't urgent.

### What each tier triggers

| | Tier A | Tier B | Tier C |
|---|---|---|---|
| Salesforce task | Due next business day, priority High | Due in 3 business days, priority Normal | None |
| Claude "why now" rationale | Yes | Yes | No |
| Gmail draft (test inbox) | Yes | No (keeps the demo focused) | No |
| Clay contact spend | First priority | If credits allow | Never |
| Enrichment Partial | "Manual Research Needed" task instead of a draft | Same | — |

### Guardrails

- **One open automation task per account per reason** — re-runs never stack duplicate tasks.
- **Moving up** (C→B, B→A) creates a task at the new SLA; **moving down** keeps the open task, adds nothing.
- **Tier C is re-scored every run** and promotes itself when a signal appears.
- **Ownership — territory-based** (decision #22):
  - The **AE owns the Account**, from its HQ state / province (`salesforce/territories.csv`).
  - Tier A/B **outreach Tasks go to the territory's BDR**.
  - **Unknown HQ location** → Account stays with RevOps (admin) with a "Fix territory" task.

### Fictional sales team (`salesforce/sales_team.csv`)

| Rep | Role | License | Territory |
|---|---|---|---|
| Maya Chen | Account Executive | Salesforce | West |
| Priya Raman | Account Executive | Salesforce | Central + East |
| Lucas Romero | BDR | Salesforce Platform | West |
| Daniel Okafor | BDR | Salesforce Platform | Central |
| Hannah Brooks | BDR | Salesforce Platform | East |

Territories (US states + Canadian provinces): **West** — Pacific and Mountain states, BC, AB, YT, NT;
**Central** — Central time-zone states, SK, MB, NU; **East** — Eastern states + DC, ON, QC and Atlantic Canada.
Moving a region between territories is a one-line edit in `territories.csv`.

### Primary signal

`Primary_Signal__c` = the signal type with the most **current** points. Ties break in this order:
Hiring RevOps → Leadership Change → Funding → Sales Team Growth → Competitor Mention → Other.

## 6. Worked examples

Computed by `clay/scoring_reference.py` (as of 2026-10-12). All accounts are fictional. The Clay formula in
Phase 3 must reproduce these exactly.

| # | Account | Fit | Intent | Score | Tier | Primary | What it demonstrates |
|---|---|---|---|---|---|---|---|
| 1 | Spreadsheet scale-up: 450 emp, Series C, spreadsheets, Salesforce; comp-analyst post with pain language (10 days), 12 open sales roles | 30 | 50 | **80** | **A** | Hiring RevOps | The ideal account: proven pain + scaling team |
| 2 | New CRO: 300 emp, Series B, incumbent unknown; new CRO (30 days), 6 open sales roles | 25 | 30 | **55** | **B** | Leadership Change | Not knowing the incumbent costs 5 points — enough to miss Tier A |
| 3 | Competitor user: 800 emp, Series D, CaptivateIQ; comp-analyst post with pain language (20 days) | 21 | 40 | **61** | **A** | Hiring RevOps | A competitor user who is actively selecting a tool still reaches A |
| 4 | Strong but stale: 250 emp, Series B, spreadsheets; funding (120 d), RevOps role (70 d), new VP Sales (100 d) | 30 | 30 | **60** | **B** | Hiring RevOps | Freshness rule: 60 points but nothing fresh → B, not A |
| 5 | Role just filled: 1,200 emp, profitable, in-house; comp role closed 10 days ago, new CFO (40 d) | 21 | 26 | **47** | **B** | Hiring RevOps | Closed-posting grace period (half points); CFO at 13 |
| 6 | Early, weak signal: 600 emp, Series A, unknown tool and CRM; one "Other" signal | 13 | 5 | **18** | **C** | Other | Watch list only — no rep time, no credits |
| 7 | HubSpot CRM: 400 emp, Series B, spreadsheets; funding (15 d) | — | — | — | **Excluded** | — | Hard exclusion runs before scoring and enrichment |
