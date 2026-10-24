# 21-9b: для «Оприходований излишков», которые не провелись после уменьшения (товар на другом складе): «Перемещение товаров» Y→X на совпавшее кол-во,
# дата = дата оприходования − 1 мин. Шаблон — последнее проведённое перемещение. Затем повторить wrRetry.
import re as _re
from collections import defaultdict
fail, okd = [], set()
for ln in open(LOG, encoding="utf-8"):
    mm = _re.search(r"21-9 ОШИБКА (.+?): ", ln)
    if mm:
        fail.append(mm.group(1))
    mm = _re.search(r"21-9 (.+?): (уменьшено|все строки)", ln)
    if mm:
        okd.add(mm.group(1))
fail = set(f for f in fail if f not in okd)
done_mv = set(_re.search(r"21-9b перемещение для (.+?) из", ln).group(1) + "|" + _re.search(r" из (.+?) →", ln).group(1)
              for ln in open(LOG, encoding="utf-8") if "21-9b перемещение для" in ln)
grp = defaultdict(list)   # (receipt, Y) -> [(item_ref, qty)]
rref, yref = {}, {}
for t, o, r, m, k in MATCH:
    rn = s(r["Р"])
    if rn in fail and s(o["С"]) != s(r["С"]):
        grp[(rn, s(o["С"]))].append((o["Н"], m)); rref[rn] = r; yref[s(o["С"])] = o["С"]
print("перемещений к созданию:", len(grp), "| по оприходованиям:", len({k[0] for k in grp}))
tpl = q("ВЫБРАТЬ ПЕРВЫЕ 1 Д.Ссылка КАК Д ИЗ Документ.ПеремещениеТоваров КАК Д ГДЕ Д.Проведен И Д.Статус = ЗНАЧЕНИЕ(Перечисление.СтатусыПеремещенийТоваров.Отгружено) УПОРЯДОЧИТЬ ПО Д.Дата УБЫВ")[0]["Д"]
for (rn, yn), lines in sorted(grp.items()):
    if rn + "|" + yn in done_mv:
        continue
    r = rref[rn]
    if DRY if "DRY" in globals() else True:
        print(f"  {yn[:24]} → {s(r['С'])[:24]} для {rn[-40:]}: строк {len(lines)}, кол-во {sum(x[1] for x in lines):,.2f}"); continue
    try:
        new = tpl.ПолучитьОбъект().Скопировать()
        new.Дата = r["П"] - datetime.timedelta(minutes=1)
        new.СкладОтправитель = yref[yn]; new.СкладПолучатель = r["С"]
        new.Товары.Очистить(); new.ВидыЗапасов.Очистить(); new.Серии.Очистить()
        try:
            new.ЗаказНаПеремещение = None
        except Exception:
            pass
        agg = defaultdict(float); refs_ = {}
        for it, qy in lines:
            agg[s(it)] += qy; refs_[s(it)] = it
        for n, qy in agg.items():
            row = new.Товары.Добавить(); row.Номенклатура = refs_[n]; row.КоличествоУпаковок = round(qy, 3); row.Количество = round(qy, 3)
        new.Комментарий = f"[аудит 24.10.2026] товар списан/израсходован на складе {yn}, оприходован излишком на {s(r['С'])} ({rn}) — оформлено как перемещение"
        new.Записать(ib.РежимЗаписиДокумента.Проведение)
        log(f"21-9b перемещение для {rn} из {yn} → {s(r['С'])}: {s(new.Ссылка)}, строк {len(agg)}")
    except Exception as e:
        msgs = []
        try:
            arr = ib.ПолучитьСообщенияПользователю(True); msgs = [arr.Получить(i).Текст for i in range(arr.Количество())]
        except Exception:
            pass
        print("ОШИБКА перемещения", yn[:20], "→", rn[-35:], "|", (" / ".join(msgs) or str(e))[-250:])
