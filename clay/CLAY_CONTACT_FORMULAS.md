# Clay contact formulas (v3, two-table model)

Accounts table picks the primary contact; contacts table (one row per person, filled by *Send table data*) flags it. Replace each `COLn` with a `/` column chip.

## Primary Contact Idx (clay_accounts_v1)

Columns: `COL1` → Find contacts at company → people, `COL2` → HQ Country

```
((people, hq, persona, seniority) => people.length === 0 ? -1 : (key => people.reduce((b, p, i) => key(p) < key(people[b]) ? i : b, 0))(p => (t => ({"Head of RevOps": 1, "Sales Ops / Comp Manager": 2, "CRO / VP Sales": 3, "CFO / VP Finance": 4, "Other": 9})[persona(t)] * 100 + (String((p && p.country) || "").toUpperCase() === String(hq || "").toUpperCase() ? 0 : 10) + ({"C-Level": 0, "VP": 1, "Director": 2, "Manager": 3, "IC": 4})[seniority(t)])(String((p && p.title) || "").toLowerCase())))((v => Array.isArray(v) ? v : [])(COL1), COL2, (t => /commission|compensation|incentive/.test(t) ? "Sales Ops / Comp Manager" : /revenue operations|revops|gtm operations|go-to-market operations/.test(t) ? (/head|vp|vice president|director|chief|svp/.test(t) ? "Head of RevOps" : "Sales Ops / Comp Manager") : /sales operations|sales ops/.test(t) ? "Sales Ops / Comp Manager" : /chief revenue|\bcro\b/.test(t) || (/sales/.test(t) && /vp|vice president|head|chief|svp/.test(t)) ? "CRO / VP Sales" : /financ|\bcfo\b/.test(t) ? "CFO / VP Finance" : "Other"), (t => /chief|\bcfo\b|\bcro\b|\bceo\b|\bcoo\b/.test(t) ? "C-Level" : /\bvp\b|vice president|\bsvp\b|\bevp\b/.test(t) ? "VP" : /head|director/.test(t) ? "Director" : /manager|\blead\b/.test(t) ? "Manager" : "IC"))
```

## Primary Contact LinkedIn (clay_accounts_v1)

Columns: `COL1` → Find contacts at company → people, `COL2` → Primary Contact Idx

```
((people, i) => i >= 0 && people[i] ? String(people[i].url || "") : "")((v => Array.isArray(v) ? v : [])(COL1), Number(COL2))
```

## Contact Persona (clay_contacts_v1)

Columns: `COL1` → Title

```
(t => t ? (t => /commission|compensation|incentive/.test(t) ? "Sales Ops / Comp Manager" : /revenue operations|revops|gtm operations|go-to-market operations/.test(t) ? (/head|vp|vice president|director|chief|svp/.test(t) ? "Head of RevOps" : "Sales Ops / Comp Manager") : /sales operations|sales ops/.test(t) ? "Sales Ops / Comp Manager" : /chief revenue|\bcro\b/.test(t) || (/sales/.test(t) && /vp|vice president|head|chief|svp/.test(t)) ? "CRO / VP Sales" : /financ|\bcfo\b/.test(t) ? "CFO / VP Finance" : "Other")(String(t).toLowerCase()) : "")(COL1)
```

## Contact Seniority (clay_contacts_v1)

Columns: `COL1` → Title

```
(t => t ? (t => /chief|\bcfo\b|\bcro\b|\bceo\b|\bcoo\b/.test(t) ? "C-Level" : /\bvp\b|vice president|\bsvp\b|\bevp\b/.test(t) ? "VP" : /head|director/.test(t) ? "Director" : /manager|\blead\b/.test(t) ? "Manager" : "IC")(String(t).toLowerCase()) : "")(COL1)
```

## Is Primary (clay_contacts_v1)

Columns: `COL1` → LinkedIn URL, `COL2` → Primary Contact LinkedIn

```
((a, b) => a !== "" && a === b)(String(COL1 || "").toLowerCase().replace(/\/+$/, ""), String(COL2 || "").toLowerCase().replace(/\/+$/, ""))
```

## Send table data (clay_accounts_v1 → clay_contacts_v1)

- Method: Send row for each item in a list → Find contacts at company → people
- Account columns sent: Account Name, Domain, HQ Country, Signal Tier, Score, Primary Signal, Primary Contact LinkedIn
- Update existing rows on re-run: ON; Auto-run: OFF; run condition `Number(COL1) >= 0` (COL1 → Primary Contact Idx)
- Person fields pulled out in the contacts table with *Add as column*: first_name, last_name, title, url (LinkedIn URL), country
