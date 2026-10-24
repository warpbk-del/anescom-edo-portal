# Повтор для оприходований, которые не провелись в wrFixAll (уменьшение по MATCH), с выводом сообщений 1С.
import re as _re
from collections import defaultdict
fail = []
for ln in open(LOG, encoding="utf-8"):
    mm = _re.search(r"21-9 ОШИБКА (.+?): ", ln)
    if mm:
        fail.append(mm.group(1))
ok_now = set()
for ln in open(LOG, encoding="utf-8"):
    mm = _re.search(r"21-9 (.+?): (уменьшено|все строки)", ln)
    if mm:
        ok_now.add(mm.group(1))
fail = [f for f in dict.fromkeys(fail) if f not in ok_now]
print("к повтору:", len(fail))
red = defaultdict(lambda: defaultdict(float)); refs = {}
for t, o, r, m, k in MATCH:
    red[s(r["Р"])][k] += m; refs[s(r["Р"])] = r["Р"]
for dname in fail[: globals().get("LIMIT", 100)]:
    items = dict(red[dname])
    o = refs[dname].ПолучитьОбъект()
    tp = o.Товары
    for i in range(tp.Количество() - 1, -1, -1):
        row = tp.Получить(i); n = s(row.Номенклатура)
        if items.get(n, 0) <= 0.0005:
            continue
        old = row.Количество; cut = min(old, items[n]); items[n] -= cut; new = round(old - cut, 3)
        if new <= 0.0005:
            tp.Удалить(i); continue
        row.Количество = new
        try:
            row.Сумма = round(row.Цена * new, 2)
        except Exception:
            pass
    try:
        ib.ПолучитьСообщенияПользователю(True)
    except Exception:
        pass
    try:
        if tp.Количество() == 0:
            o.УстановитьПометкуУдаления(True); log(f"21-9 {dname}: все строки совпали — на удаление")
        else:
            o.Записать(ib.РежимЗаписиДокумента.Проведение); log(f"21-9 {dname}: уменьшено (повтор), перепроведён")
    except Exception as e:
        msgs = []
        try:
            arr = ib.ПолучитьСообщенияПользователю(True)
            msgs = [arr.Получить(i).Текст for i in range(arr.Количество())]
        except Exception:
            pass
        print("ОШИБКА", dname[-45:], "|", " / ".join(msgs)[:300] or str(e)[-200:])
