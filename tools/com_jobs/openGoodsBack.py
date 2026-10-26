KC.Установить(False)
try:
    for kind, it, wh, ref, ns, rr, V, D in MIS:
        rows = VROW.get((wh, it), [])
        dref = rows[0][0] if rows else VV[wh][0]
        obj = dref.ПолучитьОбъект(); tp = obj.Товары
        idx = [i for i in range(tp.Количество()) if nk(s(tp.Получить(i).Номенклатура)) == it]
        if idx:
            row = tp.Получить(idx[0]); old = row.Количество; scale(row, old + rr, old)
        else:
            print('нет строки ввода — пропуск', it[:40]); continue
        obj.Записать(ib.РежимЗаписиДокумента.Проведение)
        log(f'21-28e возврат ввода {s(dref)[-40:]}: {it[:50]} +{rr} (списание {s(ref[0])[-35:]} не удалось уменьшить)')
        print('возвращено во ввод', it[:45], rr)
finally:
    KC.Установить(True); print('контроль', KC.Получить())
