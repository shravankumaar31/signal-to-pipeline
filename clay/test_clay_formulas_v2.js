// Runs clay_formulas_v2.json against clay_accounts_v1.csv, substituting COLn with each row's value.
// Two passes: values as raw CSV strings, and values typed the way Clay may pass them (numbers, booleans).
const fs = require('fs'), path = require('path');
const NOW = Date.parse((process.argv[2] || new Date().toISOString().slice(0, 10)) + 'T19:00:00Z'); Date.now = () => NOW;
const lines = fs.readFileSync(path.join(__dirname, '../data/processed/clay_accounts_v1.csv'), 'utf8').replace(/\r/g, '').trim().split('\n');
const parse = l => { const o = []; let c = '', q = false; for (const ch of l) { if (ch === '"') q = !q; else if (ch === ',' && !q) { o.push(c); c = ''; } else c += ch; } o.push(c); return o; };
const head = parse(lines[0]);
const F = JSON.parse(fs.readFileSync(path.join(__dirname, 'clay_formulas_v2.json'), 'utf8'));
let bad = 0;
for (const typed of [false, true]) {
  for (const l of lines.slice(1)) {
    const r = Object.fromEntries(parse(l).map((v, i) => [head[i], v === '' ? null : v]));
    if (typed) for (const k in r) { if (r[k] === 'TRUE') r[k] = true; else if (r[k] === 'FALSE') r[k] = false; else if (r[k] !== null && /^\d+$/.test(r[k])) r[k] = Number(r[k]); }
    for (const f of F) {
      let js = f.formula; f.columns.forEach((c, i) => { js = js.replace(new RegExp(`\\bCOL${i + 1}\\b`), JSON.stringify(r[c] ?? null)); });
      let v = eval(js); r[f.name] = v === '' ? null : v;
    }
    if (r['Score Check'] !== 'OK') { bad++; console.log((typed ? 'typed ' : 'text  ') + r['Account Name'] + ': ' + r['Score Check'] + ' got ' + r['Signal Tier'] + ' / ' + r['Score'] + ' / ' + r['Primary Signal']); }
  }
}
console.log(bad ? `${bad} mismatches` : 'All 21 rows match in both passes (text values and typed values).');
process.exit(bad ? 1 : 0);
