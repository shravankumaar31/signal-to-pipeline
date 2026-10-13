# Clay formula columns — paste guide (v2)

**How:** Add column → Formula. Paste the formula into the formula box, then replace each `COLn` at the **end** with a column chip (select `COLn`, delete, type `/`, pick the column). Check **Referenced columns** shows the right count and there is no red error, rename the column to the exact name below, then **Save**.

Clay's formula checker rejects assignments (`=`), rest parameters (`...`) and destructuring, so none are used.

Create them **in order** — later columns use earlier ones. Tested with `node clay/test_clay_formulas_v2.js` (all 21 rows match the reference scorer, with values passed as text and as typed numbers/booleans).

## 1. Exclusion

Replace: `COL1` → **CRM**, `COL2` → **Hard Exclusion**, `COL3` → **HQ Country**, `COL4` → **Employees (exact)**, `COL5` → **Employee Band**

```
((crm, hardEx, country, emp, band) => !["salesforce","unknown",""].includes(String(crm ?? "").toLowerCase()) ? "CRM is " + crm : hardEx ? String(hardEx) : !["US","CA"].includes(String(country ?? "").toUpperCase()) ? "Legal HQ outside US + Canada (" + country + ")" : (Number(emp || 0) > 5000 || ["5001-10000","10001+"].includes(String(band))) ? "Over 5,000 employees" : "")(COL1, COL2, COL3, COL4, COL5)
```

## 2. Pts Hiring

Replace: `COL1` → **Hiring Posted**, `COL2` → **Hiring Comp Specific**, `COL3` → **Hiring Pain Language**, `COL4` → **Hiring Closed**

```
((age, yes, posted, comp, pain, closed) => !posted ? 0 : (base => closed ? (age(closed) <= 30 ? Math.floor(base / 2 + 0.5) : 0) : age(posted) <= 45 ? base : age(posted) <= 90 ? Math.floor(base / 2 + 0.5) : 0)((yes(comp) ? 25 : 20) + (yes(pain) ? 10 : 0)))(v => Math.floor(Date.now() / 864e5) - Math.floor(new Date(v).getTime() / 864e5), v => v === true || String(v).toLowerCase() === "true", COL1, COL2, COL3, COL4)
```

## 3. Pts Sales Growth

Replace: `COL1` → **Open Sales Roles**

```
(n => (Number(n) || 0) >= 20 ? 20 : (Number(n) || 0) >= 10 ? 15 : (Number(n) || 0) >= 5 ? 10 : 0)(COL1)
```

## 4. Pts Funding

Replace: `COL1` → **Funding Signal Date**

```
((age, d) => !d ? 0 : age(d) <= 90 ? 20 : age(d) <= 180 ? 10 : 0)(v => Math.floor(Date.now() / 864e5) - Math.floor(new Date(v).getTime() / 864e5), COL1)
```

## 5. Pts Leadership

Replace: `COL1` → **Leadership Date**, `COL2` → **Leadership Role**

```
((age, d, role) => !d ? 0 : (b => age(d) <= 90 ? b : age(d) <= 180 ? Math.floor(b / 2 + 0.5) : 0)(String(role) === "CFO" ? 13 : 20))(v => Math.floor(Date.now() / 864e5) - Math.floor(new Date(v).getTime() / 864e5), COL1, COL2)
```

## 6. Pts Competitor

Replace: `COL1` → **Competitor Mention Live**

```
((yes, live) => yes(live) ? 5 : 0)(v => v === true || String(v).toLowerCase() === "true", COL1)
```

## 7. Pts Other

Replace: `COL1` → **Other Signal Date**

```
((age, d) => !d ? 0 : age(d) <= 45 ? 5 : age(d) <= 90 ? 3 : 0)(v => Math.floor(Date.now() / 864e5) - Math.floor(new Date(v).getTime() / 864e5), COL1)
```

## 8. Fresh Signal

Replace: `COL1` → **Hiring Posted**, `COL2` → **Hiring Closed**, `COL3` → **Open Sales Roles**, `COL4` → **Funding Signal Date**, `COL5` → **Leadership Date**, `COL6` → **Competitor Mention Live**, `COL7` → **Other Signal Date**

```
((age, yes, hp, hc, sales, fd, ld, comp, od) => !!((hp && !hc && age(hp) <= 45) || (Number(sales) || 0) >= 5 || (fd && age(fd) <= 90) || (ld && age(ld) <= 90) || yes(comp) || (od && age(od) <= 45)))(v => Math.floor(Date.now() / 864e5) - Math.floor(new Date(v).getTime() / 864e5), v => v === true || String(v).toLowerCase() === "true", COL1, COL2, COL3, COL4, COL5, COL6, COL7)
```

## 9. Fit

Replace: `COL1` → **Employees (exact)**, `COL2` → **Employee Band**, `COL3` → **Funding Stage**, `COL4` → **Incumbent Comp Tool**, `COL5` → **CRM**

```
((emp, band, stage, tool, crm) => (n => n > 0 ? (n >= 200 && n <= 1000 ? 8 : (n >= 100 && n <= 199) || (n >= 1001 && n <= 2000) ? 4 : 0) : ({"51-200": 4, "201-500": 8, "501-1000": 8, "1001-5000": 4}[String(band)] || 0))(Number(emp) || 0) + ({"Series B": 8, "Series C": 8, "Series D": 6, "Profitable private": 5}[String(stage)] || 0) + ({"Spreadsheets": 10, "In-house build": 8, "Unknown": 5}[String(tool)] ?? 3) + (String(crm) === "Salesforce" ? 4 : 0))(COL1, COL2, COL3, COL4, COL5)
```

## 10. Intent

Replace: `COL1` → **Pts Hiring**, `COL2` → **Pts Sales Growth**, `COL3` → **Pts Funding**, `COL4` → **Pts Leadership**, `COL5` → **Pts Competitor**, `COL6` → **Pts Other**

```
((a, b, c, d, e, f) => Math.min(70, [a, b, c, d, e, f].reduce((s, v) => s + (Number(v) || 0), 0)))(COL1, COL2, COL3, COL4, COL5, COL6)
```

## 11. Score

Replace: `COL1` → **Exclusion**, `COL2` → **Fit**, `COL3` → **Intent**

```
((ex, fit, intent) => ex ? "" : Math.min(100, (Number(fit) || 0) + (Number(intent) || 0)))(COL1, COL2, COL3)
```

## 12. Below ICP Floor

Replace: `COL1` → **Employees (exact)**, `COL2` → **Employee Band**, `COL3` → **Funding Stage**

```
((emp, band, stage) => ["Pre-seed", "Seed", "Series A"].includes(String(stage)) || (n => n > 0 ? n < 100 : ["1-10", "11-50"].includes(String(band)))(Number(emp) || 0))(COL1, COL2, COL3)
```

## 13. Signal Tier

Replace: `COL1` → **Exclusion**, `COL2` → **Below ICP Floor**, `COL3` → **Score**, `COL4` → **Fresh Signal**

```
((yes, ex, floor, score, fresh) => ex ? "Excluded" : yes(floor) ? "C" : (Number(score) || 0) >= 60 && yes(fresh) ? "A" : (Number(score) || 0) >= 35 ? "B" : "C")(v => v === true || String(v).toLowerCase() === "true", COL1, COL2, COL3, COL4)
```

## 14. Primary Signal

Replace: `COL1` → **Exclusion**, `COL2` → **Pts Hiring**, `COL3` → **Pts Leadership**, `COL4` → **Pts Funding**, `COL5` → **Pts Sales Growth**, `COL6` → **Pts Competitor**, `COL7` → **Pts Other**

```
((ex, h, l, f, s, c, o) => ex ? "" : [["Hiring RevOps", h], ["Leadership Change", l], ["Funding", f], ["Sales Team Growth", s], ["Competitor Mention", c], ["Other", o]].reduce((b, p) => (Number(p[1]) || 0) > b[1] ? [p[0], Number(p[1]) || 0] : b, ["", 0])[0])(COL1, COL2, COL3, COL4, COL5, COL6, COL7)
```

## 15. Score Check

Replace: `COL1` → **Exclusion**, `COL2` → **Signal Tier**, `COL3` → **Below ICP Floor**, `COL4` → **Score**, `COL5` → **Expected Tier**, `COL6` → **Expected Score**, `COL7` → **Expected Primary**, `COL8` → **Primary Signal**

```
((yes, ex, tier, floor, score, eTier, eScore, ePrim, prim) => (t => t === String(eTier ?? "") && String(score ?? "") === String(eScore ?? "") && (ex || String(prim ?? "") === String(ePrim ?? "")) ? "OK" : "MISMATCH: expected " + eTier + " / " + eScore + " / " + ePrim)(String(tier) + (yes(floor) && !ex ? " (capped)" : "")))(v => v === true || String(v).toLowerCase() === "true", COL1, COL2, COL3, COL4, COL5, COL6, COL7, COL8)
```

## Expected after column 15
`Score Check` = **OK** on all 21 rows (through 2026-10-15; from Oct 16 Notion and from Oct 18 Bazaarvoice decay — expected, since the Expected columns are frozen).

## 16. Headcount Conflict (data quality — not used in scoring)
Flags rows where Clay's enriched Employee Count disagrees with the hand-verified headcount (outside the verified band, or under half / over double the exact count). Scoring keeps using the verified values (#38).

Replace: `COL1` → **Employee Count**, `COL2` → **Employees (exact)**, `COL3` → **Employee Band**

```
((count, exact, band) => (c => !c ? "" : (Number(exact) || 0) > 0 ? (c < Number(exact) / 2 || c > Number(exact) * 2 ? "Clay " + c + " vs verified " + exact : "") : (r => !r ? "" : (c < r[0] || c > r[1]) ? "Clay " + c + " vs verified band " + band : "")({"11-50": [11, 50], "51-200": [51, 200], "201-500": [201, 500], "501-1000": [501, 1000], "1001-5000": [1001, 5000]}[String(band)]))(Number(count) || 0))(COL1, COL2, COL3)
```

Expected flags (2026-10-13): Notion, Flai, Clipboard Health, Outmarket, Ema.

## 17. CRM Final (used by Exclusion and Fit)
Imported CRM when known; otherwise Salesforce if BuiltWith finds core Salesforce tech (My Salesforce, Salesforce SPF, Pardot, …; Commerce Cloud, Tableau, MuleSoft, Heroku, Slack, Marketing Cloud and Audience Studio don't count); otherwise Unknown. HubSpot website tools alone stay Unknown (#39).

Replace: `COL1` → **CRM**, `COL2` → **Technologiesfound**

```
((imported, tech) => String(imported || "Unknown") !== "Unknown" ? String(imported) : (l => l.some(x => x === "my salesforce" || x.startsWith("pardot") || (x.startsWith("salesforce") && !/commerce|tableau|mulesoft|heroku|slack|marketing cloud|audience studio/.test(x))) ? "Salesforce" : "Unknown")(String(tech || "").toLowerCase().split(",").map(x => x.trim())))(COL1, COL2)
```

Then re-link **Exclusion** `COL1` and **Fit** `COL5` from **CRM** to **CRM Final**.

## 18. CRM Evidence (data quality)
Replace: `COL1` → **Technologiesfound**

```
(tech => (l => l.some(x => x === "my salesforce" || x.startsWith("pardot") || (x.startsWith("salesforce") && !/commerce|tableau|mulesoft|heroku|slack|marketing cloud|audience studio/.test(x))) ? "Salesforce detected" : l.some(x => x.startsWith("hubspot")) ? "Verify CRM: HubSpot website tools only" : l.filter(x => x).length ? "Verify CRM: " + l.filter(x => x).join(", ") : "")(String(tech || "").toLowerCase().split(",").map(x => x.trim())))(COL1)
```
