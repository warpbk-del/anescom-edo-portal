import os, json
from playwright.sync_api import sync_playwright
A=[
 dict(key="zastroyshchiki",who="Застройщикам",title="Качественные узлы и заводская сборка по ГОСТу",img="hero-glass-towers.webp",
  benefits=[("Качественные узлы","рассчитаны конструктором и собраны на заводе по ГОСТу"),("Профиль заводов с 35-летним опытом","проверенные системы"),("Сроки быстрее","покраска в Актобе, без ожидания поставки"),("Короче цепочка","напрямую с завода, без посредников")],
  why="Без наценки посредника, меньше риска в каждом контракте, за изделие отвечает завод."),
 dict(key="okonnye_kompanii",who="Оконным компаниям",title="Ваша мощность без своего цеха",img="v_99.jpg",
  benefits=[("По вашим замерам","изготовление без своих сборщиков и станков"),("Партнёрская цена","с первого заказа"),("Профессиональная сборка","брака сборки нет — отвечает завод"),("Заявки на монтаж","с сайта greente.kz — нашим партнёрам")],
  why="Ваша задача — клиент и монтаж. Изготовление, покраска и упаковка — на заводе."),
 dict(key="arhitektory_predprinimateli",who="Архитекторам и предпринимателям",title="Идея из проекта — в готовом изделии",img="entrance-group-photoreal-v2.webp",
  benefits=[("Расчёт узлов и 3D-модель","бесплатно, до производства"),("Архитектору","партнёрское вознаграждение [__]% за реализованный проект"),("Предпринимателю","изделия по ГОСТу, монтаж наших партнёров"),("Цвет под проект","своя линия порошковой покраски")],
  why="Здание принимают без замечаний, а деньги идут в здание, а не в наценки."),
]
CSS="""
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Regular.otf);font-weight:400}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-SemiBold.otf);font-weight:600}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/Inter-Bold.otf);font-weight:700}
@font-face{font-family:F;src:url(file:///usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf);font-weight:800}
@page{size:297mm 210mm;margin:0}
*{box-sizing:border-box}body{margin:0;font-family:F,sans-serif;color:#13303b;font-size:9.5pt;line-height:1.4}
.sheet{width:297mm;height:210mm;display:grid;grid-template-columns:99mm 99mm 99mm;page-break-after:always;overflow:hidden}
.p{padding:12mm 10mm;position:relative;overflow:hidden}
.dark{background:#062631;color:#eef4f2}.green{background:#38B24A;color:#062631}.light{background:#f4f7f6}
.k{font-size:7.5pt;font-weight:700;letter-spacing:2pt;text-transform:uppercase;color:#38B24A}
.green .k{color:#062631}
h1{font-family:F;font-weight:800;font-size:25pt;line-height:1.05;margin:3mm 0 4mm;letter-spacing:-.4pt}
h2{font-weight:800;font-size:16pt;line-height:1.1;margin:2mm 0 5mm}
.big{font-weight:800;font-size:34pt;line-height:1;letter-spacing:-1pt}
.b{display:flex;flex-direction:column;gap:1mm;padding:3.2mm 0;border-bottom:1px solid #d5e0dd}.b b{font-size:11pt}
.dark .b{border-color:rgba(255,255,255,.15)}
.deal{border-radius:4mm;padding:5mm;margin-bottom:4mm}
.cover img.ph{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.5}
.cover .in{position:relative;height:100%;display:flex;flex-direction:column}
.logo{width:62mm;background:#fff;border-radius:2mm;padding:2.5mm 3mm}
.step{display:flex;gap:4mm;align-items:flex-start;margin-bottom:5mm}.step .n{flex:none;width:9mm;height:9mm;border-radius:50%;background:#38B24A;color:#062631;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:11pt}
.small{font-size:7.5pt;opacity:.8}
.pic{width:100%;height:40mm;object-fit:cover;border-radius:3mm;margin:3mm 0}
"""
def page(a):
    ben="".join(f'<div class="b"><b>{t}</b><span>{d}</span></div>' for t,d in a["benefits"])
    out=f"""
<div class="sheet">
 <div class="p light"><div class="k">О заводе</div><h2>Собственный завод полного цикла в Актобе</h2>
  <div class="big" style="color:#13303b">3 200 м²</div><p>производственная площадь</p>
  <img class="pic" src="v_84.jpg">
  <p><b>5 этапов на одной площадке:</b> расчёт, обработка, покраска, сборка, упаковка. Ни один этап не отдаётся на сторону.</p>
  <p><b>±0,1 мм</b> — точность реза на обрабатывающем центре.</p></div>
 <div class="p dark" style="display:flex;flex-direction:column;justify-content:space-between">
  <div><div class="k">Контакты</div><h2>Пришлите проект — рассчитаем изделия</h2>
  <p style="font-size:12pt;line-height:1.9"><b>greente.kz</b><br>@greente_gt<br>info@greente.kz<br>[телефон]</p>
  <p>Актобе · [адрес завода]</p></div>
  <img src="logo.png" class="logo">
 </div>
 <div class="p dark cover"><img class="ph" src="{a['img']}"><div class="in">
  <img src="logo.png" class="logo">
  <div style="flex:1"></div>
  <div class="k">Предложение открытия завода</div>
  <h1>{a['who']}</h1>
  <p style="font-size:12pt;font-weight:600">{a['title']}</p>
  <div class="deal green" style="margin-top:4mm;margin-bottom:0"><b>−50%</b> для проектов, присланных до 31 декабря 2026</div>
 </div></div>
</div>
<div class="sheet">
 <div class="p light"><div class="k">Ваши выгоды</div><h2>{a['title']}</h2>{ben}
  <p style="margin-top:5mm;font-weight:600">{a['why']}</p></div>
 <div class="p dark"><div class="k">Акция открытия</div><h2>Чем раньше проект — тем больше выгода</h2>
  <div class="deal green"><div class="small" style="opacity:1;font-weight:700">Проект до 31 декабря 2026</div><div class="big" style="font-size:54pt">−50%</div></div>
  <p style="font-weight:600">Мы — узкоспециализированная компания: только алюминиевые конструкции, профиль заводов с 35-летним опытом.</p>
  <p class="small">Скидка 50% — [на что распространяется: уточнить]. Для проектов, присланных в срок. Объект и объём фиксируются в заявке. Подробные условия — у менеджера.</p></div>
 <div class="p light"><div class="k">Как получить</div><h2>Три шага</h2>
  <div class="step"><div class="n">1</div><div><b>Пришлите проект</b><br>чертежи или задание на объект — на greente.kz или менеджеру</div></div>
  <div class="step"><div class="n">2</div><div><b>Получите расчёт</b><br>изделия, цена со скидкой и сроки — за [3] рабочих дня</div></div>
  <div class="step"><div class="n">3</div><div><b>Производство</b><br>изготовление, покраска, упаковка и доставка</div></div>
  <img class="pic" src="factory-aluminium-cnc.jpg" style="height:46mm">
  <p style="font-weight:700;color:#2f9a40">Долговечность в каждом миллиметре</p></div>
</div>"""
    return f"<!doctype html><html lang=ru><head><meta charset=utf-8><style>{CSS}</style></head><body>{out}</body></html>"
here=os.path.abspath('.')
with sync_playwright() as p:
    br=p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    for a in A:
        f=f"b_{a['key']}.html"; open(f,"w",encoding="utf-8").write(page(a))
        pg=br.new_page(); pg.goto("file://"+here+"/"+f); pg.wait_for_timeout(500)
        pg.pdf(path=f"/home/claude/GREENTE_buklet_{a['key']}.pdf",print_background=True,prefer_css_page_size=True); pg.close()
    br.close()
print("ok")
