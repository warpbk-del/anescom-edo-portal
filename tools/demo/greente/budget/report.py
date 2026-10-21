# PDF-отчёт по бюджету открытия GREENTE: HTML (A4) -> PNG (Playwright) -> растровый PDF (PIL)
import re, asyncio, os, sys
from data import *
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/GREENTE_byudzhet_otchet.pdf"
LOGO_L = "file:///home/claude/deckimg/logo_light.png"
IMG = "file:///home/claude/booklet/factory-coating-workshop.jpg"

def m(x):  # 3961650 -> "3 961 650"
    return f"{round(x):,}".replace(",", " ")
def mln(x): return f"{x/1e6:.2f}".replace(".", ",")

T = totals(); S = sum(t[1] for t in T); MN = sum(t[2] for t in T); MX = sum(t[3] for t in T)
R = S*RESERVE; G = S+R
UG = T[0][1]

css = """
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Regular.otf);font-weight:400}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Medium.otf);font-weight:500}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-SemiBold.otf);font-weight:600}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Bold.otf);font-weight:700}
@font-face{font-family:D;src:url(file:///usr/share/fonts/opentype/inter/InterDisplay-Bold.otf);font-weight:700}
@font-face{font-family:D;src:url(file:///usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf);font-weight:800}
:root{--ink:#0B1F27;--teal:#2B4B5C;--teal2:#3E6577;--green:#46B254;--g2:#E8F5EA;--mist:#8FA9B3;--line:#DCE6E4;--paper:#FFFFFF;--soft:#F3F7F6}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#ccc;font-family:F,sans-serif;color:var(--ink);font-variant-numeric:tabular-nums}
.pg{width:794px;height:1123px;background:var(--paper);position:relative;overflow:hidden;margin:0 auto 20px;padding:56px 56px 48px}
.dark{background:var(--ink);color:#fff}
.num{font-family:D,sans-serif;font-weight:800;letter-spacing:-1px}
.k{font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--green)}
h1{font-family:D;font-weight:800;font-size:46px;line-height:1.02;letter-spacing:-1.5px}
h2{font-family:D;font-weight:800;font-size:26px;letter-spacing:-.5px;color:var(--teal)}
.sub{font-size:12.5px;color:#5B7079;line-height:1.5}
.foot{position:absolute;left:56px;right:56px;bottom:26px;display:flex;justify-content:space-between;font-size:9px;color:var(--mist);border-top:1px solid var(--line);padding-top:8px}
.dark .foot{border-color:rgba(255,255,255,.12)}
.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:26px}
.top img{height:22px}
.top span{font-size:9.5px;color:var(--mist);letter-spacing:1.5px;text-transform:uppercase;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:10.2px}
th{font-size:8.5px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--mist);text-align:left;padding:6px 6px;border-bottom:1.5px solid var(--teal)}
td{padding:5.5px 6px;border-bottom:1px solid var(--line);vertical-align:top}
td.r,th.r{text-align:right;white-space:nowrap}
tr.cat td{background:var(--teal);color:#fff;font-weight:700;font-size:10.5px;padding:7px 8px;border:0}
tr.cat td .s{font-weight:400;color:#C9DCE2;font-size:9.5px;margin-left:8px}
tr.st td{font-weight:700;background:var(--soft);border-bottom:0}
.pill{display:inline-block;font-size:8px;font-weight:700;letter-spacing:.8px;padding:2px 6px;border-radius:9px;text-transform:uppercase;white-space:nowrap}
.p-kp{background:var(--green);color:#fff}.p-est{background:#E3ECEF;color:var(--teal)}.p-in{border:1px solid var(--teal2);color:var(--teal2)}
.note{font-size:8.8px;color:#6E8590;line-height:1.35}
.card{background:var(--soft);border-radius:10px;padding:16px 18px}
"""

def foot(n, dark=False):
    return f'<div class="foot"><span>GREENTE · Бюджет открытия завода · {EVENT}</span><span>{n} / 6</span></div>'
def top(t):
    return f'<div class="top"><img src="file:///home/claude/booklet/logo.png"><span>{t}</span></div>'

# ---------- 1. обложка ----------
p1 = f"""<section class="pg dark" style="padding:0">
<div style="position:absolute;inset:0 0 auto 0;height:520px;background:url({IMG}) center/cover;filter:saturate(.25) brightness(.55)"></div>
<div style="position:absolute;inset:0 0 auto 0;height:520px;background:linear-gradient(180deg,rgba(11,31,39,.35),#0B1F27)"></div>
<div style="position:relative;padding:56px">
 <img src="{LOGO_L}" style="height:40px">
 <div style="margin-top:250px" class="k">Смета мероприятия · для руководства</div>
 <h1 style="margin-top:14px;font-size:58px">Бюджет открытия<br>завода GREENTE</h1>
 <p style="margin-top:16px;font-size:15px;color:#A9C3CC">{EVENT} · Актобе, Богословская трасса, 108Д · {GUESTS} гостей</p>
</div>
<div style="position:absolute;left:56px;right:56px;top:640px">
 <div style="display:flex;align-items:flex-end;gap:22px;border-top:1px solid rgba(255,255,255,.15);padding-top:28px">
  <div><div class="k">Рекомендуемый бюджет с резервом 10%</div>
  <div class="num" style="font-size:84px;line-height:1;margin-top:10px">{m(G)} <span style="font-size:40px;color:var(--green)">₸</span></div></div>
 </div>
 <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:34px">
  <div style="border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:18px"><div class="k" style="color:#8FA9B3">Эконом</div><div class="num" style="font-size:30px;margin-top:8px">{mln(MN*(1+RESERVE))} млн</div><div class="note" style="color:#8FA9B3;margin-top:6px">простой фуршет, свои силы, электронные приглашения</div></div>
  <div style="background:var(--green);border-radius:12px;padding:18px"><div class="k" style="color:#fff">Оптимум · рекомендуем</div><div class="num" style="font-size:30px;margin-top:8px">{mln(G)} млн</div><div class="note" style="color:#E8F5EA;margin-top:6px">полноценный фуршет, фото/видео, реклама</div></div>
  <div style="border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:18px"><div class="k" style="color:#8FA9B3">Максимум</div><div class="num" style="font-size:30px;margin-top:8px">{mln(MX*(1+RESERVE))} млн</div><div class="note" style="color:#8FA9B3;margin-top:6px">премиум-кейтеринг, больше PR и блогеров</div></div>
 </div>
 <div style="display:flex;gap:40px;margin-top:34px;font-size:12px;color:#A9C3CC">
  <div><b class="num" style="font-size:22px;color:#fff">{m(G/GUESTS)} ₸</b><br>на одного гостя</div>
  <div><b class="num" style="font-size:22px;color:#fff">{round(UG/S*100)}%</b><br>пакет UGROUP.KZ</div>
  <div><b class="num" style="font-size:22px;color:#fff">{sum(len(c[2]) for c in CATS)}</b><br>статей расходов</div>
 </div>
</div>
{foot(1,True)}</section>"""

# ---------- 2. сводка ----------
mxv = max(t[3] for t in T)
W = 420
bars = ""
for i, (n, o, a, b) in enumerate(T):
    y = i*58
    col = "#46B254" if i == 0 else "#2B4B5C"
    bars += f'<text x="0" y="{y+14}" font-size="11.5" font-weight="600" fill="#0B1F27">{n}</text>'
    bars += f'<rect x="0" y="{y+22}" width="{W*o/mxv:.1f}" height="16" rx="3" fill="{col}"/>'
    if b > a:
        bars += f'<line x1="{W*a/mxv:.1f}" x2="{W*b/mxv:.1f}" y1="{y+30}" y2="{y+30}" stroke="#8FA9B3" stroke-width="1.5" stroke-dasharray="3 2"/>'
        bars += f'<line x1="{W*a/mxv:.1f}" x2="{W*a/mxv:.1f}" y1="{y+24}" y2="{y+36}" stroke="#8FA9B3" stroke-width="1.5"/><line x1="{W*b/mxv:.1f}" x2="{W*b/mxv:.1f}" y1="{y+24}" y2="{y+36}" stroke="#8FA9B3" stroke-width="1.5"/>'
    bars += f'<text x="{W+14}" y="{y+35}" font-size="13" font-weight="700" fill="#0B1F27">{m(o)} ₸</text>'
    bars += f'<text x="{W+14}" y="{y+14}" font-size="9.5" fill="#8FA9B3">{round(o/S*100)}% бюджета</text>'
rows = "".join(f'<tr><td>{n}</td><td class="r">{m(a)}</td><td class="r"><b>{m(o)}</b></td><td class="r">{m(b)}</td></tr>' for n, o, a, b in T)
p2 = f"""<section class="pg">{top("Сводка")}
<div class="k">Куда уходят деньги</div><h2 style="margin-top:6px">5 направлений расходов</h2>
<p class="sub" style="margin-top:8px;max-width:560px">Треть бюджета — пакет ивент-агентства с фиксированной ценой по КП. Остальное — оценки по рынку Актобе: их можно сдвинуть в коридоре «эконом — максимум» (пунктир на графике).</p>
<svg width="682" height="300" style="margin-top:24px;overflow:visible">{bars}</svg>
<table style="margin-top:6px"><tr><th>Направление</th><th class="r">Эконом, ₸</th><th class="r">Оптимум, ₸</th><th class="r">Максимум, ₸</th></tr>{rows}
<tr class="st"><td>Итого по статьям</td><td class="r">{m(MN)}</td><td class="r">{m(S)}</td><td class="r">{m(MX)}</td></tr>
<tr><td>Резерв на непредвиденное, 10%</td><td class="r">{m(MN*RESERVE)}</td><td class="r">{m(R)}</td><td class="r">{m(MX*RESERVE)}</td></tr>
<tr class="cat"><td>ВСЕГО С РЕЗЕРВОМ</td><td class="r">{m(MN*1.1)}</td><td class="r" style="font-size:12px">{m(G)}</td><td class="r">{m(MX*1.1)}</td></tr></table>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:22px">
 <div class="card"><div class="k">Не входит в смету</div><p class="sub" style="margin-top:6px">Уже оплаченное: подарки, флаги, флешки, спецодежда, сайт, VIP-номера, гонорар SMM. Фактические суммы — в таблице на стр. 4.</p></div>
 <div class="card"><div class="k">Как платим UGROUP</div><p class="sub" style="margin-top:6px">По КП расчёт идёт напрямую с каждым подрядчиком пакета; агентство координирует.</p></div>
</div>
{foot(2)}</section>"""

# ---------- 3–4. детальная смета ----------
def pill(s): return {"КП": '<span class="pill p-kp">КП</span>', "Оценка": '<span class="pill p-est">оценка</span>'}.get(s, f'<span class="pill p-in">{s}</span>')
def cat_rows(i):
    n, sub, items = CATS[i]
    h = f'<tr class="cat"><td colspan="6">{i+1}. {n}<span class="s">{sub}</span></td></tr>'
    for (a, who, q, p, lo, hi, st, due, cm) in items:
        h += f'<tr><td><b style="font-weight:600">{a}</b>{"<div class=note>"+cm+"</div>" if cm else ""}</td><td class="note" style="font-size:9.5px">{who}</td><td class="r">{m(q)}</td><td class="r">{m(p)}</td><td class="r"><b>{m(q*p)}</b></td><td>{pill(st)}</td></tr>'
    h += f'<tr class="st"><td colspan="4">Итого: {n}</td><td class="r">{m(T[i][1])}</td><td></td></tr>'
    return h
TH = '<tr><th>Статья</th><th>Подрядчик</th><th class="r">Кол-во</th><th class="r">Цена, ₸</th><th class="r">Сумма, ₸</th><th>Статус</th></tr>'
p3 = f"""<section class="pg">{top("Детальная смета · 1/2")}
<div class="k">Вариант «Оптимум»</div><h2 style="margin-top:6px;margin-bottom:16px">Детальная смета</h2>
<table>{TH}{cat_rows(0)}{cat_rows(1)}{cat_rows(2)}</table>{foot(3)}</section>"""
done = "".join(f'<tr><td>{a}</td><td class="note">{s}</td><td class="r" style="color:#8FA9B3">_________ ₸</td></tr>' for a, s in DONE)
p4 = f"""<section class="pg">{top("Детальная смета · 2/2")}
<table>{TH}{cat_rows(3)}{cat_rows(4)}</table>
<div class="k" style="margin-top:26px">Уже сделано — вне сметы</div>
<p class="sub" style="margin:4px 0 8px">Впишите фактические суммы, чтобы видеть полную стоимость открытия.</p>
<table><tr><th>Позиция</th><th>Статус</th><th class="r">Факт</th></tr>{done}</table>
<div style="margin-top:14px;display:flex;gap:16px;font-size:9px;color:#6E8590;align-items:center">{pill("КП")} цена зафиксирована в КП подрядчика {pill("Оценка")} ориентир по рынку Актобе, уточнить у поставщика</div>
{foot(4)}</section>"""

# ---------- 5. график оплат, экономия, решения ----------
def bucket(s):
    if "после" in s: return (9999, "после 13.11")
    d = re.findall(r"(\d\d)\.(\d\d)", s)
    if d: dd, mm = d[-1] if "до" in s and len(d) > 1 else d[0]; return (int(mm)*100+int(dd), f"{dd}.{mm}")
    if "день" in s: return (1112, "12.11")
    return (1028, "28.10")
B = {}
for n, sub, items in CATS:
    for (a, who, q, p, lo, hi, st, due, cm) in items:
        k = bucket(due); amt = q*p*(0.5 if "50%" in due else 1)
        B.setdefault(k, [0, []]); B[k][0] += amt; B[k][1].append(a.split(":")[0].split(" (")[0])
        if "50%" in due:
            k2 = (1112, "12.11"); B.setdefault(k2, [0, []]); B[k2][0] += q*p*0.5; B[k2][1].append(a.split(":")[0] + " — остаток 50%")
keys = sorted(B); cum = 0; tl = ""
mxb = max(v[0] for v in B.values())
for k in keys:
    v = B[k]; cum += v[0]
    names = ", ".join(dict.fromkeys(v[1]))
    if len(names) > 120: names = names[:117] + "…"
    tl += f'''<div style="display:grid;grid-template-columns:78px 1fr 120px;gap:14px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)">
<div class="num" style="font-size:17px;color:var(--teal)">{k[1]}</div>
<div><div style="height:9px;border-radius:5px;background:var(--green);width:{max(4,100*v[0]/mxb):.0f}%"></div><div class="note" style="margin-top:4px">{names}</div></div>
<div class="r" style="text-align:right"><b style="font-size:12px">{m(v[0])} ₸</b><div class="note">нарастающим: {m(cum)}</div></div></div>'''
save = [("Электронные приглашения для бизнеса", 30000), ("Пресс-релиз в СМИ бесплатно вместо платных публикаций", 120000),
        ("Охрана и парковка своими сотрудниками", 30000), ("VIP-гостей встречаем на своих авто", 40000),
        ("Фуршет-канапе вместо горячих закусок (5 000 ₸/чел)", 400000)]
sv = "".join(f'<div style="display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid var(--line);font-size:10.5px"><span>{a}</span><b style="color:var(--green);white-space:nowrap">−{m(b)} ₸</b></div>' for a, b in save)
dec = [("до 25.10", "Утвердить вариант бюджета и подписать КП UGROUP.KZ"),
       ("до 28.10", "Выбрать кейтеринг: запросить 2–3 предложения на 100 гостей"),
       ("до 28.10", "Сверить размер бэкдропа: 4×6 м в КП или 6×3 м в эскизе"),
       ("до 01.11", "Внести фактические суммы уже сделанного (стр. 4)"),
       ("до 05.11", "Решить: арендовать тепловые пушки или купить одну для цеха (~125 000 ₸)")]
dc = "".join(f'<div style="display:grid;grid-template-columns:70px 1fr;gap:10px;padding:6px 0;border-bottom:1px solid var(--line);font-size:10.5px"><b style="color:var(--teal)">{d}</b><span>{t}</span></div>' for d, t in dec)
p5 = f"""<section class="pg">{top("Оплаты и решения")}
<div class="k">Когда нужны деньги</div><h2 style="margin-top:6px">График оплат</h2>
<p class="sub" style="margin:6px 0 10px">По срокам из сметы, вариант «Оптимум», без резерва. Кейтеринг и видео — предоплата 50%, остаток в день события.</p>
{tl}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:22px">
 <div class="card"><div class="k">Где можно сэкономить</div><div style="margin-top:6px">{sv}</div>
 <div style="display:flex;justify-content:space-between;margin-top:8px;font-weight:700;font-size:11px"><span>Всего возможно</span><span style="color:var(--green)">−{m(sum(b for _, b in save))} ₸</span></div></div>
 <div class="card"><div class="k">Решения руководства</div><div style="margin-top:6px">{dc}</div></div>
</div>{foot(5)}</section>"""

# ---------- 6. источники ----------
src = "".join(f'<div style="padding:9px 0;border-bottom:1px solid var(--line)"><div style="font-size:11px;font-weight:600">{a}</div>{"<div class=note style=word-break:break-all;margin-top:2px>"+b+"</div>" if b else ""}</div>' for a, b in SOURCES)
p6 = f"""<section class="pg">{top("Источники и допущения")}
<div class="k">Откуда цифры</div><h2 style="margin-top:6px;margin-bottom:10px">Источники цен</h2>{src}
<div class="card" style="margin-top:24px"><div class="k">Допущения</div>
<p class="sub" style="margin-top:6px">• {GUESTS} гостей; фуршет считается на всех.<br>• Цены «оценка» — ориентиры по открытым объявлениям Актобе и соседних городов на октябрь 2026; финальные цены уточнить у поставщиков.<br>• Резерв 10% покрывает рост цен и мелкие покупки в последний момент.<br>• Суммы без НДС, если подрядчик работает без него.</p></div>
<div style="position:absolute;left:56px;right:56px;bottom:70px;display:flex;justify-content:space-between;align-items:center">
<img src="file:///home/claude/booklet/logo.png" style="height:26px">
<div style="text-align:right;font-size:10.5px;color:var(--teal)"><b>greente.kz · +7 777 111 2128</b><br>Актобе, Богословская трасса, 108Д</div></div>
{foot(6)}</section>"""

html = f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>{css}</style></head><body>{p1}{p2}{p3}{p4}{p5}{p6}</body></html>'
open(os.path.join(HERE, "report.html"), "w", encoding="utf-8").write(html)

async def shoot():
    from playwright.async_api import async_playwright
    from PIL import Image
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args=["--allow-file-access-from-files"])
        pg = await br.new_page(viewport={"width": 900, "height": 1200}, device_scale_factor=2.6)
        await pg.goto("file://" + os.path.join(HERE, "report.html")); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(400)
        els = await pg.query_selector_all("section.pg"); ims = []
        for i, e in enumerate(els):
            f = os.path.join(HERE, f"rp{i+1}.png"); await e.screenshot(path=f); ims.append(Image.open(f).convert("RGB"))
        await br.close()
    ims[0].save(OUT, save_all=True, append_images=ims[1:], resolution=250)
    print("PDF", OUT, len(ims))
asyncio.run(shoot())
