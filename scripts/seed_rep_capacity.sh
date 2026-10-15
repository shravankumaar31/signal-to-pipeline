#!/usr/bin/env bash
# Writes the fictional rep roster (salesforce/rep_capacity.csv) to the routing fields on User (decision #47).
# Safe to re-run; edit the CSV (status, OOO date, attainment) and run again to change routing inputs.
#   bash scripts/seed_rep_capacity.sh            (org alias signal-dev)
set -euo pipefail
ORG="${1:-signal-dev}"
[ -f sfdx-project.json ] || { echo "Run this from the repo root."; exit 1; }
tail -n +2 salesforce/rep_capacity.csv | while IFS=, read -r ALIAS STATUS OOO START QUOTA ATT MAX; do
  VALUES="Routing_Status__c='$STATUS' Rep_Start_Date__c=$START Quota_Amount__c=$QUOTA Quota_Attainment__c=$ATT Max_Accounts__c=$MAX"
  # OOO date only matters while status = Out of Office, so a stale date on an Available rep is ignored by routing
  [ -n "$OOO" ] && VALUES="$VALUES OOO_Until__c=$OOO"
  # --where takes space-separated field=value pairs (all must match), not SOQL
  sf data update record --target-org "$ORG" --sobject User --where "Alias=$ALIAS Department=Sales" --values "$VALUES" </dev/null >/dev/null \
    && echo "   updated: $ALIAS ($STATUS)" || echo "   FAILED: $ALIAS"
done
sf data query --target-org "$ORG" --query "SELECT Alias, Title, Routing_Status__c, OOO_Until__c, Rep_Start_Date__c, Quota_Attainment__c, Max_Accounts__c FROM User WHERE Department = 'Sales' ORDER BY Title, Alias"
