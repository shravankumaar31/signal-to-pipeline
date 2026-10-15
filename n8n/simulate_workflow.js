// Dry-run the workflow's Code nodes outside n8n with mocked $/$input (no Salesforce calls, no personal data printed).
// Usage: node n8n/simulate_workflow.js <accounts.csv> [contacts.csv]
const fs = require('fs');
const wf = require('./workflows/clay_to_salesforce.json');
const { parseCSV } = (() => { const src = fs.readFileSync(__dirname + '/test_mapping.js', 'utf8'); const m = {}; eval(src.match(/function parseCSV[\s\S]*?\n}\n/)[0] + ';m.parseCSV=parseCSV'); return m; })();
const codeOf = n => wf.nodes.find(x => x.name === n).parameters.jsCode;
const out = {};
const mk = (name) => ({ all: () => out[name], first: () => out[name][0] });
const $ = (name) => mk(name);
function run(name, input) { out[name] = new Function('$', '$input', codeOf(name))($, { first: () => input[0], all: () => input }); return out[name]; }
const items = f => parseCSV(fs.readFileSync(f, 'utf8')).map(json => ({ json }));
run('Config', []);
out['Extract Accounts'] = items(process.argv[2]);
const acc = run('Map Accounts', [{ json: { records: [] } }]);
const sig = run('Build Signals', [{ json: { records: [] } }]);
console.log('Map Accounts ->', acc.length, 'items; Build Signals ->', sig.length, 'items; sample signal body keys:', Object.keys(sig[0].json.body).join(','));
if (process.argv[3]) {
  out['Extract Contacts'] = items(process.argv[3]);
  const con = run('Map Contacts', [{ json: { records: [] } }]);
  console.log('Map Contacts ->', con.length, 'items; channels', con.reduce((a, c) => (a[c.json.channel] = (a[c.json.channel] || 0) + 1, a), {}));
}
out['Upsert Account'] = acc.map(() => ({ json: { statusCode: 201 } }));
out['Upsert Signal'] = sig.map(() => ({ json: { statusCode: 201 } }));
out['Map Contacts'] = out['Map Contacts'] || []; out['Upsert Contact'] = out['Map Contacts'].map(() => ({ json: { statusCode: 201 } }));
console.log('Summary ->', JSON.stringify(run('Summary', [{ json: {} }])[0].json));
