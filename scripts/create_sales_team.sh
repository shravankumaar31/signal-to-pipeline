#!/usr/bin/env bash
# Creates the fictional Flozero sales team (salesforce/sales_team.csv) as real Salesforce users,
# assigns the pipeline permission set, then commits and pushes. Safe to re-run: existing users are skipped.
#   bash scripts/create_sales_team.sh            (org alias signal-dev)
set -euo pipefail
ORG="${1:-signal-dev}"
[ -f sfdx-project.json ] || { echo "Run this from the repo root."; exit 1; }

# Usernames must be unique across ALL Salesforce orgs, so suffix them with this org's Id.
ORG_ID=$(sf data query --target-org "$ORG" --query "SELECT Id FROM Organization" --result-format csv | tail -1 | tr -d '\r')
SUFFIX=$(echo "$ORG_ID" | tail -c 7 | tr 'A-Z' 'a-z')
profile_id() { sf data query --target-org "$ORG" --query "SELECT Id FROM Profile WHERE Name = '$1'" --result-format csv | tail -1 | tr -d '\r'; }

echo "== Creating users (org suffix: $SUFFIX)"
tail -n +2 salesforce/sales_team.csv | while IFS=, read -r FIRST LAST ALIAS ROLE LICENSE PROFILE TERRITORY TZ; do
  LOWER_FIRST=$(echo "$FIRST" | tr 'A-Z' 'a-z'); LOWER_LAST=$(echo "$LAST" | tr 'A-Z' 'a-z')
  USERNAME="${LOWER_FIRST}.${LOWER_LAST}.${SUFFIX}@flozero-demo.example"
  if sf data get record --target-org "$ORG" --sobject User --where "Username='$USERNAME'" </dev/null >/dev/null 2>&1; then
    echo "   exists: $FIRST $LAST"; continue
  fi
  PID=$(profile_id "$PROFILE" </dev/null)
  sf data create record --target-org "$ORG" --sobject User --values \
    "FirstName='$FIRST' LastName='$LAST' Alias='$ALIAS' Username='$USERNAME' Email='${LOWER_FIRST}.${LOWER_LAST}@flozero-demo.example' CommunityNickname='${ALIAS}${SUFFIX}' Title='$ROLE' Department='Sales' Division='$TERRITORY' ProfileId='$PID' TimeZoneSidKey='$TZ' LocaleSidKey='en_US' EmailEncodingKey='UTF-8' LanguageLocaleKey='en_US' UserPermissionsSFContentUser=false" </dev/null >/dev/null
  echo "   created: $FIRST $LAST ($ROLE, $TERRITORY, $LICENSE)"
done

echo "== Assigning the Signal_Pipeline_Admin permission set"
tail -n +2 salesforce/sales_team.csv | while IFS=, read -r FIRST LAST REST; do
  LOWER_FIRST=$(echo "$FIRST" | tr 'A-Z' 'a-z'); LOWER_LAST=$(echo "$LAST" | tr 'A-Z' 'a-z')
  sf org assign permset --target-org "$ORG" --name Signal_Pipeline_Admin \
    --on-behalf-of "${LOWER_FIRST}.${LOWER_LAST}.${SUFFIX}@flozero-demo.example" </dev/null >/dev/null 2>&1 \
    && echo "   assigned: $FIRST $LAST" || echo "   already assigned (or check): $FIRST $LAST"
done

echo "== Verifying"
sf data query --target-org "$ORG" --query "SELECT Name, Alias, Title, Division, Profile.Name, IsActive FROM User WHERE Department = 'Sales' ORDER BY Title, Name"
echo "   Expect 5 active users: 2 Account Executives, 3 Business Development Reps"

echo "== Committing and pushing"
git add -A
git commit -q -m "Add fictional Flozero sales team, territories and Phase 1 taxonomy (decisions #16-22)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Cd5yt51VbTJAz2SMqaNpag" || echo "   nothing new to commit"
git push
echo "== Done"
