# 21-9d: 9 оставшихся оприходований — по каждому ТОВАРУ отдельной транзакцией: уменьшить парные расходы (строку того же склада),
# при другом складе — перемещение Y→X (Принято) на дату оприходования −1 мин, уменьшить строку оприходования. Ошибка → откат только этого товара.
import re as _re
from collections import defaultdict
okd, fail = set(), []
for ln in open(LOG, encoding="utf-8"):
    mm = _re.search(r"21-9 (.+?): (уменьшено|все строки)", ln)
    if mm: okd.add(mm.group(1))
    mm = _re.search(r"21-9 ОШИБКА (.+?): ", ln)
    if mm: fail.append(mm.group(1))
REST = set(f for f in fail if f not in okd)
doneI = set(_re.search(r"21-9d (.+?) \| (.+?): ", ln).group(1) + "|" + _re.search(r"21-9d (.+?) \| (.+?): ", ln).group(2)
            for ln in open(LOG, encoding="utf-8") if "21-9d " in ln and " | " in ln)
TP = {"СписаниеНедостачТоваров": "Товары", "ВнутреннееПотреблениеТоваров": "Товары", "ПроизводствоБезЗаказа": "МатериалыИРаботы", "ОприходованиеИзлишковТоваров": "Товары"}
tplMv = q("ВЫБРАТЬ ПЕРВЫЕ 1 Д.Ссылка КАК Д ИЗ Документ.ПеремещениеТоваров КАК Д ГДЕ Д.Комментарий ПОДОБНО \"%аудит 24.10.2026%\" И Д.Проведен")[0]["Д"]
ACC = ib.Перечисления.СтатусыПеремещенийТоваров.Принято
work = defaultdict(list); rref = {}
for t, o, r, m, k in MATCH:
    if s(r["Р"]) in REST:
        work[(s(r["Р"]), k)].append((o, m)); rref[s(r["Р"])] = r


def cut(ref, item, qty, wh=None):
    obj = ref.ПолучитьОбъект(); tp = getattr(obj, TP[ref.Метаданные().Имя]); left = qty
    for i in range(tp.Количество() - 1, -1, -1):
        row = tp.Получить(i)
        if s(row.Номенклатура) != item or left <= 0.0005:
            continue
        if wh is not None:
            try:
                if s(row.Склад) and s(row.Склад) != s(wh):
                    continue
            except Exception:
                pass
        old = row.Количество; c = min(old, left); left -= c; new = round(old - c, 3)
        if new <= 0.0005:
            tp.Удалить(i); continue
        row.Количество = new
        try: row.КоличествоУпаковок = round(row.КоличествоУпаковок * new / old, 3)
        except Exception: pass
        try: row.Сумма = round(row.Цена * new, 2)
        except Exception: pass
    if left > 0.0005:
        raise RuntimeError(f"в {s(ref)[-30:]} не нашлось строк на {left}")
    if tp.Количество() == 0:
        obj.УстановитьПометкуУдаления(True)
    else:
        obj.Записать(ib.РежимЗаписиДокумента.Проведение)


ok = bad = 0
for (rn, k), pairs in sorted(work.items()):
    if rn + "|" + k in doneI:
        continue
    r = rref[rn]; total = sum(m for _, m in pairs)
    ib.НачатьТранзакцию()
    try:
        for o, m in pairs:
            cut(o["Р"], k, m, o["С"])
            if s(o["С"]) != s(r["С"]):
                mv = tplMv.ПолучитьОбъект().Скопировать()
                mv.Дата = r["П"] - datetime.timedelta(minutes=1); mv.СкладОтправитель = o["С"]; mv.СкладПолучатель = r["С"]; mv.Статус = ACC
                mv.Товары.Очистить(); mv.ВидыЗапасов.Очистить(); mv.Серии.Очистить()
                row = mv.Товары.Добавить(); row.Номенклатура = o["Н"]; row.КоличествоУпаковок = round(m, 3); row.Количество = round(m, 3)
                mv.Комментарий = f"[аудит 24.10.2026] товар списан/израсходован на складе {s(o['С'])}, оприходован излишком на {s(r['С'])} ({rn}) — оформлено как перемещение"
                mv.Записать(ib.РежимЗаписиДокумента.Проведение)
        cut(r["Р"], k, total)
        ib.ЗафиксироватьТранзакцию(); ok += 1
        log(f"21-9d {rn} | {k}: уменьшено {total:.3f} (пар {len(pairs)})")
    except Exception as e:
        try: ib.ОтменитьТранзакцию()
        except Exception: pass
        bad += 1
        msgs = []
        try:
            arr = ib.ПолучитьСообщенияПользователю(True); msgs = [arr.Получить(i).Текст for i in range(arr.Количество())]
        except Exception: pass
        print("НЕ ВЫШЛО", rn[-30:], "|", k[:35], "|", (" / ".join(msgs) or str(e))[-160:])
print(f"товаров обработано {ok}, не вышло {bad}")
