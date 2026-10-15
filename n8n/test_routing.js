// Scenario tests for n8n/lib/routing.js (decision #47). Company-level data only.
// Usage: node n8n/test_routing.js [path/to/clay_accounts.csv]
const fs = require('fs');
const assert = require('assert');
const { route } = require('./lib/routing.js');

const TERR = Object.fromEntries(fs.readFileSync(__dirname + '/../salesforce/territories.csv', 'utf8').trim().split('\n').slice(1)
  .map(l => l.split(',')).map(([region, , territory, ae, bdr]) => [region, { territory, ae, bdr }]));
const ROSTER = () => [
  { id: 'U-maya', alias: 'mchen', name: 'Maya Chen', role: 'AE', isActive: true, status: 'Available', startDate: '2024-03-01', attainment: 112, max: 10 },
  { id: 'U-priya', alias: 'praman', name: 'Priya Raman', role: 'AE', isActive: true, status: 'Available', startDate: '2026-08-17', attainment: 38, max: 10 },
  { id: 'U-lucas', alias: 'lromero', name: 'Lucas Romero', role: 'BDR', isActive: true, status: 'Available', startDate: '2025-01-06', attainment: 125, max: 10 },
  { id: 'U-daniel', alias: 'dokafor', name: 'Daniel Okafor', role: 'BDR', isActive: true, status: 'Available', startDate: '2026-09-01', attainment: 20, max: 8 },
  { id: 'U-hannah', alias: 'hbrooks', name: 'Hannah Brooks', role: 'BDR', isActive: true, status: 'Out of Office', oooUntil: '2026-10-24', startDate: '2025-06-02', attainment: 90, max: 8 },
];
const QUEUE = 'U-revops';

function loadAccounts(file) {
  const t = fs.readFileSync(file, 'utf8').replace(/^﻿/, '').replace(/\r/g, '');
  const rows = []; let row = [], f = '', q = false;
  for (let i = 0; i < t.length; i++) { const c = t[i];
    if (q) { if (c === '"' && t[i + 1] === '"') { f += '"'; i++; } else if (c === '"') q = false; else f += c; }
    else if (c === '"') q = true; else if (c === ',') { row.push(f); f = ''; } else if (c === '\n') { row.push(f); rows.push(row); row = []; f = ''; } else f += c; }
  if (f || row.length) { row.push(f); rows.push(row); }
  const [h, ...r] = rows;
  return r.filter(x => x.length > 1).map(x => Object.fromEntries(h.map((k, i) => [k, x[i]]))).filter(x => ['A', 'B', 'C'].includes(x['Signal Tier']))
    .map(x => ({ id: x['Domain'], tier: x['Signal Tier'], score: Number(x['Score']), region: x['HQ Region'], OwnerId: QUEUE }));
}
const apply = (accts, out) => { for (const u of out.updates) Object.assign(accts.find(a => a.id === u.Id), u); };
const owners = (accts, reps, f) => { const n = Object.fromEntries(reps.map(r => [r.id, r.name])); const m = {}; for (const a of accts) if (a.tier !== 'C') { const k = n[a[f]] || 'RevOps queue'; m[k] = (m[k] || 0) + 1; } return m; };

const file = process.argv[2];
if (!file) { console.log('usage: node n8n/test_routing.js <clay_accounts.csv>'); process.exit(0); }
const NOW = '2026-10-15T19:00:00.000Z';

// 1. initial routing
let reps = ROSTER(), accts = loadAccounts(file);
let out = route({ reps, accounts: accts, territories: TERR, today: '2026-10-15', nowIso: NOW, queueId: QUEUE });
apply(accts, out);
const ae = owners(accts, reps, 'OwnerId'), bdr = owners(accts, reps, 'BDR__c');
console.log('1. initial  AE', ae, 'BDR', bdr);
assert.deepStrictEqual(ae, { 'Maya Chen': 10, 'Priya Raman': 4 });
assert.deepStrictEqual(bdr, { 'Lucas Romero': 10, 'Daniel Okafor': 4 });
const get = d => accts.find(a => a.id === d);
assert.equal(get('keepersecurity.com').OwnerId, 'U-maya');      // Tier A, Priya ramping -> overflow
assert.equal(get('keepersecurity.com').Home_AE__c, 'U-maya');   // overflow = new home
assert.equal(get('confidotech.com').BDR__c, 'U-lucas');         // Hannah OOO -> coverage
assert.equal(get('confidotech.com').Home_BDR__c, 'U-hannah');   // home kept for return
assert.ok(accts.filter(a => a.tier === 'C').every(a => a.OwnerId === QUEUE), 'Tier C stays in queue');
for (const u of out.updates.slice(0, 4)) console.log('   ', u.Id.padEnd(18), u.Routing_Reason__c);

// 2. idempotent re-run
out = route({ reps: ROSTER(), accounts: accts, territories: TERR, today: '2026-10-15', nowIso: NOW, queueId: QUEUE });
console.log('2. re-run   updates:', out.updates.length); assert.equal(out.updates.length, 0);

// 3. Hannah back after 10/24 -> her East accounts return
reps = ROSTER(); out = route({ reps, accounts: accts, territories: TERR, today: '2026-10-26', nowIso: NOW, queueId: QUEUE }); apply(accts, out);
console.log('3. Hannah back  BDR', owners(accts, reps, 'BDR__c'), out.updates.map(u => u.Id).join(', '));
assert.equal(owners(accts, reps, 'BDR__c')['Hannah Brooks'], 4);

// 4. Maya goes OOO -> coverage only where Priya is eligible (Tier B, ramp cap 5)
reps = ROSTER(); reps[0].status = 'Out of Office'; reps[0].oooUntil = '2026-11-05';
out = route({ reps, accounts: accts, territories: TERR, today: '2026-10-26', nowIso: NOW, queueId: QUEUE }); apply(accts, out);
console.log('4. Maya OOO   AE', owners(accts, reps, 'OwnerId'), '| moved', out.updates.length, '|', out.updates[0] && out.updates[0].Routing_Reason__c);
assert.equal(owners(accts, reps, 'OwnerId')['Priya Raman'], 5);

// 5. Maya back -> covered account returns home
reps = ROSTER(); out = route({ reps, accounts: accts, territories: TERR, today: '2026-11-06', nowIso: NOW, queueId: QUEUE }); apply(accts, out);
console.log('5. Maya back  AE', owners(accts, reps, 'OwnerId'));
assert.deepStrictEqual(owners(accts, reps, 'OwnerId'), { 'Maya Chen': 10, 'Priya Raman': 4 });

// 6. Lucas inactive -> permanent reassignment to eligible BDRs, rest queued
reps = ROSTER(); reps[2].isActive = false; reps[4].status = 'Available';
out = route({ reps, accounts: accts, territories: TERR, today: '2026-11-06', nowIso: NOW, queueId: QUEUE }); apply(accts, out);
console.log('6. Lucas inactive  BDR', owners(accts, reps, 'BDR__c'));
assert.ok(!owners(accts, reps, 'BDR__c')['Lucas Romero'], 'inactive rep keeps nothing');
console.log('routing scenarios OK');
