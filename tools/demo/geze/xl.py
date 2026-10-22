import json, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
d=json.load(open('geze2.json')); wb=openpyxl.Workbook(); ws=wb.active; ws.title='По позициям'
H=['Артикул','Номенклатура','Остаток 31.12.25, шт','Остаток 31.12.25, ₸','Приход 2026, шт','Цена поставщика, ₸','Себест. с доставкой и пошлиной, ₸','Доп. расходы, %','Расход всего, шт','Продано клиентам, шт','Прайс Актобе с НДС, ₸','Выручка с НДС, ₸','Скидки, ₸','Скидка, %','Выручка без НДС, ₸','Себест. продаж (упр.), ₸','Прибыль без НДС, ₸','Маржа, %','Остаток сейчас, шт','Остаток сейчас, ₸','Запас, мес.']
ws.append(H)
for i,x in enumerate(sorted(d,key=lambda x:-x['c1']-x['rev']),start=2):
    ws.append([x['art'],x['name'],x['q0'],x['c0'],x['qin'],x['pin'],x['cin'],f'=IF(F{i}=0,"",G{i}/F{i}-1)',x['qout'],x['qs'],x['list'],x['rev'],x['disc'],f'=IF(L{i}+M{i}=0,"",M{i}/(L{i}+M{i}))',f'=L{i}/1.16',x['scost'],f'=O{i}-P{i}',f'=IF(O{i}=0,"",Q{i}/O{i})',x['q1'],x['c1'],f'=IF(J{i}=0,"",S{i}/(J{i}/9.7))'])
n=ws.max_row; t=n+1
ws.append(['','Итого']+[f'=SUM({c}2:{c}{n})' if c not in 'HKNRU' else '' for c in 'CDEFGHIJKLMNOPQRSTU'])
ws[f'H{t}']=f'=G{t}/F{t}-1'; ws[f'N{t}']=f'=M{t}/(L{t}+M{t})'; ws[f'R{t}']=f'=Q{t}/O{t}'; ws[f'U{t}']=f'=S{t}/(J{t}/9.7)'
for c in ws[1]: c.font=Font(bold=True,color='FFFFFF'); c.fill=PatternFill('solid',fgColor='1F2328'); c.alignment=Alignment(wrap_text=True,vertical='top')
for c in ws[t]: c.font=Font(bold=True)
for row in ws.iter_rows(min_row=2):
    for c in row[2:]:
        c.number_format='0.0%' if c.column_letter in 'HNR' else ('0.0' if c.column_letter=='U' else '#,##0')
ws.column_dimensions['B'].width=60
for c in 'CDEFGHIJKLMNOPQRSTU': ws.column_dimensions[c].width=13
ws.freeze_panes='C2'; ws.row_dimensions[1].height=45
s=wb.create_sheet('Как читать',0)
for r in [['Анализ группы GEZE · 22.10.2026'],[''],['Источник: 1С «Себестоимость товаров организаций» (01.01–22.10.2026) и «Валовая прибыль предприятия» (01.01–31.10.2026), отбор «GEZE» в наименовании.'],['Себестоимость — без НДС (импортный НДС 16% зачитывается). Доп. расходы = доставка + пошлина + брокер.'],['Выручка в 1С — с НДС 16%, скидки — автоматическая скидка группы ≈30%. Прибыль пересчитана без НДС.'],['«Продано клиентам» — без продаж своим юрлицам (GREENTE); разница с «Расход всего» — внутренние продажи и потребление.'],['Запас, мес. = остаток / (продано клиентам / 9,7 мес.).'],['Партии в 1С рассчитаны до 30.09.2026 — себестоимость октября предварительная.']]: s.append(r)
s['A1'].font=Font(bold=True,size=14); s.column_dimensions['A'].width=120
wb.save('ANESCOM_GEZE_analiz_2026.xlsx')
