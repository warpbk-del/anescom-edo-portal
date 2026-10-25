import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
F = "Arial"
def norm(s):
    s = s.lower().replace("ё","е")
    s = re.sub(r"^\s*(ак|ak)-", "", s)
    s = s.replace("темно-серый","тс").replace("темно-серая","тс").replace("чёрн","чер").replace("черн","чер")
    s = re.sub(r"[^0-9a-zа-я]+", "", s)
    return s
lam = {}
for l in open("lam_in_2026.txt"):
    n,q = l.rstrip("\n").rsplit("|",1); lam[norm(n)] = (n, float(q))
ak = [(n, -float(q)) for n,q in (l.rstrip("\n").split("|") for l in open("rec1_2026.txt"))]
sm = [l.rstrip("\n").split("|") for l in open("s_match.txt")]
surp = [l.rstrip("\n").split("|") for l in open("surp_0908.txt")]

wb = Workbook(); hdr_fill = PatternFill("solid", fgColor="2B4B5C"); hdr_font = Font(name=F, bold=True, color="FFFFFF")
thin = Side(style="thin", color="BBBBBB")
def sheet(ws, headers, widths):
    ws.append(headers)
    for i,w in enumerate(widths,1):
        ws.column_dimensions[get_column_letter(i)].width = w
        c = ws.cell(1,i); c.fill = hdr_fill; c.font = hdr_font; c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 42; ws.freeze_panes = "A2"
def finish(ws):
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if c.font.name != F or not c.font.bold: c.font = Font(name=F, bold=c.font.bold, color=c.font.color)
            c.border = Border(bottom=thin)
    ws.auto_filter.ref = ws.dimensions

# 1. АК-профиль
ws = wb.active; ws.title = "АК-профиль"
sheet(ws, ["Позиция в АВТОКОМП (пересчёт №1 от 08.09.2026, не проведён)", "Недостача по пересчёту, шт", "Тот же товар в ANESCOM (без «АК-»)", "Получено ANESCOM в 2026 «Поступлением от переработчика», шт", "Вывод"], [62,14,58,18,46])
r = 2
for n,q in ak:
    m = lam.get(norm(n))
    ws.append([n, q, m[0] if m else "", m[1] if m else 0, None])
    ws.cell(r,5).value = f'=IF(D{r}>=B{r},"Передано ANESCOM (у ANESCOM оформлено) — в АВТОКОМП оформить выбытие продукции",IF(D{r}>0,"Частично передано — проверить остаток","Не найдено в поступлениях — проверить (окраска/фурнитура?)"))'
    for c in (2,4): ws.cell(r,c).number_format = '#,##0.0;-#,##0.0;"-"'
    r += 1
akN = r-1
ws.cell(r,1,"ИТОГО").font = Font(name=F, bold=True)
ws.cell(r,2,f"=SUM(B2:B{akN})").font = Font(name=F, bold=True)
ws.cell(r,4,f'=SUMPRODUCT((D2:D{akN}>=B2:B{akN})*B2:B{akN})').font = Font(name=F, bold=True)
ws.cell(r,5,"← в колонке D: сколько шт недостачи покрыто поступлениями ANESCOM").font = Font(name=F, italic=True)
akTot = r
finish(ws)

# 2. Комплектующие
ws2 = wb.create_sheet("Комплектующие")
sheet(ws2, ["Позиция (списано недостачей в АВТОКОМП 08.09.2026)", "Списано, шт/м", "Излишки тех же позиций у ANESCOM 2024–2026, шт/м", "Сумма излишков ANESCOM, ₸", "Где и когда оприходовали", "Покрыто излишками, шт/м", "Вывод"], [58,12,16,16,60,14,40])
r = 2
for n,q,hq,hs,w in sm:
    ws2.append([n, float(q), float(hq), float(hs), w, None, None])
    ws2.cell(r,6).value = f"=MIN(B{r},C{r})"
    ws2.cell(r,7).value = f'=IF(ISNUMBER(SEARCH("ПРОВЕРИТЬ",E{r})),"Проверить вручную",IF(C{r}>=B{r},"Найдено в филиалах — реализация вместо списания",IF(C{r}>0,"Частично найдено","Не найдено — реальная недостача / пересортица")))'
    for c in (2,3,6): ws2.cell(r,c).number_format = '#,##0.0;-#,##0.0;"-"'
    ws2.cell(r,4).number_format = '#,##0;-#,##0;"-"'
    r += 1
sN = r-1
ws2.cell(r,1,"ИТОГО").font = Font(name=F, bold=True)
for c,col in ((2,"B"),(4,"D"),(6,"F")): ws2.cell(r,c,f"=SUM({col}2:{col}{sN})").font = Font(name=F, bold=True)
sTot = r
finish(ws2)


# 2b. АК — остальные 70 позиций
import json
left = json.load(open("left70.json")); af = {int(l.split("|")[0]): l.rstrip("\n").split("|") for l in open("akfind.txt")}
ws4 = wb.create_sheet("АК-прочие", 2)
sheet(ws4, ["Позиция в АВТОКОМП (пересчёт №1 от 08.09.2026)", "Недостача, шт", "ANESCOM купил у АВТОКОМП тот же товар без «АК-» (07.2025–10.2026), шт", "ANESCOM получил «Поступлением от переработчика», шт", "Все приходы этого товара в ANESCOM", "Вывод"], [58,12,18,16,60,52])
r = 2
for i,(n,q) in enumerate(left):
    a = af[i]
    ws4.append([n, q, float(a[1]), float(a[2]), a[3], None])
    c_, d_ = float(a[1]), float(a[2])
    ws4.cell(r,6).value = ("Продан ANESCOM под обычным названием — в АВТОКОМП пересортица АК- на обычный товар" if c_>=q else "Получен ANESCOM от переработчика — в АВТОКОМП оформить выбытие" if d_>=q else "Частично найден — проверить" if c_+d_>0 else "Не найден — реальная недостача")
    for c in (2,3,4): ws4.cell(r,c).number_format = '#,##0.0;-#,##0.0;"-"'
    r += 1
n4 = r-1
ws4.cell(r,1,"ИТОГО").font = Font(name=F, bold=True); ws4.cell(r,2,f"=SUM(B2:B{n4})").font = Font(name=F, bold=True)
ws4.cell(r+1,1,"Не найдено, шт").font = Font(name=F, bold=True); ws4.cell(r+1,2,sum(float(x[1]) for i_,x in enumerate(left) if float(af[i_][1])+float(af[i_][2])==0)).font = Font(name=F, bold=True)
ak4tot = r
finish(ws4)

# 3. Излишки АВТОКОМП 08.09.2026 (пересортица)
ws3 = wb.create_sheet("Излишки АВТОКОМП 08.09")
sheet(ws3, ["Оприходовано излишком в АВТОКОМП 08.09.2026 (тот же день, что и списание)", "Кол-во", "Сумма, ₸"], [70,12,16])
r = 2
for n,q,s_ in surp:
    ws3.append([n, float(q), float(s_)]); ws3.cell(r,3).number_format = '#,##0;-#,##0;"-"'; r += 1
ws3.cell(r,1,"ИТОГО").font = Font(name=F, bold=True); ws3.cell(r,3,f"=SUM(C2:C{r-1})").font = Font(name=F, bold=True); ws3.cell(r,3).number_format = '#,##0'
finish(ws3)

# 0. Итог
ws0 = wb.create_sheet("Итог", 0)
ws0.column_dimensions["A"].width = 70; ws0.column_dimensions["B"].width = 18
rows = [
 ("Расследование инвентаризации АВТОКОМП (данные на 25.10.2026)", None),
 ("", None),
 ("1. Ламинированный профиль «АК-…» — пересчёт №1 от 08.09.2026 (не проведён)", None),
 ("   Недостача по пересчёту, шт", "='АК-профиль'!B%d" % akTot),
 ("   Из неё покрыто поступлениями ANESCOM 2026 («Поступление от переработчика»), шт", "='АК-профиль'!D%d" % akTot),
 ("   Доля покрытия", "=IFERROR(B5/B4,0)"),
 ("   Вывод: не списывать; отчёт переработчика уже в ANESCOM — в АВТОКОМП оформить выбытие продукции давальцу (ANESCOM)", None),
 ("   Остальные 70 позиций «АК-» (окрашенный TATPROF, фурнитура), шт", "='АК-прочие'!B%d" % ak4tot),
 ("   из них не найдены нигде в ANESCOM (реальная недостача), шт", "='АК-прочие'!B%d" % (ak4tot+1)),
 ("   Остальные — проданы ANESCOM под обычным названием (пересортица АК- на обычный товар в АВТОКОМП)", None),
 ("", None),
 ("2. Комплектующие TATPROF и др. — списано недостачей 08.09.2026", None),
 ("   Списано, шт/м", "='Комплектующие'!B%d" % sTot),
 ("   Покрыто излишками в филиалах ANESCOM, шт/м", "='Комплектующие'!F%d" % sTot),
 ("   Сумма излишков ANESCOM по этим позициям, ₸", "='Комплектующие'!D%d" % sTot),
 ("   Вывод: найденное — оформить реализацию АВТОКОМП → ANESCOM и сторнировать излишки филиалов", None),
 ("", None),
 ("3. Излишки, оприходованные в АВТОКОМП 08.09.2026 (пересортица аналогов/цветов), ₸", "='Излишки АВТОКОМП 08.09'!C%d" % (len(surp)+2)),
 ("", None),
 ("Как читать: строки «ПРОВЕРИТЬ» — нечёткое совпадение названий, сверить вручную.", None),
 ("Источники: АВТОКОМП (веб-клиент, универсальный отчёт: пересчёты, списание недостач, оприходование излишков);", None),
 ("ANESCOM рабочая база (оприходования излишков 2024–2026) и копия на сервере (склад «Ламинация Автокомп», 2026).", None),
 ("Поступления ANESCOM в листе «АК-профиль» — только позиции с поступлением ≥ 28 шт; мелкие могут не попасть.", None),
]
for i,(a,b) in enumerate(rows,1):
    ws0.cell(i,1,a).font = Font(name=F, bold=(i==1 or a[:2] in ("1.","2.","3.")), size=13 if i==1 else 10)
    if b is not None:
        c = ws0.cell(i,2,b); c.font = Font(name=F, bold=True); c.number_format = '0.0%' if (a.strip().startswith('Доля')) else '#,##0'
wb.save("out/Инвентаризация_АВТОКОМП_сверка_ANESCOM.xlsx")
print("ok", akN-1, sN-1)
