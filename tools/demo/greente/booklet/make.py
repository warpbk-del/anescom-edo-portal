# Буклеты GREENTE (трифолд A4, 2 стороны) — по одному на аудиторию.
import os
from playwright.sync_api import sync_playwright

A = [
 dict(key="zastroyshchiki", n="01", who="Застройщикам", img="hero-glass-towers.webp", img2="factory-aluminium-cnc.jpg",
  head="Качественные узлы и заводская сборка по ГОСТу",
  lead="Фасады, окна и витражи для вашего объекта — рассчитаны конструктором и собраны на заводе.",
  benefits=[("Качественные узлы", "каждый узел рассчитан и собран на заводе"),
            ("Статика и ветровая нагрузка", "считаем до производства — без риска для объекта"),
            ("Сроки быстрее", "своя покраска в Актобе, без ожидания профиля"),
            ("Короче цепочка", "напрямую с завода, отвечает один производитель")],
  quote="Здание принимают без замечаний — за изделие отвечает завод."),
 dict(key="okonnye_kompanii", n="02", who="Оконным компаниям", img="v_99.jpg", img2="v_108.jpg",
  head="Качество завода — без своего цеха",
  lead="Продавайте и монтируйте. Изготовление по вашим замерам берём на себя.",
  benefits=[("Не нужно своё помещение", "и сборщики — изготовим по вашим замерам"),
            ("Качество по ГОСТу", "заводская сборка, брака сборки нет"),
            ("Расчёт статики и узлов", "алюминий — сложный продукт, ошибки исключаем"),
            ("Партнёрская цена", "и заявки на монтаж с greente.kz")],
  quote="Ваша задача — клиент и монтаж. Производство — наша."),
 dict(key="arhitektory_predprinimateli", n="03", who="Архитекторам и предпринимателям", img="entrance-group-photoreal-v2.webp", img2="tws65-assembly-turn.webp",
  head="Идея из проекта — в готовом изделии",
  lead="Нестандартные фасады, витражи и входные группы — точно по проекту и по ГОСТу.",
  benefits=[("Расчёт узлов и 3D-модель", "бесплатно, до запуска в цех"),
            ("Архитектору", "партнёрское вознаграждение [__]% за реализованный проект"),
            ("Предпринимателю", "изделия по ГОСТу, монтаж наших партнёров"),
            ("Цвет под проект", "своя линия порошковой покраски, любой RAL")],
  quote="Изделие получается таким, каким его задумал архитектор."),
]

CSS = """
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Regular.otf);font-weight:400}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Medium.otf);font-weight:500}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-SemiBold.otf);font-weight:600}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Bold.otf);font-weight:700}
@font-face{font-family:D;src:url(file:///usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf);font-weight:800}
@font-face{font-family:D;src:url(file:///usr/share/fonts/opentype/inter/InterDisplay-Bold.otf);font-weight:700}
@page{size:297mm 210mm;margin:0}
*{box-sizing:border-box;margin:0}
body{font-family:F,sans-serif;color:#13303b;font-size:8.6pt;line-height:1.45}
.sheet{width:297mm;height:210mm;display:grid;grid-template-columns:99mm 99mm 99mm;page-break-after:always;overflow:hidden}
.p{position:relative;overflow:hidden;padding:11mm 9mm 10mm;display:flex;flex-direction:column}
.dark{background:#062631;color:#e9f1ef}.mid{background:#0b3442;color:#e9f1ef}.light{background:#f5f8f7}.white{background:#fff}
.k{font-size:6.6pt;font-weight:700;letter-spacing:2.2pt;text-transform:uppercase;color:#2f9a40}
.dark .k,.mid .k{color:#5fd06f}
h1,h2{font-family:D,F,sans-serif;font-weight:800;letter-spacing:-.3pt}
h1{font-size:27pt;line-height:1.02}
h2{font-size:15pt;line-height:1.12;margin:2mm 0 4mm}
.muted{color:#5b7079}.dark .muted,.mid .muted{color:#a9c3cc}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,38,49,.35) 0%,rgba(6,38,49,.2) 35%,rgba(6,38,49,.92) 72%,#062631 100%)}
.z{position:relative;z-index:1;display:flex;flex-direction:column;height:100%}
.logo{width:56mm}
.badge{width:31mm;height:31mm;border-radius:50%;background:#38B24A;color:#062631;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;box-shadow:0 2mm 6mm rgba(0,0,0,.3)}
.badge b{font-family:D;font-size:23pt;line-height:1}.badge span{font-size:6pt;font-weight:700;line-height:1.2;margin-top:1mm}
.tag{display:inline-block;background:#38B24A;color:#062631;font-weight:700;font-size:7pt;padding:1.2mm 3mm;border-radius:10mm}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:3mm;margin:3mm 0 4mm}
.stat{background:#fff;border-radius:3mm;padding:3mm}.stat b{font-family:D;font-size:15pt;color:#2f9a40;display:block;line-height:1.05}
.adv{display:flex;gap:3mm;align-items:flex-start;padding:2.4mm 0;border-top:1px solid #dbe5e2}
.adv i{flex:none;width:6mm;height:6mm;border-radius:50%;background:#38B24A;color:#062631;font-style:normal;font-weight:800;font-size:7pt;display:flex;align-items:center;justify-content:center;margin-top:.3mm}
.adv b{display:block;font-size:9pt}
.ben{display:flex;flex-direction:column;gap:.6mm;padding:3mm 0 3mm 4mm;border-left:2.2pt solid #38B24A;margin-bottom:2.6mm}
.ben b{font-size:9.6pt}
.pic{width:100%;border-radius:3mm;object-fit:cover}
.quote{font-family:D;font-weight:700;font-size:11pt;line-height:1.25;color:#062631}
.row{display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid rgba(255,255,255,.12)}
.row div{padding:2.2mm 1.5mm;font-size:7.6pt;line-height:1.3}
.row .r{color:#f0b35a}.row .s{color:#e9f1ef;background:rgba(95,208,111,.08)}
.rh div{font-weight:700;font-size:7pt;letter-spacing:1pt;text-transform:uppercase}
.step{display:flex;gap:3mm;margin-bottom:3.4mm}.step .n{flex:none;width:8mm;height:8mm;border-radius:2mm;background:#062631;color:#5fd06f;font-family:D;font-weight:800;font-size:11pt;display:flex;align-items:center;justify-content:center}
.offer{background:#062631;color:#e9f1ef;border-radius:4mm;padding:5mm;position:relative;overflow:hidden;margin:2mm 0 5mm}
.offer .big{font-family:D;font-weight:800;font-size:46pt;line-height:.95;color:#5fd06f;letter-spacing:-1.5pt}
.ring{position:absolute;border-radius:50%;border:1px solid rgba(255,255,255,.08)}
.foot{margin-top:auto;font-size:6.6pt;color:#7d9097}
.contact{font-size:10.5pt;line-height:2;font-weight:600}
.contact span{color:#5fd06f;font-weight:700;display:inline-block;width:20mm;font-size:6.6pt;letter-spacing:1.4pt;text-transform:uppercase}
"""

STAGES = ["Расчёт", "Обработка", "Покраска", "Сборка", "Упаковка"]

def page(a):
    ben = "".join(f'<div class="ben"><b>{t}</b><span class="muted">{d}</span></div>' for t, d in a["benefits"])
    stages = "".join(f'<span style="display:inline-block;margin:0 1.5mm 1.5mm 0" class="tag">{i+1}. {s}</span>' for i, s in enumerate(STAGES))
    outside = f"""
<div class="sheet">
 <!-- внутренний клапан: риски -->
 <div class="p mid">
  <div class="ring" style="width:120mm;height:120mm;right:-60mm;top:-50mm"></div>
  <div class="k">Риски и наши преимущества</div>
  <h2>Алюминий не прощает ошибок — завод их исключает</h2>
  <p class="muted" style="margin-bottom:4mm">Ветер до 30 м/с срывает облицовку с домов: Алматы — 2023, Астана — 2024 и 2026. Фасаду нужен точный расчёт и надёжные узлы.</p>
  <div class="row rh"><div class="r">Риск</div><div class="s" style="color:#5fd06f">Решение GREENTE</div></div>
  <div class="row"><div class="r">Ошибка статики — конструкцию вырывает ветром</div><div class="s">Расчёт ветровой нагрузки, статики и узлов</div></div>
  <div class="row"><div class="r">Ручная сборка — перекосы, щели, протечки</div><div class="s">Заводская сборка по ГОСТу, ±0,1 мм</div></div>
  <div class="row"><div class="r">Случайный профиль и комплектующие</div><div class="s">Системы заводов с 35-летним опытом</div></div>
  <div class="row" style="border:none"><div class="r">Цветной профиль ждут 2+ недели</div><div class="s">Своя покраска в Актобе</div></div>
  <img class="pic" src="v_84.jpg" style="height:62mm;margin-top:auto">
  <p class="muted" style="margin-top:2mm;font-size:7pt">Линия порошковой покраски GREENTE, Актобе</p>
 </div>
 <!-- задняя сторона: контакты -->
 <div class="p dark">
  <div class="k">Контакты</div>
  <h2 style="font-size:17pt">Пришлите проект — рассчитаем изделия</h2>
  <p class="muted" style="margin-bottom:5mm">Расчёт с ценой по условиям открытия — за [3] рабочих дня.</p>
  <div class="contact"><span>Сайт</span>greente.kz<br><span>Instagram</span>@greente_gt<br><span>Почта</span>info@greente.kz<br><span>Телефон</span>[телефон]<br><span>Завод</span>Актобе, [адрес]</div>
  <div style="margin-top:auto"><img src="logo_light.png" class="logo"></div>
 </div>
 <!-- обложка -->
 <div class="p dark" style="padding:0">
  <img class="bg" src="{a['img']}"><div class="shade"></div>
  <div class="z" style="padding:11mm 9mm 10mm">
   <img src="logo_light.png" class="logo">
   <div style="flex:1;position:relative">
     <div class="badge" style="position:absolute;right:0;top:12mm"><b>−50%</b><span>до 31 декабря<br>2026</span></div>
   </div>
   <div class="k">Предложение {a['n']} · открытие завода</div>
   <h1 style="margin:2mm 0 3mm">{a['who']}</h1>
   <p style="font-size:10.5pt;font-weight:600;line-height:1.3">{a['head']}</p>
  </div>
 </div>
</div>"""
    inside = f"""
<div class="sheet">
 <!-- кто мы -->
 <div class="p light">
  <div class="k">Кто мы</div>
  <h2>Профессионалы узкой специализации — только алюминиевые конструкции</h2>
  <div class="stats">
   <div class="stat"><b>35 лет</b><span class="muted">опыта у заводов профиля, которые мы представляем</span></div>
   <div class="stat"><b>3 200 м²</b><span class="muted">собственного завода в Актобе</span></div>
   <div class="stat"><b>±0,1 мм</b><span class="muted">точность обработки профиля</span></div>
   <div class="stat"><b>5 этапов</b><span class="muted">на одной площадке</span></div>
  </div>
  <div style="margin-bottom:3mm">{stages}</div>
  <div class="adv"><i>1</i><div><b>Сборка по ГОСТу</b><span class="muted">за изделие отвечает завод</span></div></div>
  <div class="adv"><i>2</i><div><b>Сроки быстрее</b><span class="muted">без ожидания окрашенного профиля</span></div></div>
  <div class="adv"><i>3</i><div><b>Короче цепочка</b><span class="muted">напрямую с завода</span></div></div>
  <div class="adv"><i>4</i><div><b>Качество — наша задача</b><span class="muted">не дешёвые и не дорогие — честная цена завода</span></div></div>
 </div>
 <!-- выгоды аудитории -->
 <div class="p white">
  <div class="k">{a['who']}</div>
  <h2>{a['head']}</h2>
  <p class="muted" style="margin-bottom:4mm">{a['lead']}</p>
  {ben}
  <img class="pic" src="{a['img2']}" style="height:34mm;margin-top:auto">
  <p class="quote" style="margin-top:3mm">{a['quote']}</p>
 </div>
 <!-- акция и шаги -->
 <div class="p light">
  <div class="k">Акция открытия</div>
  <h2>Пришлите проект до конца года</h2>
  <div class="offer">
   <div class="ring" style="width:60mm;height:60mm;right:-22mm;top:-24mm"></div>
   <div class="ring" style="width:36mm;height:36mm;right:-10mm;top:-12mm;border-color:rgba(95,208,111,.3)"></div>
   <div class="big">−50%</div>
   <p style="font-weight:600;margin-top:2mm">для проектов, присланных до 31 декабря 2026</p>
  </div>
  <div class="step"><div class="n">1</div><div><b>Пришлите проект</b><br><span class="muted">чертежи или задание — на greente.kz или менеджеру</span></div></div>
  <div class="step"><div class="n">2</div><div><b>Получите расчёт</b><br><span class="muted">изделия, цена со скидкой и сроки за [3] рабочих дня</span></div></div>
  <div class="step"><div class="n">3</div><div><b>Производство</b><br><span class="muted">изготовление, покраска, упаковка, доставка</span></div></div>
  <img class="pic" src="v_72.jpg" style="height:30mm;margin-top:auto">
  <p class="foot" style="margin-top:3mm">Скидка 50% — [на что распространяется: уточнить]. Условия у менеджера. Долговечность в каждом миллиметре.</p>
 </div>
</div>"""
    return f"<!doctype html><html lang=ru><head><meta charset=utf-8><style>{CSS}</style></head><body>{outside}{inside}</body></html>"

here = os.path.abspath(".")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    for a in A:
        f = f"b_{a['key']}.html"
        open(f, "w", encoding="utf-8").write(page(a))
        pg = br.new_page()
        pg.goto("file://" + here + "/" + f)
        pg.wait_for_timeout(600)
        pg.pdf(path=f"/home/claude/GREENTE_buklet_{a['key']}.pdf", print_background=True, prefer_css_page_size=True)
        pg.close()
    br.close()
print("ok")
