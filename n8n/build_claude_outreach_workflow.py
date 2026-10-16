"""Builds n8n/workflows/claude_outreach.json (decision #50): the Claude step inside n8n.

Replaces the manual MCP step + JSON hand-off of Phase 5 (decision #46) for unattended runs.
Flow: Run -> Config -> query primary Contacts (A/B) + Signals + open automated Tasks
      -> Build requests (one per contact needing outreach)
      -> IF useMock: Mock Claude  | else: Call Claude (Messages API, JSON schema output)
      -> Validate + plan (guardrails; failures held for review, never written)
      -> PATCH Contacts (rationale + drafts) -> POST Tasks (owner = BDR) -> Summary
Safety: no email or Gmail node exists in this workflow. Drafts are saved as text on the Contact and in
the Task description; nothing is sent. Config.dryRun = true writes nothing.
Re-run: python3 n8n/build_claude_outreach_workflow.py
"""
import json, pathlib, uuid

ROOT = pathlib.Path(__file__).resolve().parent
LIB = (ROOT / "lib" / "outreach.js").read_text().split("if (typeof module")[0]
SF_BASE = "https://orgfarm-ae663148a7-dev-ed.develop.my.salesforce.com/services/data/v62.0"
SF_CRED = {"oAuth2Api": {"id": "ol4NeAZvoDuiCyN2", "name": "Salesforce signal-dev (PKCE)"}}
nodes, conns, x = [], {}, [0]

def add(name, type_, version, params, after=None, extra=None, out=0, y=300):
    nodes.append({"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "s2p-claude/" + name)), "name": name, "type": type_,
                  "typeVersion": version, "position": [x[0], y], "parameters": params, **(extra or {})})
    x[0] += 220
    if after:
        c = conns.setdefault(after, {"main": [[]]})["main"]
        while len(c) <= out: c.append([])
        c[out].append({"node": name, "type": "main", "index": 0})
    return name

def code(name, js, after, once=True, out=0, y=300):
    return add(name, "n8n-nodes-base.code", 2, {"mode": "runOnceForAllItems", "jsCode": js}, after,
               {"executeOnce": True} if once else None, out, y)

def sf(name, method, path, after, query=None, body=None):
    p = {"method": method, "url": "={{ $('Config').first().json.sfBase }}" + path,
         "authentication": "genericCredentialType", "genericAuthType": "oAuth2Api", "options": {}}
    if query:
        p.update({"sendQuery": True, "queryParameters": {"parameters": [{"name": "q", "value": query}]}})
    if body:
        p.update({"sendBody": True, "specifyBody": "json", "jsonBody": body,
                  "options": {"response": {"response": {"fullResponse": True, "neverError": True}}}})
    return add(name, "n8n-nodes-base.httpRequest", 4.2, p, after, {"credentials": SF_CRED, "executeOnce": True})

t = add("Run Claude outreach", "n8n-nodes-base.manualTrigger", 1, {})
c = code("Config", f"""return [{{ json: {{
  sfBase: '{SF_BASE}',
  model: 'claude-sonnet-5-5',   // or 'claude-haiku-5-5' for a cheaper run
  useMock: true,                // true = no API call (no key needed). Set false once the "Anthropic API" credential exists.
  dryRun: true,                 // true = generate + validate, write nothing to Salesforce
  includeExisting: false,       // true = also regenerate contacts that already have a rationale
  onlyDomains: [],              // e.g. ['keepersecurity.com'] to test on one account
  maxContacts: 20,              // cost cap per run
  runAt: new Date().toISOString(),
}} }}];""", t)
qc = sf("Query Contacts", "GET", "/query", c, query=(
    "SELECT Id, AccountId, FirstName, Title, Persona__c, Email_Verification_Status__c, LinkedIn_URL__c, "
    "Outreach_Status__c, Why_Now_Rationale__c, Account.Name, Account.Domain__c, Account.Signal_Tier__c, "
    "Account.Primary_Signal__c, Account.Open_Sales_Roles_Count__c, Account.Funding_Stage__c, "
    "Account.Last_Funding_Amount__c, Account.Last_Funding_Date__c, Account.Incumbent_Comp_Tool__c, "
    "Account.BDR__c, Account.OwnerId FROM Contact WHERE Email_Key__c != null AND Account.Signal_Tier__c IN ('A','B')"))
qs = sf("Query Signals", "GET", "/query", qc, query=(
    "SELECT Account__c, Signal_Type__c, Signal_Date__c, Detail__c, Source_URL__c FROM Signal__c "
    "WHERE Account__r.Signal_Tier__c IN ('A','B')"))
qt = sf("Query open automated Tasks", "GET", "/query", qs,
        query="SELECT Id, WhoId FROM Task WHERE Created_By_Automation__c = true AND IsClosed = false")
br = code("Build requests", LIB + """
const cfg = $('Config').first().json;
const today = cfg.runAt.slice(0, 10);
const sigBy = {};
for (const s of ($('Query Signals').first().json.records || [])) (sigBy[s.Account__c] = sigBy[s.Account__c] || []).push(s);
const openTask = new Set(($('Query open automated Tasks').first().json.records || []).map(t => t.WhoId));
const only = (cfg.onlyDomains || []).map(d => d.toLowerCase());
const out = [];
for (const ct of ($('Query Contacts').first().json.records || [])) {
  const domain = String((ct.Account || {}).Domain__c || '').toLowerCase();
  if (only.length && !only.includes(domain)) continue;
  if (ct.Why_Now_Rationale__c && !cfg.includeExisting) continue;
  const ctx = buildContext(ct, sigBy[ct.AccountId], today);
  out.push({ json: { ctx, request: buildRequest(ctx, cfg.model), status: ct.Outreach_Status__c || null, hasOpenTask: openTask.has(ct.Id) } });
  if (out.length >= cfg.maxContacts) break;
}
return out;   // no items = nothing to do; the run stops here
""", qt)
iff = add("Use mock?", "n8n-nodes-base.if", 2, {
    "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                   "conditions": [{"id": "mock", "leftValue": "={{ $('Config').first().json.useMock }}", "rightValue": "",
                                   "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                   "combinator": "and"}, "options": {}}, br)
mock = code("Mock Claude", LIB + "\nreturn $input.all().map(i => ({ json: mockResponse(i.json.ctx) }));", iff, once=False, out=0, y=200)
x[0] -= 220
call = add("Call Claude", "n8n-nodes-base.httpRequest", 4.2, {
    "method": "POST", "url": "https://api.anthropic.com/v1/messages",
    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
    "sendHeaders": True, "headerParameters": {"parameters": [
        {"name": "anthropic-version", "value": "2023-06-01"}, {"name": "content-type", "value": "application/json"}]},
    "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.request) }}",
    "options": {"timeout": 120000, "batching": {"batch": {"batchSize": 1, "batchInterval": 1000}},
                "response": {"response": {"fullResponse": True, "neverError": True}}}},
    iff, {"retryOnFail": True, "maxTries": 2, "waitBetweenTries": 3000}, out=1, y=400)
vp = code("Validate + plan", LIB + """
const cfg = $('Config').first().json;
const today = cfg.runAt.slice(0, 10);
const reqs = $('Build requests').all(), res = $input.all();
const contacts = [], tasks = [], review = [], drafts = [];
let inTok = 0, outTok = 0;
reqs.forEach((r, i) => {
  const { ctx, status, hasOpenTask } = r.json;
  const p = parseResponse(res[i] ? res[i].json : null);
  if (p.usage) { inTok += p.usage.input_tokens || 0; outTok += p.usage.output_tokens || 0; }
  const errors = p.error ? [p.error] : validate(p.out, ctx);
  if (errors.length) { review.push({ account: ctx.account, channel: ctx.channel, errors }); return; }
  const w = writesFor(ctx, p.out, today, cfg.runAt, status, hasOpenTask);
  contacts.push(w.contact); if (w.task) tasks.push(w.task);
  drafts.push({ account: ctx.account, channel: ctx.channel, why_now: w.contact.Why_Now_Rationale__c,
                subject: w.contact.Draft_Subject__c, body: w.contact.Draft_Body__c, task: w.task ? w.task.Subject : '(open task exists)' });
});
// Sonnet 5.5 list price $2 / $10 per MTok (Haiku 5.5: $0.10 / $0.50)
const price = String(cfg.model).includes('haiku') ? [0.10, 0.50] : [2, 10];
const estCostUsd = Math.round((inTok * price[0] + outTok * price[1]) / 1e4) / 100;
return [{ json: { dryRun: cfg.dryRun, mock: cfg.useMock, contacts, tasks, review, drafts, tokens: { input: inTok, output: outTok }, estCostUsd } }];
""", None, once=False)   # must see ALL items: executeOnce would pass only the first

conns.setdefault(mock, {"main": [[]]})["main"][0].append({"node": vp, "type": "main", "index": 0})
conns.setdefault(call, {"main": [[]]})["main"][0].append({"node": vp, "type": "main", "index": 0})
uc = sf("Update Contacts", "PATCH", "/composite/sobjects", vp,
        body="={{ JSON.stringify({ allOrNone: false, records: $('Config').first().json.dryRun ? [] : $('Validate + plan').first().json.contacts }) }}")
ct = sf("Create Tasks", "POST", "/composite/sobjects", uc,
        body="={{ JSON.stringify({ allOrNone: false, records: $('Config').first().json.dryRun ? [] : $('Validate + plan').first().json.tasks }) }}")
code("Summary", """
const p = $('Validate + plan').first().json;
function res(node, sent) {
  if (p.dryRun || !sent.length) return { ok: 0, errors: [] };
  const j = $(node).first().json, body = Array.isArray(j.body) ? j.body : [];
  if (!body.length) return { ok: 0, errors: [{ status: j.statusCode, error: JSON.stringify(j.body).slice(0, 400) }] };
  return { ok: body.filter(b => b.success).length, errors: body.filter(b => !b.success).map(b => JSON.stringify(b.errors).slice(0, 300)) };
}
const c = res('Update Contacts', p.contacts), t = res('Create Tasks', p.tasks);
return [{ json: { runAt: $('Config').first().json.runAt, dryRun: p.dryRun, mock: p.mock,
  planned: { contacts: p.contacts.length, tasks: p.tasks.length }, written: { contacts: c.ok, tasks: t.ok },
  needsReview: p.review, errors: c.errors.length + t.errors.length, errorDetail: [...c.errors, ...t.errors],
  tokens: p.tokens, estCostUsd: p.estCostUsd, drafts: p.drafts } }];
""", ct)

wf = {"name": "Phase 5b – Claude outreach in n8n (drafts saved, never sent)", "nodes": nodes, "connections": conns,
      "settings": {"executionOrder": "v1"}, "pinData": {}, "active": False}
out = ROOT / "workflows" / "claude_outreach.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(wf, indent=2))
print("wrote", out, len(nodes), "nodes")
