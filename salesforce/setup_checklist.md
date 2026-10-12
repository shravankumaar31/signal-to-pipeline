# Salesforce Setup Checklist (Phase 0)

**Preferred route:** deploy everything with the CLI — see `DEPLOY.md` (about 10 minutes).
Use this click-by-click checklist only if the CLI deploy fails or you want to build the fields by hand.

Work top to bottom. Field details live in `../docs/salesforce_schema.md`.

## 1. Org
- [ ] Sign up for a new Developer Edition org (use a new username; it must be unique across all orgs)
- [ ] Log in, set your time zone (Settings → Personal Information)
- [ ] Confirm API access: Setup → Users → your profile shows "API Enabled"

## 2. Account fields
Setup → Object Manager → Account → Fields & Relationships → New
- [ ] `Domain__c` — Text(255), **Unique** (case-insensitive), **External ID**
- [ ] `Enriched_Industry__c` — Text(255)
- [ ] `Employee_Range__c` — Picklist
- [ ] `LinkedIn_Company_URL__c` — URL
- [ ] `Funding_Stage__c` — Picklist
- [ ] `Last_Funding_Amount__c` — Currency(16,0)
- [ ] `Last_Funding_Date__c` — Date
- [ ] `Tech_Stack__c` — Long Text Area(5000)
- [ ] `Current_Compute_Provider__c` — Text(255)
- [ ] `Open_ML_Roles_Count__c` — Number(4,0)
- [ ] `Signal_Score__c` — Number(3,0)
- [ ] `Signal_Tier__c` — Picklist (A, B, C)
- [ ] `Primary_Signal__c` — Picklist
- [ ] `Signal_Source_URL__c` — URL
- [ ] `Last_Signal_Date__c` — Date
- [ ] `Enrichment_Status__c` — Picklist (Complete, Partial, Not Attempted, Failed)
- [ ] `Missing_Fields__c` — Text(255)
- [ ] `Enrichment_Date__c` — Date/Time
- [ ] `Enrichment_Credits_Used__c` — Number(6,1)

## 3. Contact fields
- [ ] `Email_Key__c` — Text(255), **Unique** (case-insensitive), **External ID**
- [ ] `Email_Verification_Status__c` — Picklist
- [ ] `Persona__c` — Picklist
- [ ] `Seniority__c` — Picklist
- [ ] `LinkedIn_URL__c` — URL
- [ ] `Why_Now_Rationale__c` — Long Text Area(2000)
- [ ] `Outreach_Status__c` — Picklist
- [ ] `Enrichment_Status__c` — Picklist
- [ ] `Missing_Fields__c` — Text(255)
- [ ] `Enrichment_Date__c` — Date/Time

## 4. Signal__c object
Setup → Object Manager → Create → Custom Object
- [ ] Label "Signal", record name auto number `SIG-{00000}`, allow reports
- [ ] `Account__c` — Master-Detail(Account)
- [ ] `Signal_Key__c` — Text(255), Unique, External ID
- [ ] `Signal_Type__c` — Picklist
- [ ] `Signal_Date__c` — Date
- [ ] `Points__c` — Number(3,0)
- [ ] `Source_URL__c` — URL
- [ ] `Detail__c` — Text Area(255)
- [ ] Add a Signals related list to the Account page layout

## 5. Activity fields (apply to Task)
Object Manager → Activity → Fields & Relationships
- [ ] `Created_By_Automation__c` — Checkbox
- [ ] `Automation_Reason__c` — Picklist (Tier A Outreach, Manual Research Needed)

## 6. Layouts and access
- [ ] Add new fields to Account and Contact page layouts (group them in an "Enrichment & Signals" section)
- [ ] Field-level security: visible and editable for System Administrator

## 7. Smoke test
- [ ] Create one test Account with `Domain__c = example-ai.com`
- [ ] Try creating a second Account with `Domain__c = EXAMPLE-AI.com` → should be blocked as a duplicate
- [ ] Log the result in `docs/decisions.md` if anything behaved unexpectedly
