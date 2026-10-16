// Claude outreach step inside n8n (decision #50). Pure functions, embedded in the n8n Code nodes and
// tested locally with `node n8n/test_outreach.js`. Spec: prompts/why_now_and_email.md.
//
// Safety: this module only builds requests and validates text. Nothing here (or in the workflow)
// can send email: drafts are saved to Contact.Draft_Subject__c / Draft_Body__c and the Task description.

const OUTREACH = {
  MODEL: 'claude-sonnet-5-5',
  MAX_TOKENS: 2000,
  SIGN_OFF: '— Shravan, Flozero',
  DRAFT_PREFIX: '[DRAFT] ',
  BANNED: [/\bscore/i, /\btier\b/i, /\benrich/i, /\bclay\b/i, /\bscrap/i, /\bsignal\b/i],
  // Only signals inside this window are used in outreach copy
  MAX_SIGNAL_AGE_DAYS: 120,
};

const OUTPUT_SCHEMA = {
  type: 'object',
  properties: {
    why_now: { type: 'string', description: 'Rep-facing rationale, 2-3 sentences, max 400 characters' },
    email_subject: { type: 'string', description: 'Max 7 words, lower-case style, about their signal. Empty string when channel is LinkedIn.' },
    email_body: { type: 'string', description: 'Max 90 words. Empty string when channel is LinkedIn.' },
    linkedin_note: { type: 'string', description: 'Max 300 characters. Empty string when channel is Email.' },
  },
  required: ['why_now', 'email_subject', 'email_body', 'linkedin_note'],
  additionalProperties: false,
};

const SYSTEM_PROMPT = [
  'You write outbound prep for Flozero, a sales-compensation (commissions) platform. Flozero calculates commissions from Salesforce, gives reps live statements, keeps an audit trail and lets ops change plans without code.',
  'You receive one target contact and their account\'s buying signals as JSON. Return only the JSON object described by the schema.',
  '',
  'Rules for every field:',
  '- Facts only from the input JSON. Name the specific signal, its date, and its numbers (role title, number of open sales roles, round + amount, new leader). Never invent pains, customers, metrics or claims about the prospect.',
  '- Signal wording: Hiring RevOps → use the exact job title from the detail; Sales Team Growth → "N sales roles open"; Funding → round + amount + month; Leadership Change → role + month; Competitor Mention → "with {tool} in the stack" and offer a comparison, never disparage the tool.',
  '- If a hiring detail mentions manual or spreadsheet commission work, you may say the role "describes manual commission work", nothing more specific.',
  '- Never mention scores, tiers, signals, data providers, scraping or enrichment.',
  '- Do not include email addresses, phone numbers or links anywhere.',
  '',
  'why_now (rep-facing, max 400 characters): sentence 1 = the signals with dates; sentence 2 = why this moment matters for commissions; optional sentence 3 = why this persona owns it (or why the channel is LinkedIn).',
  '',
  'When channel is "Email" or "Email + LinkedIn":',
  '- email_subject: max 7 words, lower-case style, about their situation, not about Flozero.',
  '- email_body: max 90 words. First line "Hi {first_name}," → the signal observation → what it usually means for commissions → one Flozero line → one low-friction CTA (a 20-minute call). Last line exactly "— Shravan, Flozero".',
  '- Persona angle: RevOps / Sales Ops / Comp → calc effort, disputes, plan changes, audit trail. CRO / VP Sales → rep trust in payouts, manager time, ramp. CFO / Finance → accruals, controls, one number.',
  '- linkedin_note: "" (or a note if channel is "Email + LinkedIn").',
  '',
  'When channel is "LinkedIn Task": email_subject and email_body are "". linkedin_note: max 300 characters, congratulates on the signal, says what you work on, no pitch, no link.',
].join('\n');

function clean(v) { return v === undefined || v === null ? '' : String(v).trim(); }
function words(s) { return clean(s).split(/\s+/).filter(Boolean).length; }

// Channel from verification status (same rule as the Clay "Outreach Channel" column, decision #42)
function channelFor(contact) {
  const v = clean(contact.Email_Verification_Status__c);
  if (v === 'Valid') return 'Email';
  if (v === 'Catch-all') return 'Email + LinkedIn';
  return clean(contact.LinkedIn_URL__c) ? 'LinkedIn Task' : 'Manual Research';
}

function daysBetween(a, b) { return Math.floor((Date.parse(b) - Date.parse(a)) / 86400000); }

// Builds the per-contact context sent to Claude. Company-level facts + the contact's first name and title.
function buildContext(contact, signals, today) {
  const a = contact.Account || {};
  const sig = (signals || [])
    .filter(s => !s.Signal_Date__c || daysBetween(s.Signal_Date__c, today) <= OUTREACH.MAX_SIGNAL_AGE_DAYS)
    .sort((x, y) => clean(y.Signal_Date__c).localeCompare(clean(x.Signal_Date__c)))
    .map(s => ({ type: s.Signal_Type__c, date: s.Signal_Date__c || null, detail: clean(s.Detail__c) || null, source_url: s.Source_URL__c || null }));
  return {
    contact_id: contact.Id,
    account_id: contact.AccountId,
    account: a.Name,
    domain: a.Domain__c,
    tier: a.Signal_Tier__c,
    primary_signal: a.Primary_Signal__c || null,
    open_sales_roles: a.Open_Sales_Roles_Count__c || null,
    funding_stage: a.Funding_Stage__c || null,
    last_funding_amount: a.Last_Funding_Amount__c || null,
    last_funding_date: a.Last_Funding_Date__c || null,
    incumbent_comp_tool: a.Incumbent_Comp_Tool__c && a.Incumbent_Comp_Tool__c !== 'Unknown' ? a.Incumbent_Comp_Tool__c : null,
    first_name: clean(contact.FirstName).replace(/[.,;:]+$/, ''),   // "Ed." → "Ed" (greeting check)
    title: clean(contact.Title),
    persona: contact.Persona__c || null,
    channel: channelFor(contact),
    signals: sig,
    owner_id: a.BDR__c || a.OwnerId,   // Task owner: BDR (routing), else AE
  };
}

// Only the fields Claude needs (no ids, no owner)
function promptPayload(ctx) {
  const { contact_id, account_id, owner_id, domain, tier, ...rest } = ctx;
  return rest;
}

function buildRequest(ctx, model) {
  return {
    model: model || OUTREACH.MODEL,
    max_tokens: OUTREACH.MAX_TOKENS,
    system: SYSTEM_PROMPT,
    messages: [{ role: 'user', content: 'Write the outreach prep for this contact.\n\n' + JSON.stringify(promptPayload(ctx), null, 2) }],
    output_config: { format: { type: 'json_schema', schema: OUTPUT_SCHEMA } },
  };
}

// Parses a Messages API response (or an error body) into { out, error, usage }
function parseResponse(resp) {
  const body = resp && resp.body !== undefined ? resp.body : resp;
  const status = resp && resp.statusCode;
  if (status && status >= 300) return { error: 'HTTP ' + status + ': ' + JSON.stringify(body).slice(0, 300) };
  if (!body || !Array.isArray(body.content)) return { error: 'No content in response: ' + JSON.stringify(body).slice(0, 300) };
  if (body.stop_reason && !['end_turn', 'stop_sequence'].includes(body.stop_reason)) return { error: 'stop_reason ' + body.stop_reason };
  const text = (body.content.find(b => b.type === 'text') || {}).text;
  if (!text) return { error: 'No text block' };
  try { return { out: JSON.parse(text), usage: body.usage || null }; }
  catch (e) { return { error: 'Invalid JSON: ' + text.slice(0, 200) }; }
}

// Every number in the copy must exist in the input facts (hallucination guard)
function unknownNumbers(text, ctx) {
  const facts = JSON.stringify(promptPayload(ctx)).replace(/,/g, '');
  const found = (clean(text).replace(/,/g, '').match(/\d+(?:\.\d+)?/g) || []);
  return found.filter(n => {
    if (facts.includes(n)) return false;
    const num = Number(n);
    if (/^20\d\d$/.test(n)) return false;                 // years
    if (num === 20 && /20[- ]minute/i.test(text)) return false;   // the CTA
    // amounts written short: "$50M" ↔ 50000000, "$1.2B" ↔ 1200000000
    for (const mult of [1e3, 1e6, 1e9]) if (facts.includes(String(Math.round(num * mult)))) return false;
    return true;
  });
}

function validate(out, ctx) {
  const errors = [];
  const o = out || {};
  const why = clean(o.why_now), subj = clean(o.email_subject), body = clean(o.email_body), note = clean(o.linkedin_note);
  if (!why) errors.push('why_now empty');
  if (why.length > 400) errors.push('why_now > 400 chars (' + why.length + ')');
  const all = [why, subj, body, note].join('\n');
  if (/[\w.+-]+@[\w-]+\.[\w.]+/.test(all)) errors.push('contains an email address');
  if (/https?:\/\/|www\./i.test(all)) errors.push('contains a link');
  for (const re of OUTREACH.BANNED) if (re.test([subj, body, note].join('\n'))) errors.push('prospect-facing copy uses banned word ' + re);
  const nums = unknownNumbers(all, ctx);
  if (nums.length) errors.push('numbers not in input facts: ' + nums.join(', '));
  if (ctx.channel === 'Email' || ctx.channel === 'Email + LinkedIn') {
    if (!subj) errors.push('email_subject empty');
    if (words(subj) > 7) errors.push('subject > 7 words');
    if (!body) errors.push('email_body empty');
    if (words(body.replace(OUTREACH.SIGN_OFF, '')) > 90) errors.push('email_body > 90 words (' + words(body) + ')');
    if (ctx.first_name && !body.startsWith('Hi ' + ctx.first_name)) errors.push('greeting is not "Hi ' + ctx.first_name + ',"');
    if (!body.trim().endsWith(OUTREACH.SIGN_OFF)) errors.push('missing sign-off');
  }
  if (ctx.channel === 'LinkedIn Task') {
    if (!note) errors.push('linkedin_note empty');
    if (note.length > 300) errors.push('linkedin_note > 300 chars');
  }
  return errors;
}

function addBusinessDays(iso, n) {
  const d = new Date(iso + 'T12:00:00Z');
  while (n > 0) { d.setUTCDate(d.getUTCDate() + 1); const w = d.getUTCDay(); if (w !== 0 && w !== 6) n--; }
  return d.toISOString().slice(0, 10);
}

// Salesforce writes for one validated output. Drafts are stored, never sent.
function writesFor(ctx, out, today, nowIso, existingStatus, hasOpenTask) {
  const isEmail = ctx.channel === 'Email' || ctx.channel === 'Email + LinkedIn';
  const contact = {
    attributes: { type: 'Contact' }, Id: ctx.contact_id,
    Why_Now_Rationale__c: clean(out.why_now),
    Draft_Subject__c: isEmail ? (OUTREACH.DRAFT_PREFIX + clean(out.email_subject)).slice(0, 255) : null,
    Draft_Body__c: isEmail ? clean(out.email_body) + (clean(out.linkedin_note) ? '\n\n--- LinkedIn note ---\n' + clean(out.linkedin_note) : '')
                           : (clean(out.linkedin_note) ? '--- LinkedIn note ---\n' + clean(out.linkedin_note) : null),
    Draft_Generated_At__c: nowIso,
  };
  if (!existingStatus || existingStatus === 'Not Started') contact.Outreach_Status__c = 'Drafted';
  if (hasOpenTask || ctx.channel === 'Manual Research') return { contact, task: null };
  const tierA = ctx.tier === 'A';
  const linkedin = ctx.channel === 'LinkedIn Task';
  const primary = ctx.primary_signal || (ctx.signals[0] && ctx.signals[0].type) || 'Signal';
  const src = (ctx.signals.find(s => s.source_url) || {}).source_url;
  const task = {
    attributes: { type: 'Task' }, WhoId: ctx.contact_id, WhatId: ctx.account_id, OwnerId: ctx.owner_id,
    Subject: linkedin ? `Tier ${ctx.tier} – LinkedIn connect – ${ctx.account}` : `Tier ${ctx.tier} – ${primary} – ${ctx.account}`,
    ActivityDate: addBusinessDays(today, tierA ? 1 : 3),
    Priority: tierA ? 'High' : 'Normal', Status: 'Not Started',
    Description: ['Why now: ' + clean(out.why_now), '',
      linkedin ? 'Next step: send the LinkedIn note saved in Draft Body on the Contact.'
               : 'Next step: review the draft saved on the Contact (Draft Subject / Draft Body), edit, then send it yourself. Drafts are never sent automatically.',
      src ? '\nSignal source: ' + src : ''].join('\n').trim(),
    Created_By_Automation__c: true,
    Automation_Reason__c: linkedin ? 'LinkedIn Outreach' : tierA ? 'Tier A Outreach' : 'Tier B Outreach',
  };
  return { contact, task };
}

// Stand-in for Claude while there is no API key: same response shape, built only from the input facts
function mockResponse(ctx) {
  const s = ctx.signals[0] || { type: ctx.primary_signal || 'Hiring RevOps', date: null, detail: '' };
  const when = s.date ? new Date(s.date + 'T12:00:00Z').toLocaleString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }) : 'recently';
  const what = s.type === 'Sales Team Growth' && ctx.open_sales_roles ? `${ctx.open_sales_roles} sales roles open`
    : s.type === 'Funding' && ctx.funding_stage ? `the ${ctx.funding_stage} round`
    : s.type === 'Hiring RevOps' ? 'the new RevOps hire' : s.type.toLowerCase();
  const out = {
    why_now: `${ctx.account} shows ${what} (${when}). Growth like this multiplies plan changes and payout questions, so commissions are worth automating now.`,
    email_subject: ctx.channel === 'LinkedIn Task' ? '' : `commissions as ${ctx.account.toLowerCase()} grows`,
    email_body: ctx.channel === 'LinkedIn Task' ? '' : [`Hi ${ctx.first_name},`, '',
      `Saw ${what} at ${ctx.account} (${when}). Teams at that stage usually feel it first in commission calcs and payout questions.`, '',
      'Flozero calculates commissions straight from Salesforce and gives reps live statements with an audit trail.', '',
      'Open to a 20-minute look?', '', OUTREACH.SIGN_OFF].join('\n'),
    linkedin_note: ctx.channel === 'LinkedIn Task' ? `Congrats on ${what} at ${ctx.account}. I work on commission automation for growing sales teams and would love to connect.` : '',
  };
  return { statusCode: 200, body: { content: [{ type: 'text', text: JSON.stringify(out) }], stop_reason: 'end_turn', usage: { input_tokens: 0, output_tokens: 0 }, mock: true } };
}

if (typeof module !== 'undefined') module.exports = { OUTREACH, OUTPUT_SCHEMA, SYSTEM_PROMPT, channelFor, buildContext, buildRequest, parseResponse, validate, writesFor, mockResponse, addBusinessDays, unknownNumbers };
