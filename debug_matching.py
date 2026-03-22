task = "send $5415 to chandansir and mail resusts to abcd@gmail.com".lower()
print(f"Task: {task}")
print()

checks = {
    "legal:compliance": ["compliance","audit","regulatory","regulation","sox","soc2","gdpr","policy","legal","violation"],
    "legal:contract_review": ["contract","agreement","terms","clause","legal review","nda"],
    "legal:risk_assessment": ["risk","assess","threat","vulnerability","exposure","evaluate","danger"],
    "legal:regulatory_check": ["regulatory","regulation","rule","law","statute","standard"],
    "finops:payment_request": ["pay","transfer","send money","wire","remittance","settlement","$","vendor","money","recipient","disburse"],
    "finops:email_send": ["email","send","notify","notification","message","alert","mail","confirmation","receipt","results"],
}

for group, kws in checks.items():
    for kw in kws:
        if kw in task:
            idx = task.index(kw)
            print(f"  {group} -> '{kw}' found at pos {idx} in '...{task[max(0,idx-3):idx+len(kw)+3]}...'")
