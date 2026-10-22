import base64, asyncio, html
from playwright.async_api import async_playwright
D = '/tmp/claude-0/wb/'; R = '/tmp/claude-0/rep/'
E = html.escape
LOGO = base64.b64encode(open(R + 'logo_color.png', 'rb').read()).decode()
LOGOW = base64.b64encode(open(R + 'logo_white.png', 'rb').read()).decode()
RED = '#C1272D'; DARK = '#1F2328'; GRAY = '#6B7280'; LINE = '#E5E7EB'; GREEN = '#2E8B57'; BLUE = '#3B6EA8'
src = open(D + 'pdf_pvc.py').read()
CSS = eval(src[src.index('CSS = f"""') + 6: src.index('"""\npn = [1]') + 3])

def fmt(v): return '—' if v is None else f'{v:,.0f}'.replace(',', ' ')
def pct(ours, comp):
    if ours is None or comp is None: return '<span class="eq">—</span>'
    v = (ours / comp - 1) * 100; cls = 'up' if v > 3 else ('dn' if v < -3 else 'eq')
    return f'<span class="{cls}">{"+" if v > 0 else "−" if v < 0 else ""}{abs(v):.0f}%</span>'
pn = [1]
def page(body):
    pn[0] += 1
    return f'<div class="page"><div class="hdr"><img src="data:image/png;base64,{LOGO}"><span>Алюминиевый профиль ТАТПРОФ: ANESCOM против конкурентов · 22.10.2026</span></div>{body}<div class="foot"><span>ANESCOM · внутренний документ · наши цены — «Розница Актобе» из 1С минус авто-скидка 30% (профиль)</span><span>{pn[0]}</span></div></div>'

# (наша позиция, параметры, прайс, наша со скидкой, ед, [(конкурент, аналог, страна/город, цена в нашей ед., тип, url)])
PROF = [
 ('Рама окна в витраж МП-65.01.02', 'тёплая серия 65, RAL, хлыст 6 м', 57212, 40049, 'хлыст 6 м', [
   ('Deniz/Wuko', 'рама скрытой створки FV, тёплая, RAL 7024', 'Казахстан (Алматы)', 36036, 'опт от 100 м', 'https://satu.kz/p105916694-alyuminievaya-rama-skrytoj.html'),
   ('Комплект-Плюс', 'ТАТПРОФ W65.01.02 — тот же профиль', 'РФ (Екатеринбург)', 50352, 'дилер ТАТПРОФ, без доставки', 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')]),
 ('Створка окна МП-65.04.02', 'тёплая серия 65, RAL, хлыст 6 м', 72178, 50525, 'хлыст 6 м', [
   ('Deniz/Wuko', 'створка скрытая FV, тёплая, RAL 7024', 'Казахстан (Алматы)', 49176, 'опт', 'https://satu.kz/p105916699-alyuminievaya-stvorka-skrytaya.html'),
   ('Deniz/Wuko', 'створка FV СТ-63, RAL 7021', 'Казахстан (Алматы)', 43188, 'опт', 'https://satu.kz/p106004671-alyuminievyj-profil-okonnoj.html'),
   ('Комплект-Плюс', 'ТАТПРОФ W65.02.05 — тот же профиль', 'РФ', 56532, 'дилер, без доставки', 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')]),
 ('Створка окна МП-45.04.03', 'холодная серия 45, RAL 7024, хлыст 6 м', 36525, 25568, 'хлыст 6 м', [
   ('Deniz/Wuko', 'створка FV CX-45, холодная, RAL 7024', 'Казахстан (Алматы)', 33900, 'опт', 'https://satu.kz/p106002481-alyuminievyj-profil-okonnoj.html'),
   ('КазПерСтрой (АЛЮТЕХ)', 'ALT-111 створка перегородки, анод. (слабый аналог)', 'Казахстан (Алматы)', 46095, 'розница', 'https://kazperstroy.kz/catalogue/cat/profil-alyutekh/')]),
 ('Створка двери МП-65.02.05', 'тёплая серия 65, за метр', 13154, 9208, 'м', [
   ('КазПерСтрой (АЛЮТЕХ)', '111.0106M, холодная, анод. (слабый аналог)', 'Казахстан (Алматы)', 9755, 'розница', 'https://kazperstroy.kz/catalogue/show/profil-usilennoj-stvorki-1110106m/')]),
 ('Доп. профиль МП-45.07.15', 'серия 45, окрашенный, хлыст 6 м', 8196, 5737, 'хлыст 6 м', [
   ('Комплект-Плюс', 'W45.06.03 без покраски', 'РФ', 6271, 'дилер, без доставки', 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')]),
 ('Закладная МП-5013Н L80', 'фасад 50, шт', 817, 572, 'шт', [
   ('Комплект-Плюс', 'F50.08.01, цена метра × 0,08', 'РФ', 359, 'расчёт, без резки', 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')]),
 ('Закладная МП-5013-02H L80', 'фасад 50, шт', 1010, 707, 'шт', [
   ('Комплект-Плюс', 'F50.08.03, цена метра × 0,08', 'РФ', 473, 'расчёт, без резки', 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')]),
]
ACC = [
 ('Уплотнитель ригельный ТПУ-6001', 446, 'м', 'ТехноКомплект-KZ, Астана', 'ТПУ-6001 СИАЛ/КраМЗ, ТЭП', 70, 'https://tk-kz.satu.kz/p69364383-uplotnitel-rigelya-tpu.html'),
 ('Уплотнитель стоечный ТПУ-6002', 1008, 'м', 'ТехноКомплект-KZ, Астана', 'ТПУ-6002 СИАЛ/КраМЗ, ТЭП', 136, 'https://tk-kz.satu.kz/p69364385-uplotnitel-stojki-tpu.html'),
 ('Подставка под стеклопакет F50.05.02 L100', 270, 'шт', 'Комплект-Плюс, РФ', 'F50.05.02 — та же', 223, 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/'),
 ('Подставка под стеклопакет F50.05.02 L100', 270, 'шт', 'КазПерСтрой, Алматы', 'АЛЮТЕХ ABS 115.0902', 298, 'https://kazperstroy.kz/catalogue/cat/profil-alyutekh/'),
 ('Уплотнитель притвора ТПУ-65.01 (серия 65)', None, 'м', 'ТехноКомплект-KZ, Астана', 'ТПУ-65.01 ТАТПРОФ', 127, 'https://satu.kz/search?search_term=ТПУ-65.01'),
]
READY = [
 ('UniFrame, Алматы', 'алюминиевые окна', 'от 35 000 ₸/м²', 'https://uniframe.kz/p88546365-alyuminievye-okna.html'),
 ('UniFrame, Алматы', 'фасад ФА 120С', 'от 75 000 ₸/м² (от 100 м² — 65 000)', 'https://uniframe.kz/p88546350-fasad-alyuminievogo-profilya.html'),
 ('UniFrame, Алматы', 'раздвижные двери, серия 65', 'от 110 000 ₸/м²', 'https://uniframe.kz/p88546344-razdvizhnye-alyuminievye-dveri.html'),
 ('UniFrame, Алматы', 'дверь одностворчатая, тёплая 65', 'от 180 000 ₸ (ед. не указана)', 'https://uniframe.kz/p88582677-alyuminievye-dveri-odnostvorchatye.html'),
 ('UniFrame, Алматы', 'входная группа, тёплая 65', 'от 350 000 ₸ (ед. не указана)', 'https://uniframe.kz/p88582659-vhodnaya-gruppa-alyuminievogo.html'),
 ('Фасад Плюс (satu.kz)', 'алюминиевые окна', '70 000 ₸/м²', 'https://satu.kz'),
 ('Фасад Плюс (satu.kz)', 'алюминиевые двери / раздвижные окна', '120 000 ₸/м²', 'https://satu.kz'),
 ('National Windows (satu.kz)', 'дверь 2000×900, холодная серия 45', 'от 130 000 ₸', 'https://satu.kz'),
 ('Bioclimatic (satu.kz)', 'профиль и комплектация для слайдинга', '5 000 ₸/кг', 'https://satu.kz'),
]
NOPRICE = [
 ('Alprof', 'завод: оконные, дверные, фасадные, раздвижные системы (ALP W72, W62, C40, C48, F50); ISO 9001', 'Алматы; Астана, Шымкент, Атырау', 'alprof.kz', 'расчёт под заказчика; дилер FIX MASTER — «1 ₸»'),
 ('ALUPROF Company', 'изготовление и монтаж: витражи, окна, двери (тёплый/холодный профиль)', 'Уральск; ЗКО, Атырау, Актау, Актобе', 'aluprof-company.kz', 'по заявке'),
 ('THERMINAL', 'готовые изделия: VIKING 90, HS110, VISION 50, Hi-Therm, Pivot, HG73', 'Алматы, Астана, Шымкент, Тараз', 'therminal.kz', '«Узнать цену»'),
 ('Alcon', 'в основном окна ПВХ, алюминий — дополнительно', 'Астана', 'alcon.kz', 'нет цен на алюминий'),
 ('TdZangar', 'окна, двери, витражи, фасады, смарт-системы', 'Алматы', 'tdzangar.kz', 'по заявке, предоплата 70%'),
 ('ТехноКомплект-KZ', 'системы СИАЛ КП45, КП50, КПТ60/70/74; «тёплая» АПК02', 'Астана', 'tk-kz.satu.kz', '«Цену уточняйте»'),
 ('КазПерСтрой (АЛЮТЕХ)', 'дилер АЛЮТЕХ; цены открыты в основном на перегородочные системы', 'Алматы', 'kazperstroy.kz', 'частично открыты'),
]

pages = []
pages.append(f'''<div class="cover"><div class="bar"></div><img src="data:image/png;base64,{LOGOW}" style="height:36px">
<div style="margin-top:120px;font-size:13px;color:#F3B6B8;font-weight:700;letter-spacing:2px">АНАЛИЗ ЦЕН · АЛЮМИНИЙ · 22 ОКТЯБРЯ 2026</div>
<div style="font-size:42px;font-weight:800;line-height:1.15;margin-top:12px">Алюминиевый профиль ТАТПРОФ (ANESCOM)<br>против FV/Wuko, АЛЮТЕХ, СИАЛ и рынка</div>
<p style="font-size:14px;line-height:1.55;color:#D1D5DB;margin-top:18px;max-width:880px">Наша цена — прайс 1С «Розница Актобе» минус автоматическая скидка 30% на алюминиевый профиль. Сравнение с тем же ТАТПРОФ у дилера в России и с аналогами той же серии (тёплая 65, холодная 45, фасад 50) у продавцов в Казахстане. Отдельно — цены рынка на готовые алюминиевые конструкции (для GREENTE) и список компаний, которые дают цену только по запросу.</p></div>''')

def bars():
    items = [('Рама 65 тёплая', 40049 / 6, [('ТАТПРОФ, дилер РФ', 50352 / 6), ('FV тёплая (Deniz)', 36036 / 6)]),
             ('Створка 65 тёплая', 50525 / 6, [('ТАТПРОФ, дилер РФ', 56532 / 6), ('FV тёплая (Deniz)', 49176 / 6), ('FV СТ-63 (Deniz)', 43188 / 6)]),
             ('Створка 45 холодная', 25568 / 6, [('FV CX-45 (Deniz)', 33900 / 6)])]
    w = 1040; lab = 230; rowh = 20; mx = 9800; y = 26
    s = f'<svg width="{w}" height="300" xmlns="http://www.w3.org/2000/svg" font-family="Inter" font-size="10"><text x="0" y="13" font-size="12" font-weight="700" fill="{DARK}">Цена за метр, ₸ (наша — со скидкой 30%)</text>'
    for grp, ours, comps in items:
        s += f'<text x="0" y="{y+13}" font-weight="700" fill="{DARK}">{E(grp)}</text>'; y += 18
        for n, v, col in [('ANESCOM (ТАТПРОФ)', ours, RED)] + [(a, b, '#9CA3AF' if 'РФ' in a else BLUE) for a, b in comps]:
            bw = (w - lab - 80) * v / mx
            s += f'<text x="{lab-8}" y="{y+12}" text-anchor="end" fill="{DARK}" font-weight="{700 if col==RED else 400}">{E(n)}</text><rect x="{lab}" y="{y+2}" width="{bw:.1f}" height="{rowh-7}" fill="{col}"/><text x="{lab+bw+5:.1f}" y="{y+12}" fill="{DARK}" font-weight="{700 if col==RED else 400}">{fmt(v)} ₸</text>'
            y += rowh
        y += 6
    return s.replace('height="300"', f'height="{y+4}"') + '</svg>'

pages.append(page(f'''<h2>Главное</h2>
<p class="lead">С автоматической скидкой 30% профиль ТАТПРОФ у нас дешевле, чем тот же ТАТПРОФ у дилера в России (даже без учёта доставки и таможни), а холодная серия 45 — дешевле казахстанского аналога FV. Тёплая серия 65 — на уровне или немного дороже тёплого FV. Переплата — фасадные закладные и уплотнители ТПУ.</p>
<div class="kp"><div class="g"><b>−11…−20%</b>тёплая серия 65 дешевле того же ТАТПРОФ у дилера в РФ</div><div class="g"><b>−25%</b>холодная створка 45 дешевле FV CX-45 (Deniz)</div><div><b>+3…+17%</b>тёплая серия 65 к тёплым FV (Deniz, опт)</div><div><b>+49…+59%</b>закладные фасада L80; уплотнители ТПУ — в 6–7 раз</div></div>
{bars()}
<p class="note">Красный — ANESCOM (прайс минус 30%); синий — казахстанский продавец (Deniz/Wuko, профиль FV, опт от 100 м); серый — ТАТПРОФ у дилера в России (ориентир без доставки, таможни и НДС РК, курс 5,41 ₸/₽ НБРК на 19.10.2026).</p>'''))

rows = ''
for name, par, price, net, unit, comps in PROF:
    first = True
    for c in comps:
        rows += '<tr' + (' class="our"' if False else '') + '>' + (f'<td rowspan="{len(comps)}"><b>{E(name)}</b><br><span style="color:{GRAY}">{E(par)}</span></td><td rowspan="{len(comps)}" class="n">{fmt(price)}</td><td rowspan="{len(comps)}" class="n"><b>{fmt(net)}</b></td><td rowspan="{len(comps)}">{E(unit)}</td>' if first else '') + \
            f'<td><a href="{c[5]}" style="color:inherit">{E(c[0])}</a></td><td>{E(c[1])}</td><td>{E(c[2])}</td><td>{E(c[4])}</td><td class="n">{fmt(c[3])}</td><td class="n">{pct(net, c[3])}</td></tr>'
        first = False
pages.append(page(f'''<h2>Профиль: наша цена со скидкой против аналогов</h2>
<p class="lead">Разница — (наша цена со скидкой − цена конкурента) / цена конкурента; плюс — мы дороже. Открытых казахстанских цен на сам ТАТПРОФ нет; ближайшие сравнимые — профиль FV (Deniz/Wuko) той же серии и ТАТПРОФ у российского дилера.</p>
<table><tr><th style="width:19%">Наша позиция</th><th style="width:6%">Прайс, ₸</th><th style="width:7%">Наша со скидкой 30%, ₸</th><th style="width:5%">Ед.</th><th style="width:11%">Конкурент</th><th style="width:21%">Аналог, параметры</th><th style="width:10%">Страна / город</th><th style="width:9%">Тип цены</th><th style="width:6%">Цена, ₸</th><th style="width:6%">Разница</th></tr>{rows}</table>'''))

arows = ''.join(f'<tr><td>{E(a)}</td><td class="n">{fmt(b)}</td><td>{E(c)}</td><td><a href="{g}" style="color:inherit">{E(d)}</a></td><td>{E(e)}</td><td class="n">{fmt(f)}</td><td class="n">{pct(b, f)}</td></tr>' for a, b, c, d, e, f, g in ACC)
rrows = ''.join(f'<tr><td>{E(a)}</td><td>{E(b)}</td><td class="n">{E(c)}</td></tr>' for a, b, c, d in READY)
pages.append(page(f'''<h2>Комплектующие и цены рынка на готовые конструкции</h2>
<p class="lead">Комплектующие ТАТПРОФ считаются без скидки 30% (по нашему прайсу скидка — на профиль). Уплотнители ТПУ-6001/6002 у нас в 6–7 раз дороже того же кода у ТехноКомплект — вероятная ошибка единицы в 1С.</p>
<table><tr><th style="width:27%">Наша позиция</th><th style="width:8%">Наша, ₸</th><th style="width:5%">Ед.</th><th style="width:20%">Конкурент</th><th style="width:24%">Аналог</th><th style="width:8%">Цена, ₸</th><th style="width:8%">Разница</th></tr>{arows}</table>
<h3 style="font-size:13px;margin:16px 0 6px">Готовые алюминиевые конструкции — ориентир для GREENTE</h3>
<table><tr><th style="width:28%">Компания</th><th style="width:44%">Изделие</th><th>Цена</th></tr>{rrows}</table>
<p class="note">Цены готовых изделий — «от», без уточнения, входят ли стеклопакет, фурнитура и монтаж; даты на страницах не указаны (открыты 22.10.2026).</p>'''))

nrows = ''.join(f'<tr><td><b>{E(a)}</b></td><td>{E(b)}</td><td>{E(c)}</td><td>{E(d)}</td><td>{E(e)}</td></tr>' for a, b, c, d, e in NOPRICE)
pages.append(page(f'''<h2>Кто не публикует цены — кому отправить запрос КП</h2>
<p class="lead">Открытых прайс-листов (PDF, Excel) на алюминиевый профиль в Казахстане за 2024–2026 годы не найдено ни у одной компании. Профиль как материал из списка продаёт только Alprof (завод) и дилеры систем (ТехноКомплект — СИАЛ, КазПерСтрой — АЛЮТЕХ, Deniz — FV); остальные делают и монтируют готовые конструкции.</p>
<table><tr><th style="width:15%">Компания</th><th style="width:37%">Что продаёт</th><th style="width:20%">Город</th><th style="width:13%">Сайт</th><th>Цена</th></tr>{nrows}</table>'''))

pages.append(page(f'''<h2>Выводы и рекомендации по алюминию</h2>
<ol>
<li><b>Скидку 30% на профиль сохранить.</b> С ней ТАТПРОФ у нас дешевле, чем у российского дилера, холодная серия 45 дешевле FV на 25%, тёплая 65 — на уровне тёплого FV (+3…+17%).</li>
<li><b>Тёплая серия 65 — главный конкурент FV (Deniz/Wuko).</b> Разница 3–17% оправдывается брендом ТАТПРОФ, полнотой системы и наличием в Актобе; продавать через надёжность и сроки, не через цену.</li>
<li><b>Пересчитать фасадные закладные L80</b> от цены метра + резка: сейчас 572–707 ₸ со скидкой против расчётных 360–470 ₸.</li>
<li><b>Исправить цены уплотнителей ТПУ-6001 / ТПУ-6002</b> (446 и 1 008 ₸/м против 70 и 136 ₸/м у ТехноКомплект) и уточнить, действует ли на комплектующие ТАТПРОФ скидка 30%.</li>
<li><b>Показывать клиенту цену со скидкой:</b> по прайсу «Розница» (57 212 ₸ за раму МП-65) мы выглядим дороже FV; реальная цена — 40 049 ₸.</li>
<li><b>Запросить КП</b> у Alprof (завод, есть в Атырау), ТехноКомплект-KZ (СИАЛ), КазПерСтрой (АЛЮТЕХ), Deniz (FV, есть в Актобе) — по сериям 45, 65 и фасаду 50; ALUPROF Company и THERMINAL — по готовым изделиям для сравнения с GREENTE.</li></ol>
<p class="note" style="margin-top:14px">Источники: satu.kz (Deniz/Wuko FV, ТехноКомплект-KZ, Фасад Плюс, National Windows, Bioclimatic), komplekt-plus.ru (ТАТПРОФ), kazperstroy.kz (АЛЮТЕХ), uniframe.kz, alprof.kz, aluprof-company.kz, therminal.kz, alcon.kz, tdzangar.kz, fixmaster.kz — открыты 22.10.2026.</p>'''))

doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>' + ''.join(pages) + '</body></html>'
open(D + 'alu.html', 'w').write(doc)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1123, 'height': 794}, device_scale_factor=2.2)
        await pg.goto('file://' + D + 'alu.html'); await pg.wait_for_timeout(400)
        els = await pg.query_selector_all('.page,.cover')
        for i, el in enumerate(els): await el.screenshot(path=D + f'a{i+1:02d}.png')
        await b.close(); return len(els)
n = asyncio.run(main())
from PIL import Image
ims = [Image.open(D + f'a{i:02d}.png').convert('RGB') for i in range(1, n + 1)]
ims[0].save(D + 'ANESCOM_ALU_TATPROF_sravnenie_cen_22_10_2026.pdf', save_all=True, append_images=ims[1:], resolution=200)
sh = Image.new('RGB', (561 * 3, 397 * 2), 'white')
for i, im in enumerate(ims[:6]): sh.paste(im.resize((561, 397)), ((i % 3) * 561, (i // 3) * 397))
sh.save(D + 'asheet.png'); print('pages', n)
