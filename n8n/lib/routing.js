// Account routing engine (decision #47). Pure function, embedded in the n8n Code node and tested
// locally with `node n8n/test_routing.js`.
//
// Roles: AE owns the Account (and its Contacts); BDR works it (Account.BDR__c + open automated Tasks).
// Per role, Tier A/B accounts only (Tier C stays in the RevOps queue):
//   pass 1  keep / return-to-home for routed accounts whose rep is available; territory rep for new accounts
//   pass 2  everything left: coverage (rep OOO, home kept), overflow or inactive reassignment (new home)
// Eligible rep = available (not OOO, not inactive), under capacity, and not ramping when the account is Tier A.
// Ramping = first RAMP_DAYS after start date: capacity halved, no Tier A.
// Overflow pick: Tier A -> highest quota attainment; Tier B -> most spare capacity (then attainment, then alias).

const ROUTING = { RAMP_DAYS: 90, ROLES: { AE: { field: 'OwnerId', home: 'Home_AE__c' }, BDR: { field: 'BDR__c', home: 'Home_BDR__c' } } };

function daysBetween(a, b) { return Math.floor((Date.parse(b) - Date.parse(a)) / 86400000); }

function repState(rep, today) {
  if (!rep.isActive || rep.status === 'Inactive') return 'inactive';
  if (rep.status === 'Out of Office' && (!rep.oooUntil || rep.oooUntil >= today)) return 'ooo';
  return 'available'; // OOO with a past return date counts as back
}

function route({ reps, accounts, territories, today, nowIso, queueId }) {
  const byId = Object.fromEntries(reps.map(r => [r.id, r]));
  const byAlias = Object.fromEntries(reps.map(r => [r.alias, r]));
  for (const r of reps) {
    r.state = repState(r, today);
    r.ramping = !!r.startDate && daysBetween(r.startDate, today) < ROUTING.RAMP_DAYS;
    r.cap = r.ramping ? Math.floor((r.max || 0) / 2) : (r.max || 0);
    r.load = 0;
  }
  const work = accounts.filter(a => a.tier === 'A' || a.tier === 'B')
    .sort((x, y) => (x.tier === y.tier ? (y.score || 0) - (x.score || 0) : (x.tier < y.tier ? -1 : 1)));
  // current loads (routed A/B accounts only)
  for (const a of work) for (const role of ['AE', 'BDR']) {
    const cur = byId[a[ROUTING.ROLES[role].field]];
    if (cur && cur.role === role) cur.load++;
  }
  const result = {};       // accountId -> { changes, notes: { AE, BDR } }
  const note = (a, role, text) => { (result[a.id] = result[a.id] || { changes: {}, notes: {} }).notes[role] = text; };
  const set = (a, f, v) => { if ((a[f] || null) !== (v || null)) { (result[a.id] = result[a.id] || { changes: {}, notes: {} }).changes[f] = v; a[f] = v; } };
  const tierOk = (r, tier) => !(tier === 'A' && r.ramping);
  const fits = (r, tier) => r && r.state === 'available' && r.load < r.cap && tierOk(r, tier);
  const move = (a, role, from, to) => { if (from && from.role === role) from.load--; to.load++; set(a, ROUTING.ROLES[role].field, to.id); };
  const label = r => `${r.name} (${r.load}/${r.cap}${r.ramping ? ', ramping' : ''})`;
  function pick(role, tier, exclude) {
    const c = reps.filter(r => r.role === role && !exclude.includes(r.id) && fits(r, tier));
    c.sort((x, y) => tier === 'A'
      ? (y.attainment - x.attainment) || ((y.cap - y.load) - (x.cap - x.load)) || x.alias.localeCompare(y.alias)
      : ((y.cap - y.load) - (x.cap - x.load)) || (y.attainment - x.attainment) || x.alias.localeCompare(y.alias));
    return c[0] || null;
  }

  for (const role of ['AE', 'BDR']) {
    const R = ROUTING.ROLES[role], pending = [];
    // pass 1
    for (const a of work) {
      const terr = territories[a.region] || null;
      if (terr) set(a, 'Territory__c', terr.territory);
      const T = terr ? byAlias[role === 'AE' ? terr.ae : terr.bdr] : null;
      const cur = byId[a[R.field]];
      const home = byId[a[R.home]];
      if (cur && cur.role === role) {                       // already routed
        if (cur.state !== 'available') { pending.push({ a, T, cur, why: cur.state }); continue; }
        if (home && home.id !== cur.id && fits(home, a.tier)) { move(a, role, cur, home); note(a, role, `${role} back to home rep ${label(home)}`); }
        continue;                                           // sticky
      }
      if (!T) { note(a, role, `${role}: no territory for region "${a.region || '?'}", left in RevOps queue`); continue; }
      if (fits(T, a.tier)) { move(a, role, null, T); set(a, R.home, T.id); note(a, role, `${role} ${terr.territory} territory → ${label(T)}`); }
      else pending.push({ a, T, cur: null, why: T.state !== 'available' ? T.state : (!tierOk(T, a.tier) ? 'ramping' : 'capacity') });
    }
    // pass 2
    for (const p of pending) {
      const { a, T, cur, why } = p;
      const away = cur || T;
      const coverage = why === 'ooo' && tierOk(away, a.tier);
      const c = pick(role, a.tier, [away.id]);
      if (!c) {
        if (cur && why === 'inactive') {                    // never leave work with an inactive rep
          cur.load--; set(a, R.field, role === 'AE' ? (queueId || null) : null);
          note(a, role, `${role}: ${cur.name} inactive, no eligible rep → RevOps queue`);
        } else note(a, role, `${role}: no eligible rep (${away.name} ${why}); ${cur ? 'kept with ' + cur.name : 'left in RevOps queue'}`);
        continue;
      }
      move(a, role, cur && cur.role === role ? cur : null, c);
      if (coverage) set(a, R.home, a[R.home] || away.id);
      else set(a, R.home, c.id);
      const rule = a.tier === 'A' ? `top attainment ${c.attainment}%` : 'most capacity';
      note(a, role, coverage
        ? `${role} coverage for ${away.name} (OOO${away.oooUntil ? ' until ' + away.oooUntil : ''}) → ${label(c)}`
        : `${role} overflow: ${away.name} ${why} → ${label(c)} [Tier ${a.tier}: ${rule}]`);
    }
  }

  const updates = [];
  for (const a of work) {
    const r = result[a.id];
    if (!r || !Object.keys(r.changes).length) continue;
    const reason = ['AE', 'BDR'].map(k => r.notes[k]).filter(Boolean).join(' | ');
    updates.push(Object.assign({ Id: a.id }, r.changes, { Routing_Reason__c: reason.slice(0, 255), Routing_Date__c: nowIso }));
  }
  const repSummary = reps.map(r => ({ rep: r.name, role: r.role, state: r.state, ramping: r.ramping, load: r.load, cap: r.cap }));
  return { updates, repSummary, final: Object.fromEntries(work.map(a => [a.id, { AE: a.OwnerId, BDR: a.BDR__c, homeAE: a.Home_AE__c, homeBDR: a.Home_BDR__c }])) };
}

if (typeof module !== 'undefined') module.exports = { ROUTING, route, repState };
