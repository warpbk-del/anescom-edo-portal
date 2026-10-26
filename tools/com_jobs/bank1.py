# 21-29: сверка банка с выписками Halyk 01.04–25.10.2026 по месяцам (только чтение).
import collections
STM = json.loads(STMJ)
def bank(base, regname, acc, tag):
    z = base.NewObject("Запрос")
    z.Текст = ("ВЫБРАТЬ Т.Период КАК П, Т.Субконто1 КАК С1, Т.КорСчет.Код КАК КС, Т.СуммаОборотДт КАК Д, Т.СуммаОборотКт КАК К "
               "ИЗ РегистрБухгалтерии.%s.Обороты(&Н, &К, Месяц, Счет.Код = \"1021\", , , , ) КАК Т" % regname)
    z.УстановитьПараметр("Н", datetime.datetime(2026, 4, 1, 5)); z.УстановитьПараметр("К", datetime.datetime(2026, 10, 26, 4, 59, 59))
    sel = z.Выполнить().Выбрать(); M = collections.defaultdict(lambda: [0.0] * 5); corr = collections.Counter()
    while sel.Следующий():
        if acc not in base.String(sel.С1): continue
        m = str(sel.П)[:7]; kc = (sel.КС or "").strip(); d, k = sel.Д or 0, sel.К or 0
        corr[(kc, "Д" if d else "К")] += d or k
        if kc.startswith("105"):
            M[m][0] += k; M[m][1] += d
        elif kc.startswith(("6110", "1270", "6210")) or kc == "1251":
            M[m][2] += d
        else: M[m][3] += k; M[m][4] += d
    print(f"=== {tag} счёт …{acc}: месяц | взнос (1С−банк) | выплата | вознагр. | прочие расходы | прочие поступления")
    for m in sorted(set(M) | set(STM[acc])):
        a, b = M.get(m, [0] * 5), STM[acc].get(m, [0] * 5)
        print(f"  {m} " + " ".join(f"{a[i]-b[i]:>15,.2f}" for i in range(5)))
    print("  корр. счета 1С:", ", ".join(f"{k[0]}{k[1]}={v/1e6:,.1f}м" for k, v in corr.most_common(12)))
bank(ib, REG, "2209", "ANESCOM")
bank(ib, REG, "4950", "GREENTE (база ANESCOM)")
bank(AVc, AVc.Метаданные.РегистрыБухгалтерии.Получить(0).Имя, "0651", "АВТОКОМП")
