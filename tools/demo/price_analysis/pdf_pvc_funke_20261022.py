import base64, asyncio, html
from playwright.async_api import async_playwright
D = '/tmp/claude-0/wb/'; R = '/tmp/claude-0/rep/'
E = html.escape
LOGO = base64.b64encode(open(R + 'logo_color.png', 'rb').read()).decode()
LOGOW = base64.b64encode(open(R + 'logo_white.png', 'rb').read()).decode()
RED = '#C1272D'; DARK = '#1F2328'; GRAY = '#6B7280'; LINE = '#E5E7EB'; GREEN = '#2E8B57'; BLUE = '#3B6EA8'

# (brand/line, params, origin, seller, type, frame, sash, mullion, url, ours)
C70 = [
 ('PROPLEX HIT 70 (наш, для справки)', '70 мм, 5 камер; со скидкой 21,5%', 'РФ', 'ANESCOM, Актобе', 'наша цена', 1361, 1564, 1640, '', False),
 ('FUNKE Helios — ANESCOM', 'рама 63 / створка 77 / импост 82; со скидкой 21,5%', '—', 'ANESCOM, Актобе', 'наша цена', 1801, 1985, 2024, '', True),
 ('WUKO 5 камер (Prime 70 / Effect 70)', '70 мм, 5 камер, класс А/В', 'Казахстан', 'Deniz, Алматы', 'опт', 2064, 2531, 2531, 'https://denizpipe.kz/g8491085-profil-wuko', False),
 ('WUKO 5 камер — розница', '70 мм, 5 камер', 'Казахстан', 'Deniz, Алматы', 'розница', 2440, 2670, 2675, 'https://denizpipe.kz/g8491085-profil-wuko', False),
 ('Exprof Profecta 70', '70 мм, 5 камер, класс B', 'РФ', 'san102.ru, Уфа', 'розница РФ*', 1145, 1287, 1417, 'https://san102.ru/profili-exprof.html', False),
 ('Brusbox Super Aero 70', '70 мм', 'РФ', 'rtk-ltd, С.-Петербург', 'РФ*', 1518, 1734, 1596, 'https://rtk-ltd.com/__profil-i-armirovanie/profil-brusbox/', False),
 ('Brusbox Super Termo 70', '70 мм', 'РФ', 'rtk-ltd, С.-Петербург', 'РФ*', 2215, 2508, 2459, 'https://rtk-ltd.com/__profil-i-armirovanie/profil-brusbox/', False),
]
C60 = [
 ('FUNKE Bauline — ANESCOM', 'рама 63 / створка 77; со скидкой 21,5%', '—', 'ANESCOM, Актобе', 'наша цена', 1239, 1521, None, '', True),
 ('FUNKE Standart — ANESCOM', 'рама 63 / створка 77 / импост 82; со скидкой 21,5%', '—', 'ANESCOM, Актобе', 'наша цена', 1530, 1855, 1672, '', True),
 ('KALE 3 камеры', '3 камеры, ширина не указана', '—', 'Deniz, Алматы', 'опт', 1344, 1344, 1344, 'https://denizpipe.kz/g8505296-profil-kale', False),
 ('KAVI 4 камеры', '4 камеры, белый', 'Казахстан', 'Deniz, Алматы', 'опт / розн.', 2410, 3545, None, 'https://denizpipe.kz/g8492683-profil-kavi', False),
 ('KAVI 3 камеры', '60 мм, 3 камеры, стенка 2,7 мм', 'Казахстан', 'Deniz, Алматы', 'розница', 2640, 3240, 3250, 'https://denizpipe.kz/g8492683-profil-kavi', False),
 ('Exprof ProWin 58', '58 мм', 'РФ', 'san102.ru, Уфа', 'розница РФ*', 962, 1078, 1174, 'https://san102.ru/good/3416.html', False),
 ('Brusbox Aero 60', '60 мм', 'РФ', 'rtk-ltd, С.-Петербург', 'РФ*', 1293, 1674, 1553, 'https://rtk-ltd.com/__profil-i-armirovanie/profil-brusbox/', False),
 ('Brusbox Termo 60', '60 мм', 'РФ', 'rtk-ltd, С.-Петербург', 'РФ*', 1699, 2334, 1812, 'https://rtk-ltd.com/__profil-i-armirovanie/profil-brusbox/', False),
]
NOPRICE = [
 ('WUKO', 'Prime 70A, Effect 70B, Evo 60B, Prime 60A', 'Казахстан (Seyco Group), филиал в Актобе', 'wuko.kz · info@seycogroup.com', 'по запросу; на сайте «скидки от 30%»'),
 ('KAVI (Kaviplast)', '3 и 4 камеры', 'Казахстан (Талгар), склад в Актобе', 'kaviplast.kz · info@kaviplast.kz', 'по запросу, заказ через WhatsApp'),
 ('Smart / Weber (Бастау Алматы)', 'SmartPRO 60 (4К), SmartTHERMO 70 (5К, стенка 3 мм), Weber 60/70', 'Казахстан, сайт для Актобе', 'akt.smartprof.kz · info@smartprof.kz', '«цена договорная»'),
 ('ASPAN', 'Aspan-70, Aspan-60, Skywin-60, Skytech-60', 'Казахстан (Шымкент)', 'okna-kz.com/aspanplast', 'по запросу'),
 ('OKNAESP', '3, 4 и 5 камер', 'Казахстан (Алматы)', 'oknaesp.kz', 'по запросу; «скидки до 40%»'),
 ('Exprof в Казахстане', 'Practica 58, ProWin, Profecta 70', 'ПМ Групп (Усть-Каменогорск, Семей)', 'plastmarket.kz/exprof', 'по запросу'),
 ('VEKA', 'Euroline 58, Softline 70/82', 'Меезенбург, VBH (Алматы)', 'm-365.kz', 'только в личном кабинете дилера'),
 ('KBE', '58 (Эталон, Engine), 70', 'Аленс, Veritum (Алматы), АКС (Атырау)', 'okna-kz.com/alens', 'по запросу'),
 ('Salamander, Rehau', '—', 'дилеров в каталоге okna-kz.com не найдено', '—', 'не найдено'),
 ('PROPLEX KZ', 'Proplex 58, 70', 'Астана', 'okna-kz.com/proplex-kz', 'по запросу'),
]

def fmt(v): return '—' if v is None else f'{v:,.0f}'.replace(',', ' ')
def pct(a, b):
    if a is None or b is None: return '<span class="eq">—</span>'
    v = (a / b - 1) * 100; cls = 'up' if v > 3 else ('dn' if v < -3 else 'eq')
    return f'<span class="{cls}">{"+" if v > 0 else "−" if v < 0 else ""}{abs(v):.0f}%</span>'

def bars(rows, title, idx, ref):
    data = sorted([(r[0].replace(' — ANESCOM', ''), r[idx], r[9]) for r in rows if r[idx] is not None], key=lambda t: t[1])
    w = 500; lab = 190; rowh = 22; mx = max(v for _, v, _ in data) * 1.15; h = 30 + rowh * len(data)
    s = f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" font-family="Inter" font-size="10"><text x="0" y="13" font-size="12" font-weight="700" fill="{DARK}">{E(title)}</text>'
    for i, (n, v, ours) in enumerate(data):
        y = 24 + i * rowh; bw = (w - lab - 60) * v / mx
        col = RED if ours else ('#E8A3A6' if 'PROPLEX' in n else ('#9CA3AF' if n.startswith(('Exprof','Brusbox')) else BLUE))
        s += f'<text x="{lab-8}" y="{y+13}" text-anchor="end" fill="{DARK}" font-weight="{700 if ours else 400}">{E(n)}</text>'
        s += f'<rect x="{lab}" y="{y+3}" width="{bw:.1f}" height="{rowh-8}" fill="{col}"/>'
        s += f'<text x="{lab+bw+5:.1f}" y="{y+13}" fill="{DARK}" font-weight="{700 if ours else 400}">{fmt(v)} ₸</text>'
    return s + '</svg>'

CSS = f"""*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Inter,sans-serif;color:{DARK}}}
.page{{width:1123px;height:794px;padding:36px 40px 34px;position:relative;overflow:hidden;background:#fff}}
.hdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {RED};padding-bottom:8px;margin-bottom:14px}}
.hdr img{{height:22px}}.hdr span{{font-size:10px;color:{GRAY}}}
.foot{{position:absolute;left:40px;right:40px;bottom:14px;display:flex;justify-content:space-between;font-size:9px;color:{GRAY}}}
h2{{font-size:20px;font-weight:800}} .lead{{font-size:11.5px;line-height:1.45;color:#374151;margin:6px 0 10px}}
table{{width:100%;border-collapse:collapse;font-size:9.4px}}
th{{background:{DARK};color:#fff;text-align:left;font-weight:600;padding:5px 5px;vertical-align:bottom}}
td{{border-bottom:1px solid {LINE};padding:4px 5px;vertical-align:top}} td.n{{text-align:right;white-space:nowrap}}
tr.our td{{background:#FDF0F0;font-weight:700}}
.up{{color:{RED};font-weight:700}}.dn{{color:{GREEN};font-weight:700}}.eq{{color:{GRAY};font-weight:700}}
.kp{{display:flex;gap:10px;margin:8px 0 12px}}.kp div{{flex:1;border:1px solid {LINE};border-left:4px solid {RED};padding:8px 10px;font-size:10.5px;color:#4B5563;line-height:1.35}}
.kp div.g{{border-left-color:{GREEN}}} .kp b{{display:block;font-size:19px;color:{DARK}}}
.cover{{width:1123px;height:794px;background:{DARK};color:#fff;padding:56px 60px;position:relative}}
.cover .bar{{position:absolute;left:0;top:0;width:12px;height:100%;background:{RED}}}
.note{{font-size:9.5px;color:{GRAY};margin-top:8px;line-height:1.4}}
ol,ul{{padding-left:18px}} li{{font-size:11px;line-height:1.5;margin-bottom:3px}}
"""
pn = [1]
def page(body):
    pn[0] += 1
    return f'<div class="page"><div class="hdr"><img src="data:image/png;base64,{LOGO}"><span>ПВХ-профиль FUNKE: ANESCOM против конкурентов · 22.10.2026</span></div>{body}<div class="foot"><span>ANESCOM · внутренний документ · наши цены — «Розница Актобе» из 1С минус авто-скидка 21,5%</span><span>{pn[0]}</span></div></div>'

def table(rows, ours):
    o = {r[0]: r for r in rows if r[9]}
    refs = [r for r in rows if r[9]]
    h = '<tr><th style="width:19%">Марка / линейка</th><th style="width:17%">Параметры</th><th style="width:7%">Страна</th><th style="width:13%">Продавец</th><th style="width:7%">Тип цены</th><th style="width:6%">Рама, ₸/м</th><th style="width:6%">Створка, ₸/м</th><th style="width:6%">Импост, ₸/м</th>' + \
        ''.join(f'<th style="width:9.5%">{E(r[0].split(" — ")[0])} к ним (рама / створка)</th>' for r in refs) + '</tr>'
    t = ''
    for r in rows:
        cmpc = ''
        for ref in refs:
            cmpc += '<td class="n">—</td>' if r[9] else f'<td class="n">{pct(ref[5], r[5])} / {pct(ref[6], r[6])}</td>'
        name = E(r[0]) if not r[8] else f'<a href="{r[8]}" style="color:inherit">{E(r[0])}</a>'
        t += f'<tr class="{"our" if r[9] else ""}"><td>{name}</td><td>{E(r[1])}</td><td>{E(r[2])}</td><td>{E(r[3])}</td><td>{E(r[4])}</td><td class="n">{fmt(r[5])}</td><td class="n">{fmt(r[6])}</td><td class="n">{fmt(r[7])}</td>{cmpc}</tr>'
    return f'<table>{h}{t}</table>'

pages = []
pages.append(f'''<div class="cover"><div class="bar"></div><img src="data:image/png;base64,{LOGOW}" style="height:36px">
<div style="margin-top:120px;font-size:13px;color:#F3B6B8;font-weight:700;letter-spacing:2px">АНАЛИЗ ЦЕН · ПВХ-ПРОФИЛЬ · 22 ОКТЯБРЯ 2026</div>
<div style="font-size:42px;font-weight:800;line-height:1.15;margin-top:12px">ПВХ-профиль FUNKE (ANESCOM)<br>против WUKO, KAVI, Smart, Exprof, Brusbox и других</div>
<p style="font-size:14px;line-height:1.55;color:#D1D5DB;margin-top:18px;max-width:860px">Основа сравнения — наш профиль FUNKE: Helios (класс 70 мм) и Bauline / Standart (класс 58–60 мм), белый, с уплотнителем. Цены за погонный метр рамы, створки и импоста; наша цена — прайс 1С «Розница Актобе» минус автоматическая скидка 21,5%. Цены конкурентов — открытые источники на 22.10.2026; у кого цена только по запросу, указано отдельно.</p></div>''')

pages.append(page(f'''<h2>Главное</h2>
<p class="lead">С автоматической скидкой 21,5% профиль FUNKE дешевле казахстанских заводов: Helios — WUKO 5 камер на 13–22%, Bauline и Standart — KAVI на 42–57%. Дешевле нас только эконом-профили: 3-камерный KALE и российский Exprof (у него не учтены доставка, таможня и НДС РК).</p>
<div class="kp"><div class="g"><b>−13…−22%</b>FUNKE Helios дешевле WUKO 5 камер (опт Deniz)</div><div class="g"><b>−18…−21%</b>Helios дешевле Brusbox Super Termo 70 (РФ)</div><div class="g"><b>−42…−57%</b>Bauline и Standart дешевле KAVI 3–4 камеры</div><div><b>+29…+72%</b>Bauline / Standart дороже Exprof ProWin 58 по цене в РФ (без доставки)</div></div>
<div style="display:flex;gap:30px">{bars(C70, "Класс 70 мм — рама, ₸ за метр", 5, None)}{bars(C60, "Класс 58–60 мм — рама, ₸ за метр", 5, None)}</div>
<p class="note">Красный — FUNKE (наша цена со скидкой); светло-красный — PROPLEX для справки; синий — казахстанские продавцы; серый — российские цены (ориентир, без доставки, таможни и НДС РК, курс 5,41 ₸/₽). Отнесение Helios к классу 70 мм, а Bauline и Standart к 58–60 мм — по нашему прайсу (соединители импоста FUNKE 58 и 70 серии); ширину профиля подтвердите. У Deniz на сайте единица «шт», хотя в названии «6,5 м»; рядом у KAVI явно «₸/м» — считаем за метр, нужно подтвердить звонком.</p>'''))

pages.append(page(f'''<h2>Класс 70 мм: рама, створка, импост за метр</h2>
<p class="lead">FUNKE Helios дешевле WUKO 5 камер на 13–22% (опт) и дешевле Brusbox Super Termo 70; дороже российских эконом-профилей (Brusbox Super Aero, Exprof Profecta) без учёта их доставки. Правая колонка: плюс — Helios дороже, минус — дешевле.</p>
{table(C70, None)}
<p class="note">* Российские цены — розница или прайс продавца без доставки, таможни и казахстанского НДС; с ними цена в Актобе обычно выше на 15–25% (наша оценка). Цены WUKO — оптовые от 6 хлыстов (розница отдельной строкой). Даты на страницах продавцов не указаны; открыты 22.10.2026.</p>'''))

pages.append(page(f'''<h2>Класс 58–60 мм: рама, створка, импост за метр</h2>
<p class="lead">FUNKE Bauline и Standart на 42–57% дешевле казахстанского KAVI. Bauline на уровне Brusbox Aero 60 и 3-камерного KALE; Standart дороже KALE на 14–38%. Российский Exprof ProWin 58 дешевле обоих (без учёта доставки и таможни).</p>
{table(C60, None)}
<p class="note">Китайский CONCH 60 (3 камеры, стенка 2,8 мм) продаёт Kali.kz (Алматы): рама 713, створка 791, импост 805 ₸ — единица на сайте не указана, в сравнение не включён. KAVI 4 камеры: рама — опт, створка — розница.</p>'''))

nt = ''.join(f'<tr><td><b>{E(a)}</b></td><td>{E(b)}</td><td>{E(c)}</td><td>{E(d)}</td><td>{E(e)}</td></tr>' for a, b, c, d, e in NOPRICE)
pages.append(page(f'''<h2>Кто не публикует цены — кому отправить запрос КП</h2>
<p class="lead">Открытых прайс-листов (PDF, Excel) за 2024–2026 годы в интернете нет ни у одного из производителей: цены дают по запросу или в кабинете дилера. Эти компании стоит включить в рассылку запроса КП от GREENTE (файл GREENTE_zapros_KP_materialy.xlsx, лист «ПВХ»).</p>
<table><tr><th style="width:16%">Марка</th><th style="width:27%">Линейки</th><th style="width:22%">Производство / дилер</th><th style="width:20%">Сайт · почта</th><th>Цена</th></tr>{nt}</table>'''))

pages.append(page(f'''<h2>Выводы и рекомендации по ПВХ (FUNKE)</h2>
<ol>
<li><b>FUNKE дешевле казахстанских заводов.</b> Helios на 13–22% дешевле WUKO 5 камер в опте, Bauline и Standart — на 42–57% дешевле KAVI. Снижать цены на FUNKE не нужно.</li>
<li><b>Helios: есть небольшой запас маржи.</b> При авто-скидке 17–18% вместо 21,5% Helios останется дешевле WUKO: рама примерно на 8%, створка на 18%.</li>
<li><b>Bauline и Standart держать со скидкой 21,5%.</b> Они конкурируют с эконом-сегментом — 3-камерным KALE, Exprof ProWin 58, китайским CONCH 60.</li>
<li><b>Против дешёвых марок продавать параметрами:</b> камеры, класс профиля, толщина стенки, армирование, наличие на складе в Актобе, сроки.</li>
<li><b>Показывать клиенту цену со скидкой.</b> По прайсу «Розница» (14 910 ₸ за хлыст рамы Helios = 2 294 ₸/м) мы выглядим дороже WUKO; реальная цена — 1 801 ₸/м.</li>
<li><b>Уточнить у Deniz (Актобе)</b> единицу цены WUKO и KAVI и разослать запрос КП: WUKO, KAVI, Smart, ASPAN, OKNAESP, Exprof (ПМ Групп), VEKA (Меезенбург), KBE (Аленс, АКС Атырау), PROPLEX KZ.</li></ol>
<p class="note" style="margin-top:14px">Источники: denizpipe.kz (WUKO, KAVI, KALE), san102.ru (Exprof), rtk-ltd.com (Brusbox), kali.kz (CONCH), okna-kz.com (каталог поставщиков), wuko.kz, kaviplast.kz, akt.smartprof.kz, oknaesp.kz, plastmarket.kz, m-365.kz — страницы открыты 22.10.2026.</p>'''))

doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>' + ''.join(pages) + '</body></html>'
open(D + 'pvc.html', 'w').write(doc)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1123, 'height': 794}, device_scale_factor=2.2)
        await pg.goto('file://' + D + 'pvc.html'); await pg.wait_for_timeout(400)
        els = await pg.query_selector_all('.page,.cover')
        for i, el in enumerate(els): await el.screenshot(path=D + f'v{i+1:02d}.png')
        await b.close(); return len(els)
n = asyncio.run(main())
from PIL import Image
ims = [Image.open(D + f'v{i:02d}.png').convert('RGB') for i in range(1, n + 1)]
ims[0].save(D + 'ANESCOM_PVH_FUNKE_sravnenie_cen_22_10_2026.pdf', save_all=True, append_images=ims[1:], resolution=200)
sh = Image.new('RGB', (561 * 3, 397 * 2), 'white')
for i, im in enumerate(ims[:6]): sh.paste(im.resize((561, 397)), ((i % 3) * 561, (i // 3) * 397))
sh.save(D + 'vsheet.png'); print('pages', n)
