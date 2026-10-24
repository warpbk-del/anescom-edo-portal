# 21-9c: для оприходований, которые так и не удалось уменьшить, вернуть парным расходным документам совпавшее количество (чтобы остатки не завысились).
import re as _re
from collections import defaultdict
okd, fail = set(), []
for ln in open(LOG, encoding="utf-8"):
    mm = _re.search(r"21-9 (.+?): (уменьшено|все строки)", ln)
    if mm:
        okd.add(mm.group(1))
    mm = _re.search(r"21-9 ОШИБКА (.+?): ", ln)
    if mm:
        fail.append(mm.group(1))
rest = set(f for f in fail if f not in okd)
reverted = set(_re.search(r"21-9c возврат кол-ва: (.+?) \+", ln).group(1) for ln in open(LOG, encoding="utf-8") if "21-9c возврат кол-ва:" in ln)
print("не уменьшены оприходования:", len(rest))
for mv in q("""ВЫБРАТЬ Д.Ссылка КАК Д, Д.Комментарий КАК К ИЗ Документ.ПеремещениеТоваров КАК Д ГДЕ Д.Комментарий ПОДОБНО "%аудит 24.10.2026%" И НЕ Д.ПометкаУдаления"""):
    if any(rn in mv["К"] for rn in rest):
        mv["Д"].ПолучитьОбъект().УстановитьПометкуУдаления(True)
        log(f"21-9c перемещение снято (оприходование не уменьшено): {s(mv['Д'])}")
back = defaultdict(lambda: defaultdict(float)); oref = {}; itref = {}; whref = {}
for t, o, r, m, k in MATCH:
    if s(r["Р"]) in rest:
        back[s(o["Р"])][k] += m; oref[s(o["Р"])] = o["Р"]; itref[k] = o["Н"]; whref[(s(o["Р"]), k)] = o["С"]
TP = {"СписаниеНедостачТоваров": "Товары", "ВнутреннееПотреблениеТоваров": "Товары", "ПроизводствоБезЗаказа": "МатериалыИРаботы"}
print("расходных документов к возврату:", len(back))
for dn, items in back.items():
    if dn in reverted:
        continue
    try:
        ref = oref[dn]; o = ref.ПолучитьОбъект(); tp = getattr(o, TP[ref.Метаданные().Имя])
        for k, m in items.items():
            row = None
            for i in range(tp.Количество()):
                if s(tp.Получить(i).Номенклатура) == k:
                    row = tp.Получить(i); break
            if row is not None:
                old = row.Количество; row.Количество = round(old + m, 3)
                try:
                    row.КоличествоУпаковок = round(row.КоличествоУпаковок * row.Количество / old, 3) if old else row.Количество
                except Exception:
                    pass
            else:
                tmpl = tp.Получить(0) if tp.Количество() else None
                row = tp.Добавить()
                if tmpl is not None:
                    for fld in ("СтатьяРасходов", "Склад", "АналитикаРасходов", "Подразделение"):
                        try:
                            setattr(row, fld, getattr(tmpl, fld))
                        except Exception:
                            pass
                row.Номенклатура = itref[k]
                try:
                    row.Склад = whref[(dn, k)]
                except Exception:
                    pass
                row.Количество = round(m, 3)
                try:
                    row.КоличествоУпаковок = round(m, 3)
                except Exception:
                    pass
        o.Записать(ib.РежимЗаписиДокумента.Проведение)
        log(f"21-9c возврат кол-ва: {dn} + по {len(items)} товарам")
    except Exception as e:
        print("ОШИБКА", dn[-45:], str(e)[-180:])
