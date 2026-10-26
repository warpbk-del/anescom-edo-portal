# 21-28e: доделка 21-28d. Временно выключить контроль остатков организаций (решение пользователя 26.10 08:27),
# дописать то, что упало (по журналу: okS/okO/okV из проверки inv), включить контроль обратно.
KC = ib.Константы.КонтролироватьОстаткиТоваровОрганизаций
was = KC.Получить(); KC.Установить(False); log(f"21-28e контроль остатков организаций: было {was}, временно выключен")
okd = err = 0
try:
    for (kind, dn), items in sorted(byDoc.items()):
        if kind != "списание" or dn in okS: continue
        try: res = cut_lines(items[0][0], items); okd += 1; log(f"21-28d списание {dn}: {res}, строк {len(items)}")
        except Exception as e: err += 1; print("ОШИБКА", dn[-35:], msgs(e))
    for wh, chg in vvChg.items():
        docs = {}
        for it, d in chg.items():
            if abs(d) < 0.0005 or _vd(wh, it) in okV: continue
            rows = VROW.get((wh, it), [])
            dref = rows[0][0] if rows else VV[wh][0]; key = s(dref)
            if key not in docs: docs[key] = [dref.ПолучитьОбъект(), 0]
            obj = docs[key][0]; tp = obj.Товары
            idx = [i for i in range(tp.Количество()) if nk(s(tp.Получить(i).Номенклатура)) == it]
            if d > 0:
                if idx:
                    row = tp.Получить(idx[0]); old = row.Количество; scale(row, old + d, old)
                else:
                    tpl = tp.Получить(0); row = tp.Добавить()
                    for c in ("Назначение", "Упаковка", "СтавкаНДС", "ВидЗапасов", "СтатусУказанияСерий", "ГруппаПродукции"):
                        try: setattr(row, c, getattr(tpl, c))
                        except Exception: pass
                    nref, pr = vvRef[(wh, it)]
                    bq, bs = BPI2.get(it, [0, 0]); pr = (bs / bq) if bq > 0.0005 and bs > 0 else pr
                    row.Номенклатура = nref; row.Количество = round(d, 3); row.КоличествоУпаковок = round(d, 3); row.Цена = round(pr, 2)
                    for f in ("Сумма", "СуммаБезНДС", "СуммаРегл", "СуммаСНДС"):
                        try: setattr(row, f, round(pr * d, 2))
                        except Exception: pass
            else:
                left = -d
                for i in sorted(idx, reverse=True):
                    if left <= 0.0005: break
                    row = tp.Получить(i); old = row.Количество; c = min(old, left); left -= c
                    if old - c <= 0.0005: tp.Удалить(i)
                    else: scale(row, old - c, old)
                if left > 0.0005: print("НЕ ХВАТИЛО ввода", wh[:20], it[:40], round(left, 3))
            docs[key][1] += 1
        for key, (obj, n) in docs.items():
            try:
                if CM not in (obj.Комментарий or ""): obj.Комментарий = (obj.Комментарий or "") + CM
                obj.Записать(ib.РежимЗаписиДокумента.Проведение); okd += 1; log(f"21-28d ввод {key[-40:]}: изменено позиций {n}")
            except Exception as e: err += 1; print("ОШИБКА ввода", key[-35:], msgs(e))
    for (kind, dn), items in sorted(byDoc.items()):
        if kind != "оприходование" or dn in okO: continue
        try: res = cut_lines(items[0][0], items); okd += 1; log(f"21-28d оприходование {dn}: {res}, строк {len(items)}")
        except Exception as e: err += 1; print("ОШИБКА", dn[-35:], msgs(e))
finally:
    KC.Установить(was); log(f"21-28e контроль остатков организаций возвращён: {KC.Получить()}")
print(f"ДОДЕЛКА: документов записано {okd}, ошибок {err}; контроль = {KC.Получить()}")
