"""Build data/processed/clay_accounts_v1.csv — the Phase 3 Clay import.

One row per account: firmographics from clay_import_accounts.csv plus flat signal-input columns
taken from the same Account objects the reference scorer uses, so Clay's formula columns can
recompute fit / intent / score / tier live (with decay against today) and must match
clay/final_set_preview.py on the run date.
"""
import csv, os, sys
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "clay"))
from final_set_preview import ACCOUNTS

def best(acct, typ):
    sigs = [s for s in acct.signals if s.type == typ]
    if not sigs: return None
    return max(sigs, key=lambda s: s.current_points()[0])

meta = {r["account"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/processed/clay_import_accounts.csv")))}
jobs = {r["company_token"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/raw/job_signals_2026-10-12.csv")))}
funding = {r["company"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/raw/funding_signals_2026-10-12.csv")))}
TOKEN = {"Keeper Security": "keepersecurity", "Sierra": "Sierra", "Gong": "gongio", "Notion": "notion", "Confido": "confidotech",
         "Tines": "tines", "Numeral": "numeral", "Semperis": "semperis", "Socure": "socure", "Bazaarvoice": "bazaarvoice",
         "Ema": "ema", "Flow Engineering": "flowengineering", "Flai": "flai", "Outmarket": "outmarket", "DoiT": "doitintl",
         "Chainguard": "chainguard", "Solink": "solink", "Tailscale": "tailscale", "Metaview": "metaview",
         "Clipboard Health": "clipboard", "Ambrook": "ambrook"}

rows = []
for a in ACCOUNTS:
    m = meta[a.name]; j = jobs.get(TOKEN[a.name], {}); f = funding.get(a.name, {})
    h, s, fu, l, c, o = (best(a, t) for t in ["Hiring RevOps", "Sales Team Growth", "Funding", "Leadership Change", "Competitor Mention", "Other"])
    src = j.get("comp_role_url") or (f.get("source") if f.get("source", "").startswith("http") else "")
    rows.append({
        "Account Name": a.name, "Domain": m["domain"], "HQ City": m["hq_city"], "HQ Region": m["hq_region"], "HQ Country": a.hq_country,
        "Employees (exact)": a.headcount or "", "Employee Band": a.headcount_band or "", "Funding Stage": a.funding,
        "Last Funding Amount": f.get("amount_usd", ""), "Last Funding Date": f.get("announced_date", ""),
        "CRM": a.crm, "Incumbent Comp Tool": a.incumbent, "Hard Exclusion": a.excluded_reason or "",
        "Hiring Role Title": j.get("comp_role_title", ""), "Hiring Posted": h.date.isoformat() if h and h.date else "",
        "Hiring Comp Specific": "TRUE" if h and h.comp_specific else "FALSE", "Hiring Pain Language": "TRUE" if h and h.pain_language else "FALSE",
        "Hiring Closed": h.closed.isoformat() if h and h.closed else "",
        "Open Sales Roles": s.open_sales_roles if s else (j.get("open_sales_roles") or 0),
        "Funding Signal Date": fu.date.isoformat() if fu else "",
        "Leadership Date": l.date.isoformat() if l else "", "Leadership Role": l.role if l else "",
        "Competitor Mention Live": "TRUE" if c else "FALSE", "Other Signal Date": o.date.isoformat() if o else "",
        "Signal Source URL": src,
        "Expected Tier": m["expected_tier"], "Expected Score": m["expected_score"], "Expected Primary": m["primary_signal"],
    })
out = os.path.join(ROOT, "data/processed/clay_accounts_v1.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"{len(rows)} rows, {len(rows[0])} columns -> {out}")
