# Phase 5 prompt spec: "why now" rationale, email draft, task

Claude (over MCP, on demand) turns each primary contact's signals into three outputs.
Input = the account's signal fields + the contact's title/persona (from the Clay exports).
Output = `data/clay_exports/inbox/claude_outreach_<date>.json` (git-ignored, contains people data),
which the n8n workflow `n8n/workflows/outreach_to_salesforce.json` writes to Salesforce.

## Rules (all outputs)
- **Facts only from the signal data.** Name the specific signal, its date, and numbers (role title, open sales roles, round + amount, new leader). No invented pains, customers, metrics or claims about the prospect.
- Signal wording: Hiring RevOps → the exact job title; Sales Team Growth → "N sales roles open"; Funding → round + amount + date; Leadership Change → role + month; Competitor Mention → "with {tool} in the stack" and offer a comparison, never disparage the tool.
- If the hiring post had pain language, say the role "describes manual commission work", nothing more specific.
- Never mention scores, tiers, or that the person was found by enrichment.

## 1. Why-now rationale → `Contact.Why_Now_Rationale__c`
2–3 sentences, ≤ 400 characters, rep-facing. Sentence 1: the signals with dates. Sentence 2: why this moment matters for commissions. Optional sentence 3: why this persona owns it (or why the channel is LinkedIn).

## 2. Email (channel = Email)
- To: **the test inbox only** (the owner's own Gmail). Subject starts with `[TEST]`. The first body line names the intended recipient by title and account; real prospect addresses are never used.
- Subject (after `[TEST]`): ≤ 7 words, lower-case style, about their signal, not about Flozero.
- Body: ≤ 90 words. Greeting with first name → signal observation → what it usually means for commissions → one Flozero line (calculates commissions from Salesforce, live rep statements, audit trail, no-code plan changes) → one low-friction CTA (20 minutes). Sign-off "— Shravan, Flozero".
- Persona angle: Head of RevOps / Sales Ops / Comp Manager → calc effort, disputes, plan changes, audit trail. CRO / VP Sales → rep trust in payouts, manager time, ramp. CFO / VP Finance → accruals, controls, one number.

## 3. LinkedIn note (channel = LinkedIn Task)
≤ 300 characters, congratulates on the signal, says what you work on, no pitch, no link.

## 4. Task → Salesforce `Task`
- Subject: `Tier {A|B} – {Primary Signal} – {Account}` (LinkedIn: `Tier B – LinkedIn connect – {Account}`).
- Due: Tier A = next day; Tier B = 3 business days. Priority: High (A) / Normal (B).
- Description: rationale + what to do (send the Gmail draft after review / send the LinkedIn note) + the signal source URL.
- `Created_By_Automation__c = true`; `Automation_Reason__c` = Tier A Outreach / Tier B Outreach / LinkedIn Outreach.
- One open automated task per contact: if one exists, don't create another.
