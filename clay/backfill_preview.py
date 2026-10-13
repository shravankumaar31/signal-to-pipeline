"""Phase 2 Step 3 backfill candidates (#33). Firmographics verified on LinkedIn 2026-10-12."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from scoring_reference import Account, Signal, score
from datetime import date as D

BF = [
 # Apify route: comp role with no ICM tool named, Excel/Sheets + macros, "automate manual commission processes"
 Account("Keeper Security",0,"Profitable private","Unknown","Salesforce",[Signal("Hiring RevOps",D(2026,10,5),comp_specific=True,pain_language=True),Signal("Sales Team Growth",open_sales_roles=20)],headcount_band="501-1000"),
 # Funding route
 Account("Confido",0,"Series B","Unknown","Salesforce",[Signal("Funding",D(2026,9,25)),Signal("Hiring RevOps",D(2026,9,30))],headcount_band="51-200"), 
 Account("Numeral",0,"Series C","Unknown","Salesforce",[Signal("Funding",D(2026,9,23)),Signal("Sales Team Growth",open_sales_roles=5)],headcount_band="51-200"),
 Account("Ema",0,"Series B","Unknown","Unknown",[Signal("Funding",D(2026,9,23))],headcount_band="51-200"),  # ~200 employees per TechCrunch
]
if __name__ == "__main__":
    for a in BF:
        r = score(a)
        print(f"{a.name:<16} fit {r['fit']:>2} + intent {r['intent']:>2} = {r['score']:>3}  Tier {r['tier']}{' (capped)' if r['capped'] else ''}  {r['breakdown']}")
