# Детали расхождений ввода остатков по выбранным счетам (после openKey: KD, BPN, KAR)
ACCS = globals().get("DET_ACCS", ("1030", "1010", "3350", "3360", "1421", "1411", "1310", "1720", "1430", "5610", "3221", "3150", "3250"))
for a in ACCS:
    rs = [(k, v) for k, v in KD.items() if k[0] == a]
    print(f"== {a}: {len(rs)} строк, КА−БП {sum(v[1] - v[0] for k, v in rs):,.2f}")
    for k, (b, c) in sorted(rs, key=lambda x: -abs(x[1][1] - x[1][0]))[:6]:
        nm = BPN.get(k) or (s(KAR[k]) if k in KAR else "")
        print(f"    {k[1][:28]:<28} | {nm[:34]:<34} | БП {b:>14,.2f} | КА {c:>14,.2f}")
