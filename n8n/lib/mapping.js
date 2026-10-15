// Clay CSV row -> Salesforce payload mapping (decisions #43, #44; write rules in docs/salesforce_schema.md).
// Pure functions: the same source is embedded in the n8n Code nodes and tested locally
// with `node n8n/test_mapping.js`.

const MAP = {
  ACCOUNT_FILL_IF_BLANK: ['Name', 'Website', 'Enriched_Industry__c', 'BillingCity', 'BillingCountry', 'LinkedIn_Company_URL__c'],
  CONTACT_FILL_IF_BLANK: ['FirstName', 'LastName', 'Email', 'LinkedIn_URL__c'],
  TIERS: ['A', 'B', 'C'],
  SIGNAL_TYPES: ['Hiring RevOps', 'Sales Team Growth', 'Funding', 'Leadership Change', 'Competitor Mention', 'Other'],
  FUNDING: ['Seed', 'Series A', 'Series B', 'Series C', 'Series D', 'Series E+', 'Public', 'Unknown'],
  COMP_TOOLS: ['Spreadsheets', 'Xactly', 'CaptivateIQ', 'Varicent', 'Spiff', 'QuotaPath', 'Everstage', 'Performio', 'In-house build', 'Other', 'Unknown'],
  PERSONAS: ['Head of RevOps', 'Sales Ops / Comp Manager', 'CRO / VP Sales', 'CFO / VP Finance', 'Other'],
  SENIORITY: ['C-Level', 'VP', 'Director', 'Manager', 'IC'],
  VERIFICATION: ['Valid', 'Catch-all', 'Invalid', 'Unknown'],
  COUNTRY: { US: 'United States', CA: 'Canada' },
};

function clean(v) { return v === undefined || v === null ? '' : String(v).trim(); }
function pick(row, names) { for (const n of names) { const v = clean(row[n]); if (v !== '') return v; } return ''; }
function num(v) { const s = clean(v).replace(/[$,\s]/g, ''); if (!s) return null; const n = Number(s); return Number.isFinite(n) ? n : null; }
function isoDate(v) {
  const s = clean(v);
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d) ? null : d.toISOString().slice(0, 10);
}
function truthy(v) { return /^(true|yes|1)$/i.test(clean(v)); }
function cap(s, n) { s = clean(s); return s.length <= n ? s : s.slice(0, n - 1) + '…'; }

function employeeRange(exact, band) {
  let n = num(exact);
  if (n === null) { const m = clean(band).match(/^(\d[\d,]*)/); if (m) n = Number(m[1].replace(/,/g, '')); }
  if (n === null) return null;
  if (n <= 50) return '1-50';
  if (n <= 200) return '51-200';
  if (n <= 500) return '201-500';
  if (n <= 1000) return '501-1000';
  return '1001+';
}

function fundingStage(v) {
  const s = clean(v);
  if (!s) return null;
  if (MAP.FUNDING.includes(s)) return s;
  if (/^series\s+[e-z]\b/i.test(s)) return 'Series E+';
  const m = s.match(/^series\s+([a-d])\b/i); if (m) return 'Series ' + m[1].toUpperCase();
  if (/seed/i.test(s)) return 'Seed';
  if (/public|ipo|nyse|nasdaq/i.test(s)) return 'Public';
  return 'Unknown'; // e.g. "Profitable private": known state, no matching picklist value
}

function compTool(v) { const s = clean(v); if (!s) return 'Unknown'; return MAP.COMP_TOOLS.includes(s) ? s : 'Other'; }

function mergeList(existing, incoming, max) {
  const out = [], seen = new Set();
  for (const part of (clean(existing) + ',' + clean(incoming)).split(',')) {
    const t = part.trim(); if (!t) continue;
    const k = t.toLowerCase(); if (seen.has(k)) continue;
    seen.add(k); out.push(t);
  }
  let s = out.join(', ');
  if (s.length > max) s = s.slice(0, s.lastIndexOf(',', max));
  return s;
}

function dropFilled(body, existing, fields) {
  if (!existing) return body;
  for (const f of fields) if (clean(existing[f]) !== '') delete body[f];
  return body;
}

// --- Signals: one Signal__c per scoring signal. Events are keyed by date (history kept);
// states (Sales Team Growth, Competitor Mention) are re-measured each run, keyed "current".
function buildSignals(row, domain, runDate) {
  const primary = clean(row['Primary Signal']);
  const src = clean(row['Signal Source URL']);
  const defs = [
    ['Pts Hiring', 'Hiring RevOps', 'event', () => row['Hiring Posted'],
      () => 'Hiring: ' + (clean(row['Hiring Role Title']) || 'RevOps / comp role') + (truthy(row['Hiring Comp Specific']) ? ' (comp-specific)' : '') + (truthy(row['Hiring Closed']) ? ' — posting closed' : '')],
    ['Pts Funding', 'Funding', 'event', () => row['Funding Signal Date'] || row['Last Funding Date'],
      () => 'Funding: ' + [clean(row['Funding Stage']), num(row['Last Funding Amount']) ? '$' + Math.round(num(row['Last Funding Amount']) / 1e6) + 'M' : ''].filter(Boolean).join(' ')],
    ['Pts Sales Growth', 'Sales Team Growth', 'state', () => null, () => 'Sales team growth: ' + (num(row['Open Sales Roles']) || 0) + ' open sales roles'],
    ['Pts Leadership', 'Leadership Change', 'event', () => row['Leadership Date'], () => 'Leadership change: new ' + (clean(row['Leadership Role']) || 'GTM / finance leader')],
    ['Pts Competitor', 'Competitor Mention', 'state', () => null, () => 'Competitor mention: ' + (clean(row['Incumbent Comp Tool']) || 'comp tool')],
    ['Pts Other', 'Other', 'event', () => row['Other Signal Date'], () => 'Other signal'],
  ];
  const out = [];
  for (const [col, type, kind, dateFn, detailFn] of defs) {
    const pts = num(row[col]);
    if (!pts || pts <= 0) continue;
    const d = kind === 'event' ? isoDate(dateFn()) : null;
    out.push({
      key: [domain, type, kind === 'state' ? 'current' : (d || 'undated')].join('|'),
      body: {
        Signal_Type__c: type,
        Signal_Date__c: d || runDate,
        Points__c: pts,
        Detail__c: cap(detailFn(), 255),
        Source_URL__c: type === primary && src ? src : null,
      },
      eventDate: d,
    });
  }
  return out;
}

function mapAccount(row, existing, runAt) {
  const runDate = runAt.slice(0, 10);
  const domain = clean(row['Domain']).toLowerCase().replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/.*$/, '');
  const tier = clean(row['Signal Tier']);
  if (!domain) return { skip: 'no domain', name: clean(row['Account Name']) };
  if (!MAP.TIERS.includes(tier)) return { skip: 'tier ' + (tier || 'blank') + (clean(row['Exclusion']) ? ' (' + clean(row['Exclusion']) + ')' : ''), domain };

  const conflict = clean(row['Headcount Conflict.'] !== undefined ? row['Headcount Conflict.'] : row['Headcount Conflict']);
  const exact = num(row['Employees (exact)']);
  const employees = exact !== null ? exact : (conflict ? null : num(row['Employee Count']));
  const country = clean(row['HQ Country']);
  const primary = clean(row['Primary Signal']);
  const signals = buildSignals(row, domain, runDate);
  const lastSignal = signals.map(s => s.eventDate).filter(Boolean).sort().pop() || null;
  const crm = clean(row['CRM Final']) || clean(row['CRM']);
  const ranBuiltWith = clean(row['Find technology stack']) !== '' || clean(row['Technologiesfound']) !== '';
  const ranContacts = clean(row['Find contacts at company']) !== '';

  const body = {
    Name: clean(row['Account Name']) || clean(row['Name']) || domain,
    Website: 'https://' + domain,
    Enriched_Industry__c: clean(row['Industry']) || null,
    NumberOfEmployees: employees,
    Employee_Range__c: employeeRange(row['Employees (exact)'], row['Employee Band']),
    BillingCity: clean(row['HQ City']) || null,
    BillingCountry: MAP.COUNTRY[country] || clean(row['HQ Country Name']) || country || null,
    LinkedIn_Company_URL__c: clean(row['Url']) || null,
    Funding_Stage__c: fundingStage(row['Funding Stage']),
    Last_Funding_Amount__c: num(row['Last Funding Amount']),
    Last_Funding_Date__c: isoDate(row['Last Funding Date']),
    Tech_Stack__c: mergeList(existing && existing.Tech_Stack__c, row['Technologiesfound'], 5000) || null,
    Incumbent_Comp_Tool__c: compTool(row['Incumbent Comp Tool']),
    Open_RevOps_Roles_Count__c: (num(row['Pts Hiring']) || 0) > 0 && !truthy(row['Hiring Closed']) ? 1 : 0,
    Open_Sales_Roles_Count__c: num(row['Open Sales Roles']) || 0,
    Signal_Score__c: num(row['Score']),
    Signal_Tier__c: tier,
    Primary_Signal__c: MAP.SIGNAL_TYPES.includes(primary) ? primary : null,
    Signal_Source_URL__c: clean(row['Signal Source URL']) || null,
    Last_Signal_Date__c: lastSignal,
    Enrichment_Date__c: runAt,
    Enrichment_Credits_Used__c: 0.5 + (ranBuiltWith ? 1 : 0) + (ranContacts ? 0.5 : 0),
  };

  const required = { Enriched_Industry__c: body.Enriched_Industry__c, NumberOfEmployees: body.NumberOfEmployees, BillingCountry: body.BillingCountry, Funding_Stage__c: body.Funding_Stage__c, Signal_Score__c: body.Signal_Score__c, Primary_Signal__c: body.Primary_Signal__c };
  const missing = Object.keys(required).filter(k => required[k] === null || required[k] === '');
  const flags = [];
  if (conflict) flags.push('Verify headcount');
  if (!crm || crm === 'Unknown') flags.push('Verify CRM');
  body.Enrichment_Status__c = missing.length ? 'Partial' : 'Complete';
  body.Missing_Fields__c = cap(missing.concat(flags).join('; '), 255) || null;

  dropFilled(body, existing, MAP.ACCOUNT_FILL_IF_BLANK);
  return { domain, tier, body, signals: signals.map(({ key, body }) => ({ key, body })) };
}

function linkedinSlug(url) {
  const m = clean(url).match(/linkedin\.com\/in\/([^/?#]+)/i);
  if (!m) return '';
  try { return decodeURIComponent(m[1]).toLowerCase(); } catch (e) { return m[1].toLowerCase(); }
}

function mapContact(row, existing, runAt) {
  if (!truthy(row['Is Primary'])) return { skip: 'not primary' };
  const domain = clean(row['Domain']).toLowerCase();
  const email = pick(row, ['Work Email', 'Email']).toLowerCase();
  const li = pick(row, ['Linkedin URL', 'LinkedIn URL']);
  const key = email || (linkedinSlug(li) ? 'li:' + linkedinSlug(li) : '');
  if (!key) return { skip: 'no email or LinkedIn', domain };
  if (!domain) return { skip: 'no domain', key };

  const persona = clean(row['Contact Persona']);
  const seniority = clean(row['Contact Seniority']);
  const verification = clean(row['Email Verification Status']);
  const body = {
    FirstName: clean(row['First Name']) || null,
    LastName: clean(row['Last Name']) || '(unknown)',
    Title: clean(row['Title']) || null,
    Email: email || null,
    Email_Verification_Status__c: email ? (MAP.VERIFICATION.includes(verification) ? verification : 'Unknown') : null,
    Persona__c: MAP.PERSONAS.includes(persona) ? persona : 'Other',
    Seniority__c: MAP.SENIORITY.includes(seniority) ? seniority : null,
    LinkedIn_URL__c: li || null,
    Account: { Domain__c: domain },
    Enrichment_Date__c: runAt,
  };
  if (!existing) body.Outreach_Status__c = 'Not Started';

  const missing = [];
  if (!email || !['Valid', 'Catch-all'].includes(body.Email_Verification_Status__c)) missing.push('Email');
  for (const f of ['FirstName', 'Title', 'Seniority__c']) if (!body[f]) missing.push(f);
  if (body.LastName === '(unknown)') missing.push('LastName');
  body.Enrichment_Status__c = missing.length ? 'Partial' : 'Complete';
  body.Missing_Fields__c = missing.join('; ') || null;

  if (!email) delete body.Email;
  if (!body.Email_Verification_Status__c) delete body.Email_Verification_Status__c;
  dropFilled(body, existing, MAP.CONTACT_FILL_IF_BLANK);
  return { key, domain, channel: clean(row['Outreach Channel']) || (email ? 'Email' : 'LinkedIn Task'), body };
}

if (typeof module !== 'undefined') module.exports = { MAP, mapAccount, mapContact, buildSignals, employeeRange, fundingStage, mergeList, linkedinSlug };
