import base64, asyncio, html, openpyxl, statistics
from playwright.async_api import async_playwright
D = '/tmp/claude-0/wb/'; R = '/tmp/claude-0/rep/'
E = html.escape
LOGO = base64.b64encode(open(R + 'logo_color.png', 'rb').read()).decode()
LOGOW = base64.b64encode(open(R + 'logo_white.png', 'rb').read()).decode()
RED = '#C1272D'; DARK = '#1F2328'; GRAY = '#6B7280'; LINE = '#E5E7EB'; GREEN = '#2E8B57'
wb = openpyxl.load_workbook(D + 'ANESCOM_sravnenie_cen_VNUTR_22_10_2026.xlsx', data_only=True)
CATS = ['ПВХ', 'Алюминий', 'Комплектующие', 'Фурнитура']
NOTE = {
 'ПВХ': 'Профиль PROPLEX 70 и FUNKE в рынке или дешевле 5-камерных аналогов (WUKO, KAVI, Brusbox). Дороже только 3-камерного KALE. Переплата — армирование и цветной подоконник. Цены WUKO/KAVI/KALE оптовые.',
 'Алюминий': 'Холодная серия 45 в рынке (+8%). Тёплая серия 65 дороже тёплых аналогов на 47–67% и дороже того же ТАТПРОФ у дилера в РФ на 14–28%. Закладные — примерно вдвое дороже.',
 'Комплектующие': 'Уплотнители ТПУ-6001/6002 в 6–7 раз дороже рынка по тому же коду — вероятная ошибка единицы в 1С. Пена TYTAN в середине рынка, но эконом-пена 65 л дешевле на 40%. Герметик и анкеры — в рынке.',
 'Фурнитура': 'Против брендов того же класса (Fores, Vorne, ALFA) мы в рынке или дешевле. Против китайских петель и дверных ручек (ProfiMart, Kaspi) дороже на 43–107% — нужна эконом-линейка.',
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
    cmp = [r for r in rows if r[17] not in (None, '')]
    diffs = [r[18] for r in cmp if isinstance(r[18], (int, float))]
    stats[k] = (len(rows), len(cmp), diffs)

grid = ''.join(f'<div><b>{k}</b>{stats[k][0]} позиций, с ценой конкурента — {stats[k][1]}</div>' for k in CATS)
pages.append(f'''<div class="cover"><div class="bar"></div><img src="data:image/png;base64,{LOGOW}" style="height:36px">
<div style="margin-top:110px;font-size:13px;color:#F3B6B8;font-weight:700;letter-spacing:2px">АНАЛИЗ ЦЕН ПО ГРУППАМ · 22 ОКТЯБРЯ 2026</div>
<div style="font-size:40px;font-weight:800;line-height:1.15;margin-top:12px">ПВХ, алюминий, комплектующие, фурнитура:<br>наши цены против конкурентов</div>
<p style="font-size:14px;line-height:1.55;color:#D1D5DB;margin-top:18px;max-width:820px">По 45 ходовых позиций в каждой группе из прайса 1С. Рядом — до трёх конкурентов с аналогами по техническим параметрам (включая китайские марки), разница в процентах и наша цена к минимальной на рынке. Пустые ячейки — цены закрыты, их дополнят ответы на запрос КП.</p>
<div class="grid">{grid}</div></div>''')

for k in CATS:
    ws = wb[k]; rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[1]]
    n, c, diffs = stats[k]
    above = sum(1 for d in diffs if d > 0.03); below = sum(1 for d in diffs if d < -0.03)
    med = statistics.median(diffs) * 100 if diffs else 0
    kp = f'<div class="kp"><div><b>{c} из {n}</b>позиций с ценой конкурента</div><div><b>{above}</b>мы дороже минимума рынка (&gt;3%)</div><div><b>{below}</b>мы дешевле минимума рынка</div><div><b>{"+" if med>0 else "−" if med<0 else ""}{abs(med):.0f}%</b>медиана: наша цена к минимуму</div></div>'
    head = '<tr><th style="width:2.5%">№</th><th style="width:25%">Наименование (прайс 1С)</th><th style="width:4%">Ед.</th><th style="width:6.5%">Наша, ₸</th>' + \
           ''.join(f'<th style="width:16%">Конкурент {j}: аналог · цена · разница</th>' for j in (1, 2, 3)) + '<th style="width:6.5%">Мин. рынка, ₸</th><th style="width:7%">Наша к мин.</th></tr>'
    def trs(chunk):
        out = ''
        for r in chunk:
            cells = ''
            for j in range(3):
                b = 5 + j * 4
                if r[b + 2] in (None, ''): cells += '<td class="c">—</td>'
                else: cells += f'<td class="c">{E(str(r[b]))}<br>{E(str(r[b+1]))}<br><b>{fmt(r[b+2])}</b> · {pct(r[b+3])}</td>'
            cls = ' class="k"' if r[17] not in (None, '') else ''
            out += f'<tr{cls}><td>{r[0]}</td><td class="nm">{E(r[1])}</td><td>{E(str(r[2] or ""))}</td><td class="n">{fmt(r[4], 2 if r[4] < 100 else 0)}</td>{cells}<td class="n">{fmt(r[17])}</td><td class="n">{pct(r[18])}</td></tr>'
        return out
    withc = [r for r in rows if r[17] not in (None, '')]; noc = [r for r in rows if r[17] in (None, '')]
    pages.append(page(f'<h2>{k}: позиции с ценами конкурентов</h2><p class="lead">{NOTE[k]}</p>{kp}<table>{head}{trs(withc)}</table>'))
    # remaining items compact, two columns list
    half = (len(noc) + 1) // 2
    def lst(ch): return '<table><tr><th style="width:6%">№</th><th>Наименование</th><th style="width:9%">Ед.</th><th style="width:14%">Наша, ₸</th></tr>' + ''.join(f'<tr><td>{r[0]}</td><td>{E(r[1])}</td><td>{E(str(r[2] or ""))}</td><td class="n">{fmt(r[4], 2 if r[4] < 100 else 0)}</td></tr>' for r in ch) + '</table>'
    pages.append(page(f'<h2>{k}: позиции без открытых цен конкурентов ({len(noc)})</h2><p class="lead">Цены по этим позициям конкуренты дают только по запросу — они включены в запрос КП от GREENTE (файл GREENTE_zapros_KP_materialy.xlsx).</p><div style="display:flex;gap:16px"><div style="flex:1">{lst(noc[:half])}</div><div style="flex:1">{lst(noc[half:])}</div></div>'))

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
