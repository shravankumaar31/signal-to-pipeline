"""Builds n8n/workflows/outreach_to_salesforce.json (Phase 5, decision #46).

Input: data/clay_exports/inbox/claude_outreach_*.json, written by Claude over MCP
(rationale + task per primary contact; Gmail drafts already created in the test inbox).
Flow: Run -> Config -> read JSON -> query Contacts + open automated Tasks
      -> Plan (one item: contact updates + new tasks)
      -> PATCH /composite/sobjects (Contact: Why_Now_Rationale__c, Outreach_Status__c)
      -> POST  /composite/sobjects (Task, skipped per contact if an open automated task exists)
      -> Summary -> archive the JSON to processed/<run> when there were no errors.
Re-run: python3 n8n/build_outreach_workflow.py
"""
import json, pathlib, uuid

ROOT = pathlib.Path(__file__).resolve().parent
SF_BASE = "https://orgfarm-ae663148a7-dev-ed.develop.my.salesforce.com/services/data/v62.0"
REPO = "/Users/shravankumaar/signal-to-pipeline"
CRED = {"oAuth2Api": {"id": "ol4NeAZvoDuiCyN2", "name": "Salesforce signal-dev (PKCE)"}}
nodes, conns, x = [], {}, [0]

def add(name, type_, version, params, after=None, extra=None):
    nodes.append({"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "s2p-outreach/" + name)), "name": name, "type": type_,
                  "typeVersion": version, "position": [x[0], 300], "parameters": params, **(extra or {})})
    x[0] += 220
    if after:
        conns.setdefault(after, {"main": [[]]})["main"][0].append({"node": name, "type": "main", "index": 0})
    return name

def code(name, js, after):
    return add(name, "n8n-nodes-base.code", 2, {"mode": "runOnceForAllItems", "jsCode": js}, after, {"executeOnce": True})

def http(name, method, path, after, body=None, query=None):
    p = {"method": method, "url": "={{ $('Config').first().json.sfBase }}" + path,
         "authentication": "genericCredentialType", "genericAuthType": "oAuth2Api", "options": {}}
    if query:
        p.update({"sendQuery": True, "queryParameters": {"parameters": [{"name": "q", "value": query}]}})
    if body:
        p.update({"sendBody": True, "specifyBody": "json", "jsonBody": body,
                  "options": {"response": {"response": {"fullResponse": True, "neverError": True}}}})
    return add(name, "n8n-nodes-base.httpRequest", 4.2, p, after, {"credentials": CRED, "executeOnce": True})

t = add("Run outreach sync", "n8n-nodes-base.manualTrigger", 1, {})
c = code("Config", f"""return [{{ json: {{
  sfBase: '{SF_BASE}',
  inbox: '{REPO}/data/clay_exports/inbox',
  processed: '{REPO}/data/clay_exports/processed',
  runAt: new Date().toISOString(),
}} }}];""", t)
r = add("Read outreach JSON", "n8n-nodes-base.readWriteFile", 1,
        {"operation": "read", "fileSelector": "={{ $('Config').first().json.inbox }}/claude_outreach_*.json", "options": {}}, c)
e = add("Extract outreach", "n8n-nodes-base.extractFromFile", 1, {"operation": "fromJson", "options": {}}, r)
qc = http("Query Contacts", "GET", "/query", e,
          query="SELECT Id, AccountId, Email_Key__c, Outreach_Status__c FROM Contact WHERE Email_Key__c != null")
qt = http("Query open automated Tasks", "GET", "/query", qc,
          query="SELECT Id, WhoId FROM Task WHERE Created_By_Automation__c = true AND IsClosed = false")
plan = code("Plan", """
const contacts = Object.fromEntries(($('Query Contacts').first().json.records || []).map(r => [String(r.Email_Key__c).toLowerCase(), r]));
const openTaskFor = new Set(($input.first().json.records || []).map(r => r.WhoId));
const records = $('Extract outreach').all().flatMap(i => (i.json.data && i.json.data.records) || []);
const updates = [], tasks = [], notFound = [], skippedTasks = [];
for (const rec of records) {
  const c = contacts[String(rec.key).toLowerCase()];
  if (!c) { notFound.push(rec.domain); continue; }
  const u = { attributes: { type: 'Contact' }, Id: c.Id, Why_Now_Rationale__c: String(rec.why_now).slice(0, 2000) };
  // Outreach status is workflow-owned: only move Not Started -> Drafted when an email draft exists
  if (rec.channel === 'Email' && rec.gmail_draft_id && (!c.Outreach_Status__c || c.Outreach_Status__c === 'Not Started')) u.Outreach_Status__c = 'Drafted';
  updates.push(u);
  if (openTaskFor.has(c.Id)) { skippedTasks.push(rec.domain); continue; }
  tasks.push(Object.assign({ attributes: { type: 'Task' }, WhoId: c.Id, WhatId: c.AccountId }, rec.task));
}
return [{ json: { updates, tasks, notFound, skippedTasks } }];
""", qt)
uc = http("Update Contacts", "PATCH", "/composite/sobjects", plan,
          body="={{ JSON.stringify({ allOrNone: false, records: $('Plan').first().json.updates }) }}")
ct = http("Create Tasks", "POST", "/composite/sobjects", uc,
          body="={{ JSON.stringify({ allOrNone: false, records: $('Plan').first().json.tasks }) }}")
sm = code("Summary", """
const plan = $('Plan').first().json;
function res(node, sent) {
  if (!sent.length) return { ok: 0, errors: [] };
  const j = $(node).first().json, body = Array.isArray(j.body) ? j.body : [];
  if (!body.length) return { ok: 0, errors: [{ status: j.statusCode, error: JSON.stringify(j.body).slice(0, 400) }] };
  return { ok: body.filter(b => b.success).length, errors: body.filter(b => !b.success).map(b => JSON.stringify(b.errors).slice(0, 300)) };
}
const contacts = res('Update Contacts', plan.updates), tasks = res('Create Tasks', plan.tasks);
const errors = contacts.errors.length + tasks.errors.length + plan.notFound.length;
return [{ json: { runAt: $('Config').first().json.runAt, errors, contactsUpdated: contacts.ok, tasksCreated: tasks.ok,
  tasksSkippedExisting: plan.skippedTasks, contactsNotFound: plan.notFound, contactErrors: contacts.errors, taskErrors: tasks.errors } }];
""", ct)
add("Archive file", "n8n-nodes-base.executeCommand", 1, {
    "command": "={{ $json.errors === 0 ? `mkdir -p \"${$('Config').first().json.processed}/${$json.runAt.replace(/[:.]/g, '-')}\" && mv \"${$('Config').first().json.inbox}\"/claude_outreach_*.json \"${$('Config').first().json.processed}/${$json.runAt.replace(/[:.]/g, '-')}/\" && echo archived` : 'echo \"errors found: file left in inbox\"' }}"},
    sm, {"executeOnce": True})

wf = {"name": "Phase 5 – Claude outreach → Salesforce (rationale + tasks)", "nodes": nodes, "connections": conns,
      "settings": {"executionOrder": "v1"}, "pinData": {}, "active": False}
out = ROOT / "workflows" / "outreach_to_salesforce.json"
out.write_text(json.dumps(wf, indent=2))
print("wrote", out, len(nodes), "nodes")
