"""Phase 2 Step 3 — batch 1 screening preview (firmographics verified on LinkedIn 2026-10-12)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from scoring_reference import Account, Signal, score
from datetime import date as D

B1 = [
 Account("Flow Engineering",0,"Series B","Unknown","Unknown",[Signal("Hiring RevOps",D(2026,10,5)),Signal("Funding",D(2026,10,1)),Signal("Sales Team Growth",open_sales_roles=8)],headcount_band="11-50"),
 Account("Metaview",0,"Series C","Unknown","Unknown",[Signal("Hiring RevOps",D(2026,8,24)),Signal("Sales Team Growth",open_sales_roles=14)],hq_country="GB",headcount_band="51-200"),
 Account("Tines",500,"Series C","CaptivateIQ","Salesforce",[Signal("Hiring RevOps",D(2026,9,30),comp_specific=True)]),
 Account("Sierra",0,"Series E","Unknown","Salesforce",[Signal("Hiring RevOps",D(2026,10,6),comp_specific=True),Signal("Sales Team Growth",open_sales_roles=6),Signal("Funding",D(2026,5,15)),Signal("Leadership Change",D(2026,8,31),role="CFO")],headcount_band="1001-5000"),
 Account("Semperis",0,"Series D","Xactly","Salesforce",[Signal("Hiring RevOps",D(2026,9,18),comp_specific=True)],headcount_band="501-1000"),
 Account("Tailscale",250,"Series C","CaptivateIQ","Unknown",[Signal("Sales Team Growth",open_sales_roles=9)],hq_country="CA"),
 Account("Chainguard",500,"Series D","Everstage","Unknown",[Signal("Sales Team Growth",open_sales_roles=16)]),
 Account("Gong",0,"Series E","Other","Salesforce",[Signal("Hiring RevOps",D(2026,10,8),comp_specific=True,pain_language=True),Signal("Sales Team Growth",open_sales_roles=32)],headcount_band="1001-5000"),
 Account("Notion",0,"Series C","Everstage","Salesforce",[Signal("Hiring RevOps",D(2026,8,31),comp_specific=True),Signal("Sales Team Growth",open_sales_roles=10)],headcount_band="501-1000"),
 Account("Bazaarvoice",0,"Profitable private","Everstage","Salesforce",[Signal("Hiring RevOps",D(2026,9,3),comp_specific=True)],headcount_band="1001-5000"),
 Account("Flai",0,"Series A","Spreadsheets","Salesforce",[Signal("Hiring RevOps",D(2026,10,6),pain_language=True),Signal("Sales Team Growth",open_sales_roles=5)],headcount_band="51-200"),
]
if __name__ == "__main__":
    for a in B1:
        r = score(a)
        if r["tier"] == "Excluded": print(f"{a.name:<18} Excluded — {r['reason']}"); continue
        print(f"{a.name:<18} fit {r['fit']:>2} + intent {r['intent']:>2} = {r['score']:>3}  Tier {r['tier']}{' (capped)' if r['capped'] else ''}  {r['primary']}")
