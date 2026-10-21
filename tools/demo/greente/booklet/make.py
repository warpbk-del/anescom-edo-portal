# Буклеты GREENTE (трифолд A4, 2 стороны) — по одному на аудиторию.
import os
from playwright.sync_api import sync_playwright

A = [
 dict(key="zastroyshchiki", n="01", who="Застройщикам", img="home-audience-developers-v1.webp", img2="/home/claude/vstill/p_section.jpg",
  head="Качественные узлы и заводская сборка по ГОСТу",
  lead="Фасады, окна и витражи для вашего объекта — рассчитаны конструктором и собраны на заводе.",
  benefits=[("Качественные узлы", "каждый узел рассчитан и собран на заводе"),
            ("Статика и ветровая нагрузка", "считаем до производства — без риска для объекта"),
            ("Сроки в разы быстрее", "окрашенный профиль с завода ждут до 60 дней — мы красим сами"),
            ("Минимум расходов", "оптимизация раскроя, автоматика без человеческого фактора")],
  quote="Здание принимают без замечаний — за изделие отвечает завод."),
 dict(key="okonnye_kompanii", n="02", who="Оконным компаниям", img="home-audience-dealers-v1.webp", img2="/home/claude/vstill/i_lockholes.jpg",
  head="Качество завода — без своего цеха",
  lead="Продавайте и монтируйте. Изготовление по вашим замерам берём на себя.",
  benefits=[("Не нужно своё помещение", "и сборщики — изготовим по вашим замерам"),
            ("Качество по ГОСТу", "заводская сборка, брака сборки нет"),
            ("Расчёт статики и узлов", "алюминий — сложный продукт, ошибки исключаем"),
            ("Без отходов и ошибок", "оптимизация раскроя и автоматика; партнёрская цена")],
  quote="Ваша задача — клиент и монтаж. Производство — наша."),
 dict(key="arhitektory_predprinimateli", n="03", who="Архитекторам и пред\u00adпринимателям", img="home-project-background-v1.webp", img2="/home/claude/vstill/d_saw.jpg",
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
body{font-family:F,sans-serif;color:#E7EFEE;font-size:8.4pt;line-height:1.42}
.sheet{width:297mm;height:210mm;display:grid;grid-template-columns:99mm 99mm 99mm;page-break-after:always;overflow:hidden;background:#0B1F27}
.p{position:relative;overflow:hidden;padding:10mm 8.5mm 9mm;display:flex;flex-direction:column;background:#0B1F27}
.p+.p{border-left:0.25mm solid #1D3944}
.alt{background:#10293300;background:#0F2833}
.k{display:inline-block;align-self:flex-start;background:#46B254;color:#0B1F27;font-size:6.4pt;font-weight:800;letter-spacing:1.6pt;text-transform:uppercase;padding:1.2mm 2.6mm;margin-bottom:2.5mm}
h1,h2{font-family:D,F,sans-serif;font-weight:800;letter-spacing:-.3pt;color:#fff}
h1{font-size:24pt;line-height:1.03}
h2{font-size:14pt;line-height:1.14;margin:0 0 3.5mm}
h2 em{font-style:normal;color:#5FD06F}
.muted{color:#9FB6BE}
.bar{background:#46B254;color:#0B1F27;font-weight:700;font-size:7.6pt;padding:1.6mm 3mm;margin:3mm 0 2mm}
.bar.grey{background:#1D3944;color:#C9D8DD}
.logo{width:56mm}
.plate{background:#fff;padding:2.4mm 3.4mm;display:inline-block}
.bg{position:absolute;left:0;top:0;width:100%;height:130mm;object-fit:cover}
.fade{position:absolute;left:0;top:70mm;width:100%;height:60mm;background:linear-gradient(180deg,rgba(11,31,39,0) 0%,#0B1F27 100%)}
.z{position:relative;z-index:1;display:flex;flex-direction:column;height:100%}
.badge{width:30mm;height:30mm;border-radius:50%;background:#46B254;color:#0B1F27;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;border:1mm solid #0B1F27;outline:0.5mm solid #46B254}
.badge b{font-family:D;font-size:21pt;line-height:1}.badge span{font-size:6pt;font-weight:800;line-height:1.2;margin-top:1mm}
.tag{display:inline-block;border:0.3mm solid #46B254;color:#5FD06F;font-weight:700;font-size:6.8pt;padding:1mm 2.4mm}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:2.5mm;margin:1mm 0 3.5mm}
.stat{background:#132F3B;padding:3mm;border-left:1mm solid #46B254}.stat b{font-family:D;font-size:15pt;color:#5FD06F;display:block;line-height:1.05}
.stat span{color:#9FB6BE;font-size:7.4pt}
.adv{display:flex;gap:3mm;align-items:flex-start;padding:2.2mm 0;border-top:0.25mm solid #1D3944}
.adv i{flex:none;width:6mm;height:6mm;background:#46B254;color:#0B1F27;font-style:normal;font-weight:800;font-size:7pt;display:flex;align-items:center;justify-content:center;margin-top:.3mm}
.adv b{display:block;font-size:9pt;color:#fff}
.ben{display:flex;flex-direction:column;gap:.5mm;padding:2.4mm 0 2.4mm 3.5mm;border-left:0.9mm solid #46B254;margin-bottom:2.4mm;background:linear-gradient(90deg,#132F3B,rgba(19,47,59,0))}
.ben b{font-size:9.4pt;color:#fff}
.pic{width:100%;object-fit:cover;border-bottom:1.2mm solid #46B254}
.quote{font-family:D;font-weight:700;font-size:10.5pt;line-height:1.25;color:#5FD06F}
.row{display:grid;grid-template-columns:1fr 1fr;border-bottom:0.25mm solid #1D3944}
.row div{padding:1.9mm 2mm;font-size:7.3pt;line-height:1.28}
.row .r{color:#9FB6BE}.row .s{color:#fff;font-weight:600;background:#132F3B}
.rh{border:none}.rh div{font-weight:800;font-size:6.6pt;letter-spacing:1pt;text-transform:uppercase;padding:1.6mm 2mm}
.rh .r{background:#1D3944;color:#C9D8DD}.rh .s{background:#46B254;color:#0B1F27}
.step{display:flex;gap:3mm;margin-bottom:3.2mm}.step .n{flex:none;width:8mm;height:8mm;background:#46B254;color:#0B1F27;font-family:D;font-weight:800;font-size:11pt;display:flex;align-items:center;justify-content:center}
.step b{color:#fff}
.offer{background:#46B254;color:#0B1F27;padding:5mm;margin:1mm 0 5mm;position:relative}
.offer .big{font-family:D;font-weight:800;font-size:48pt;line-height:.95;letter-spacing:-1.5pt}
.ring{display:none}
.foot{margin-top:auto;font-size:6.4pt;color:#7F98A1}
.contact{font-size:10.5pt;line-height:2;font-weight:600;color:#fff}
.contact span{color:#5FD06F;font-weight:800;display:inline-block;width:20mm;font-size:6.4pt;letter-spacing:1.4pt;text-transform:uppercase}
"""

STAGES = ["Расчёт", "Обработка", "Покраска", "Сборка", "Упаковка"]

def page(a):
    ben = "".join(f'<div class="ben"><b>{t}</b><span class="muted">{d}</span></div>' for t, d in a["benefits"])
    stages = "".join(f'<span style="display:inline-block;margin:0 1.5mm 1.5mm 0" class="tag">{i+1}. {s}</span>' for i, s in enumerate(STAGES))
    outside = f"""
<div class="sheet">
 <!-- внутренний клапан: риски -->
 <div class="p alt">
  <div class="k">Почему выгодно заказывать у нас</div>
  <h2>Покраска и сборка на заводе — <em>риски исключены</em></h2>
  <div class="row rh"><div class="r">Риск «где придётся»</div><div class="s">У GREENTE</div></div>
  <div class="row"><div class="r">Без химподготовки краска отслаивается</div><div class="s">Ванны химподготовки перед окраской</div></div>
  <div class="row"><div class="r">Тонкий слой — коррозия под краской</div><div class="s">Контроль толщины: на улицу от 60 мкм</div></div>
  <div class="row"><div class="r">Разнотон между партиями</div><div class="s">Весь объект — одна партия RAL</div></div>
  <div class="row"><div class="r">Окрашенный профиль с завода — до 50–70 дней</div><div class="s">Склад неокрашенного профиля, красим за дни</div></div>
  <div class="row"><div class="r">Угол «на глаз» — щели, перекос</div><div class="s">Опрессовка углов на прессе 68 кН</div></div>
  <div class="row"><div class="r">Нет дренажа — протечки, продувание</div><div class="s">2 контура уплотнений и дренаж по ГОСТу</div></div>
  <div class="row" style="border:none"><div class="r">Нет расчёта на ветер — риск на высоте</div><div class="s">Расчёт ветровой нагрузки до запуска</div></div>
  <img class="pic" src="/home/claude/vstill/k_profiles.jpg" style="height:44mm;margin-top:auto">
  <p class="muted" style="margin-top:2mm;font-size:7pt">Сборка — по ГОСТ 21519-2022. Линия покраски GREENTE, Актобе</p>
 </div>
 <!-- задняя сторона: контакты -->
 <div class="p">
  <div class="k">Контакты</div>
  <h2 style="font-size:17pt">Пришлите проект — рассчитаем изделия</h2>
  <p class="muted" style="margin-bottom:5mm">Расчёт с ценой по условиям открытия — за [3] рабочих дня.</p>
  <div class="contact"><span>Сайт</span>greente.kz<br><span>Instagram</span>@greente_gt<br><span>Почта</span>info@greente.kz<br><span>Телефон</span>+7 777 111 2128<br><span>Завод</span>Актобе, Богословская трасса, 108Д</div>
  <img class="pic" src="home-audience-dealers-v1.webp" style="height:52mm;margin:auto 0 5mm">
  <div class="plate" style="align-self:flex-start"><img src="logo.png" class="logo" style="display:block"></div>
 </div>
 <!-- обложка -->
 <div class="p" style="padding:0">
  <img class="bg" src="{a['img']}"><div class="fade"></div>
  <div class="z" style="padding:9mm 8.5mm 9mm">
   <div><div class="plate"><img src="logo.png" class="logo" style="width:48mm;display:block"></div></div>
   <div style="flex:1;position:relative"><div class="badge" style="position:absolute;right:0;top:62mm"><b>−50%</b><span>до 31 декабря<br>2026</span></div></div>
   <div class="k">Предложение {a['n']} · открытие завода</div>
   <h1 style="margin:1mm 0 3mm">{a['who']}</h1>
   <div class="bar" style="margin:0 0 3mm;font-size:8.6pt">{a['head']}</div>
   <p class="muted" style="font-size:7.6pt">Завод алюминиевых конструкций полного цикла · Актобе · greente.kz</p>
  </div>
 </div>
</div>"""
    inside = f"""
<div class="sheet">
 <!-- кто мы -->
 <div class="p alt">
  <div class="k">Кто мы</div>
  <h2>Профессионалы узкой специализации — только алюминиевые конструкции</h2>
  <div class="stats">
   <div class="stat"><b>35 лет</b><span class="muted">опыта у заводов профиля, которые мы представляем</span></div>
   <div class="stat"><b>3 200 м²</b><span class="muted">собственного завода в Актобе</span></div>
   <div class="stat"><b>±0,1 мм</b><span class="muted">точность обработки профиля</span></div>
   <div class="stat"><b>5 этапов</b><span class="muted">на одной площадке</span></div>
  </div>
  <div style="margin-bottom:3mm">{stages}</div>
  <p class="bar" style="margin:0 0 3mm">Оптимизация раскроя и автоматика: минимум отходов и расходов, без ошибок человеческого фактора.</p>
  <div class="adv"><i>1</i><div><b>Сборка по ГОСТу</b><span class="muted">за изделие отвечает завод</span></div></div>
  <div class="adv"><i>2</i><div><b>Сроки в разы быстрее</b><span class="muted">не ждём окрашенный профиль до 60 дней</span></div></div>
  <div class="adv"><i>3</i><div><b>Короче цепочка</b><span class="muted">напрямую с завода</span></div></div>
  <div class="adv"><i>4</i><div><b>Качество — наша задача</b><span class="muted">не дешёвые и не дорогие — честная цена завода</span></div></div>
 </div>
 <!-- выгоды аудитории -->
 <div class="p">
  <div class="k">{a['who']}</div>
  <h2>{a['head']}</h2>
  <p class="muted" style="margin-bottom:4mm">{a['lead']}</p>
  {ben}
  <img class="pic" src="{a['img2']}" style="height:34mm;margin-top:auto">
  <p class="quote" style="margin-top:3mm">{a['quote']}</p>
 </div>
 <!-- акция и шаги -->
 <div class="p alt">
  <div class="k">Акция открытия</div>
  <h2>Пришлите проект <em>до конца года</em></h2>
  <div class="offer">
   <div class="ring" style="width:60mm;height:60mm;right:-22mm;top:-24mm"></div>
   <div class="ring" style="width:36mm;height:36mm;right:-10mm;top:-12mm;border-color:rgba(95,208,111,.3)"></div>
   <div class="big">−50%</div>
   <p style="font-weight:600;margin-top:2mm">для проектов, присланных до 31 декабря 2026</p>
  </div>
  <div class="step"><div class="n">1</div><div><b>Пришлите проект</b><br><span class="muted">чертежи или задание — на greente.kz или менеджеру</span></div></div>
  <div class="step"><div class="n">2</div><div><b>Получите расчёт</b><br><span class="muted">изделия, цена со скидкой и сроки за [3] рабочих дня</span></div></div>
  <div class="step"><div class="n">3</div><div><b>Производство</b><br><span class="muted">изготовление, покраска, упаковка, доставка</span></div></div>
  <img class="pic" src="/home/claude/vstill/c_spindle.jpg" style="height:30mm;margin-top:auto">
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
