"""Clay formulas that pick the primary contact from the 'Find contacts at company' result.
Same paste rules as clay_formulas_v2: arrow functions, COLn at the end, no `=`."""
import json
# people list from the enrichment cell (object or JSON string; key casing tolerant)
F = '(o, k) => o == null ? undefined : o[Object.keys(o).find(x => x.toLowerCase().replace(/[^a-z]/g, "") === k)]'
P = f'(v => (f => (o => f(o, "people") || [])(typeof v === "string" ? JSON.parse(v) : v))({F}))'
PERSONA = ('(t => /commission|compensation|incentive/.test(t) ? "Sales Ops / Comp Manager" : /revenue operations|revops|gtm operations|go-to-market operations/.test(t) ? '
           '(/head|vp|vice president|director|chief|svp/.test(t) ? "Head of RevOps" : "Sales Ops / Comp Manager") : /sales operations|sales ops/.test(t) ? "Sales Ops / Comp Manager" : '
           '/chief revenue|\\bcro\\b/.test(t) || (/sales/.test(t) && /vp|vice president|head|chief|svp/.test(t)) ? "CRO / VP Sales" : /financ|\\bcfo\\b/.test(t) ? "CFO / VP Finance" : "Other")')
SENIORITY = ('(t => /chief|\\bcfo\\b|\\bcro\\b|\\bceo\\b|\\bcoo\\b/.test(t) ? "C-Level" : /\\bvp\\b|vice president|\\bsvp\\b|\\bevp\\b/.test(t) ? "VP" : /head|director/.test(t) ? "Director" : /manager|\\blead\\b/.test(t) ? "Manager" : "IC")')
RANK = '({"Head of RevOps": 1, "Sales Ops / Comp Manager": 2, "CRO / VP Sales": 3, "CFO / VP Finance": 4, "Other": 9})'
SEN = '({"C-Level": 0, "VP": 1, "Director": 2, "Manager": 3, "IC": 4})'

FORMULAS = [
 ("Primary Contact Idx", ["Find contacts at company", "HQ Country"],
  f'((people, f, persona, seniority, hq) => people.length === 0 ? -1 : (key => people.reduce((b, p, i) => key(p) < key(people[b]) ? i : b, 0))(p => (t => {RANK}[persona(t)] * 100 + (String(f(p, "country") || "").toUpperCase() === String(hq || "").toUpperCase() ? 0 : 10) + {SEN}[seniority(t)])(String(f(p, "title") || "").toLowerCase())))({P}(COL1), {F}, {PERSONA}, {SENIORITY}, COL2)'),
]
for name, key in [("Contact First Name", "firstname"), ("Contact Last Name", "lastname"), ("Contact Title", "title"), ("Contact LinkedIn", "url"), ("Contact Country", "country")]:
    FORMULAS.append((name, ["Find contacts at company", "Primary Contact Idx"],
      f'((people, f, i) => i >= 0 && people[i] ? String(f(people[i], "{key}") || "") : "")({P}(COL1), {F}, Number(COL2))'))
FORMULAS += [
 ("Contact Persona", ["Contact Title"], f'(t => t ? {PERSONA}(String(t).toLowerCase()) : "")(COL1)'),
 ("Contact Seniority", ["Contact Title"], f'(t => t ? {SENIORITY}(String(t).toLowerCase()) : "")(COL1)'),
]
json.dump([{"name": n, "columns": c, "formula": f} for n, c, f in FORMULAS], open("contact_formulas.json", "w"), indent=1)
print(len(FORMULAS), "formulas")
