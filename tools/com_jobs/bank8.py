# 21-30a: помесячно 01.2025–10.2026: банк (выписка) против 1С — всего поступило/списано, депозит взнос/выплата, вознаграждение (только чтение).
import collections, json
MON = json.loads(MONJ)
def side(base, acc, key, excl=None):
    rg = base.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
    z = base.NewObject("Запрос")
    z.Текст = ("ВЫБРАТЬ Т.Период КАК П, Т.СчетДт.Код КАК СД, Т.СчетКт.Код КАК СК, Т.СубконтоДт1 КАК ДС, Т.СубконтоКт1 КАК КС, Т.Сумма КАК С "
               "ИЗ РегистрБухгалтерии.%s.ДвиженияССубконто(&Н, &К, , , ) КАК Т ГДЕ Т.СчетДт.Код = &А ИЛИ Т.СчетКт.Код = &А" % rg)
    z.УстановитьПараметр("Н", datetime.datetime(2025, 1, 1, 5)); z.УстановитьПараметр("К", datetime.datetime(2026, 10, 26, 4, 59, 59)); z.УстановитьПараметр("А", acc)
    sel = z.Выполнить().Выбрать(); M = collections.defaultdict(lambda: [0] * 6)
    while sel.Следующий():
        m = str(sel.П)[:7]; a = round((sel.С or 0) * 100)
        ds, ks = base.String(sel.ДС), base.String(sel.КС)
        dt = sel.СД.strip() == acc and key in ds and not (excl and excl in ds)
        kt = sel.СК.strip() == acc and key in ks and not (excl and excl in ks)
        if dt and kt: continue
        if not (dt or kt): continue
        corr = (sel.СК if dt else sel.СД).strip(); cs = ks if dt else ds
        isdep = corr.startswith("105") or (corr == "1021" and "епозит" in cs) or (corr == "1021" and acc == "1030")
        x = M[m]
        if dt:
            x[0] += a
            if isdep: x[3] += a
            elif corr.startswith(("6110", "1270")) or corr == "1151": x[4] += a
        else:
            x[1] += a
            if isdep: x[2] += a
    return M
def show(tag, M, B):
    print(f"=== {tag}: месяц | поступило 1С−банк | списано 1С−банк | взнос деп. 1С−банк | выплата деп. 1С−банк | вознагр. 1С−банк")
    t = [0] * 5
    for m in sorted(set(M) | set(B)):
        a, b = M.get(m, [0] * 6), B.get(m, [0] * 6)
        d = [a[0] - b[0], a[1] - b[1], a[2] - b[2], a[3] - b[3], a[4] - b[4]]
        t = [t[i] + d[i] for i in range(5)]
        print(f"  {m} " + " ".join(f"{x/100:>16,.2f}" for x in d))
    print("  ИТОГО " + " ".join(f"{x/100:>16,.2f}" for x in t))
show("ANESCOM 1030/2209", side(ib, "1030", "2209", "(KZT)"), MON["AN"])
show("АВТОКОМП 1021/АВТОКОМП KZT", side(AVc, "1021", "АВТОКОМП KZT"), MON["AV"])
