"""Phase 2 Step 3 (cut per #33: 1Password, Ibotta, Perforce, BlueCat, Outreach) — batch 2 screening preview. Firmographics verified on LinkedIn 2026-10-12."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from scoring_reference import Account, Signal, score
from datetime import date as D

B2 = [
 Account("Clipboard Health",0,"Series C","Spreadsheets","Unknown",[Signal("Hiring RevOps",D(2026,8,21),comp_specific=True,pain_language=True)],headcount_band="501-1000",excluded_reason="staffing / recruiting marketplace"),
 Account("DoiT",0,"Profitable private","Unknown","Salesforce",[Signal("Sales Team Growth",open_sales_roles=10)],headcount_band="501-1000"),
 Account("Solink",0,"Series C","Unknown","Salesforce",[Signal("Sales Team Growth",open_sales_roles=6)],hq_country="CA",headcount_band="201-500"),
 Account("Socure",500,"Series E","Unknown","Salesforce",[Signal("Sales Team Growth",open_sales_roles=6),Signal("Funding",D(2026,8,27))]),
 Account("Ambrook",0,"Series B","Spreadsheets","HubSpot",[Signal("Funding",D(2026,8,6)),Signal("Hiring RevOps",D(2026,9,10))],headcount_band="51-200"),
 Account("Outmarket",0,"Series B","Spreadsheets","Unknown",[Signal("Funding",D(2026,10,1)),Signal("Other",D(2026,9,11))],headcount_band="11-50"),
]
if __name__ == "__main__":
    for a in B2:
        r = score(a)
        if r["tier"] == "Excluded": print(f"{a.name:<18} Excluded — {r['reason']}"); continue
        print(f"{a.name:<18} fit {r['fit']:>2} + intent {r['intent']:>2} = {r['score']:>3}  Tier {r['tier']}{' (capped)' if r['capped'] else ''}  {r['primary']}  {r['breakdown']}")
