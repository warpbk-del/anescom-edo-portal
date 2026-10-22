import base64, asyncio, html
from playwright.async_api import async_playwright
D = '/tmp/claude-0/rep/'
b64 = lambda p: base64.b64encode(open(D + p, 'rb').read()).decode()
LOGO = b64('logo_color.png'); LOGOW = b64('logo_white.png')
RED = '#C1272D'; DARK = '#1F2328'; GRAY = '#6B7280'; LINE = '#E5E7EB'; GREEN = '#2E8B57'; AMBER = '#B7791F'
E = html.escape

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,sans-serif;color:{DARK};background:#fff}}
.page{{width:794px;height:1123px;padding:56px 56px 48px;position:relative;overflow:hidden;background:#fff}}
.hdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {RED};padding-bottom:10px;margin-bottom:22px}}
.hdr img{{height:26px}} .hdr span{{font-size:10px;color:{GRAY}}}
.foot{{position:absolute;left:56px;right:56px;bottom:24px;display:flex;justify-content:space-between;font-size:9px;color:{GRAY}}}
h1{{font-size:30px;line-height:1.15;font-weight:800}}
h2{{font-size:20px;font-weight:800;margin-bottom:6px}}
h3{{font-size:13px;font-weight:700;margin:14px 0 6px}}
p.lead{{font-size:12.5px;line-height:1.5;color:#374151;margin-bottom:14px}}
p,li{{font-size:11px;line-height:1.5}}
ul,ol{{padding-left:18px}} li{{margin-bottom:4px}}
table{{width:100%;border-collapse:collapse;font-size:9.6px}}
th{{background:{DARK};color:#fff;text-align:left;font-weight:600;padding:6px 6px}}
td{{border-bottom:1px solid {LINE};padding:5px 6px;vertical-align:top}}
td.n{{text-align:right;white-space:nowrap}}
tr.sub td{{color:#4B5563}}
.up{{color:{RED};font-weight:700}} .dn{{color:{GREEN};font-weight:700}} .eq{{color:{GRAY};font-weight:700}}
.kpis{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:22px 0}}
.kpi{{border:1px solid {LINE};border-left:4px solid {RED};padding:12px 14px}}
.kpi.g{{border-left-color:{GREEN}}} .kpi.a{{border-left-color:{AMBER}}}
.kpi b{{display:block;font-size:24px;font-weight:800;margin-bottom:2px}}
.kpi span{{font-size:10.5px;color:#4B5563;line-height:1.35;display:block}}
.box{{background:#F7F7F8;border:1px solid {LINE};padding:12px 14px;margin:10px 0}}
.tag{{display:inline-block;font-size:9px;font-weight:700;padding:2px 6px;border:1px solid currentColor}}
.cover{{background:{DARK};color:#fff;height:1123px;width:794px;padding:64px 56px;position:relative}}
.cover .bar{{position:absolute;left:0;top:0;width:12px;height:100%;background:{RED}}}
"""

def pct(v):
    if v is None: return '<span class="eq">—</span>'
    cls = 'up' if v > 3 else ('dn' if v < -3 else 'eq')
    s = ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.0f}%'
    return f'<span class="{cls}">{s}</span>'

def money(v): return f'{v:,.0f}'.replace(',', ' ') if isinstance(v, (int, float)) else E(str(v))

def page(n, body, title='Анализ цен ANESCOM и конкурентов'):
    return f'<div class="page"><div class="hdr"><img src="data:image/png;base64,{LOGO}"><span>{title} · 22.10.2026</span></div>{body}<div class="foot"><span>ANESCOM · внутренний документ</span><span>{n}</span></div></div>'

def table(head, rows, widths=None):
    th = ''.join(f'<th style="width:{w}">{E(h)}</th>' if widths else f'<th>{E(h)}</th>' for h, w in zip(head, widths or [None]*len(head)))
    tr = ''
    for r in rows:
        cls = ' class="sub"' if r and r[0] == '' else ''
        tds = ''
        for c in r:
            if isinstance(c, tuple) and c[0] == 'pct': tds += f'<td class="n">{pct(c[1])}</td>'
            elif isinstance(c, (int, float)): tds += f'<td class="n">{money(c)}</td>'
            else:
                ci = r.index(c) if c in r else -1
                cc = c.replace(' / ', '<br>') if isinstance(c, str) and len(r) == 6 else c
                cls_ = ' class="n"' if len(r) == 6 and r.index(c) in (4, 5) else ''
                tds += f'<td{cls_}>{cc}</td>'
        tr += f'<tr{cls}>{tds}</tr>'
    return f'<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'

# ---------- chart: diverging bars ----------
def chart(items, title, cap=100, w=682):
    rowh = 19; top = 26; lab = 250; mid = lab + (w - lab - 60) / 2; half = (w - lab - 60) / 2
    h = top + rowh * len(items) + 30
    s = f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" font-family="Inter" font-size="10">'
    s += f'<text x="0" y="14" font-size="12" font-weight="700" fill="{DARK}">{E(title)}</text>'
    for k in (-100, -50, 0, 50, 100):
        x = mid + k / cap * half
        s += f'<line x1="{x}" y1="{top-4}" x2="{x}" y2="{h-24}" stroke="{"#9CA3AF" if k==0 else LINE}" stroke-width="{1.2 if k==0 else 1}"/>'
        s += f'<text x="{x}" y="{h-10}" text-anchor="middle" fill="{GRAY}" font-size="9">{("+" if k>0 else "")}{k}%</text>'
    for i, (name, v) in enumerate(items):
        y = top + i * rowh
        vv = max(-cap, min(cap, v)); x2 = mid + vv / cap * half
        col = RED if v > 3 else (GREEN if v < -3 else '#9CA3AF')
        s += f'<text x="{lab-8}" y="{y+13}" text-anchor="end" fill="{DARK}">{E(name)}</text>'
        s += f'<rect x="{min(mid,x2):.1f}" y="{y+3}" width="{max(1.5,abs(x2-mid)):.1f}" height="{rowh-7}" fill="{col}"/>'
        txt = ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.0f}%' + (' ▸' if abs(v) > cap else '')
        tx = x2 + (5 if v >= 0 else -5)
        s += f'<text x="{tx:.1f}" y="{y+13}" text-anchor="{"start" if v>=0 else "end"}" fill="{col}" font-weight="700">{txt}</text>'
    return s + '</svg>'

same = [('ПВХ PROPLEX 70 — рама (vs WUKO 5К)', -29), ('ПВХ PROPLEX 70 — створка (vs WUKO 5К)', -25),
        ('ПВХ PROPLEX 70 — импост (vs WUKO 5К)', -22), ('FUNKE Helios — рама (vs WUKO 5К)', -6),
        ('FUNKE Helios — створка (vs WUKO 5К)', -5), ('FUNKE Bauline — рама (vs Brusbox 60)', -7),
        ('Штапик 14 мм (vs WUKO)', -1), ('Армирование 1,5 мм (ориентир РФ)', 18), ('Армирование 1,2 мм (ориентир РФ)', 64),
        ('Подоконник 300 цветной (vs белый)', 26), ('Алюминий 45 холодн. — створка (vs FV)', 8),
        ('Алюминий 65 тёпл. — рама (vs ТАТПРОФ РФ)', 14), ('Алюминий 65 тёпл. — створка (vs ТАТПРОФ РФ)', 28),
        ('Алюминий 65 тёпл. — створка (vs FV тёпл.)', 47), ('Закладная фасадная L80', 128),
        ('Уплотнитель ТПУ-6001 (тот же код)', 538), ('Петля оконная ECO (vs Fores KZ)', -30),
        ('Петля дверная FS (vs Fores KZ)', -33), ('Привод T&T KALE (vs Vorne)', 6), ('Ручка оконная ALFA (та же)', -4),
        ('Пена TYTAN 70 (та же)', -7), ('Герметик А+В (Qaraseal)', 4), ('Анкер 7,5×132 (STARFIX)', -3),
        ('Ручка москитной сетки', -58)]
cheap = [('ПВХ PROPLEX 70 рама vs KALE 3К', 29), ('ПВХ Bauline створка vs KALE 3К', 44),
         ('Петля оконная ECO vs Китай 75 мм', 43), ('Петля дверная FS vs Китай 95 мм', 107),
         ('Ручка дверная MEGA vs Китай 85×35', 81), ('Пена TYTAN 70 vs PROFPUR 65', 70)]

L = lambda t, u: f'<a href="{u}" style="color:inherit">{E(t)}</a>'
pages = []

# 1 cover
pages.append(f'''<div class="cover"><div class="bar"></div>
<img src="data:image/png;base64,{LOGOW}" style="height:40px">
<div style="margin-top:150px;font-size:13px;color:#F3B6B8;font-weight:700;letter-spacing:2px">АНАЛИЗ ЦЕН · 22 ОКТЯБРЯ 2026</div>
<h1 style="font-size:40px;margin-top:14px">ANESCOM и конкуренты:<br>ПВХ, алюминий, фурнитура</h1>
<p style="font-size:14px;line-height:1.55;color:#D1D5DB;margin-top:22px;max-width:560px">Сравнение 40 ходовых позиций с ценами конкурентов по Казахстану — те же бренды и аналоги с такими же техническими параметрами, включая китайские марки. В конце — рекомендованные цены и план развития.</p>
<div style="position:absolute;left:56px;right:56px;bottom:64px;display:grid;grid-template-columns:repeat(3,1fr);gap:14px">
<div style="border-top:3px solid {RED};padding-top:10px"><b style="font-size:26px">4 410</b><div style="font-size:11px;color:#D1D5DB">позиций в нашем прайсе 1С</div></div>
<div style="border-top:3px solid {RED};padding-top:10px"><b style="font-size:26px">40</b><div style="font-size:11px;color:#D1D5DB">ключевых позиций сравнено</div></div>
<div style="border-top:3px solid {RED};padding-top:10px"><b style="font-size:26px">12+</b><div style="font-size:11px;color:#D1D5DB">продавцов в Казахстане и РФ</div></div></div></div>''')

# 2 summary
pages.append(page(2, f'''<h2>Главное за минуту</h2>
<p class="lead">По ПВХ-профилю мы в рынке или дешевле аналогов того же класса. Переплата сосредоточена в тёплом алюминии ТАТПРОФ, армировании, цветных подоконниках и фасадных закладных; часть «дорогих» позиций — ошибки в прайсе 1С. Главная угроза — дешёвые китайские петли и ручки.</p>
<div class="kpis">
<div class="kpi g"><b>−15…−44%</b><span>ПВХ PROPLEX 70 дешевле 5-камерных аналогов (WUKO, KAVI, Brusbox). Есть запас поднять цену на 5–8%.</span></div>
<div class="kpi"><b>+47…+67%</b><span>Тёплый алюминий 65 дороже тёплых аналогов; +14…28% даже к тому же ТАТПРОФ у дилера в РФ.</span></div>
<div class="kpi a"><b>×6–7</b><span>Уплотнители ТПУ-6001/6002 дороже рынка по тому же коду — вероятная ошибка единицы в 1С.</span></div>
<div class="kpi"><b>+43…+107%</b><span>Наши петли и дверные ручки дороже китайских у ProfiMart (Астана). Нужна своя эконом-линейка.</span></div></div>
<h3>Что делать</h3>
<ol>
<li><b>Исправить прайс 1С:</b> уплотнители ТПУ, 5 позиций ТАТПРОФ дешевле опта, единицы «метр / хлыст / бухта», 74 позиции без цены.</li>
<li><b>Снизить</b> тёплый алюминий 65, армирование, цветной подоконник и закладные до уровня рынка +10%.</li>
<li><b>Поднять</b> PROPLEX 70 на 5–8% и ручку москитной сетки — мы заметно дешевле рынка.</li>
<li><b>Ввести два уровня «Стандарт / Эконом»</b> в петлях, дверных ручках и пене — чтобы клиент за дешёвым не уходил к конкуренту.</li>
<li><b>Оптовая шкала для цехов и дилеров</b> и продажа комплектами на окно; сравнение с рынком — раз в квартал.</li></ol>
<div class="box" style="margin-top:18px"><p><b>Как читать проценты:</b> (наша цена − цена конкурента) / цена конкурента. <span class="up">Красный +</span> — мы дороже, <span class="dn">зелёный −</span> — мы дешевле. Наши цены — «Розница Актобе» с НДС из 1С на 22.10.2026.</p></div>'''))

# 3 chart
pages.append(page(3, f'''<h2>Где мы дороже и где дешевле</h2>
<p class="lead">Сравнение с аналогом того же класса (камерность, серия, материал). Шкала обрезана на ±100%, реальное значение подписано.</p>
{chart(same, 'Наша цена против аналога того же класса')}
<div style="height:16px"></div>
{chart(cheap, 'Наша цена против дешёвых аналогов (3-камерный, китайский, эконом)')}'''))

# 4 PVC
pvc = [
 ['Рама PROPLEX HIT 70, м', 1734, 'WUKO 5К, 70 мм, класс А, KZ', L('Deniz/WUKO, Алматы','https://denizpipe.kz/p105601255-profil-kamernyj-tsvet.html'), 2440, ('pct', -29)],
 ['', '', 'Brusbox 70, РФ (ориентир)', L('rtk-ltd','https://rtk-ltd.com/__profil-i-armirovanie/profil-brusbox/super-termo-706/'), 2215, ('pct', -22)],
 ['', '', 'KALE 3К', L('Deniz','https://denizpipe.kz/g8505296-profil-kale'), 1344, ('pct', 29)],
 ['Створка PROPLEX HIT 70, м', 1992, 'WUKO 5К / KAVI 4К, KZ', L('Deniz','https://denizpipe.kz/g8491085-profil-wuko'), '2 670 / 3 545', '−25% / −44%'],
 ['', '', 'KALE 3К', 'Deniz', 1344, ('pct', 48)],
 ['Импост PROPLEX HIT 70, м', 2090, 'WUKO 5К / KAVI 3К / Brusbox T86', 'Deniz, rtk-ltd', '2 675 / 3 250 / 2 459', '−22% / −36% / −15%'],
 ['Рама FUNKE Helios, хлыст 6,5 м', 14910, 'WUKO 5К / Brusbox 70 / KAVI 4К', 'Deniz, rtk-ltd', '15 860 / 14 400 / 18 590', '−6% / +4% / −20%'],
 ['Створка FUNKE Helios, хлыст', 16439, 'WUKO 5К / Brusbox 70 / KAVI 4К', 'Deniz, rtk-ltd', '17 355 / 16 299 / 23 043', '−5% / +1% / −29%'],
 ['Импост FUNKE Helios, хлыст', 16759, 'WUKO 5К / Brusbox T86 / KAVI 3К', 'Deniz, rtk-ltd', '17 388 / 15 982 / 21 125', '−4% / +5% / −21%'],
 ['Рама FUNKE Bauline, хлыст', 10262, 'KALE 3К / Brusbox 60 / KAVI 3К', 'Deniz, rtk-ltd', '8 736 / 11 042 / 17 160', '+17% / −7% / −40%'],
 ['Створка FUNKE Bauline, хлыст', 12592, 'KALE 3К / Brusbox 60 / KAVI 3К', 'Deniz, rtk-ltd', '8 736 / 15 174 / 21 060', '+44% / −17% / −40%'],
 ['Армирование 1,5 мм (207), м', 820, '35×28×1,4 мм, РФ (ориентир)', L('rtk-ltd','https://rtk-ltd.com/__profil-i-armirovanie/armirovanie/'), 695, ('pct', 18)],
 ['Армирование 1,2 мм (604), м', 887, '35×20×1,2 мм, РФ (ориентир)', 'rtk-ltd', 541, ('pct', 64)],
 ['Штапик 14 мм, хлыст', 3289, 'WUKO / KAVI / KALE', 'Deniz', '3 315 / 2 691 / 2 620', '−1% / +22% / +26%'],
 ['Уплотнитель KBE 254, м', 123, 'KBE 255 / 228, РФ', L('torgbest','https://torgbest.ru/uplotnitel-dlya-plastikovykh-okon'), '114 / 152', '+8% / −19%'],
 ['Подоконник PROPLEX 300 махагон, м', 3532, 'KAVI 300 золотой дуб, KZ (опт)', L('Deniz','https://denizpipe.kz/g8489028-podokonniki-kavi'), 1161, ('pct', 204)],
 ['', '', '300 мм белый', L('Аквилон, Павлодар','https://akvilon.kz/c/podokonniki-pvkh/'), '2 670–2 980', '+19…+32%'],
]
def fixpct(rows):
    out = []
    for r in rows:
        r = list(r)
        if isinstance(r[5], str) and '%' in r[5]:
            parts = r[5].split(' / ')
            r[5] = '<br>'.join(pct(float(p.replace('−', '-').replace('%', '').replace('…', ' ').split()[0])) if '…' not in p else f'<span class="{"up" if p.startswith("+") else "dn"}">{p}</span>' for p in parts)
        out.append(r)
    return out
pages.append(page(4, f'''<h2>ПВХ-профиль и комплектующие</h2>
<p class="lead">Профиль 70 мм у нас дешевле 5-камерных аналогов; дороже только 3-камерного KALE. Цены WUKO, KAVI и KALE — оптовые (от 5–6 хлыстов), наши — розничные, поэтому в опте разрыв в нашу пользу ещё больше. Переплата — армирование и цветной подоконник.</p>
{table(['Наша позиция','Наша, ₸','Аналог (параметры, страна)','Продавец','Цена аналога, ₸','Разница'], fixpct(pvc), ['24%','8%','25%','17%','14%','12%'])}
<div class="box"><p><b>Китай:</b> CONCH 60 (3 камеры, стенка 2,8 мм) продаёт {L('Kali.kz','https://www.kali.kz/components/profil-conch-46')}, Алматы: рама 713, створка 791, импост 805 ₸ — единица на сайте не указана, нужно уточнить звонком. PROPLEX KZ, FUNKE (Бастау), KBE, VEKA, WDS дают цены только по запросу.</p></div>'''))

# 5 Alu
alu = [
 ['Рама МП-65.01.02 (9006), хлыст 6 м', 57212, 'Рама скрытой створки FV, тёплая, RAL 7024', L('Deniz/Wuko','https://satu.kz/p105916694-alyuminievaya-rama-skrytoj.html'), 36036, ('pct', 59)],
 ['', '', 'ТАТПРОФ W65.01.02 (тот же), РФ', L('Комплект-Плюс','https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/'), 50352, ('pct', 14)],
 ['Створка МП-65.04.02 (8017), хлыст', 72178, 'FV тёплая / FV СТ-63', L('Deniz/Wuko','https://satu.kz/p105916699-alyuminievaya-stvorka-skrytaya.html'), '49 176 / 43 188', '+47% / +67%'],
 ['', '', 'ТАТПРОФ W65.02.05 (тот же), РФ', 'Комплект-Плюс', 56532, ('pct', 28)],
 ['Створка МП-45.04.03 (7024), хлыст', 36525, 'FV CX-45 холодная, RAL 7024', L('Deniz/Wuko','https://satu.kz/p106002481-alyuminievyj-profil-okonnoj.html'), 33900, ('pct', 8)],
 ['Створка двери МП-65.02.05, м', 13154, 'ALUTECH 111.0106M, холодная (слабый аналог)', L('КазПерСтрой','https://kazperstroy.kz/catalogue/show/profil-usilennoj-stvorki-1110106m/'), 9755, ('pct', 35)],
 ['Доп. профиль МП-45.07.15, хлыст', 8132, 'W45.06.03 без покраски, РФ', 'Комплект-Плюс', 6271, ('pct', 30)],
 ['Закладная МП-5013Н L80, шт', 817, 'F50.08.01, цена м × 0,08, РФ', 'Комплект-Плюс', 359, ('pct', 128)],
 ['Закладная МП-5013-02H L80, шт', 1010, 'F50.08.03, РФ', 'Комплект-Плюс', 473, ('pct', 113)],
 ['Уплотнитель ТПУ-6001, м', 446, 'ТПУ-6001 СИАЛ/КраМЗ, ТЭП', L('ТехноКомплект-KZ, Астана','https://tk-kz.satu.kz/p69364383-uplotnitel-rigelya-tpu.html'), 70, ('pct', 538)],
 ['Уплотнитель ТПУ-6002, м', 1008, 'ТПУ-6002 СИАЛ/КраМЗ, ТЭП', L('ТехноКомплект-KZ','https://tk-kz.satu.kz/p69364385-uplotnitel-stojki-tpu.html'), 136, ('pct', 641)],
 ['Подставка F50.05.02 L100, шт', 270, 'F50.05.02 РФ / ALUTECH ABS 115.0902', 'Комплект-Плюс / КазПерСтрой', '223 / 298', '+21% / −9%'],
]
pages.append(page(5, f'''<h2>Алюминий</h2>
<p class="lead">Холодная 45-я серия в рынке (+8%). Тёплая 65-я дороже тёплых аналогов на 47–67% и дороже того же ТАТПРОФ у российского дилера на 14–28% (без доставки и таможни, курс 5,41 ₸/₽). Закладные и уплотнители ТПУ — кратная переплата, вероятно, ошибки в прайсе.</p>
{table(['Наша позиция','Наша, ₸','Аналог (параметры)','Продавец','Цена аналога, ₸','Разница'], fixpct(alu), ['24%','8%','25%','17%','14%','12%'])}
<div class="box"><p><b>Китай:</b> открытых цен на китайские алюминиевые системы в Казахстане не нашлось — продавцы дают «цену по запросу» или цену за м² готового окна. Открытых казахстанских цен на сам ТАТПРОФ тоже нет; дилер АЛЮТЕХ ({L('КазПерСтрой','https://kazperstroy.kz/')}) публикует цены в основном на перегородочные системы.</p></div>'''))

# 6 fittings
fit = [
 ['Петля оконная 75 мм ECO', 401, 'Fores 75, цинк, Казахстан', L('Winnova, Алматы','https://satu.kz/p128345976'), 575, ('pct', -30)],
 ['', '', 'EVAplast 75, Турция', 'Winnova', 350, ('pct', 15)],
 ['', '', '75 мм, алюминий, 120 кг, Китай', L('ProfiMart, Астана','https://satu.kz/p132578153'), 280, ('pct', 43)],
 ['Петля дверная 100 мм FS', 601, 'Fores 100, цинк, Казахстан', L('Winnova','https://satu.kz/p128345965'), 897, ('pct', -33)],
 ['', '', '95 мм пластик / алюминий, Китай', L('ProfiMart','https://satu.kz/p132579530'), '290 / 360', '+107% / +67%'],
 ['Привод T&T KALE 980', 1310, 'Vorne ОС-ПВР 15.5, Турция', L('Deniz/Wuko','https://denizpipe.kz/p106893807'), 1234, ('pct', 6)],
 ['Ручка оконная ALFA алюм. 9016', 881, 'ALFA (та же) / Lara, Китай', L('Winnova','https://satu.kz/p128346177') + ' / ' + L('ProfiMart','https://satu.kz/p132591435'), '920 / 850', '−4% / +4%'],
 ['Ручка оконная пласт. коричн.', 349, 'MEGA / DESA коричневые', L('ProfiMart','https://satu.kz/p132871269'), '410 / 480', '−15% / −27%'],
 ['Ручка дверная MEGA 35/85', 3532, 'WC 85×35, металлопластик, Китай', L('ProfiMart','https://satu.kz/p132591473'), 1950, ('pct', 81)],
 ['Пена TYTAN 70, 870 мл', 3735, 'TYTAN 70 (та же)', L('Turan Stroy','https://satu.kz/p99241278') + ' / ' + L('Ala-Mart','https://satu.kz/p126378151'), '4 000 / 4 820', '−7% / −23%'],
 ['', '', 'PROFPUR 65 (Беларусь) / Soudal 65', L('TRADE CK','https://satu.kz/p47181798') + ' / ' + L('ORGSTROY','https://satu.kz/p122611087'), '2 200 / 2 300', '+70% / +62%'],
 ['Герметик А+В 33 кг, за кг', 847, 'Qaraseal, тиоколовый 2К', L('AVplus, Шымкент','https://satu.kz/p123266833'), 818, ('pct', 4)],
 ['Анкер 7,5×132', 64, 'STARFIX 8×132, Китай', L('Отвёртка.kz','https://otvertka.kz/product/starfix-smp-70538-1'), 66, ('pct', -3)],
 ['Ручка москитной сетки', 11.9, 'STARFIX / ручка-кольцо', L('R&A Partners','https://satu.kz/p127976716') + ' / ' + L('Аквилон','https://akvilon.kz/p/ruchka-koltso-dlya-moskitnoy-setki/'), '28 / 35', '−58% / −66%'],
]
pages.append(page(6, f'''<h2>Фурнитура и расходники</h2>
<p class="lead">Против казахстанских и турецких брендов того же класса мы в рынке или дешевле. Против китайской фурнитуры у ProfiMart (Астана) наши петли и дверные ручки дороже на 43–107%. Пена TYTAN дешевле той же пены у конкурентов, но эконом-пена 65 л стоит на 40% меньше.</p>
{table(['Наша позиция','Наша, ₸','Аналог (параметры, страна)','Продавец','Цена аналога, ₸','Разница'], fixpct(fit), ['22%','8%','25%','19%','14%','12%'])}
<p style="margin-top:10px;color:{GRAY}">Не нашли открытых цен на замок 85-30 (у нас 4 603 ₸) и комплекты поворотно-откидной фурнитуры Roto, Maco, Vorne, Axor, G-U — запросить у ТБМ, Deniz и ProfiMart.</p>'''))

# 7 errors + prices
rec = [
 ['ПВХ PROPLEX HIT 70 (рама / створка / импост), м', '1 734 / 1 992 / 2 090', '1 820–1 870 / 2 090–2 150 / 2 190–2 260', '<span class="up">Поднять 5–8%</span>'],
 ['FUNKE Helios, Bauline', 'без изменений', '—', '<span class="eq">Держать</span>'],
 ['Армирование 1,2 / 1,5 мм, м', '887 / 820', '600–650 / 750–780', '<span class="dn">Снизить</span>'],
 ['Подоконник 300 мм цветной, м', '3 532', '2 400–2 700', '<span class="dn">Снизить</span>'],
 ['Алюминий тёплый 65: рама / створка, хлыст', '57 212 / 72 178', '52 000–55 000 / 60 000–64 000', '<span class="dn">Снизить</span>'],
 ['Алюминий холодный 45', '36 525', 'без изменений', '<span class="eq">Держать</span>'],
 ['Уплотнители ТПУ-6001 / 6002, м', '446 / 1 008', '80–95 / 150–170', '<span class="dn">Исправить</span>'],
 ['Закладные L80', '817 / 1 010', '450–600', '<span class="dn">Пересчитать</span>'],
 ['Петли — эконом-линейка (новая)', '401 / 601', '290–330 / 380–450', 'Добавить рядом'],
 ['Ручка дверная — эконом (новая)', '3 532', '2 100–2 400', 'Добавить'],
 ['Пена — эконом 65 л (новая)', '3 735', '2 400–2 600', 'Добавить'],
 ['Ручка москитной сетки', '11,9', '20–25', '<span class="up">Поднять</span>'],
]
pages.append(page(7, f'''<h2>Ошибки прайса и рекомендованные цены</h2>
<p class="lead">Сначала исправить очевидные ошибки в 1С, затем выставить цены в коридор «рынок того же класса +0…15%». Перед изменением сверить с закупочной ценой и маржой.</p>
<h3>Проверить в 1С</h3>
<ul>
<li>Уплотнители ТПУ-6001 / 6002: розница 446 и 1 008 ₸/м при оптовой 41,6 и 77 ₸ и рынке 70 и 136 ₸ — единица «метр или бухта», материал.</li>
<li>5 позиций ТАТПРОФ, где розница ниже опта (МП-5013-11Н, МП-5004-01, МП-65.02.05 в 7024, МП-45.07.02) — продажа в убыток или ошибка.</li>
<li>Сухарь МП-5004 — 87 966 ₸ «за шт» при опте 1 299; соединительные планки 12 291–13 519 ₸ при опте 265; шаблоны KALE 5 000 ₸ при опте 4 ₸.</li>
<li>74 позиции без цены «Розница Актобе»; колонка «Оптовая цена» в среднем в 4,2 раза ниже розницы — устарела или это закупка.</li></ul>
<h3>Рекомендованные цены (розница с НДС, ₸)</h3>
{table(['Позиция','Сейчас','Коридор','Действие'], rec, ['34%','18%','30%','18%'])}'''))

# 8 strategy
pages.append(page(8, f'''<h2>Как развиваться дальше</h2>
<p class="lead">Наше преимущество — не цена, а наличие на складах в 6 городах, проверенные бренды и своё производство (АВТОКОМП, GREENTE). Цена должна быть «не дороже рынка того же класса», а разницу оправдывают сроки и сервис.</p>
<ol>
<li><b>Два уровня в каждой группе:</b> «Стандарт» (наши бренды) и «Эконом» (китайский или турецкий товар с проверенными параметрами). Клиент, пришедший за дешёвым, остаётся у нас.</li>
<li><b>Отвечать китайским брендам параметрами:</b> в каталоге и у менеджеров — толщина стенки, класс профиля, камеры, материал фурнитуры, гарантия. Памятка «почему дешёвое дороже обходится» для оконных цехов.</li>
<li><b>Оптовая шкала</b> для цехов и дилеров (например, −5% от 1 млн ₸ в месяц, −10% от 5 млн ₸). Конкуренты (WUKO, KAVI, KALE) уже продают по оптовым ценам.</li>
<li><b>Порядок в прайсе 1С:</b> единые единицы (м / хлыст / бухта), цена на каждую позицию, пересчёт при смене закупки через обработку «ЦенообразованиеANESCOM».</li>
<li><b>Продавать комплектами:</b> цена за комплект на окно или м² витража сравнивается труднее и даёт маржу на позициях, где мы дешевле рынка.</li>
<li><b>Раз в квартал повторять сравнение</b> и добирать закрытые цены запросами КП (PROPLEX KZ, Бастау, ТБМ, КазПерСтрой, ТехноКомплект).</li></ol>
<h3>Почему китайские бренды дешевле</h3>
<ul>
<li>Дешевле сырьё и энергия: Китай выплавляет больше половины мирового алюминия и сам производит ПВХ-смолу.</li>
<li>Масштаб производства и экспортная поддержка (возврат НДС экспортёрам).</li>
<li>Экономия на изделии: тоньше стенки алюминия (1,2 мм против 1,4–2,0), профиль ПВХ класса B, вторичное сырьё, цинковый сплав вместо стали в фурнитуре, тоньше покрытие.</li>
<li>Мало расходов на бренд: испытания, сертификацию, гарантию и сервис.</li></ul>
<h3>Источники и оговорки</h3>
<p style="color:#4B5563">Наши цены — отчёт 1С «Прайс-лист» на 22.10.2026, «Розница Актобе-18» с НДС. Цены конкурентов — открытые страницы, проверены 22.10.2026: {L('Deniz/WUKO','https://denizpipe.kz/g8491085-profil-wuko')}, {L('Winnova','https://satu.kz/c779522-too-winnova.html')}, {L('ProfiMart','https://satu.kz/c873786-profimart.html')}, {L('КазПерСтрой / Алютех','https://kazperstroy.kz/')}, {L('ТехноКомплект-KZ','https://tk-kz.satu.kz/')}, {L('Kali.kz','https://www.kali.kz/components/profil-conch-46')}, {L('Аквилон','https://akvilon.kz/c/podokonniki-pvkh/')}; ориентиры РФ — {L('Комплект-Плюс','https://komplekt-plus.ru/catalog/alyuminievye-sistemy/tatprof/')}, {L('rtk-ltd','https://rtk-ltd.com/__profil-i-armirovanie/')}. Цены WUKO, KAVI, KALE — оптовые; НДС у конкурентов не указан. Kaspi, OLX и часть satu.kz проверить не удалось.</p>'''))

doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>' + ''.join(pages) + '</body></html>'
open(D + 'report.html', 'w').write(doc)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 794, 'height': 1123}, device_scale_factor=2.5)
        await pg.goto('file://' + D + 'report.html'); await pg.wait_for_timeout(400)
        n = await pg.evaluate("document.querySelectorAll('.page,.cover').length")
        els = await pg.query_selector_all('.page,.cover')
        for i, el in enumerate(els):
            await el.screenshot(path=D + f'p{i+1:02d}.png')
        await b.close(); print('pages', n)
asyncio.run(main())
from PIL import Image
ims = [Image.open(D + f'p{i:02d}.png').convert('RGB') for i in range(1, 9)]
ims[0].save(D + 'ANESCOM_analiz_cen_22_10_2026.pdf', save_all=True, append_images=ims[1:], resolution=240)
print('ok')
