"""Reference implementation of the Flozero scoring spec (docs/signal_taxonomy.md).

Source of truth for testing: the Clay formula built in Phase 3 must produce the same score, tier and
primary signal as this script for every account. Run it to print the worked examples:

    python3 clay/scoring_reference.py
"""
from dataclasses import dataclass, field
from datetime import date
from math import floor
from typing import Optional

TODAY = date(2026, 10, 12)

# ---------- Fit (max 30) ----------
def headcount_pts(n):
    if 200 <= n <= 1000: return 8
    if 100 <= n <= 199 or 1001 <= n <= 2000: return 4
    return 0

# When only a LinkedIn band is known (no exact count), score the band (decision #29).
BAND_PTS = {"11-50": 0, "51-200": 4, "201-500": 8, "501-1000": 8, "1001-5000": 4}
EXCLUDED_BANDS = {"5001-10000", "10001+"}

ICP_COUNTRIES = {"US", "CA"}                               # legal HQ (decision #27)
BELOW_FLOOR_FUNDING = {"Pre-seed", "Seed", "Series A"}     # capped at Tier C (decision #28)
BELOW_FLOOR_BANDS = {"1-10", "11-50"}                      # under 100 employees: capped at Tier C (decision #30)

def below_floor(acct):
    if acct.funding in BELOW_FLOOR_FUNDING: return True
    if acct.headcount: return acct.headcount < 100
    return acct.headcount_band in BELOW_FLOOR_BANDS

FUNDING_PTS = {"Series B": 8, "Series C": 8, "Series D": 6, "Profitable private": 5}
INCUMBENT_PTS = {"Spreadsheets": 10, "In-house build": 8, "Unknown": 5}   # any competitor / Other -> 3
CRM_PTS = {"Salesforce": 4}                                               # unknown -> 0

COMPETITORS = {"Xactly", "CaptivateIQ", "Varicent", "Spiff", "QuotaPath", "Everstage", "Performio"}

# ---------- Intent (max 70) ----------
# (full-points window days, half-points window end days); None = state signal (no decay)
DECAY = {
    "Hiring RevOps": (45, 90),
    "Funding": (90, 180),
    "Leadership Change": (90, 180),
    "Sales Team Growth": None,
    "Competitor Mention": None,
    "Other": (45, 90),
}
TIE_BREAK = ["Hiring RevOps", "Leadership Change", "Funding", "Sales Team Growth", "Competitor Mention", "Other"]

def half_up(x):
    return int(floor(x + 0.5))

@dataclass
class Signal:
    type: str
    date: Optional[date] = None          # event date (posting, announcement, start date)
    comp_specific: bool = False          # Hiring RevOps: comp / commissions / ICM role
    pain_language: bool = False          # Hiring RevOps: posting names the pain
    closed: Optional[date] = None        # Hiring RevOps / Competitor Mention: posting close date
    role: str = ""                       # Leadership Change: "CRO-level" or "CFO"
    open_sales_roles: int = 0            # Sales Team Growth

    def base_points(self):
        if self.type == "Hiring RevOps":
            return (25 if self.comp_specific else 20) + (10 if self.pain_language else 0)
        if self.type == "Sales Team Growth":
            n = self.open_sales_roles
            return 20 if n >= 20 else 15 if n >= 10 else 10 if n >= 5 else 0
        if self.type == "Funding": return 20
        if self.type == "Leadership Change": return 13 if self.role == "CFO" else 20
        if self.type in ("Competitor Mention", "Other"): return 5
        raise ValueError(self.type)

    def current_points(self, today=TODAY):
        """Returns (points now, is_full_strength)."""
        base = self.base_points()
        if base == 0: return 0, False
        window = DECAY[self.type]
        if self.closed:                                   # posting has closed
            if self.type == "Hiring RevOps" and (today - self.closed).days <= 30:
                return half_up(base / 2), False
            return 0, False
        if window is None:                                # state signal: current while live
            return base, True
        age = (today - self.date).days
        full, half = window
        if age <= full: return base, True
        if age <= half: return half_up(base / 2), False
        return 0, False

@dataclass
class Account:
    name: str
    headcount: int
    funding: str
    incumbent: str
    crm: str                                              # "Salesforce", "HubSpot", "Unknown", ...
    signals: list = field(default_factory=list)
    excluded_reason: Optional[str] = None
    hq_country: str = "US"                                # legal HQ, ISO-2
    headcount_band: Optional[str] = None                  # LinkedIn band, used when headcount is 0 / unknown

def score(acct, today=TODAY):
    if acct.crm not in ("Salesforce", "Unknown"):
        return {"tier": "Excluded", "reason": f"CRM is {acct.crm}"}
    if acct.excluded_reason:
        return {"tier": "Excluded", "reason": acct.excluded_reason}
    if acct.hq_country not in ICP_COUNTRIES:
        return {"tier": "Excluded", "reason": f"legal HQ outside US + Canada ({acct.hq_country})"}
    if acct.headcount > 5000 or acct.headcount_band in EXCLUDED_BANDS:
        return {"tier": "Excluded", "reason": "over 5,000 employees"}

    hc = headcount_pts(acct.headcount) if acct.headcount else BAND_PTS.get(acct.headcount_band, 0)
    fit = (hc + FUNDING_PTS.get(acct.funding, 0)
           + INCUMBENT_PTS.get(acct.incumbent, 3) + CRM_PTS.get(acct.crm, 0))

    best = {}                                             # strongest instance per type
    for s in acct.signals:
        pts, fresh = s.current_points(today)
        if s.type not in best or pts > best[s.type][0]:
            best[s.type] = (pts, fresh)
    intent = min(70, sum(p for p, _ in best.values()))
    total = min(100, fit + intent)
    has_fresh = any(f and p > 0 for p, f in best.values())

    if total >= 60 and has_fresh: tier = "A"
    elif total >= 35: tier = "B"
    else: tier = "C"
    capped = below_floor(acct) and tier != "C"
    if capped: tier = "C"                                 # below the funding floor: watch list only

    live = [(p, t) for t, (p, _) in best.items() if p > 0]
    primary = max(live, key=lambda x: (x[0], -TIE_BREAK.index(x[1])))[1] if live else None
    return {"fit": fit, "intent": intent, "score": total, "tier": tier, "primary": primary,
            "fresh": has_fresh, "capped": capped, "breakdown": {t: p for t, (p, _) in best.items()}}

# ---------- Worked examples (fictional accounts) ----------
def d(days_ago): return date.fromordinal(TODAY.toordinal() - days_ago)

EXAMPLES = [
    (Account("Sample 1: spreadsheet scale-up", 450, "Series C", "Spreadsheets", "Salesforce", [
        Signal("Hiring RevOps", d(10), comp_specific=True, pain_language=True),
        Signal("Sales Team Growth", open_sales_roles=12)]), "A"),
    (Account("Sample 2: new CRO, incumbent unknown", 300, "Series B", "Unknown", "Salesforce", [
        Signal("Leadership Change", d(30), role="CRO-level"),
        Signal("Sales Team Growth", open_sales_roles=6)]), "B"),
    (Account("Sample 3: competitor user selecting a new tool", 800, "Series D", "CaptivateIQ", "Salesforce", [
        Signal("Hiring RevOps", d(20), comp_specific=True, pain_language=True),
        Signal("Competitor Mention")]), "A"),
    (Account("Sample 4: strong but stale", 250, "Series B", "Spreadsheets", "Salesforce", [
        Signal("Funding", d(120)), Signal("Hiring RevOps", d(70)),
        Signal("Leadership Change", d(100), role="CRO-level")]), "B"),
    (Account("Sample 5: comp role just filled, new CFO", 1200, "Profitable private", "In-house build", "Salesforce", [
        Signal("Hiring RevOps", d(50), comp_specific=True, closed=d(10)),
        Signal("Leadership Change", d(40), role="CFO")]), "B"),
    (Account("Sample 6: early, weak signal", 600, "Series A", "Unknown", "Unknown", [
        Signal("Other", d(5))]), "C"),
    (Account("Sample 8: just funded, still on spreadsheets", 250, "Series B", "Spreadsheets", "Salesforce", [
        Signal("Funding", d(25)), Signal("Sales Team Growth", open_sales_roles=8)]), "A"),
    (Account("Sample 9: strong signals, Series A", 150, "Series A", "Spreadsheets", "Salesforce", [
        Signal("Hiring RevOps", d(5), comp_specific=True, pain_language=True),
        Signal("Sales Team Growth", open_sales_roles=6)]), "C"),
    (Account("Sample 11: just funded, 40 people", 40, "Series B", "Unknown", "Salesforce", [
        Signal("Hiring RevOps", d(7)), Signal("Funding", d(10)), Signal("Sales Team Growth", open_sales_roles=5)]), "C"),
    (Account("Sample 10: legal HQ in London", 300, "Series C", "Unknown", "Salesforce", [
        Signal("Funding", d(20))], hq_country="GB"), "Excluded"),
    (Account("Sample 7: HubSpot CRM", 400, "Series B", "Spreadsheets", "HubSpot", [
        Signal("Funding", d(15))]), "Excluded"),
]

if __name__ == "__main__":
    ok = True
    print(f"As of {TODAY}\n")
    for acct, expected in EXAMPLES:
        r = score(acct)
        mark = "ok" if r["tier"] == expected else "MISMATCH"
        ok &= mark == "ok"
        if r["tier"] == "Excluded":
            print(f"{acct.name:<48} Excluded ({r['reason']})  [{mark}]")
        else:
            print(f"{acct.name:<48} fit {r['fit']:>2} + intent {r['intent']:>2} = {r['score']:>3}  "
                  f"Tier {r['tier']}{' (capped)' if r['capped'] else ''}  primary: {r['primary']}  fresh: {r['fresh']}  [{mark}]")
            print(f"{'':<48} {r['breakdown']}")
    print("\nAll examples match expected tiers." if ok else "\nSome examples did not match.")
    raise SystemExit(0 if ok else 1)
