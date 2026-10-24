# Дозаполнить строки материалов, добавленные wrRevert без группы затрат/статьи калькуляции (Производство без заказа, 2025–2026), перепровести.
from collections import Counter
docs = q("""ВЫБРАТЬ РАЗЛИЧНЫЕ Д.Ссылка КАК Д ИЗ Документ.ПроизводствоБезЗаказа.МатериалыИРаботы КАК Д
ГДЕ Д.Ссылка.Проведен И Д.Ссылка.Дата >= &Н И (Д.ГруппаЗатрат = НЕОПРЕДЕЛЕНО ИЛИ Д.ГруппаЗатрат.Пустая() ИЛИ Д.СтатьяКалькуляции = ЗНАЧЕНИЕ(Справочник.СтатьиКалькуляции.ПустаяСсылка))""",
         Н=datetime.datetime(2025, 1, 1))
print("документов с пустыми строками:", len(docs))
for r in docs:
    o = r["Д"].ПолучитьОбъект(); tp = o.МатериалыИРаботы
    groups = Counter(); arts = Counter(); fixed = 0
    for i in range(tp.Количество()):
        row = tp.Получить(i)
        g, a = s(row.ГруппаЗатрат), s(row.СтатьяКалькуляции)
        if g: groups[g] += 1
        if a: arts[a] += 1
    gref = aref = None
    for i in range(tp.Количество()):
        row = tp.Получить(i)
        if s(row.ГруппаЗатрат) == (groups.most_common(1)[0][0] if groups else "") and gref is None:
            gref = row.ГруппаЗатрат
        if s(row.СтатьяКалькуляции) == (arts.most_common(1)[0][0] if arts else "") and aref is None:
            aref = row.СтатьяКалькуляции
    for i in range(tp.Количество()):
        row = tp.Получить(i)
        if not s(row.ГруппаЗатрат) and gref is not None:
            row.ГруппаЗатрат = gref; fixed += 1
        if not s(row.СтатьяКалькуляции) and aref is not None:
            row.СтатьяКалькуляции = aref; fixed += 1
    try:
        o.Записать(ib.РежимЗаписиДокумента.Проведение)
        log(f"21-12 дозаполнены строки ({fixed}) и перепроведён {s(r['Д'])}")
    except Exception as e:
        print("ОШИБКА", s(r["Д"])[-40:], str(e)[-150:])
