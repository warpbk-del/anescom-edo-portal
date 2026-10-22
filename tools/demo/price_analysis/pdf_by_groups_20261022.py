import base64, asyncio, html, openpyxl, statistics
from playwright.async_api import async_playwright
D = '/tmp/claude-0/wb/'; R = '/tmp/claude-0/rep/'
E = html.escape
LOGO = base64.b64encode(open(R + 'logo_color.png', 'rb').read()).decode()
LOGOW = base64.b64encode(open(R + 'logo_white.png', 'rb').read()).decode()
RED = '#C1272D'; DARK = '#1F2328'; GRAY = '#6B7280'; LINE = '#E5E7EB'; GREEN = '#2E8B57'
wb = openpyxl.load_workbook(D + 'ANESCOM_sravnenie_cen_VNUTR_22_10_2026.xlsx', data_only=True)
CATS = ['ПВХ', 'Алюминий', 'Комплектующие', 'Фурнитура']
NOTE_OLD = {
 'ПВХ': 'Профиль PROPLEX 70 и FUNKE в рынке или дешевле 5-камерных аналогов (WUKO, KAVI, Brusbox). Дороже только 3-камерного KALE. Переплата — армирование и цветной подоконник. Цены WUKO/KAVI/KALE оптовые.',
 'Алюминий': 'Холодная серия 45 в рынке (+8%). Тёплая серия 65 дороже тёплых аналогов на 47–67% и дороже того же ТАТПРОФ у дилера в РФ на 14–28%. Закладные — примерно вдвое дороже.',
 'Комплектующие': 'Уплотнители ТПУ-6001/6002 в 6–7 раз дороже рынка по тому же коду — вероятная ошибка единицы в 1С. Пена TYTAN в середине рынка, но эконом-пена 65 л дешевле на 40%. Герметик и анкеры — в рынке.',
 'Фурнитура': 'Против брендов того же класса (Fores, Vorne, ALFA) мы в рынке или дешевле. Против китайских петель и дверных ручек (ProfiMart, Kaspi) дороже на 43–107% — нужна эконом-линейка.',
}
NOTE = {
 'ПВХ': 'С автоматической скидкой 21,5% профиль PROPLEX 70 и FUNKE на 18–56% дешевле 5-камерных аналогов (WUKO, KAVI, Brusbox) и на уровне 3-камерного KALE. Армирование 1,5 мм и белый подоконник — в рынке; армирование 1,2 мм (+29%) и цветной подоконник против KAVI (+139%) — дороже. Цены WUKO/KAVI/KALE оптовые.',
 'Алюминий': 'Со скидкой 30% мы дешевле того же ТАТПРОФ у дилера в РФ на 11–20%, холодная серия 45 дешевле аналога на 25%, тёплая 65 — на уровне тёплых FV (+3…+11%). Дороже остаются только закладные (+49…59%).',
 'Комплектующие': 'Скидки по группе нет. Уплотнители ТПУ-6001/6002 в 6–7 раз дороже рынка по тому же коду — вероятная ошибка единицы в 1С (если на них действует скидка алюминия 30%, всё равно ×4,5). Пена TYTAN в рынке, эконом-пена 65 л дешевле на 40%. Герметик и анкеры — в рынке.',
 'Фурнитура': 'Скидки по группе нет. Против брендов того же класса (Fores, Vorne, ALFA) мы в рынке или дешевле. Против китайских петель и дверных ручек (ProfiMart, Kaspi) дороже на 36–120% — нужна эконом-линейка.',
}
def fmt(v, d=0):
    if v is None or v == '': return '—'
    return f'{v:,.{d}f}'.replace(',', ' ')
def pct(v):
    if v is None or v == '': return '<span class="eq">—</span>'
    v = v * 100; cls = 'up' if v > 3 else ('dn' if v < -3 else 'eq')
    return f'<span class="{cls}">{"+" if v > 0 else "−" if v < 0 else ""}{abs(v):.0f}%</span>'

CSS = f"""*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Inter,sans-serif;color:{DARK}}}
.page{{width:1123px;height:794px;padding:36px 40px 34px;position:relative;overflow:hidden;background:#fff}}
.hdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {RED};padding-bottom:8px;margin-bottom:14px}}
.hdr img{{height:22px}}.hdr span{{font-size:10px;color:{GRAY}}}
.foot{{position:absolute;left:40px;right:40px;bottom:14px;display:flex;justify-content:space-between;font-size:9px;color:{GRAY}}}
h2{{font-size:20px;font-weight:800}} .lead{{font-size:11.5px;line-height:1.45;color:#374151;margin:6px 0 10px}}
table{{width:100%;border-collapse:collapse;font-size:8.6px}}
th{{background:{DARK};color:#fff;text-align:left;font-weight:600;padding:5px 4px;vertical-align:bottom}}
td{{border-bottom:1px solid {LINE};padding:3.2px 4px;vertical-align:top}} td.n{{text-align:right;white-space:nowrap}}
td.c{{color:#374151}} tr.k td.nm{{font-weight:600}}
.up{{color:{RED};font-weight:700}}.dn{{color:{GREEN};font-weight:700}}.eq{{color:{GRAY};font-weight:700}}
.kp{{display:flex;gap:10px;margin:8px 0 10px}}.kp div{{flex:1;border:1px solid {LINE};border-left:4px solid {RED};padding:7px 10px;font-size:10px;color:#4B5563}}
.kp b{{display:block;font-size:18px;color:{DARK}}}
.cover{{width:1123px;height:794px;background:{DARK};color:#fff;padding:56px 60px;position:relative}}
.cover .bar{{position:absolute;left:0;top:0;width:12px;height:100%;background:{RED}}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:40px}}
.grid div{{border-top:3px solid {RED};padding-top:10px;font-size:11px;color:#D1D5DB;line-height:1.45}}.grid b{{display:block;color:#fff;font-size:16px;margin-bottom:4px}}
"""
pages = []; pn = [1]
def page(body):
    pn[0] += 1
    return f'<div class="page"><div class="hdr"><img src="data:image/png;base64,{LOGO}"><span>Анализ цен ANESCOM и конкурентов по группам · 22.10.2026</span></div>{body}<div class="foot"><span>ANESCOM · внутренний документ · цены «Розница Актобе» с НДС из 1С; конкуренты — открытые источники 22.10.2026</span><span>{pn[0]}</span></div></div>'

stats = {}
for k in CATS:
    ws = wb[k]; rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[1]]
    cmp = [r for r in rows if r[19] not in (None, '')]
    diffs = [r[20] for r in cmp if isinstance(r[20], (int, float))]
    stats[k] = (len(rows), len(cmp), diffs)

grid = ''.join(f'<div><b>{k}</b>{stats[k][0]} позиций, с ценой конкурента — {stats[k][1]}</div>' for k in CATS)
pages.append(f'''<div class="cover"><div class="bar"></div><img src="data:image/png;base64,{LOGOW}" style="height:36px">
<div style="margin-top:110px;font-size:13px;color:#F3B6B8;font-weight:700;letter-spacing:2px">АНАЛИЗ ЦЕН ПО ГРУППАМ · 22 ОКТЯБРЯ 2026</div>
<div style="font-size:40px;font-weight:800;line-height:1.15;margin-top:12px">ПВХ, алюминий, комплектующие, фурнитура:<br>наши цены против конкурентов</div>
<p style="font-size:14px;line-height:1.55;color:#D1D5DB;margin-top:18px;max-width:820px">По 45 ходовых позиций в каждой группе из прайса 1С. Наша цена — прайс 1С «Розница Актобе» минус автоматическая скидка группы (ПВХ 21,5%, алюминий 30%). Рядом — до трёх конкурентов с аналогами по техническим параметрам (включая китайские марки), разница в процентах и наша цена к минимальной на рынке. Пустые ячейки — цены закрыты, их дополнят ответы на запрос КП.</p>
<div class="grid">{grid}</div></div>''')

pages.append(page(f"""<h2>Главное: с учётом автоматической скидки картина другая</h2>
<p class="lead">Если считать нашу реальную цену — прайс 1С минус автоматическая скидка группы (ПВХ 21,5%, алюминий 30%), — по профилю мы не дороже рынка, а заметно дешевле. Переплата остаётся в отдельных позициях и в группах без скидки.</p>
<div class="kp"><div><b>−18…−56%</b>ПВХ PROPLEX 70 и FUNKE Helios дешевле 5-камерных аналогов (WUKO, KAVI, Brusbox)</div>
<div><b>−11…−20%</b>алюминий ТАТПРОФ дешевле того же профиля у дилера в РФ; к тёплым аналогам FV +3…+11%</div>
<div><b>×6–7</b>уплотнители ТПУ-6001/6002 дороже рынка — вероятная ошибка в 1С</div>
<div><b>+36…+120%</b>петли и дверные ручки дороже китайских аналогов (скидки по группе нет)</div></div>
<table><tr><th style="width:24%">Группа / позиция</th><th style="width:16%">Против аналогов того же класса</th><th style="width:20%">Против дешёвых (3-камерные, Китай, эконом)</th><th>Вывод</th></tr>
<tr><td>ПВХ PROPLEX HIT 70 (рама, створка, импост)</td><td class="n"><span class="dn">−33…−56%</span></td><td class="n"><span class="eq">+1…+16% к KALE 3К</span></td><td>Сильно дешевле рынка — есть запас маржи</td></tr>
<tr><td>FUNKE Helios</td><td class="n"><span class="dn">−18…−44%</span></td><td class="n">—</td><td>Дешевле рынка</td></tr>
<tr><td>FUNKE Bauline</td><td class="n"><span class="dn">−27…−53%</span></td><td class="n"><span class="eq">−8…+13% к KALE 3К</span></td><td>В рынке против самого дешёвого профиля</td></tr>
<tr><td>Армирование 1,5 / 1,2 мм</td><td class="n"><span class="eq">−7%</span> / <span class="up">+29%</span></td><td class="n">—</td><td>1,2 мм — пересмотреть</td></tr>
<tr><td>Подоконник 300 цветной</td><td class="n"><span class="eq">−2% к белым</span></td><td class="n"><span class="up">+139% к KAVI в цвете</span></td><td>Проверить цену на цветные</td></tr>
<tr><td>Алюминий тёплый 65 (рама, створка)</td><td class="n"><span class="dn">−11…−20% к ТАТПРОФ РФ</span></td><td class="n"><span class="up">+3…+11% к FV</span></td><td>В рынке</td></tr>
<tr><td>Алюминий холодный 45, дверные и доборные</td><td class="n"><span class="dn">−6…−25%</span></td><td class="n">—</td><td>Дешевле рынка</td></tr>
<tr><td>Закладные фасадные L80</td><td class="n"><span class="up">+49…+59%</span></td><td class="n">—</td><td>Пересчитать от цены метра</td></tr>
<tr><td>Уплотнители ТПУ-6001 / 6002 (скидки нет)</td><td class="n"><span class="up">в 6–7 раз</span></td><td class="n">—</td><td>Исправить прайс</td></tr>
<tr><td>Пена TYTAN 70</td><td class="n"><span class="eq">−7…+7%</span></td><td class="n"><span class="up">+70% к эконом 65 л</span></td><td>Добавить эконом-пену</td></tr>
<tr><td>Петли ECO / FS</td><td class="n"><span class="dn">−30…−33% к Fores</span></td><td class="n"><span class="up">+36…+67% к Китаю</span></td><td>Эконом-линейка</td></tr>
<tr><td>Ручка дверная MEGA</td><td class="n">—</td><td class="n"><span class="up">+81% к Китаю</span></td><td>Эконом-линейка</td></tr>
</table>
<p style="margin-top:8px;color:#6B7280;font-size:10px">Разница = (наша цена со скидкой − цена конкурента) / цена конкурента; плюс — мы дороже. Скидки по группам — со слов руководителя 22.10.2026; если скидка действует и на часть комплектующих ТАТПРОФ (уплотнители, закладные), их разница уменьшится на 30%.</p>"""))

for k in CATS:
    ws = wb[k]; rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[1]]
    n, c, diffs = stats[k]
    above = sum(1 for d in diffs if d > 0.03); below = sum(1 for d in diffs if d < -0.03)
    med = statistics.median(diffs) * 100 if diffs else 0
    kp = f'<div class="kp"><div><b>{c} из {n}</b>позиций с ценой конкурента</div><div><b>{above}</b>мы дороже минимума рынка (&gt;3%)</div><div><b>{below}</b>мы дешевле минимума рынка</div><div><b>{"+" if med>0 else "−" if med<0 else ""}{abs(med):.0f}%</b>медиана: наша цена со скидкой к минимуму</div></div>'
    head = '<tr><th style="width:2.5%">№</th><th style="width:21%">Наименование (прайс 1С)</th><th style="width:3.5%">Ед.</th><th style="width:5.5%">Прайс, ₸</th><th style="width:4.5%">Скидка</th><th style="width:6%">Наша со скидкой, ₸</th>' + \
           ''.join(f'<th style="width:15%">Конкурент {j}: аналог · цена · разница</th>' for j in (1, 2, 3)) + '<th style="width:6.5%">Мин. рынка, ₸</th><th style="width:7%">Наша к мин.</th></tr>'
    def trs(chunk):
        out = ''
        for r in chunk:
            cells = ''
            for j in range(3):
                b = 7 + j * 4
                if r[b + 2] in (None, ''): cells += '<td class="c">—</td>'
                else: cells += f'<td class="c">{E(str(r[b]))}<br>{E(str(r[b+1]))}<br><b>{fmt(r[b+2])}</b> · {pct(r[b+3])}</td>'
            cls = ' class="k"' if r[19] not in (None, '') else ''
            out += f'<tr{cls}><td>{r[0]}</td><td class="nm">{E(r[1])}</td><td>{E(str(r[2] or ""))}</td><td class="n">{fmt(r[4], 2 if r[4] < 100 else 0)}</td><td class="n">{"−"+format(r[5]*100,".1f").rstrip("0").rstrip(".")+"%" if r[5] else "—"}</td><td class="n"><b>{fmt(r[6], 2 if r[6] < 100 else 0)}</b></td>{cells}<td class="n">{fmt(r[19])}</td><td class="n">{pct(r[20])}</td></tr>'
        return out
    withc = [r for r in rows if r[19] not in (None, '')]; noc = [r for r in rows if r[19] in (None, '')]
    pages.append(page(f'<h2>{k}: позиции с ценами конкурентов</h2><p class="lead">{NOTE[k]}</p>{kp}<table>{head}{trs(withc)}</table>'))
    # remaining items compact, two columns list
    half = (len(noc) + 1) // 2
    def lst(ch): return '<table><tr><th style="width:6%">№</th><th>Наименование</th><th style="width:9%">Ед.</th><th style="width:13%">Прайс, ₸</th><th style="width:15%">Со скидкой, ₸</th></tr>' + ''.join(f'<tr><td>{r[0]}</td><td>{E(r[1])}</td><td>{E(str(r[2] or ""))}</td><td class="n">{fmt(r[4], 2 if r[4] < 100 else 0)}</td><td class="n">{fmt(r[6], 2 if r[6] < 100 else 0)}</td></tr>' for r in ch) + '</table>'
    pages.append(page(f'<h2>{k}: позиции без открытых цен конкурентов ({len(noc)})</h2><p class="lead">Цены по этим позициям конкуренты дают только по запросу — они включены в запрос КП от GREENTE (файл GREENTE_zapros_KP_materialy.xlsx).</p><div style="display:flex;gap:16px"><div style="flex:1">{lst(noc[:half])}</div><div style="flex:1">{lst(noc[half:])}</div></div>'))

pages.append(page(f"""<h2>Рекомендации: какие должны быть цены и как развиваться</h2>
<p class="lead">Наш профиль уже дешевле рынка. Задача — не снижать цены, а вернуть маржу там, где мы отдаём слишком много, и закрыть дешёвый сегмент отдельной линейкой.</p>
<table><tr><th style="width:30%">Что</th><th style="width:22%">Сейчас</th><th style="width:22%">Рекомендация</th><th>Почему</th></tr>
<tr><td>Авто-скидка ПВХ (PROPLEX, Helios)</td><td>21,5%</td><td>15–17%</td><td>Даже со скидкой 15% PROPLEX 70 дешевле WUKO 5К на ~40%, Helios — на ~20%</td></tr>
<tr><td>Авто-скидка ПВХ на Bauline</td><td>21,5%</td><td>оставить</td><td>Конкурирует с самым дешёвым KALE 3К</td></tr>
<tr><td>Авто-скидка алюминия</td><td>30%</td><td>оставить</td><td>Тёплая 65 уже на уровне FV, ТАТПРОФ дешевле, чем у дилера в РФ</td></tr>
<tr><td>Армирование 1,2 мм</td><td>887 → 696 со скидкой</td><td>~600 со скидкой</td><td>+29% к рынку</td></tr>
<tr><td>Закладные L80</td><td>572–707 со скидкой</td><td>450–550</td><td>+49…59% к расчёту от цены метра</td></tr>
<tr><td>Уплотнители ТПУ-6001 / 6002</td><td>446 / 1 008</td><td>80–95 / 150–170</td><td>Ошибка единицы — в 6–7 раз дороже рынка</td></tr>
<tr><td>Эконом-петли, дверная ручка, пена</td><td>нет в ассортименте</td><td>290–330 / 2 100–2 400 / 2 400–2 600 ₸</td><td>Клиент за дешёвым уходит к ProfiMart и на Kaspi</td></tr>
<tr><td>Ручка москитной сетки</td><td>11,9</td><td>20–25</td><td>В 2–3 раза дешевле рынка</td></tr></table>
<h3 style="font-size:13px;margin:14px 0 6px">Как развиваться</h3>
<ol style="padding-left:18px;font-size:11px;line-height:1.5">
<li><b>Показывать клиенту цену со скидкой.</b> Прайс «Розница» выглядит дороже рынка; тот, кто сравнивает по прайсу, сайту или Kaspi, видит 1 734 ₸ вместо реальных 1 361 ₸ за метр PROPLEX.</li>
<li><b>Два уровня в каждой группе:</b> «Стандарт» (наши бренды) и «Эконом» (проверенный китайский или турецкий товар) — особенно в фурнитуре и расходниках.</li>
<li><b>Отвечать китайским брендам параметрами:</b> толщина стенки, класс профиля, камеры, материал фурнитуры, гарантия; памятка для оконных цехов.</li>
<li><b>Оптовая шкала для цехов и дилеров</b> поверх авто-скидки (например, ещё −3% от 5 млн ₸ в месяц) — конкуренты (WUKO, KAVI, KALE) продают оптом.</li>
<li><b>Порядок в прайсе 1С:</b> единицы (м / хлыст / бухта), 74 позиции без цены, колонка «Оптовая цена».</li>
<li><b>Раз в квартал повторять сравнение</b> и дополнять закрытые цены ответами на запрос КП от GREENTE.</li></ol>"""))

doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>' + ''.join(pages) + '</body></html>'
open(D + 'cat.html', 'w').write(doc)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1123, 'height': 794}, device_scale_factor=2.2)
        await pg.goto('file://' + D + 'cat.html'); await pg.wait_for_timeout(400)
        els = await pg.query_selector_all('.page,.cover')
        for i, el in enumerate(els): await el.screenshot(path=D + f'c{i+1:02d}.png')
        await b.close(); return len(els)
n = asyncio.run(main())
from PIL import Image
ims = [Image.open(D + f'c{i:02d}.png').convert('RGB') for i in range(1, n + 1)]
ims[0].save(D + 'ANESCOM_analiz_cen_po_gruppam_22_10_2026.pdf', save_all=True, append_images=ims[1:], resolution=200)
sheet = Image.new('RGB', (561 * 3, 397 * 3), 'white')
for i, im in enumerate(ims[:9]): sheet.paste(im.resize((561, 397)), ((i % 3) * 561, (i // 3) * 397))
sheet.save(D + 'csheet.png'); print('pages', n)
