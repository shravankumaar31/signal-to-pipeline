const F = require('./contact_formulas.json');
const run = (name, args) => { const f = F.find(x => x.name === name); let js = f.formula; args.forEach((a, i) => { js = js.replace(new RegExp(`\\bCOL${i + 1}\\b`), JSON.stringify(a)); }); return eval(js); };
const mk = (titles, up) => ({ "Clay Company Id": "1", [up ? "People" : "people"]: titles.map(([t, c], i) => ({ [up ? "First Name" : "first_name"]: "P" + i, [up ? "Last Name" : "last_name"]: "L" + i, [up ? "Title" : "title"]: t, [up ? "Url" : "url"]: "https://linkedin.com/in/p" + i, [up ? "Country" : "country"]: c })) });
const cases = [
 ["Keeper-like", mk([["Sales Commission Manager", "US"], ["Chief Revenue Officer", "US"], ["CFO", "US"], ["Director, Revenue Operations", "US"], ["VP Sales EMEA", "IE"]], true), "US", "Director, Revenue Operations"],
 ["comp mgr vs CRO", mk([["Chief Revenue Officer", "US"], ["Sales Commission Manager", "US"]], false), "US", "Sales Commission Manager"],
 ["prefer HQ country", mk([["Head of Revenue Operations", "GB"], ["Senior Director, Revenue Operations", "CA"]], true), "CA", "Senior Director, Revenue Operations"],
 ["only finance", mk([["VP Finance", "US"], ["Chief Financial Officer", "US"]], true), "US", "Chief Financial Officer"],
 ["empty", { People: [] }, "US", ""],
 ["json string", JSON.stringify(mk([["VP of Sales", "US"]], true)), "US", "VP of Sales"],
];
let bad = 0;
for (const [n, cell, hq, want] of cases) {
  const i = run("Primary Contact Idx", [cell, hq]);
  const title = run("Contact Title", [cell, i]);
  const ok = title === want; if (!ok) bad++;
  console.log(`${ok ? 'OK ' : 'BAD'} ${n.padEnd(18)} idx=${i} title="${title}" persona=${run("Contact Persona", [title])} seniority=${run("Contact Seniority", [title])} first=${run("Contact First Name", [cell, i])} country=${run("Contact Country", [cell, i])}`);
}
process.exit(bad ? 1 : 0);
