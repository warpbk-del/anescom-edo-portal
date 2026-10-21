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
            ("Минимум расходов", "оптимизация раскроя, автоматика без человеческого фактора")],
  quote="Здание принимают без замечаний — за изделие отвечает завод."),
 dict(key="okonnye_kompanii", n="02", who="Оконным компаниям", img="v_99.jpg", img2="v_108.jpg",
  head="Качество завода — без своего цеха",
  lead="Продавайте и монтируйте. Изготовление по вашим замерам берём на себя.",
  benefits=[("Не нужно своё помещение", "и сборщики — изготовим по вашим замерам"),
            ("Качество по ГОСТу", "заводская сборка, брака сборки нет"),
            ("Расчёт статики и узлов", "алюминий — сложный продукт, ошибки исключаем"),
            ("Без отходов и ошибок", "оптимизация раскроя и автоматика; партнёрская цена")],
  quote="Ваша задача — клиент и монтаж. Производство — наша."),
 dict(key="arhitektory_predprinimateli", n="03", who="Архитекторам и пред\u00adпринимателям", img="entrance-group-photoreal-v2.webp", img2="tws65-assembly-turn.webp",
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
body{font-family:F,sans-serif;color:#2B4B5C;font-size:8.6pt;line-height:1.45}
.sheet{width:297mm;height:210mm;display:grid;grid-template-columns:99mm 99mm 99mm;page-break-after:always;overflow:hidden;background:#fff}
.p{position:relative;overflow:hidden;padding:11mm 9mm 10mm;display:flex;flex-direction:column;background:#fff}
.p+.p{border-left:0.3mm solid #E4ECEA}
.dark{background:#2B4B5C;color:#fff}.light{background:#F3F7F6}.white{background:#fff}
.k{font-size:6.6pt;font-weight:700;letter-spacing:2.2pt;text-transform:uppercase;color:#46B254}
h1,h2{font-family:D,F,sans-serif;font-weight:800;letter-spacing:-.3pt;color:#2B4B5C}
.dark h1,.dark h2{color:#fff}
h1{font-size:24pt;line-height:1.04}
h2{font-size:14.5pt;line-height:1.14;margin:2mm 0 4mm}
.muted{color:#6B8290}.dark .muted{color:#C6D6DC}
.bg{position:absolute;left:0;top:0;width:100%;height:118mm;object-fit:cover}
.z{position:relative;z-index:1;display:flex;flex-direction:column;height:100%}
.logo{width:58mm}
.badge{width:30mm;height:30mm;border-radius:50%;background:#46B254;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;border:1.2mm solid #fff}
.badge b{font-family:D;font-size:21pt;line-height:1}.badge span{font-size:6pt;font-weight:700;line-height:1.2;margin-top:1mm}
.tag{display:inline-block;background:#E8F5EA;color:#2B4B5C;font-weight:700;font-size:7pt;padding:1.2mm 3mm;border-radius:10mm}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:3mm;margin:2mm 0 4mm}
.stat{background:#fff;border-radius:3mm;padding:3mm;border:0.3mm solid #E4ECEA}.stat b{font-family:D;font-size:15pt;color:#46B254;display:block;line-height:1.05}
.adv{display:flex;gap:3mm;align-items:flex-start;padding:2.4mm 0;border-top:0.3mm solid #E4ECEA}
.adv i{flex:none;width:6mm;height:6mm;border-radius:50%;background:#46B254;color:#fff;font-style:normal;font-weight:800;font-size:7pt;display:flex;align-items:center;justify-content:center;margin-top:.3mm}
.adv b{display:block;font-size:9pt}
.ben{display:flex;flex-direction:column;gap:.6mm;padding:2.6mm 0 2.6mm 4mm;border-left:0.8mm solid #46B254;margin-bottom:2.6mm}
.ben b{font-size:9.6pt}
.pic{width:100%;border-radius:3mm;object-fit:cover}
.quote{font-family:D;font-weight:700;font-size:11pt;line-height:1.25;color:#2B4B5C}
.row{display:grid;grid-template-columns:1fr 1fr;border-bottom:0.3mm solid #E4ECEA}
.row div{padding:2.2mm 2mm;font-size:7.6pt;line-height:1.3}
.row .r{color:#6B8290}.row .s{color:#2B4B5C;font-weight:600;background:#EEF7F0}
.rh div{font-weight:700;font-size:6.8pt;letter-spacing:1pt;text-transform:uppercase}
.rh .r{background:#F3F7F6}.rh .s{background:#46B254;color:#fff}
.step{display:flex;gap:3mm;margin-bottom:3.4mm}.step .n{flex:none;width:8mm;height:8mm;border-radius:2mm;background:#2B4B5C;color:#fff;font-family:D;font-weight:800;font-size:11pt;display:flex;align-items:center;justify-content:center}
.offer{background:#46B254;color:#fff;border-radius:4mm;padding:5mm;margin:2mm 0 5mm}
.offer .big{font-family:D;font-weight:800;font-size:46pt;line-height:.95;letter-spacing:-1.5pt}
.ring{display:none}
.foot{margin-top:auto;font-size:6.6pt;color:#8A9EA8}
.contact{font-size:10.5pt;line-height:2;font-weight:600}
.contact span{color:#9DDCA6;font-weight:700;display:inline-block;width:20mm;font-size:6.6pt;letter-spacing:1.4pt;text-transform:uppercase}
"""

STAGES = ["Расчёт", "Обработка", "Покраска", "Сборка", "Упаковка"]

def page(a):
    ben = "".join(f'<div class="ben"><b>{t}</b><span class="muted">{d}</span></div>' for t, d in a["benefits"])
    stages = "".join(f'<span style="display:inline-block;margin:0 1.5mm 1.5mm 0" class="tag">{i+1}. {s}</span>' for i, s in enumerate(STAGES))
    outside = f"""
<div class="sheet">
 <!-- внутренний клапан: риски -->
 <div class="p white">
  <div class="ring" style="width:120mm;height:120mm;right:-60mm;top:-50mm"></div>
  <div class="k">Почему выгодно заказывать у нас</div>
  <h2>Покраска и сборка на заводе — риски исключены</h2>
  <div class="row rh"><div class="r">Риск «где придётся»</div><div class="s">У GREENTE</div></div>
  <div class="row"><div class="r">Без химподготовки краска отслаивается</div><div class="s">Ванны химподготовки перед окраской</div></div>
  <div class="row"><div class="r">Тонкий слой — коррозия под краской</div><div class="s">Контроль толщины: на улицу от 60 мкм</div></div>
  <div class="row"><div class="r">Разнотон между партиями</div><div class="s">Весь объект — одна партия RAL</div></div>
  <div class="row"><div class="r">Угол «на глаз» — щели, перекос</div><div class="s">Опрессовка углов на прессе 68 кН</div></div>
  <div class="row"><div class="r">Нет дренажа — протечки, продувание</div><div class="s">2 контура уплотнений и дренаж по ГОСТу</div></div>
  <div class="row" style="border:none"><div class="r">Нет расчёта на ветер — риск на высоте</div><div class="s">Расчёт ветровой нагрузки до запуска</div></div>
  <img class="pic" src="v_84.jpg" style="height:44mm;margin-top:auto">
  <p class="muted" style="margin-top:2mm;font-size:7pt">Сборка — по ГОСТ 21519-2022. Линия покраски GREENTE, Актобе</p>
 </div>
 <!-- задняя сторона: контакты -->
 <div class="p dark">
  <div class="k">Контакты</div>
  <h2 style="font-size:17pt">Пришлите проект — рассчитаем изделия</h2>
  <p class="muted" style="margin-bottom:5mm">Расчёт с ценой по условиям открытия — за [3] рабочих дня.</p>
  <div class="contact"><span>Сайт</span>greente.kz<br><span>Instagram</span>@greente_gt<br><span>Почта</span>info@greente.kz<br><span>Телефон</span>[телефон]<br><span>Завод</span>Актобе, [адрес]</div>
  <div style="margin-top:auto;background:#fff;border-radius:2.5mm;padding:3mm 4mm;align-self:flex-start"><img src="logo.png" class="logo" style="display:block"></div>
 </div>
 <!-- обложка -->
 <div class="p white" style="padding:0">
  <img class="bg" src="{a['img']}">
  <div class="z" style="padding:9mm 9mm 10mm">
   <div style="height:100mm;position:relative">
     <div style="background:#fff;border-radius:2.5mm;padding:2.5mm 3.5mm;display:inline-block"><img src="logo.png" class="logo" style="width:50mm;display:block"></div>
     <div class="badge" style="position:absolute;right:0;bottom:-6mm"><b>−50%</b><span>до 31 декабря<br>2026</span></div>
   </div>
   <div style="flex:1"></div>
   <div class="k">Предложение {a['n']} · открытие завода</div>
   <h1 style="margin:2mm 0 3mm">{a['who']}</h1>
   <p style="font-size:10.5pt;font-weight:600;line-height:1.3;color:#6B8290">{a['head']}</p>
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
  <p style="background:#EEF7F0;border-radius:2.5mm;padding:2.5mm 3mm;margin-bottom:3mm;font-weight:600">Оптимизация раскроя и автоматика: минимум отходов и расходов, без ошибок человеческого фактора.</p>
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
