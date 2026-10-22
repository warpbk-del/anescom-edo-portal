import json, re, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

it = json.load(open('/tmp/claude-0/price_items.json'))
excl = re.compile(r'фреза|фрез|шаблон|цулаг|бита|сверл|перчатк|станок|диск |нож |пила|кондуктор|брак|инструмент|неликвид', re.I)
FURN = r'петл|ручк|привод|замок|запор|ножниц|угловой перекл|цапф|ответн|фиксатор|доводчик|шпингалет|ограничит|KALE|ROTO|SIEGENIA|VORNE|AXOR|навес|микролифт|декор накл'
PROF = r'(профил|рама|створк|импост|стойк|ригел|закладн|сухар|штапик|штульп|порог|отлив|подоконник|армир|эркер|расширит|доборн|труба|адаптер|полурам|крышк|переходник)'
ALU = r'ТАТПРОФ|TATPROF|МП-|МП |F50\.|W50\.|W45|W65|КП-|алюмин'
CATS = ['ПВХ', 'Алюминий', 'Комплектующие', 'Фурнитура']
out = collections.OrderedDict((k, []) for k in CATS)
for x in it:
    n = x['name']
    if not x['aktobe'] or excl.search(n): continue
    if re.search(FURN, n, re.I) and not re.search(r'уплотнит|профил', n, re.I): k = 'Фурнитура'
    elif re.search(PROF, n, re.I) and re.search(ALU, n, re.I) and not re.search(r'уплотнит|винт|шуруп|подставк|пластин', n, re.I): k = 'Алюминий'
    elif re.search(PROF, n, re.I) and not re.search(r'уплотнит|винт|шуруп|подставк|соединит', n, re.I): k = 'ПВХ'
    else: k = 'Комплектующие'
    out[k].append(x)

U = lambda u: u
COMP = {  # must-key -> competitor rows: (продавец, город, аналог/параметры, страна, цена в нашей ед., ссылка)
 'Рама оконная 70мм PROPLEX HIT': [('Deniz/WUKO', 'Алматы', 'WUKO 5К, 70 мм, класс А (опт)', 'KZ', 2440, 'https://denizpipe.kz/p105601255-profil-kamernyj-tsvet.html'), ('rtk-ltd', 'РФ', 'Brusbox 70 (ориентир)', 'РФ', 2215, 'https://rtk-ltd.com/__profil-i-armirovanie/profil-brusbox/super-termo-706/'), ('Deniz', 'Алматы', 'KALE 3К (опт)', '—', 1344, 'https://denizpipe.kz/g8505296-profil-kale')],
 'Створка 70мм PROPLEX HIT': [('Deniz/WUKO', 'Алматы', 'WUKO 5К (опт)', 'KZ', 2670, 'https://denizpipe.kz/g8491085-profil-wuko'), ('Deniz', 'Алматы', 'KAVI 4К (опт)', 'KZ', 3545, 'https://denizpipe.kz/g8492683-profil-kavi'), ('Deniz', 'Алматы', 'KALE 3К (опт)', '—', 1344, 'https://denizpipe.kz/g8505296-profil-kale')],
 'Импост 70мм PROPLEX HIT': [('Deniz/WUKO', 'Алматы', 'WUKO 5К (опт)', 'KZ', 2675, 'https://denizpipe.kz/g8491085-profil-wuko'), ('Deniz', 'Алматы', 'KAVI 3К (опт)', 'KZ', 3250, 'https://denizpipe.kz/g8492683-profil-kavi'), ('rtk-ltd', 'РФ', 'Brusbox T86 (ориентир)', 'РФ', 2459, 'https://rtk-ltd.com/__profil-i-armirovanie/')],
 'Рама 63мм Bauline с сер упл бел': [('Deniz', 'Алматы', 'KALE 3К, хлыст 6,5 м (опт)', '—', 8736, 'https://denizpipe.kz/g8505296-profil-kale'), ('rtk-ltd', 'РФ', 'Brusbox 60, хлыст (ориентир)', 'РФ', 11042, 'https://rtk-ltd.com/__profil-i-armirovanie/'), ('Deniz', 'Алматы', 'KAVI 3К, хлыст (опт)', 'KZ', 17160, 'https://denizpipe.kz/g8492683-profil-kavi')],
 'Створка 77мм Bauline с 2 сер упл бел': [('Deniz', 'Алматы', 'KALE 3К, хлыст (опт)', '—', 8736, 'https://denizpipe.kz/g8505296-profil-kale'), ('rtk-ltd', 'РФ', 'Brusbox 60 Z60, хлыст', 'РФ', 15174, 'https://rtk-ltd.com/__profil-i-armirovanie/'), ('Deniz', 'Алматы', 'KAVI 3К, хлыст (опт)', 'KZ', 21060, 'https://denizpipe.kz/g8492683-profil-kavi')],
 'Рама 63мм Helios с 1 сер упл бел': [('Deniz/WUKO', 'Алматы', 'WUKO 5К, хлыст (опт)', 'KZ', 15860, 'https://denizpipe.kz/g8491085-profil-wuko'), ('rtk-ltd', 'РФ', 'Brusbox 70, хлыст', 'РФ', 14400, 'https://rtk-ltd.com/__profil-i-armirovanie/'), ('Deniz', 'Алматы', 'KAVI 4К, хлыст (опт)', 'KZ', 18590, 'https://denizpipe.kz/g8492683-profil-kavi')],
 'Створка 77мм Helios с 2 сер упл бел': [('Deniz/WUKO', 'Алматы', 'WUKO 5К, хлыст (опт)', 'KZ', 17355, 'https://denizpipe.kz/g8491085-profil-wuko'), ('rtk-ltd', 'РФ', 'Brusbox 70, хлыст', 'РФ', 16299, 'https://rtk-ltd.com/__profil-i-armirovanie/'), ('Deniz', 'Алматы', 'KAVI 4К, хлыст (опт)', 'KZ', 23043, 'https://denizpipe.kz/g8492683-profil-kavi')],
 'Импост 82мм Helios с 2 сер упл бел': [('Deniz/WUKO', 'Алматы', 'WUKO 5К, хлыст (опт)', 'KZ', 17388, 'https://denizpipe.kz/g8491085-profil-wuko'), ('rtk-ltd', 'РФ', 'Brusbox T86, хлыст', 'РФ', 15982, 'https://rtk-ltd.com/__profil-i-armirovanie/'), ('Deniz', 'Алматы', 'KAVI 3К, хлыст (опт)', 'KZ', 21125, 'https://denizpipe.kz/g8492683-profil-kavi')],
 'армирующий 1,5мм 207': [('rtk-ltd', 'РФ', '35×28×1,4 мм (ориентир)', 'РФ', 695, 'https://rtk-ltd.com/__profil-i-armirovanie/armirovanie/')],
 'армирующий 1,2мм 604': [('rtk-ltd', 'РФ', '35×20×1,2 мм (ориентир)', 'РФ', 541, 'https://rtk-ltd.com/__profil-i-armirovanie/armirovanie/')],
 'Штапик 14мм с сер': [('Deniz/WUKO', 'Алматы', 'Штапик WUKO, хлыст', 'KZ', 3315, 'https://denizpipe.kz/g8491085-profil-wuko'), ('Deniz', 'Алматы', 'Штапик KAVI, хлыст', 'KZ', 2691, 'https://denizpipe.kz/g8492683-profil-kavi'), ('Deniz', 'Алматы', 'Штапик KALE, хлыст', '—', 2620, 'https://denizpipe.kz/g8505296-profil-kale')],
 'Подоконник PROPLEX 300': [('Deniz', 'Алматы', 'KAVI 300 золотой дуб (опт)', 'KZ', 1161, 'https://denizpipe.kz/g8489028-podokonniki-kavi'), ('Аквилон', 'Павлодар', '300 мм белый', '—', 2825, 'https://akvilon.kz/c/podokonniki-pvkh/')],
 'МП-65.01.02': [('Deniz/Wuko', 'Алматы', 'FV рама скрытой створки, тёплая, хлыст 6 м', '—', 36036, 'https://satu.kz/p105916694-alyuminievaya-rama-skrytoj.html'), ('Комплект-Плюс', 'РФ', 'ТАТПРОФ W65.01.02 (тот же), хлыст', 'РФ', 50352, 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')],
 'МП-65.04.02': [('Deniz/Wuko', 'Алматы', 'FV створка скрытая, тёплая, хлыст', '—', 49176, 'https://satu.kz/p105916699-alyuminievaya-stvorka-skrytaya.html'), ('Комплект-Плюс', 'РФ', 'ТАТПРОФ W65.02.05 (тот же), хлыст', 'РФ', 56532, 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')],
 'МП-45.04.03': [('Deniz/Wuko', 'Алматы', 'FV CX-45 холодная, RAL 7024, хлыст', '—', 33900, 'https://satu.kz/p106002481-alyuminievyj-profil-okonnoj.html')],
 'МП-65.02.05': [('КазПерСтрой', 'Алматы', 'ALUTECH 111.0106M, холодная (слабый аналог), м', '—', 9755, 'https://kazperstroy.kz/catalogue/show/profil-usilennoj-stvorki-1110106m/')],
 'МП-45.07.15': [('Комплект-Плюс', 'РФ', 'W45.06.03 без покраски, хлыст', 'РФ', 6271, 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')],
 'МП-5013Н L 80': [('Комплект-Плюс', 'РФ', 'F50.08.01, цена м × 0,08', 'РФ', 359, 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')],
 'МП-5013-02H L 80': [('Комплект-Плюс', 'РФ', 'F50.08.03, цена м × 0,08', 'РФ', 473, 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')],
 'ТПУ-6001': [('ТехноКомплект-KZ', 'Астана', 'ТПУ-6001 СИАЛ/КраМЗ, ТЭП', 'РФ', 70, 'https://tk-kz.satu.kz/p69364383-uplotnitel-rigelya-tpu.html')],
 'ТПУ-6002': [('ТехноКомплект-KZ', 'Астана', 'ТПУ-6002 СИАЛ/КраМЗ, ТЭП', 'РФ', 136, 'https://tk-kz.satu.kz/p69364385-uplotnitel-stojki-tpu.html')],
 'F50.05.02': [('Комплект-Плюс', 'РФ', 'F50.05.02 (та же)', 'РФ', 223, 'https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/'), ('КазПерСтрой', 'Алматы', 'ALUTECH ABS 115.0902', '—', 298, 'https://kazperstroy.kz/catalogue/cat/profil-alyutekh/')],
 'КВЕ-254 серый': [('torgbest', 'РФ', 'KBE 255 серый', 'РФ', 114, 'https://torgbest.ru/uplotnitel-dlya-plastikovykh-okon')],
 'TYTAN': [('Kaspi (Актобе)', 'Актобе', 'TYTAN 70 870 мл (та же), мин–макс 3 490–5 100', '—', 3490, 'https://kaspi.kz/shop/search/?text=пена монтажная Tytan 70'), ('Turan Stroy', '—', 'TYTAN 70 870 мл (та же)', '—', 4000, 'https://satu.kz/p99241278'), ('TRADE CK', 'Алматы', 'PROFPUR Mega 65, 870 мл', 'Беларусь', 2200, 'https://satu.kz/p47181798')],
 'Герметик А+В': [('AVplus', 'Шымкент', 'Qaraseal тиоколовый 2К, за кг', '—', 818, 'https://satu.kz/p123266833')],
 'Анкер 7,5': [('Отвёртка.kz', 'Алматы', 'STARFIX 8×132', 'Китай', 66, 'https://otvertka.kz/product/starfix-smp-70538-1')],
 'есо (9016)': [('Winnova', 'Алматы', 'Fores 75, цинк', 'KZ', 575, 'https://satu.kz/p128345976'), ('ProfiMart', 'Астана', '75 мм, алюминий, 120 кг', 'Китай', 280, 'https://satu.kz/p132578153'), ('Kaspi (Актобе)', 'Актобе', 'Навес 75×15 мм', '—', 295, 'https://kaspi.kz/shop/search/?text=петля оконная 75 мм')],
 '100мм FS': [('Winnova', 'Алматы', 'Fores 100, цинк', 'KZ', 897, 'https://satu.kz/p128345965'), ('ProfiMart', 'Астана', '95 мм, алюминий', 'Китай', 360, 'https://satu.kz/p132849858')],
 '1-11115-09': [('Deniz/Wuko', 'Алматы', 'Vorne ОС-ПВР 15.5', 'Турция', 1234, 'https://denizpipe.kz/p106893807')],
 'ALFA': [('Winnova', 'Алматы', 'ALFA (та же)', '—', 920, 'https://satu.kz/p128346177'), ('ProfiMart', 'Астана', 'Lara, алюминий', 'Китай', 850, 'https://satu.kz/p132591435'), ('Kaspi (Актобе)', 'Актобе', 'Fores ALFA (проверить материал)', 'KZ', 400, 'https://kaspi.kz/shop/search/?text=ручка для пластиковой двери')],
 'пласт L50': [('ProfiMart', 'Астана', 'MEGA коричневая', '—', 410, 'https://satu.kz/p132871269')],
 'MEGA 35/85': [('ProfiMart', 'Астана', 'WC 85×35, металлопластик', 'Китай', 1950, 'https://satu.kz/p132591473')],
 'моск сетки полукруг белая': [('R&A Partners', '—', 'STARFIX', 'РФ', 28, 'https://satu.kz/p127976716'), ('Аквилон', 'Павлодар', 'Ручка-кольцо', 'РФ', 35, 'https://akvilon.kz/p/ruchka-koltso-dlya-moskitnoy-setki/')],
}
MUST = {'ПВХ': ['Рама оконная 70мм PROPLEX HIT', 'Створка 70мм PROPLEX HIT', 'Импост 70мм PROPLEX HIT', 'Рама 63мм Bauline с сер упл бел', 'Створка 77мм Bauline с 2 сер упл бел', 'Рама 63мм Helios с 1 сер упл бел', 'Створка 77мм Helios с 2 сер упл бел', 'Импост 82мм Helios с 2 сер упл бел', 'армирующий 1,5мм 207', 'армирующий 1,2мм 604', 'Штапик 14мм с сер', 'Подоконник PROPLEX 300', 'Отлив экструзионный'],
        'Алюминий': ['МП-65.01.02', 'МП-65.04.02', 'МП-45.04.03', 'МП-65.02.05', 'МП-45.07.15', 'МП-5013Н L 80', 'МП-5013-02H L 80', 'W50.12.02'],
        'Комплектующие': ['ТПУ-6001', 'ТПУ-6002', 'F50.05.02', 'КВЕ-254 серый', 'TYTAN', 'Герметик А+В', 'Анкер 7,5'],
        'Фурнитура': ['есо (9016)', '100мм FS', '1-11601-00', '1-11115-09', 'ALFA', 'пласт L50', 'MEGA 35/85', 'СТН-0611', 'WINDORPRO', 'моск сетки полукруг белая', 'Ограничитель открывания']}
MUSTRE = {'МП-65.01.02': r'^Рама окна в витраж МП-65.01.02', 'МП-65.04.02': r'^Створка окна МП-65.04.02', 'МП-45.04.03': r'^Створка окна МП-45.04.03',
          'МП-65.02.05': r'^Створка двери открывание внутрь МП-65.02.05', 'МП-45.07.15': r'^Доп профиль для витражей МП-45.07.15',
          'МП-5013Н L 80': r'^Закладная крепления стоек МП-5013Н L 80', 'МП-5013-02H L 80': r'^Закладная стойки МП-5013-02H L 80',
          'W50.12.02': r'Профиль полурамы W50.12.02', 'TYTAN': r'Пена.*TYTAN 70'}
def key(n): return re.sub(r'\(.*?\)|бел\w*|корич\w*|антрацит.*|темн\w*|золот\w*|махагон\w*|дуб\w*|сер\w*|чер\w*|орех\w*|\d{4}', '', n.lower())
sel = {}
for k in CATS:
    v = sorted(out[k], key=lambda x: -(x['stock'] or 0))
    chosen, keys = [], set()
    for m in MUST[k]:
        for x in v:
            if re.search(MUSTRE.get(m, re.escape(m)), x['name']) and x not in chosen:
                x = dict(x); x['must'] = m; chosen.append(x); keys.add(key(x['name'])); break
    for x in v:
        if len(chosen) >= 45: break
        if key(x['name']) in keys: continue
        chosen.append(dict(x)); keys.add(key(x['name']))
    sel[k] = chosen

def unit(n):
    m = re.search(r',\s*([^,]+)$', n); return m.group(1).strip() if m else ''
def clean(n): return re.sub(r',\s*[^,]+$', '', n).strip()

F = 'Arial'
HDR = PatternFill('solid', fgColor='1F2328'); RED = PatternFill('solid', fgColor='C1272D')
YEL = PatternFill('solid', fgColor='FFF4C2'); GRY = PatternFill('solid', fgColor='F3F4F6')
thin = Side(style='thin', color='D1D5DB'); BRD = Border(left=thin, right=thin, top=thin, bottom=thin)
def hdr(ws, row, cols, widths):
    for i, (c, w) in enumerate(zip(cols, widths), 1):
        cell = ws.cell(row=row, column=i, value=c)
        cell.font = Font(name=F, bold=True, color='FFFFFF', size=10); cell.fill = HDR
        cell.alignment = Alignment(wrap_text=True, vertical='center'); cell.border = BRD
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 32

# ---------- internal comparison ----------
wb = Workbook(); ws0 = wb.active; ws0.title = 'Как читать'
lines = ['ANESCOM — сравнение цен с конкурентами (внутренний файл, НЕ отправлять конкурентам)',
         'Наша цена — «Розница Актобе-18» с НДС из 1С на 22.10.2026. Остаток — сумма по складам из того же отчёта.',
         'Колонки «Конкурент 1–3» заполнены там, где цена найдена в открытом доступе (сайты, satu.kz, Kaspi) 22.10.2026; ссылки в колонке «Источник».',
         'Жёлтые ячейки — для ввода цен из полученных КП. Разница считается от нашей цены СО СКИДКОЙ: (наша со скидкой − конкурент) / конкурент; плюс = мы дороже.',
         'Цены WUKO, KAVI, KALE — оптовые; российские (РФ) — ориентир без доставки и таможни, курс 5,41 ₸/₽ (НБРК 19.10.2026).',
         'Пример строки: «Рама оконная 70мм PROPLEX HIT» на листе ПВХ.']
for i, t in enumerate(lines, 1):
    c = ws0.cell(row=i, column=1, value=t); c.font = Font(name=F, size=11, bold=(i == 1), color='C1272D' if i == 1 else '1F2328')
ws0.column_dimensions['A'].width = 140
DROW = {}
ws0.cell(row=8, column=1, value='Автоматическая скидка по группам (со слов руководителя, 22.10.2026) — меняйте здесь, пересчитается всё:').font = Font(name=F, bold=True)
for i, (k, d) in enumerate([('ПВХ', 0.215), ('Алюминий', 0.30), ('Комплектующие', 0.0), ('Фурнитура', 0.0)], 9):
    ws0.cell(row=i, column=1, value=k).font = Font(name=F)
    c = ws0.cell(row=i, column=2, value=d); c.number_format = '0.0%'; c.font = Font(name=F, color='0000FF', bold=True); c.fill = YEL
    DROW[k] = i
ws0.column_dimensions['B'].width = 12

COLS = ['№', 'Наименование (наш прайс 1С)', 'Ед.', 'Остаток, шт/м', 'Цена прайса, ₸ с НДС', 'Авто-скидка группы', 'Наша цена со скидкой, ₸']
for j in (1, 2, 3):
    COLS += [f'Конкурент {j}', f'Аналог / параметры {j}', f'Цена {j}, ₸', f'Разница {j}']
COLS += ['Минимум у конкурентов, ₸', 'Наша цена к минимуму', 'Источник (ссылки)']
W = [5, 52, 8, 11, 13, 10, 14] + [16, 30, 11, 10] * 3 + [14, 12, 50]
for k in CATS:
    ws = wb.create_sheet(k); hdr(ws, 1, COLS, W); ws.freeze_panes = 'C2'
    for r, x in enumerate(sel[k], 2):
        comps = COMP.get(x.get('must', ''), [])
        vals = [r - 1, clean(x['name']), unit(x['name']), round(x['stock'] or 0), x['aktobe']]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v); cell.font = Font(name=F, size=10); cell.border = BRD
        ws.cell(row=r, column=5).number_format = '#,##0.00'; ws.cell(row=r, column=4).number_format = '#,##0'
        dcell = ws.cell(row=r, column=6, value=f"='Как читать'!$B${DROW[k]}"); dcell.number_format = '0.0%'; dcell.font = Font(name=F, size=10, color='008000'); dcell.border = BRD
        pc7 = ws.cell(row=r, column=7, value=f'=E{r}*(1-F{r})'); pc7.number_format = '#,##0.00'; pc7.font = Font(name=F, size=10, bold=True); pc7.border = BRD
        srcs = []
        for j in range(3):
            base = 8 + j * 4
            cname, ccity, an, country, price, url = comps[j] if j < len(comps) else ('', '', '', '', None, '')
            ws.cell(row=r, column=base, value=(f'{cname} ({ccity})' if cname else None))
            ws.cell(row=r, column=base + 1, value=(f'{an}; {country}' if an else None))
            pc = ws.cell(row=r, column=base + 2, value=price); pc.number_format = '#,##0'
            if price is None: pc.fill = YEL
            else: pc.font = Font(name=F, size=10, color='0000FF')
            L = get_column_letter(base + 2)
            dc = ws.cell(row=r, column=base + 3, value=f'=IF({L}{r}="","",G{r}/{L}{r}-1)'); dc.number_format = '+0%;-0%;0%'
            for cc in range(base, base + 4):
                ws.cell(row=r, column=cc).border = BRD
                ws.cell(row=r, column=cc).font = Font(name=F, size=10, color='0000FF' if (cc == base + 2 and price is not None) else '1F2328')
            if url: srcs.append(url)
        p1, p2, p3 = 'J', 'N', 'R'
        mc = ws.cell(row=r, column=20, value=f'=IF(COUNT({p1}{r},{p2}{r},{p3}{r})=0,"",MIN({p1}{r},{p2}{r},{p3}{r}))'); mc.number_format = '#,##0'
        rc = ws.cell(row=r, column=21, value=f'=IF(T{r}="","",G{r}/T{r}-1)'); rc.number_format = '+0%;-0%;0%'
        ws.cell(row=r, column=22, value='; '.join(srcs) if srcs else None)
        for cc in (20, 21, 22):
            ws.cell(row=r, column=cc).border = BRD; ws.cell(row=r, column=cc).font = Font(name=F, size=10)
        if x.get('must'): ws.cell(row=r, column=2).fill = GRY
    ws.auto_filter.ref = f'A1:V{len(sel[k]) + 1}'
    # conditional colour for differences
    from openpyxl.formatting.rule import CellIsRule
    for col in ('L', 'P', 'T', 'U'):
        rng = f'{col}2:{col}{len(sel[k]) + 1}'
        ws.conditional_formatting.add(rng, CellIsRule(operator='greaterThan', formula=['0.03'], font=Font(color='C1272D', bold=True)))
        ws.conditional_formatting.add(rng, CellIsRule(operator='lessThan', formula=['-0.03'], font=Font(color='2E8B57', bold=True)))
wb.save('/tmp/claude-0/wb/ANESCOM_sravnenie_cen_VNUTR_22_10_2026.xlsx')

# ---------- request for quotation (to send) ----------
wb2 = Workbook(); w0 = wb2.active; w0.title = 'Запрос'
txt = ['Запрос коммерческого предложения', '', 'ТОО «GREENTE» — производство окон, дверей и фасадов (Актобе, Богословская трасса, 108Д)',
       'Просим указать цены на материалы по листам «ПВХ», «Алюминий», «Комплектующие», «Фурнитура».',
       'Если точной позиции нет — предложите аналог и укажите его параметры (бренд, серия/ширина, камеры, толщина стенки, материал).',
       'Цены — в тенге с НДС, за единицу из колонки «Ед.»; укажите наличие, срок поставки и минимальную партию.',
       'Заполняются жёлтые ячейки. Пример: «Ваша позиция / аналог» — «профиль 70 мм, 5 камер, класс А, белый»; «Цена» — 2 000; «Наличие» — да; «Срок» — 3; «Мин. партия» — 6 хлыстов.', '', 'Контакт для ответа: ______________________']
for i, t in enumerate(txt, 1):
    c = w0.cell(row=i, column=1, value=t); c.font = Font(name=F, size=12 if i == 1 else 11, bold=(i == 1))
w0.column_dimensions['A'].width = 120
C2 = ['№', 'Наименование', 'Ед.', 'Ориентир объёма в месяц', 'Ваша позиция / аналог (бренд, параметры)', 'Цена, ₸ с НДС', 'Наличие (да/нет)', 'Срок поставки, дней', 'Мин. партия', 'Комментарий']
W2 = [5, 60, 8, 14, 40, 14, 12, 12, 12, 30]
for k in CATS:
    ws = wb2.create_sheet(k); hdr(ws, 1, C2, W2); ws.freeze_panes = 'C2'
    dv = DataValidation(type='list', formula1='"да,нет,под заказ"', allow_blank=True); ws.add_data_validation(dv)
    for r, x in enumerate(sel[k], 2):
        vals = [r - 1, clean(x['name']), unit(x['name']), None]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v); cell.font = Font(name=F, size=10); cell.border = BRD
        for c in range(4, 11):
            cell = ws.cell(row=r, column=c); cell.fill = YEL; cell.border = BRD; cell.font = Font(name=F, size=10, color='0000FF')
        ws.cell(row=r, column=6).number_format = '#,##0'
        dv.add(f'G{r}')
wb2.save('/tmp/claude-0/wb/GREENTE_zapros_KP_materialy.xlsx')
print({k: len(v) for k, v in sel.items()})
