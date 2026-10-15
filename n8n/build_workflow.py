"""Builds n8n/workflows/clay_to_salesforce.json from n8n/lib/mapping.js (decisions #43, #44).

Flow: Run -> Config -> read accounts CSV -> query existing Accounts -> map -> upsert Account
      -> query existing Signals -> build -> upsert Signal__c
      -> read contacts CSV -> query existing Contacts -> map -> upsert Contact
      -> summary -> move files to processed/<run> (only when there were no errors)
Re-run: python3 n8n/build_workflow.py
"""
import json, pathlib, uuid

ROOT = pathlib.Path(__file__).resolve().parent
LIB = (ROOT / "lib" / "mapping.js").read_text().split("if (typeof module")[0]

SF_BASE = "https://orgfarm-ae663148a7-dev-ed.develop.my.salesforce.com/services/data/v62.0"
REPO = "/Users/shravankumaar/signal-to-pipeline"
CRED = {"oAuth2Api": {"id": "ol4NeAZvoDuiCyN2", "name": "Salesforce signal-dev (PKCE)"}}

nodes, conns = [], {}
def node(name, type_, version, params, x, extra=None, after=None):
    n = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "s2p/" + name)), "name": name, "type": type_,
         "typeVersion": version, "position": [x, 300 if after is None or len(nodes) % 2 == 0 else 300], "parameters": params}
    n.update(extra or {})
    nodes.append(n)
    if after:
        conns.setdefault(after, {"main": [[]]})["main"][0].append({"node": name, "type": "main", "index": 0})
    return name

def code(name, js, x, after, once=False):
    return node(name, "n8n-nodes-base.code", 2, {"mode": "runOnceForAllItems", "jsCode": js}, x,
                {"executeOnce": True} if once else None, after)

def http(name, method, url, x, after, body=None, once=False, query=None, full=True):
    p = {"method": method, "url": url, "authentication": "genericCredentialType", "genericAuthType": "oAuth2Api", "options": {}}
    if query:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": [{"name": k, "value": v} for k, v in query.items()]}
    if body:
        p.update({"sendBody": True, "specifyBody": "json", "jsonBody": body})
    if full:
        p["options"] = {"response": {"response": {"fullResponse": True, "neverError": True}}}
    extra = {"credentials": CRED}
    if once: extra["executeOnce"] = True
    return node(name, "n8n-nodes-base.httpRequest", 4.2, p, x, extra, after)

def read_csv(name, pattern, x, after, once=False):
    r = node(f"Read {name} CSV", "n8n-nodes-base.readWriteFile", 1,
             {"operation": "read", "fileSelector": "={{ $('Config').first().json.inbox }}/" + pattern, "options": {}},
             x, {"executeOnce": True} if once else None, after)
    return node(f"Extract {name}", "n8n-nodes-base.extractFromFile", 1, {"operation": "csv", "options": {}}, x + 220, None, r)

X = iter(range(0, 10000, 220))
t = node("Run pipeline", "n8n-nodes-base.manualTrigger", 1, {}, next(X))
c = code("Config", f"""return [{{ json: {{
  sfBase: '{SF_BASE}',
  inbox: '{REPO}/data/clay_exports/inbox',
  processed: '{REPO}/data/clay_exports/processed',
  runAt: new Date().toISOString(),
}} }}];""", next(X), t)

ea = read_csv("Accounts", "clay_accounts_*.csv", next(X), c); next(X)
qa = http("Query existing Accounts", "GET", "={{ $('Config').first().json.sfBase }}/query", next(X), ea, once=True, full=False,
          query={"q": "SELECT Id, Domain__c, Name, Website, Enriched_Industry__c, BillingCity, BillingCountry, LinkedIn_Company_URL__c, Tech_Stack__c FROM Account WHERE Domain__c != null"})
ma = code("Map Accounts", LIB + """
const runAt = $('Config').first().json.runAt;
const existing = Object.fromEntries(($input.first().json.records || []).map(r => [String(r.Domain__c).toLowerCase(), r]));
const byDomain = {};
for (const item of $('Extract Accounts').all()) {
  const d = String(item.json['Domain'] || '').trim().toLowerCase();
  byDomain[d || ('row' + Object.keys(byDomain).length)] = item.json;   // later export wins
}
const out = [];
for (const row of Object.values(byDomain)) {
  const m = mapAccount(row, existing[String(row['Domain'] || '').trim().toLowerCase()], runAt);
  out.push({ json: m });
}
return out.filter(o => !o.json.skip);   // Excluded / no-domain rows are not written
""", next(X), qa)
ua = http("Upsert Account", "PATCH", "={{ $('Config').first().json.sfBase }}/sobjects/Account/Domain__c/{{ encodeURIComponent($json.domain) }}",
          next(X), ma, body="={{ JSON.stringify($json.body) }}")

qs = http("Query existing Signals", "GET", "={{ $('Config').first().json.sfBase }}/query", next(X), ua, once=True, full=False,
          query={"q": "SELECT Signal_Key__c FROM Signal__c WHERE Signal_Key__c != null"})
bs = code("Build Signals", """
const have = new Set(($input.first().json.records || []).map(r => r.Signal_Key__c));
const out = [];
for (const a of $('Map Accounts').all()) {
  for (const s of (a.json.signals || [])) {
    const body = Object.assign({}, s.body);
    if (!have.has(s.key)) body.Account__r = { Domain__c: a.json.domain };   // master-detail set on create only
    out.push({ json: { key: s.key, body } });
  }
}
return out;
""", next(X), qs)
us = http("Upsert Signal", "PATCH", "={{ $('Config').first().json.sfBase }}/sobjects/Signal__c/Signal_Key__c/{{ encodeURIComponent($json.key) }}",
          next(X), bs, body="={{ JSON.stringify($json.body) }}")

ec = read_csv("Contacts", "clay_contacts_*.csv", next(X), us, once=True); next(X)
qc = http("Query existing Contacts", "GET", "={{ $('Config').first().json.sfBase }}/query", next(X), ec, once=True, full=False,
          query={"q": "SELECT Id, Email_Key__c, FirstName, LastName, Email, LinkedIn_URL__c, Outreach_Status__c FROM Contact WHERE Email_Key__c != null"})
mc = code("Map Contacts", LIB + """
const runAt = $('Config').first().json.runAt;
const existing = Object.fromEntries(($input.first().json.records || []).map(r => [String(r.Email_Key__c).toLowerCase(), r]));
const out = [];
for (const item of $('Extract Contacts').all()) {
  const pre = mapContact(item.json, null, runAt);
  if (pre.skip) continue;
  const m = mapContact(item.json, existing[pre.key], runAt);
  out.push({ json: m });
}
return out;
""", next(X), qc)
uc = http("Upsert Contact", "PATCH", "={{ $('Config').first().json.sfBase }}/sobjects/Contact/Email_Key__c/{{ encodeURIComponent($json.key) }}",
          next(X), mc, body="={{ JSON.stringify($json.body) }}")

sm = code("Summary", """
function tally(upsertNode, mapNode, label) {
  const sent = $(mapNode).all(), res = $(upsertNode).all();
  const r = { created: 0, updated: 0, skipped: 0, errors: [] };
  res.forEach((it, i) => {
    const src = sent[i] ? sent[i].json : {};
    if (src.skip) { r.skipped++; return; }
    const code = it.json.statusCode;
    if (code === 201) r.created++;
    else if (code === 200 || code === 204) r.updated++;
    else r.errors.push({ [label]: src.domain || src.key, status: code, error: JSON.stringify(it.json.body || it.json).slice(0, 300) });
  });
  return r;
}
const accounts = tally('Upsert Account', 'Map Accounts', 'account');
const signals = tally('Upsert Signal', 'Build Signals', 'signal');
const contacts = tally('Upsert Contact', 'Map Contacts', 'contact');
const errors = accounts.errors.length + signals.errors.length + contacts.errors.length;
const channels = {};
for (const c of $('Map Contacts').all()) if (c.json.channel) channels[c.json.channel] = (channels[c.json.channel] || 0) + 1;
return [{ json: { runAt: $('Config').first().json.runAt, errors, accounts, signals, contacts, outreachChannels: channels } }];
""", next(X), uc, once=True)
node("Archive files", "n8n-nodes-base.executeCommand", 1, {
    "command": "={{ $json.errors === 0 ? `mkdir -p \"${$('Config').first().json.processed}/${$json.runAt.replace(/[:.]/g, '-')}\" && mv \"${$('Config').first().json.inbox}\"/clay_*.csv \"${$('Config').first().json.processed}/${$json.runAt.replace(/[:.]/g, '-')}/\" && echo archived` : 'echo \"errors found: files left in inbox\"' }}"},
    next(X), {"executeOnce": True}, sm)

wf = {"name": "Phase 4 – Clay CSV → Salesforce upsert", "nodes": nodes, "connections": conns,
      "settings": {"executionOrder": "v1"}, "pinData": {}, "active": False}
out = ROOT / "workflows" / "clay_to_salesforce.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(wf, indent=2))
print("wrote", out, len(nodes), "nodes")
