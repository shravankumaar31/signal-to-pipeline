"""Builds n8n/workflows/route_accounts.json (decision #47) from n8n/lib/routing.js + salesforce/territories.csv.

Runs after the Phase 4 load and before Phase 5 outreach.
Flow: Run -> Config -> query sales reps (User routing fields) -> query RevOps queue user -> query Accounts
      -> query Contacts -> query open automated Tasks
      -> Plan (route(): AE = Account.OwnerId, BDR = Account.BDR__c; Contacts follow the AE, open automated Tasks follow the BDR)
      -> PATCH /composite/sobjects Accounts -> Contacts -> Tasks -> Summary
Config.dryRun = true plans everything and writes nothing (Summary shows the plan). Flip to false to apply.
Re-run: python3 n8n/build_routing_workflow.py
"""
import csv, json, pathlib, uuid

ROOT = pathlib.Path(__file__).resolve().parent
LIB = (ROOT / "lib" / "routing.js").read_text().split("if (typeof module")[0]
with open(ROOT.parent / "salesforce" / "territories.csv") as f:
    TERR = {r["region_code"]: {"territory": r["territory"], "ae": r["ae_alias"], "bdr": r["bdr_alias"]} for r in csv.DictReader(f)}

SF_BASE = "https://orgfarm-ae663148a7-dev-ed.develop.my.salesforce.com/services/data/v62.0"
CRED = {"oAuth2Api": {"id": "ol4NeAZvoDuiCyN2", "name": "Salesforce signal-dev (PKCE)"}}
nodes, conns, x = [], {}, [0]

def add(name, type_, version, params, after=None, extra=None):
    nodes.append({"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "s2p-routing/" + name)), "name": name, "type": type_,
                  "typeVersion": version, "position": [x[0], 300], "parameters": params, **(extra or {})})
    x[0] += 220
    if after:
        conns.setdefault(after, {"main": [[]]})["main"][0].append({"node": name, "type": "main", "index": 0})
    return name

def code(name, js, after):
    return add(name, "n8n-nodes-base.code", 2, {"mode": "runOnceForAllItems", "jsCode": js}, after, {"executeOnce": True})

def query(name, soql, after):
    p = {"method": "GET", "url": "={{ $('Config').first().json.sfBase }}/query", "authentication": "genericCredentialType",
         "genericAuthType": "oAuth2Api", "sendQuery": True, "queryParameters": {"parameters": [{"name": "q", "value": soql}]}, "options": {}}
    return add(name, "n8n-nodes-base.httpRequest", 4.2, p, after, {"credentials": CRED, "executeOnce": True})

def patch(name, key, after):
    p = {"method": "PATCH", "url": "={{ $('Config').first().json.sfBase }}/composite/sobjects", "authentication": "genericCredentialType",
         "genericAuthType": "oAuth2Api", "sendBody": True, "specifyBody": "json",
         "jsonBody": "={{ JSON.stringify({ allOrNone: false, records: $('Config').first().json.dryRun ? [] : $('Plan').first().json." + key + " }) }}",
         "options": {"response": {"response": {"fullResponse": True, "neverError": True}}}}
    return add(name, "n8n-nodes-base.httpRequest", 4.2, p, after, {"credentials": CRED, "executeOnce": True})

t = add("Run routing", "n8n-nodes-base.manualTrigger", 1, {})
c = code("Config", f"""return [{{ json: {{
  sfBase: '{SF_BASE}',
  dryRun: true,              // true = plan only, nothing is written. Set to false to apply.
  queueProfile: 'System Administrator',   // RevOps queue = the first active admin (you); Tier C and unassignable accounts stay here
  runAt: new Date().toISOString(),
}} }}];""", t)
qr = query("Query sales reps", "SELECT Id, Alias, Name, Title, IsActive, Routing_Status__c, OOO_Until__c, Rep_Start_Date__c, "
           "Quota_Attainment__c, Max_Accounts__c FROM User WHERE Department = 'Sales'", c)
qq = query("Query RevOps queue user", "SELECT Id, Name FROM User WHERE IsActive = true AND UserType = 'Standard' "
           "AND Profile.Name = 'System Administrator' AND Department != 'Sales' ORDER BY CreatedDate LIMIT 1", qr)
qa = query("Query Accounts", "SELECT Id, Name, Domain__c, Signal_Tier__c, Signal_Score__c, HQ_Region__c, OwnerId, BDR__c, "
           "Home_AE__c, Home_BDR__c FROM Account WHERE Domain__c != null", qq)
qc = query("Query Contacts", "SELECT Id, AccountId, OwnerId FROM Contact WHERE AccountId != null AND Account.Domain__c != null", qa)
qt = query("Query open automated Tasks", "SELECT Id, WhatId, OwnerId FROM Task WHERE Created_By_Automation__c = true AND IsClosed = false", qc)
plan = code("Plan", LIB + f"""
const TERRITORIES = {json.dumps(TERR, separators=(',', ':'))};
const cfg = $('Config').first().json;
const recs = n => $(n).first().json.records || [];
const queueId = (recs('Query RevOps queue user')[0] || {{}}).Id;
if (!queueId) throw new Error('RevOps queue user not found (Config.queueProfile)');
const reps = recs('Query sales reps').map(u => ({{
  id: u.Id, alias: u.Alias, name: u.Name,
  role: /account executive/i.test(u.Title || '') ? 'AE' : /business development/i.test(u.Title || '') ? 'BDR' : null,
  isActive: u.IsActive, status: u.Routing_Status__c || 'Available', oooUntil: u.OOO_Until__c, startDate: u.Rep_Start_Date__c,
  attainment: Number(u.Quota_Attainment__c || 0), max: Number(u.Max_Accounts__c || 0),
}})).filter(r => r.role);
const accounts = recs('Query Accounts').map(a => ({{
  id: a.Id, name: a.Name, tier: a.Signal_Tier__c, score: a.Signal_Score__c, region: a.HQ_Region__c,
  OwnerId: a.OwnerId, BDR__c: a.BDR__c, Home_AE__c: a.Home_AE__c, Home_BDR__c: a.Home_BDR__c,
}}));
const r = route({{ reps, accounts, territories: TERRITORIES, today: cfg.runAt.slice(0, 10), nowIso: cfg.runAt, queueId }});
const accountUpdates = r.updates.map(u => Object.assign({{ attributes: {{ type: 'Account' }} }}, u));
// Contacts follow the AE (Account owner); open automated Tasks follow the BDR (AE if no BDR)
const contactUpdates = [], taskUpdates = [];
for (const c of recs('Query Contacts')) {{
  const f = r.final[c.AccountId];
  if (f && f.AE && c.OwnerId !== f.AE) contactUpdates.push({{ attributes: {{ type: 'Contact' }}, Id: c.Id, OwnerId: f.AE }});
}}
for (const t of recs('Query open automated Tasks')) {{
  const f = r.final[t.WhatId], o = f && (f.BDR || f.AE);
  if (o && t.OwnerId !== o) taskUpdates.push({{ attributes: {{ type: 'Task' }}, Id: t.Id, OwnerId: o }});
}}
const nameOf = Object.fromEntries(accounts.map(a => [a.id, a.name]));
const plan = r.updates.map(u => ({{ account: nameOf[u.Id], reason: u.Routing_Reason__c }}));
return [{{ json: {{ dryRun: cfg.dryRun, accountUpdates, contactUpdates, taskUpdates, plan, reps: r.repSummary }} }}];
""", qt)
ua = patch("Update Accounts", "accountUpdates", plan)
uc = patch("Update Contacts", "contactUpdates", ua)
ut = patch("Update Tasks", "taskUpdates", uc)
code("Summary", """
const p = $('Plan').first().json;
function res(node, sent) {
  if (p.dryRun || !sent.length) return { ok: 0, errors: [] };
  const j = $(node).first().json, body = Array.isArray(j.body) ? j.body : [];
  if (!body.length) return { ok: 0, errors: [{ status: j.statusCode, error: JSON.stringify(j.body).slice(0, 400) }] };
  return { ok: body.filter(b => b.success).length, errors: body.filter(b => !b.success).map(b => JSON.stringify(b.errors).slice(0, 300)) };
}
const a = res('Update Accounts', p.accountUpdates), c = res('Update Contacts', p.contactUpdates), t = res('Update Tasks', p.taskUpdates);
return [{ json: { runAt: $('Config').first().json.runAt, dryRun: p.dryRun,
  planned: { accounts: p.accountUpdates.length, contacts: p.contactUpdates.length, tasks: p.taskUpdates.length },
  written: { accounts: a.ok, contacts: c.ok, tasks: t.ok }, errors: a.errors.length + c.errors.length + t.errors.length,
  errorDetail: [...a.errors, ...c.errors, ...t.errors], reps: p.reps, plan: p.plan } }];
""", ut)

wf = {"name": "Routing – auto-assign Accounts to AE / BDR", "nodes": nodes, "connections": conns,
      "settings": {"executionOrder": "v1"}, "pinData": {}, "active": False}
out = ROOT / "workflows" / "route_accounts.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(wf, indent=2))
print("wrote", out, len(nodes), "nodes")
