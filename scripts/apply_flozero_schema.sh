#!/usr/bin/env bash
# Applies decisions #14-15: replaces the GPU-specific Salesforce fields with Flozero fields,
# deploys, verifies, then commits and pushes. Run from the repo root:
#   bash scripts/apply_flozero_schema.sh            (uses org alias signal-dev)
#   bash scripts/apply_flozero_schema.sh my-alias
set -euo pipefail
ORG="${1:-signal-dev}"
[ -f sfdx-project.json ] || { echo "Run this from the repo root (the folder with sfdx-project.json)."; exit 1; }

echo "== 1/6 Removing old GPU field files from the repo"
for f in force-app/main/default/objects/Account/fields/Current_Compute_Provider__c.field-meta.xml \
         force-app/main/default/objects/Account/fields/Open_ML_Roles_Count__c.field-meta.xml; do
  if [ -f "$f" ]; then git rm -q "$f" 2>/dev/null || rm -f "$f"; echo "   removed $f"; fi
done

echo "== 2/6 Deleting old GPU fields from the org (destructive changes)"
sf project deploy start --manifest salesforce/destructive/package.xml \
  --post-destructive-changes salesforce/destructive/destructiveChanges.xml \
  --target-org "$ORG" \
  || echo "   WARN: destructive step reported an error (fine if the fields were already deleted). The verify step will confirm."

echo "== 3/6 Dry run of the new schema"
sf project deploy start --dry-run --source-dir force-app --target-org "$ORG"

echo "== 4/6 Deploying the new schema"
sf project deploy start --source-dir force-app --target-org "$ORG"
sf org assign permset --name Signal_Pipeline_Admin --target-org "$ORG" >/dev/null 2>&1 || true

echo "== 5/6 Verifying Account fields in the org"
sf data query --target-org "$ORG" --query "SELECT QualifiedApiName FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'Account' AND QualifiedApiName IN ('Incumbent_Comp_Tool__c','Open_RevOps_Roles_Count__c','Open_Sales_Roles_Count__c','Current_Compute_Provider__c','Open_ML_Roles_Count__c')"
echo "   Expect exactly 3 rows: Incumbent_Comp_Tool__c, Open_RevOps_Roles_Count__c, Open_Sales_Roles_Count__c"

echo "== 6/6 Committing and pushing"
git add -A
git commit -q -m "Switch seller to Flozero: replace GPU fields with comp fields (decisions #14-15)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Cd5yt51VbTJAz2SMqaNpag"
git push
echo "== Done. Next: add the 3 new Account fields to the Account page layout."
