"""Phase 2 Step 6 — score the locked test set (decision #34) and write data/processed/account_set_preview.csv."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from scoring_reference import score, TODAY
from batch1_preview import B1
from batch2_preview import B2
from backfill_preview import BF

ACCOUNTS = B1 + B2 + BF
ORDER = {"A": 0, "B": 1, "C": 2, "Excluded": 3}

def main():
    rows = []
    for a in ACCOUNTS:
        r = score(a)
        rows.append({
            "account": a.name, "hq_country": a.hq_country,
            "employees": a.headcount or a.headcount_band, "funding": a.funding,
            "incumbent": a.incumbent, "crm": a.crm,
            "fit": r.get("fit", ""), "intent": r.get("intent", ""), "score": r.get("score", ""),
            "tier": r["tier"] + (" (capped)" if r.get("capped") else ""),
            "primary_signal": r.get("primary") or "", "reason": r.get("reason", ""),
            "breakdown": "; ".join(f"{k} {v}" for k, v in r.get("breakdown", {}).items()),
        })
    rows.sort(key=lambda x: (ORDER[x["tier"].split()[0]], -(x["score"] or 0)))
    out = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "account_set_preview.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"As of {TODAY} — {len(rows)} accounts\n")
    for x in rows:
        s = f"{x['score']:>3}" if x["score"] != "" else "  —"
        print(f"{x['tier']:<14} {s}  {x['account']:<18} {x['primary_signal'] or x['reason']}")
    from collections import Counter
    c = Counter(x["tier"].split()[0] for x in rows)
    print("\n" + " · ".join(f"{k} {c[k]}" for k in ["A", "B", "C", "Excluded"]))

if __name__ == "__main__":
    main()
