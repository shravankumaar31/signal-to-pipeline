"""Clay-ready formulas (v2): each is an arrow function called with its columns as the LAST arguments,
so in Clay you paste the text and replace COL1..COLn with column chips (type / and pick the column)."""
import json
AGE = "v => Math.floor(Date.now() / 864e5) - Math.floor(new Date(v).getTime() / 864e5)"
YES = 'v => v === true || String(v).toLowerCase() === "true"'
F = [
 ("Exclusion", ["CRM","Hard Exclusion","HQ Country","Employees (exact)","Employee Band"],
  '((crm, hardEx, country, emp, band) => !["salesforce","unknown",""].includes(String(crm ?? "").toLowerCase()) ? "CRM is " + crm : hardEx ? String(hardEx) : !["US","CA"].includes(String(country ?? "").toUpperCase()) ? "Legal HQ outside US + Canada (" + country + ")" : (Number(emp || 0) > 5000 || ["5001-10000","10001+"].includes(String(band))) ? "Over 5,000 employees" : "")'),
 ("Pts Hiring", ["Hiring Posted","Hiring Comp Specific","Hiring Pain Language","Hiring Closed"],
  f'((age, yes, posted, comp, pain, closed) => !posted ? 0 : (base => closed ? (age(closed) <= 30 ? Math.floor(base / 2 + 0.5) : 0) : age(posted) <= 45 ? base : age(posted) <= 90 ? Math.floor(base / 2 + 0.5) : 0)((yes(comp) ? 25 : 20) + (yes(pain) ? 10 : 0)))({AGE}, {YES}, '),
 ("Pts Sales Growth", ["Open Sales Roles"],
  '(n => (n = Number(n) || 0) >= 20 ? 20 : n >= 10 ? 15 : n >= 5 ? 10 : 0)'),
 ("Pts Funding", ["Funding Signal Date"],
  f'((age, d) => !d ? 0 : age(d) <= 90 ? 20 : age(d) <= 180 ? 10 : 0)({AGE}, '),
 ("Pts Leadership", ["Leadership Date","Leadership Role"],
  f'((age, d, role) => !d ? 0 : (b => age(d) <= 90 ? b : age(d) <= 180 ? Math.floor(b / 2 + 0.5) : 0)(String(role) === "CFO" ? 13 : 20))({AGE}, '),
 ("Pts Competitor", ["Competitor Mention Live"],
  f'((yes, live) => yes(live) ? 5 : 0)({YES}, '),
 ("Pts Other", ["Other Signal Date"],
  f'((age, d) => !d ? 0 : age(d) <= 45 ? 5 : age(d) <= 90 ? 3 : 0)({AGE}, '),
 ("Fresh Signal", ["Hiring Posted","Hiring Closed","Open Sales Roles","Funding Signal Date","Leadership Date","Competitor Mention Live","Other Signal Date"],
  f'((age, yes, hp, hc, sales, fd, ld, comp, od) => !!((hp && !hc && age(hp) <= 45) || (Number(sales) || 0) >= 5 || (fd && age(fd) <= 90) || (ld && age(ld) <= 90) || yes(comp) || (od && age(od) <= 45)))({AGE}, {YES}, '),
 ("Fit", ["Employees (exact)","Employee Band","Funding Stage","Incumbent Comp Tool","CRM"],
  '((emp, band, stage, tool, crm) => (n => n > 0 ? (n >= 200 && n <= 1000 ? 8 : (n >= 100 && n <= 199) || (n >= 1001 && n <= 2000) ? 4 : 0) : ({"51-200": 4, "201-500": 8, "501-1000": 8, "1001-5000": 4}[String(band)] || 0))(Number(emp) || 0) + ({"Series B": 8, "Series C": 8, "Series D": 6, "Profitable private": 5}[String(stage)] || 0) + ({"Spreadsheets": 10, "In-house build": 8, "Unknown": 5}[String(tool)] ?? 3) + (String(crm) === "Salesforce" ? 4 : 0))'),
 ("Intent", ["Pts Hiring","Pts Sales Growth","Pts Funding","Pts Leadership","Pts Competitor","Pts Other"],
  '((...p) => Math.min(70, p.reduce((s, v) => s + (Number(v) || 0), 0)))'),
 ("Score", ["Exclusion","Fit","Intent"],
  '((ex, fit, intent) => ex ? "" : Math.min(100, (Number(fit) || 0) + (Number(intent) || 0)))'),
 ("Below ICP Floor", ["Employees (exact)","Employee Band","Funding Stage"],
  '((emp, band, stage) => ["Pre-seed", "Seed", "Series A"].includes(String(stage)) || (n => n > 0 ? n < 100 : ["1-10", "11-50"].includes(String(band)))(Number(emp) || 0))'),
 ("Signal Tier", ["Exclusion","Below ICP Floor","Score","Fresh Signal"],
  f'((yes, ex, floor, score, fresh) => ex ? "Excluded" : yes(floor) ? "C" : (Number(score) || 0) >= 60 && yes(fresh) ? "A" : (Number(score) || 0) >= 35 ? "B" : "C")({YES}, '),
 ("Primary Signal", ["Exclusion","Pts Hiring","Pts Leadership","Pts Funding","Pts Sales Growth","Pts Competitor","Pts Other"],
  '((ex, h, l, f, s, c, o) => ex ? "" : [["Hiring RevOps", h], ["Leadership Change", l], ["Funding", f], ["Sales Team Growth", s], ["Competitor Mention", c], ["Other", o]].reduce((b, [k, v]) => (Number(v) || 0) > b[1] ? [k, Number(v) || 0] : b, ["", 0])[0])'),
 ("Score Check", ["Exclusion","Signal Tier","Below ICP Floor","Score","Expected Tier","Expected Score","Expected Primary","Primary Signal"],
  f'((yes, ex, tier, floor, score, eTier, eScore, ePrim, prim) => (t => t === String(eTier ?? "") && String(score ?? "") === String(eScore ?? "") && (ex || String(prim ?? "") === String(ePrim ?? "")) ? "OK" : "MISMATCH: expected " + eTier + " / " + eScore + " / " + ePrim)(String(tier) + (yes(floor) && !ex ? " (capped)" : "")))({YES}, '),
]
out = []
for name, cols, head in F:
    args = ", ".join(f"COL{i+1}" for i in range(len(cols)))
    formula = head + args + ")" if head.endswith(", ") else head + "(" + args + ")"
    out.append({"name": name, "columns": cols, "formula": formula})
json.dump(out, open("clay_formulas_v2.json", "w"), indent=1)
