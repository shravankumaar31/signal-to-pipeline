// Evaluates clay_formulas.json row by row exactly as Clay would (columns resolved in order), against clay_accounts_v1.csv.
const fs = require('fs'); const path = require('path');
const NOW = process.argv[2] ? Date.parse(process.argv[2] + 'T19:00:00Z') : Date.now();
Date.now = () => NOW;
const csv = fs.readFileSync(path.join(__dirname, '../data/processed/clay_accounts_v1.csv'), 'utf8').replace(/\r/g, '').trim().split('\n');
const parse = l => { const out = []; let cur = '', q = false; for (const ch of l) { if (ch === '"') q = !q; else if (ch === ',' && !q) { out.push(cur); cur = ''; } else cur += ch; } out.push(cur); return out; };
const head = parse(csv[0]); const rows = csv.slice(1).map(l => Object.fromEntries(parse(l).map((v, i) => [head[i], v])));
const formulas = JSON.parse(fs.readFileSync(path.join(__dirname, 'clay_formulas.json'), 'utf8'));
let bad = 0;
for (const r of rows) {
  for (const [name, f] of formulas) {
    const js = f.replace(/\{\{([^}]+)\}\}/g, (_, c) => `__r[${JSON.stringify(c)}]`);
    r[name] = new Function('__r', 'return ' + js)(Object.fromEntries(Object.entries(r).map(([k, v]) => [k, v === '' ? undefined : v])));
  }
  if (r['Score Check'] !== 'OK') bad++;
  console.log(`${r['Signal Tier'].padEnd(9)} ${String(r.Score ?? '—').padStart(3)}  ${r['Account Name'].padEnd(18)} ${r['Primary Signal'] || r.Exclusion}  ${r['Score Check']}`);
}
console.log(bad ? `\n${bad} mismatches` : '\nAll 21 rows match the reference scorer.');
process.exit(bad ? 1 : 0);
