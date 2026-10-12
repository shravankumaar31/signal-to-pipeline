# Deploy the Salesforce Schema (Phase 0)

All 39 custom fields, the `Signal__c` object, its tab and a permission set are defined as metadata in
`force-app/`. One deploy creates them, and the same command rebuilds the schema in any new org.

## 1. Create the org (you)
1. Sign up for a Salesforce Developer Edition org.
2. Verify your email, set a password, and log in once in the browser.

## 2. Install the Salesforce CLI (one time)
```bash
npm install --global @salesforce/cli
sf --version
```

## 3. Connect the CLI to your org
**Every `sf` command below must run from the repo root** — the folder that contains `sfdx-project.json`:
```bash
cd ~/signal-to-pipeline
ls sfdx-project.json   # must print the file name
```
```bash
sf org login web --alias signal-dev --set-default
```
A browser window opens; log in and click **Allow**.

## 4. Validate first, then deploy
```bash
# Dry run: checks everything, changes nothing
sf project deploy start --dry-run --source-dir force-app --target-org signal-dev

# Real deploy
sf project deploy start --source-dir force-app --target-org signal-dev
```
`--source-dir force-app` is required: Developer Edition orgs don't use source tracking, so the CLI must be told exactly what to deploy.
If the dry run reports errors, copy the output into the chat before changing anything.

## 5. Give yourself access to the new fields
```bash
sf org assign permset --name Signal_Pipeline_Admin --target-org signal-dev
```

## 6. Manual steps (layouts aren't in the deploy on purpose, so it can't overwrite standard layouts)
- [ ] Account page layout: add an **Enrichment & Signals** section with the new fields
- [ ] Account page layout: add the **Signals** related list
- [ ] Contact page layout: add an **Enrichment & Outreach** section with the new fields
- [ ] Task page layout: add Created By Automation and Automation Reason

## 7. Smoke test
- [ ] Create Account "Example AI" with Domain `example-ai.com`
- [ ] Try a second Account with Domain `EXAMPLE-AI.com` → must be blocked as a duplicate value
- [ ] On Example AI, create a Signal: Signal Key `example-ai.com|Funding|2026-10-01`, Type Funding, Points 25
- [ ] Try a second Signal with the same key → must be blocked
- [ ] Delete the test records

## What gets created

| Object | Fields |
|---|---|
| Account | 20 (incl. `Domain__c` external ID) |
| Contact | 10 (incl. `Email_Key__c` external ID) |
| Activity (Task) | 2 |
| Signal__c (new) | 7 (incl. `Signal_Key__c` external ID, master-detail to Account) |
| Permission set | Signal_Pipeline_Admin |
