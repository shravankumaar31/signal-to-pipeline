// Tests for n8n/lib/outreach.js (decision #50). Fixtures are company-level; contact names are placeholders.
const assert = require('assert');
const o = require('./lib/outreach.js');

const TODAY = '2026-10-15', NOW = '2026-10-15T19:00:00.000Z';
const acct = { Name: 'Keeper Security', Domain__c: 'keepersecurity.com', Signal_Tier__c: 'A', Primary_Signal__c: 'Hiring RevOps',
  Open_Sales_Roles_Count__c: 20, Funding_Stage__c: 'Unknown', Incumbent_Comp_Tool__c: 'Unknown', BDR__c: 'U-lucas', OwnerId: 'U-maya' };
const contact = { Id: 'C1', AccountId: 'A1', FirstName: 'Alex', Title: 'VP of Revenue Operations', Persona__c: 'RevOps',
  Email_Verification_Status__c: 'Valid', LinkedIn_URL__c: 'https://linkedin.com/in/x', Outreach_Status__c: 'Not Started', Account: acct };
const signals = [
  { Signal_Type__c: 'Hiring RevOps', Signal_Date__c: '2026-10-05', Detail__c: 'Senior Sales Commission Analyst', Source_URL__c: 'https://job-boards.greenhouse.io/x/1' },
  { Signal_Type__c: 'Sales Team Growth', Signal_Date__c: '2026-10-15', Detail__c: '20 open sales roles' },
  { Signal_Type__c: 'Funding', Signal_Date__c: '2025-01-10', Detail__c: 'old round' },   // > 120 days: dropped
];

// context
const ctx = o.buildContext(contact, signals, TODAY);
assert.equal(ctx.channel, 'Email');
assert.equal(ctx.owner_id, 'U-lucas', 'task owner = BDR');
assert.equal(ctx.signals.length, 2, 'stale signal dropped');
assert.equal(ctx.signals[0].type, 'Sales Team Growth', 'newest first');
assert.equal(ctx.incumbent_comp_tool, null, 'Unknown tool not passed');
assert.equal(o.channelFor({ Email_Verification_Status__c: 'Catch-all' }), 'Email + LinkedIn');
assert.equal(o.channelFor({ Email_Verification_Status__c: 'Invalid', LinkedIn_URL__c: 'x' }), 'LinkedIn Task');
assert.equal(o.channelFor({}), 'Manual Research');

assert.equal(o.buildContext({ ...contact, FirstName: 'Ed.' }, signals, TODAY).first_name, 'Ed', 'trailing period stripped');

// request
const req = o.buildRequest(ctx);
assert.equal(req.model, 'claude-sonnet-5-5');
assert.equal(req.output_config.format.type, 'json_schema');
assert.ok(!req.messages[0].content.includes('U-lucas') && !req.messages[0].content.includes('C1'), 'no ids in prompt');
assert.ok(!('temperature' in req), 'no sampling params');

// mock → parse → validate → writes
const parsed = o.parseResponse(o.mockResponse(ctx));
assert.ok(parsed.out, parsed.error);
assert.deepStrictEqual(o.validate(parsed.out, ctx), [], 'mock output passes validation');
const w = o.writesFor(ctx, parsed.out, TODAY, NOW, 'Not Started', false);
assert.ok(w.contact.Draft_Subject__c.startsWith('[DRAFT] '));
assert.equal(w.contact.Outreach_Status__c, 'Drafted');
assert.equal(w.task.OwnerId, 'U-lucas');
assert.equal(w.task.ActivityDate, '2026-10-16', 'Tier A: next business day');
assert.equal(w.task.Automation_Reason__c, 'Tier A Outreach');
assert.ok(!JSON.stringify(w).match(/"(To|ToAddress|Email)"/), 'no recipient fields anywhere');
assert.equal(o.writesFor(ctx, parsed.out, TODAY, NOW, 'Sent', true).task, null, 'open task exists → no new task');
assert.equal(o.writesFor(ctx, parsed.out, TODAY, NOW, 'Replied', false).contact.Outreach_Status__c, undefined, 'status only moves from Not Started');
assert.equal(o.addBusinessDays('2026-10-16', 3), '2026-10-21', 'Fri + 3 business days = Wed');

// LinkedIn channel
const li = o.buildContext({ ...contact, Email_Verification_Status__c: 'Unknown' }, signals, TODAY);
const liOut = o.parseResponse(o.mockResponse(li)).out;
assert.deepStrictEqual(o.validate(liOut, li), []);
const liW = o.writesFor(li, liOut, TODAY, NOW, 'Not Started', false);
assert.equal(liW.contact.Draft_Subject__c, null);
assert.equal(liW.task.Automation_Reason__c, 'LinkedIn Outreach');

// validation catches bad output
const bad = { why_now: 'x'.repeat(401), email_subject: 'a b c d e f g h', linkedin_note: '',
  email_body: 'Hello there, email me at a@b.com or see https://x.io — we cut payout disputes by 73% for 500 teams. Your score is high.' };
const errs = o.validate(bad, ctx);
['why_now > 400', 'email address', 'link', 'subject > 7', 'greeting', 'sign-off', 'banned word', 'numbers not in input'].forEach(k =>
  assert.ok(errs.some(e => e.includes(k)), 'expected error: ' + k + ' in ' + JSON.stringify(errs)));
assert.deepStrictEqual(o.unknownNumbers('20 sales roles open since Oct 5, 2026 — 20-minute call', ctx), []);

// response parsing
assert.ok(o.parseResponse({ statusCode: 401, body: { error: { message: 'invalid x-api-key' } } }).error.startsWith('HTTP 401'));
assert.ok(o.parseResponse({ statusCode: 200, body: { content: [{ type: 'text', text: '{}' }], stop_reason: 'max_tokens' } }).error.includes('max_tokens'));
assert.ok(o.parseResponse({ statusCode: 200, body: { content: [{ type: 'text', text: 'not json' }], stop_reason: 'end_turn' } }).error.startsWith('Invalid JSON'));

console.log('outreach checks OK');
console.log('\nSample mock draft:\n' + w.contact.Draft_Subject__c + '\n' + w.contact.Draft_Body__c);
