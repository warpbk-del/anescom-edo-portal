import json, sys, html, asyncio, base64
sys.path.insert(0,'/tmp/claude-0/rep')
E=html.escape
d=json.load(open('geze2.json')); T=json.load(open('tot.json'))
R='/tmp/claude-0/rep/'
b64=lambda p: base64.b64encode(open(p,'rb').read()).decode()
LOGO=b64(R+'logo_color.png')
RED='#C1272D';DARK='#1F2328';GRAY='#6B7280';LINE='#E5E7EB';GREEN='#2E8B57';AMBER='#B7791F'
CSS=open(R+'build.py').read().split('CSS = f"""')[1].split('"""')[0].replace('{{','{').replace('}}','}')
for k,v in dict(RED=RED,DARK=DARK,GRAY=GRAY,LINE=LINE,GREEN=GREEN,AMBER=AMBER).items(): CSS=CSS.replace('{'+k+'}',v)
CSS+='table{font-size:8.6px} td{padding:3.5px 4px} th{padding:5px 4px;font-size:8.4px} tr.tot td{font-weight:800;border-top:2px solid #1F2328} .neg{color:#C1272D;font-weight:700} .pos{color:#2E8B57;font-weight:700}'
m=lambda v: '—' if v is None else f'{v:,.0f}'.replace(',', ' ')
mm=lambda v: f'{v/1e6:,.2f}'.replace(',', ' ').replace('.',',')
pc=lambda v,cls=False: '—' if v is None else (f'<span class="{"neg" if v<10 else "pos" if v>=25 else ""}">{v:.0f}%</span>' if cls else f'{v:.0f}%')
def page(n,body): return f'<div class="page"><div class="hdr"><img src="data:image/png;base64,{LOGO}"><span>GEZE: закупка, остатки, продажи 2026 · 22.10.2026</span></div>{body}<div class="foot"><span>ANESCOM · внутренний документ · данные 1С</span><span>{n}</span></div></div>'
def tbl(head,rows,tot=None,al=None):
    h=''.join(f'<th{" style=\"text-align:right\"" if i>0 else ""}>{E(x)}</th>' for i,x in enumerate(head))
    b=''
    for r in rows+([tot] if tot else []):
        cls=' class="tot"' if tot and r is tot else ''
        b+=f'<tr{cls}>'+''.join(f'<td{" class=\"n\"" if i>0 else ""}>{c}</td>' for i,c in enumerate(r))+'</tr>'
    return f'<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'
mpct=T['marg']/T['revx']*100; ext=(T['cin']/T['pin']-1)*100; disc=T['disc']/(T['rev']+T['disc'])*100; mon=T['q1']/(T['qs']/9.7)
P=[]
# 1
P.append(page(1,f'''<h1>Группа GEZE: за сколько купили,<br>что осталось и как продаём</h1>
<p class="lead" style="margin-top:12px">Период: остатки на 31.12.2025, приход и продажи 01.01–22.10.2026. Источник — отчёты 1С «Себестоимость товаров организаций» и «Валовая прибыль предприятия» (отбор «GEZE» в наименовании). Себестоимость в 1С — без НДС; выручка в 1С — с НДС 16%, поэтому прибыль ниже пересчитана без НДС.</p>
<div class="kpis">
<div class="kpi"><b>{m(T['q0'])} шт · {mm(T['c0'])} млн ₸</b><span>остаток на 31.12.2025 по себестоимости (без НДС)</span></div>
<div class="kpi a"><b>{m(T['qin'])} шт · {mm(T['cin'])} млн ₸</b><span>пришло в 2026 с доставкой и пошлинами; цена поставщика {mm(T['pin'])} млн, доп. расходы +{str(round(ext,1)).replace('.',',')}%</span></div>
<div class="kpi g"><b>{m(T['qs'])} шт · {mm(T['rev'])} млн ₸</b><span>продано клиентам (выручка с НДС, уже после скидок); без НДС — {mm(T['revx'])} млн</span></div>
<div class="kpi"><b>{disc:.0f}% · {mm(T['disc'])} млн ₸</b><span>отдано скидками: автоматическая скидка по группе ≈30% на все продажи</span></div>
<div class="kpi"><b>{str(round(mpct,1)).replace('.',',')}% · {mm(T['marg'])} млн ₸</b><span>реальная валовая прибыль без НДС по упр. себестоимости 1С; по себестоимости партий (регл.) — 28%. 1С показывает 32,3%, потому что считает выручку с НДС</span></div>
<div class="kpi a"><b>{m(T['q1'])} шт · {mm(T['c1'])} млн ₸</b><span>остаток сейчас — запас примерно на {mon:.0f} месяцев продаж</span></div></div>
<h3>Главное</h3><ul>
<li><b>Закупили почти в 2,6 раза больше, чем продали:</b> пришло {m(T['qin'])} шт, клиентам ушло {m(T['qs'])} шт. Деньги в остатке выросли с {mm(T['c0'])} до {mm(T['c1'])} млн ₸ (+{(T['c1']/T['c0']-1)*100:.0f}%).</li>
<li><b>Скидка 30% съедает маржу.</b> После скидки и НДС зарабатываем {mpct:.0f}% с выручки. На TS 3000 — убыток, на TS 4000 и TS 2100 — 10–18% (по себестоимости партий 22–30%).</li>
<li><b>TS 2100 — главный риск:</b> на складе 782 шт (≈12,0 млн ₸), продаём ≈22 шт в месяц, то есть запаса хватит примерно на 3 года.</li>
<li><b>Неликвид:</b> {m(T['deadq'])} шт на {mm(T['dead'])} млн ₸ в 2026 не продавались ни разу: E800, кнопки 3A, консоли, кожухи, TS 2100 RAL-7024.</li>
<li>Ещё {m(T['qout']-T['qs'])} шт списаны со склада без выручки клиентам — это продажи своим юрлицам (GREENTE) и внутреннее потребление. В отчёт о прибыли они не входят.</li></ul>'''))
# 2 закупка
rows=[];
for x in sorted([x for x in d if x['qin']],key=lambda x:-x['cin']):
    rows.append([E(x['short']),m(x['qin']),m(x['uin']),m(x['uland']),f"+{x['extra']:.0f}%",m(x['uland']*1.16),mm(x['cin'])])
tot=['<b>Итого</b>',m(T['qin']),'','',f'+{str(round(ext,1)).replace('.',',')}%','',mm(T['cin'])]
P.append(page(2,f'''<h2>1. За сколько купили в 2026 году</h2>
<p class="lead">Цена поставщика — «Стоимость поступления» в 1С. «С доставкой и пошлиной» — себестоимость партии после распределения доп. расходов: транспорт, таможенная пошлина, брокер. Импортный НДС 16% мы зачитываем, поэтому в себестоимость он не входит. Для расчёта нужных денег ориентир — последняя колонка (примерно ×1,16).</p>
{tbl(['Позиция','Пришло, шт','Цена поставщика, ₸/шт','С доставкой и пошлиной, ₸/шт','Доп. расходы','С НДС ≈, ₸/шт','Сумма, млн ₸'],rows,tot)}
<div class="box" style="margin-top:12px"><b>Вывод.</b> Доставка и пошлины добавили к цене поставщика {ext:.1f}% ({mm(T['cin']-T['pin'])} млн ₸). Разбить эту сумму на транспорт и пошлину можно только по документам «Доп. расходы» и ГТД. Если нужна точная разбивка, выгружу их отдельно.</div>'''))
# 3 остатки
rows=[]
for x in sorted([x for x in d if x['q0'] or x['q1']],key=lambda x:-x['c1']):
    rows.append([E(x['short']),m(x['q0']),mm(x['c0']),m(x['qin']),m(x['qs']),m(x['q1']),mm(x['c1']),('нет продаж' if not x['qs'] else f"{x['mon']:.0f}") if x['q1'] else '—'])
tot=['<b>Итого</b>',m(T['q0']),mm(T['c0']),m(T['qin']),m(T['qs']),m(T['q1']),mm(T['c1']),f'{mon:.0f}']
P.append(page(3,f'''<h2>2. Остатки: 31.12.2025 → сейчас</h2>
<p class="lead">Себестоимость без НДС. Запас в месяцах — текущий остаток, делённый на средние продажи клиентам за 9,7 месяца 2026 года.</p>
{tbl(['Позиция','Остаток 31.12.25, шт','Сумма, млн ₸','Пришло 2026, шт','Продано клиентам, шт','Остаток сейчас, шт','Сумма, млн ₸','Запас, мес.'],rows,tot)}'''))
# 4 продажи
rows=[]
for x in sorted([x for x in d if x['qs']],key=lambda x:-x['rev']):
    rows.append([E(x['short']),m(x['qs']),m(x['list']),m(x['avgp']),f"{x['dpct']:.0f}%",m(x['avgp']/1.16),m(x['ucs']),mm(x['marg']),pc(x['mpct'],True)])
tot=['<b>Итого</b>',m(T['qs']),'','',f'{disc:.0f}%','','',mm(T['marg']),str(round(mpct,1)).replace('.',',')+'%']
P.append(page(4,f'''<h2>3. Как продавали в 2026 году (с учётом скидок)</h2>
<p class="lead">Прайс — «Розница Актобе-18» с НДС на 22.10.2026. Средняя цена — фактическая выручка с НДС, делённая на количество (уже после скидки). Прибыль считается без НДС: (выручка ÷ 1,16) − себестоимость продаж из «Валовой прибыли» (упр. учёт: закупка + доп. расходы). По себестоимости партий (регл. учёт) маржа на доводчиках выше на 5–12 п.п., в целом по группе — 28%.</p>
{tbl(['Позиция','Продано, шт','Прайс, ₸','Ср. цена с НДС, ₸','Скидка','Ср. цена без НДС, ₸','Себест., ₸/шт','Прибыль, млн ₸','Маржа'],rows,tot)}'''))
# 5 выводы
P.append(page(5,f'''<h2>4. Выводы и что делать</h2>
<h3>Цены и скидка</h3><ul>
<li>На GEZE действует автоматическая скидка около 30%. Вместе с НДС 16% от прайса нам остаётся около 60%. Получается, что прайс должен быть минимум в 2 раза выше себестоимости, а у доводчиков он выше только в 1,5–2,1 раза.</li>
<li><b>TS 3000 V</b> продаём в минус (−8%): цена после скидки 36 149 ₸ при себестоимости 33 522 ₸. Безубыточный прайс при скидке 30% — 55 600 ₸, для маржи 20% — около 69 500 ₸ (сейчас 50 941 ₸). Другой вариант — ограничить скидку на эту модель до 10%.</li>
<li><b>TS 4000 и TS 2100</b> дают 10–18%. Предлагаю скидку на доводчики не больше 15–20%, а 30% давать только под объект от N штук и по согласованию.</li>
<li>Тяги, монтажные пластины и TS 2000 приносят 45–80% — их скидку можно оставить.</li></ul>
<h3>Закупки и склад</h3><ul>
<li>Остановить закупку <b>TS 2100</b>, пока запас не опустится ниже 6 месяцев (сейчас ≈35 мес.). Подготовить объектное предложение для застройщиков на 200–300 шт.</li>
<li>Неликвид на {mm(T['dead'])} млн ₸ (E800, кнопки 3A, консоли, кожухи, TS 2100 RAL-7024): включить в комплекты к автоматике и окнам GREENTE или распродать со скидкой без ухода в минус.</li>
<li>Закупать по фактической скорости продаж: держать запас на 3–4 месяца плюс срок поставки.</li></ul>
<h3>Порядок в данных</h3><ul>
<li>В прайсе нет цен на Boxer EN 3-6 и пластину TS 3000 RAL-7024. Артикул 102425 стоит у двух разных тяг.</li>
<li>В 1С «Валовая прибыль» по умолчанию считает выручку с НДС, из-за этого рентабельность завышена (32% вместо 21%). Для управленческих решений лучше переключить «Данные продаж» на «без НДС».</li>
<li>Партии в 1С рассчитаны до 30.09.2026, поэтому себестоимость продаж за октябрь предварительная.</li></ul>'''))
doc=f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'+''.join(P)+'</body></html>'
open('report.html','w').write(doc)
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':794,'height':1123},device_scale_factor=2.5)
        await pg.goto('file:///tmp/claude-0/geze/report.html'); await pg.wait_for_timeout(400)
        for i,el in enumerate(await pg.query_selector_all('.page')):
            await el.screenshot(path=f'p{i+1}.png')
            print(i+1, await el.evaluate('e=>e.scrollHeight'))
        await b.close()
asyncio.run(main())
from PIL import Image
ims=[Image.open(f'p{i}.png').convert('RGB') for i in range(1,len(P)+1)]
ims[0].save('ANESCOM_GEZE_analiz_2026.pdf',save_all=True,append_images=ims[1:],resolution=240)
