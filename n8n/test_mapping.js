// Tests the Clay -> Salesforce mapping without printing any personal data.
// Usage: node n8n/test_mapping.js [accounts.csv] [contacts.csv]
const fs = require('fs');
const assert = require('assert');
const M = require('./lib/mapping.js');

function parseCSV(text) {
  text = text.replace(/^﻿/, '').replace(/\r/g, '');
  const rows = []; let row = [], f = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"' && text[i + 1] === '"') { f += '"'; i++; } else if (c === '"') q = false; else f += c; }
    else if (c === '"') q = true; else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n') { row.push(f); rows.push(row); row = []; f = ''; } else f += c;
  }
  if (f || row.length) { row.push(f); rows.push(row); }
  const [h, ...r] = rows;
  return r.filter(x => x.length > 1).map(x => Object.fromEntries(h.map((k, i) => [k, x[i] ?? ''])));
}

const RUN = '2026-10-14T22:00:00.000Z';

// --- unit checks
assert.equal(M.employeeRange('', '11-50'), '1-50');
assert.equal(M.employeeRange('500', ''), '201-500');
assert.equal(M.employeeRange('', '1001-5000'), '1001+');
assert.equal(M.fundingStage('Series E'), 'Series E+');
assert.equal(M.fundingStage('Series B'), 'Series B');
assert.equal(M.fundingStage('Profitable private'), 'Unknown');
assert.equal(M.mergeList('Salesforce, HubSpot', 'hubspot, Marketo', 100), 'Salesforce, HubSpot, Marketo');
assert.equal(M.linkedinSlug('https://www.linkedin.com/in/r%c3%a9my-x/'), 'rémy-x');

const c1 = M.mapContact({ 'Is Primary': 'true', Domain: 'x.com', 'Work Email': 'A@X.com', 'First Name': 'A', 'Last Name': 'B', Title: 'VP RevOps', 'Contact Persona': 'Head of RevOps', 'Contact Seniority': 'VP', 'Email Verification Status': 'Valid', 'Linkedin URL': 'https://www.linkedin.com/in/ab/' }, null, RUN);
assert.equal(c1.key, 'a@x.com'); assert.equal(c1.body.Enrichment_Status__c, 'Complete'); assert.equal(c1.body.Outreach_Status__c, 'Not Started');
const c2 = M.mapContact({ 'Is Primary': 'true', Domain: 'y.com', 'First Name': 'C', 'Last Name': 'D', Title: 'VP', 'Contact Persona': 'Head of RevOps', 'Contact Seniority': 'VP', 'Linkedin URL': 'https://www.linkedin.com/in/cd-1/' }, null, RUN);
assert.equal(c2.key, 'li:cd-1'); assert.equal(c2.body.Enrichment_Status__c, 'Partial'); assert.equal(c2.body.Missing_Fields__c, 'Email'); assert.ok(!('Email' in c2.body));
const c3 = M.mapContact({ 'Is Primary': 'true', Domain: 'x.com', 'Work Email': 'a@x.com', 'First Name': 'New', 'Last Name': 'B' }, { FirstName: 'Rep-edited', Email: 'a@x.com' }, RUN);
assert.ok(!('FirstName' in c3.body) && !('Outreach_Status__c' in c3.body), 'fill-if-blank + workflow-owned status');
assert.equal(M.mapContact({ 'Is Primary': 'false' }, null, RUN).skip, 'not primary');
console.log('unit checks OK');

// --- real accounts file
const accFile = process.argv[2];
if (accFile) {
  const rows = parseCSV(fs.readFileSync(accFile, 'utf8'));
  const out = rows.map(r => M.mapAccount(r, null, RUN));
  const ok = out.filter(o => !o.skip), skipped = out.filter(o => o.skip);
  const picks = { Signal_Tier__c: M.MAP.TIERS, Primary_Signal__c: M.MAP.SIGNAL_TYPES.concat([null]), Funding_Stage__c: M.MAP.FUNDING.concat([null]), Incumbent_Comp_Tool__c: M.MAP.COMP_TOOLS, Employee_Range__c: ['1-50', '51-200', '201-500', '501-1000', '1001+', null], Enrichment_Status__c: ['Complete', 'Partial'] };
  for (const o of ok) {
    for (const [f, vals] of Object.entries(picks)) assert.ok(vals.includes(o.body[f]), `${o.domain} ${f}=${o.body[f]}`);
    for (const s of o.signals) assert.ok(M.MAP.SIGNAL_TYPES.includes(s.body.Signal_Type__c) && s.body.Detail__c.length <= 255);
    assert.ok(!o.body.Missing_Fields__c || o.body.Missing_Fields__c.length <= 255);
    assert.ok(!o.body.Tech_Stack__c || o.body.Tech_Stack__c.length <= 5000);
  }
  const keys = ok.flatMap(o => o.signals.map(s => s.key));
  assert.equal(new Set(keys).size, keys.length, 'signal keys unique');
  console.log(`accounts: ${rows.length} rows -> ${ok.length} upserts, ${skipped.length} skipped, ${keys.length} signals`);
  for (const s of skipped) console.log('  skip', s.domain, '-', s.skip);
  for (const o of ok) console.log(`  ${o.domain.padEnd(20)} ${o.tier} score=${o.body.Signal_Score__c} ${o.body.Enrichment_Status__c.padEnd(8)} range=${o.body.Employee_Range__c} emp=${o.body.NumberOfEmployees} fund=${o.body.Funding_Stage__c} signals=${o.signals.map(s => s.key.split('|').slice(1).join('@')).join(', ')} missing=[${o.body.Missing_Fields__c || ''}]`);
}

// --- real contacts file (counts only)
const conFile = process.argv[3];
if (conFile) {
  const rows = parseCSV(fs.readFileSync(conFile, 'utf8'));
  const out = rows.map(r => M.mapContact(r, null, RUN));
  const ok = out.filter(o => !o.skip);
  const by = (f) => ok.reduce((a, o) => (a[f(o)] = (a[f(o)] || 0) + 1, a), {});
  assert.equal(new Set(ok.map(o => o.key)).size, ok.length, 'contact keys unique');
  console.log(`contacts: ${rows.length} rows -> ${ok.length} upserts; columns present: Work Email=${'Work Email' in rows[0]}, Email Verification Status=${'Email Verification Status' in rows[0]}, Outreach Channel=${'Outreach Channel' in rows[0]}`);
  console.log('  status', by(o => o.body.Enrichment_Status__c), 'key type', by(o => o.key.startsWith('li:') ? 'linkedin' : 'email'), 'persona', by(o => o.body.Persona__c));
  console.log('  domains', ok.map(o => o.domain).join(', '));
}
