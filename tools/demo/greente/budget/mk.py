from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment
wb=Workbook(); ws=wb.active; ws.title="Бюджет"
F="Arial"; teal="2B4B5C"; green="46B254"
hdr=Font(name=F,bold=True,color="FFFFFF",size=10); bold=Font(name=F,bold=True,size=10); norm=Font(name=F,size=10)
inp=Font(name=F,size=10,color="0000FF")
thin=Side(style="thin",color="D5E0DD"); bd=Border(bottom=thin)
ws["A1"]="GREENTE — бюджет открытия завода, 12 ноября 2026, Актобе"; ws["A1"].font=Font(name=F,bold=True,size=14,color=teal)
ws["A2"]="Суммы в тенге. Синие цифры — вводятся вручную (меняйте их), чёрные — формулы. Статус: Утверждено / Предложение / Оценка / Внести."; ws["A2"].font=Font(name=F,size=9,color="5B7079")
ws["A3"]="Гостей (для расчёта питания):"; ws["A3"].font=bold; ws["D3"]=100; ws["D3"].font=inp
cols=["Статья","Подрядчик / источник","Кол-во","Цена за ед.","Сумма","Статус","Комментарий / откуда цифра"]
r=5
for i,c in enumerate(cols):
    x=ws.cell(r,i+1,c); x.font=hdr; x.fill=PatternFill("solid",fgColor=teal); x.alignment=Alignment(vertical="center",wrap_text=True)
rows=[
("1. Ивент-агентство UGROUP.KZ (КП Рамиса Халиуллина)",None),
("Арка из шаров в цветах логотипа","Party Time",1,113000,"Предложение","КП UGROUP.KZ"),
("LED-экран 3×4 м","Арт-Техника",1,375000,"Предложение","КП UGROUP.KZ"),
("Подиум-сцена 3×4 м","Арт-Техника",1,80000,"Предложение","КП UGROUP.KZ"),
("Лого-баннер (бэкдроп) 4×6 м","РА «Город А»",1,92000,"Предложение","КП UGROUP.KZ; в нашем эскизе бэкдроп 6×3 м — сверить размер"),
("Звук: колонки, микрофоны, гарнитура, 8 сателлитов","Арт-Техника",1,220000,"Предложение","КП UGROUP.KZ"),
("Ведущие на казахском и русском (2 чел.)","Р. Халиуллин, Б. Турехан",1,220000,"Предложение","КП UGROUP.KZ"),
("Координация проекта в день события","UGROUP.KZ",1,120000,"Предложение","КП UGROUP.KZ"),
("2. Питание",None),
("Фуршет для гостей","Smart Catering или др.","=D3",9000,"Оценка","В КП UGROUP 115–250 тыс. — это уровень кофе-брейка. Банкет в Актобе в среднем ~20 000 ₸/чел. (Inform.kz, дек. 2025); фуршет дешевле — заложено 9 000 ₸/чел."),
("Кофе-зона на входе (чай, кофе, вода)","кейтеринг",1,60000,"Оценка","Оценка; уточнить у кейтеринга"),
("3. Печать и оформление",None),
("Пресс-волл 3×2 м с каркасом","типография Актобе",1,75000,"Оценка","Широкоформатная печать в Актобе от 1 500 ₸ (Kaspi Объявления) + каркас/монтаж"),
("Буклеты-трифолд A4, 3 вида × 150","типография",450,250,"Оценка","Буклеты A4 в Казахстане: от 18 до 650 ₸/шт (Satu.kz); плотная бумага — ~250 ₸"),
("Бейджи 90×120 + ланъярды","типография",150,450,"Оценка","Оценка: печать + ленты"),
("Официальные приглашения (бланк)","типография",15,1500,"Оценка","Плотная бумага, конверт"),
("Приглашения для бизнеса","типография",100,300,"Оценка","Евроформат; можно электронные — тогда 0"),
("Навигация и таблички у станков (A2/A3 на стойках)","типография",14,3500,"Оценка","10 указателей + 4 таблички станков"),
("Таблички к изделиям, «Резерв» VIP, программа","типография",1,35000,"Оценка","Комплект мелкой печати"),
("Наклейка-логотип на трибуну","типография",1,10000,"Оценка",""),
("Знаки безопасности, лента, разметка","хозмаг",1,20000,"Оценка",""),
("Ленточка для открытия: лента, стойки, ножницы","",1,15000,"Оценка",""),
("4. Съёмка и контент",None),
("Фотограф (4 часа)","фотограф Актобе",4,20000,"Оценка","Фотографы Актобе: 15–30 тыс. ₸ (Kaspi Объявления); за час — уточнить"),
("Видеограф + монтаж ролика","видеограф",1,200000,"Оценка","Видеосъёмка от 25 000 ₸ (Kaspi Объявления) + монтаж итогового ролика"),
("Таргетированная реклама приглашения/итогов","SMM-агентство",1,150000,"Оценка","Бюджет на рекламу, без гонорара агентства"),
("Блогеры (2–3)","",2,75000,"Оценка","Уточнить у SMM-агентства"),
("5. Площадка",None),
("Тепловые пушки (аренда 2 шт. + топливо)","прокат",1,80000,"Оценка","Аренду в Актобе не нашёл; покупка дизельной пушки 30 кВт ~125 000 ₸ (Satu.kz). Возможно, выгоднее купить — пригодится цеху"),
("Уборка цеха до и после","клининг",1,60000,"Оценка",""),
("Вода, салфетки, мелочи, гардероб","",1,40000,"Оценка",""),
("6. Уже готово (впишите фактические суммы)",None),
("Подарочные комплекты","",100,0,"Внести","Готово — внесите стоимость"),
("Флаги в цеху","",1,0,"Внести","Готово"),
("Флешки с логотипом","",1,0,"Внести","Готово"),
("Спецодежда","",1,0,"Внести","Готово"),
("VIP-номера, карта, регистрация","",1,0,"Внести","Готово"),
("Сайт greente.kz","",1,0,"Внести","Готово"),
("SMM-агентство (гонорар)","",1,0,"Внести","Подобрано — внесите сумму договора"),
]
r=6; subtotal_rows=[]; sec_start=None
for row in rows:
    if row[1] is None:
        c=ws.cell(r,1,row[0]); c.font=Font(name=F,bold=True,size=10,color=teal); c.fill=PatternFill("solid",fgColor="EEF7F0")
        for j in range(2,8): ws.cell(r,j).fill=PatternFill("solid",fgColor="EEF7F0")
        r+=1; continue
    name,who,q,p,st,cm=row
    ws.cell(r,1,name).font=norm; ws.cell(r,2,who).font=norm
    cq=ws.cell(r,3,q); cq.font=norm if str(q).startswith("=") else inp
    cp=ws.cell(r,4,p); cp.font=inp
    ws.cell(r,5,f"=C{r}*D{r}").font=norm
    ws.cell(r,6,st).font=Font(name=F,size=10,color=green if st=="Предложение" else ("C0392B" if st=="Внести" else "5B7079"),bold=True)
    ws.cell(r,7,cm).font=Font(name=F,size=9,color="5B7079"); ws.cell(r,7).alignment=Alignment(wrap_text=True,vertical="top")
    for j in range(1,8): ws.cell(r,j).border=bd
    subtotal_rows.append(r); r+=1
first,last=subtotal_rows[0],subtotal_rows[-1]
r+=1
ws.cell(r,1,"Итого по статьям").font=bold; ws.cell(r,5,f"=SUM(E{first}:E{last})").font=bold; tot=r; r+=1
ws.cell(r,1,"Резерв на непредвиденное").font=norm; ws.cell(r,4,0.1).font=inp; ws.cell(r,4).number_format="0%"; ws.cell(r,5,f"=E{tot}*D{r}").font=norm; res=r; r+=1
ws.cell(r,1,"ВСЕГО С РЕЗЕРВОМ").font=Font(name=F,bold=True,size=12,color="FFFFFF"); ws.cell(r,5,f"=E{tot}+E{res}").font=Font(name=F,bold=True,size=12,color="FFFFFF")
for j in range(1,8): ws.cell(r,j).fill=PatternFill("solid",fgColor=green)
grand=r; r+=2
ws.cell(r,1,"В том числе пакет UGROUP.KZ").font=norm; ws.cell(r,5,"=SUM(E7:E13)").font=norm; r+=1
ws.cell(r,1,"Стоимость на одного гостя (с резервом)").font=norm; ws.cell(r,5,f"=E{grand}/D3").font=norm; r+=2
ws.cell(r,1,"Расчёт и оплата по КП UGROUP — напрямую между компанией и каждым подрядчиком (как указано в КП). Цены «Оценка» — ориентиры по открытым объявлениям Актобе/Казахстана, уточнить у поставщиков.").font=Font(name=F,size=9,color="5B7079")
for rr in range(6,grand+3):
    for cc in (4,5): ws.cell(rr,cc).number_format='# ##0" ₸"' if ws.cell(rr,cc).number_format!="0%" else "0%"
ws.column_dimensions["A"].width=50; ws.column_dimensions["B"].width=24; ws.column_dimensions["C"].width=8
ws.column_dimensions["D"].width=13; ws.column_dimensions["E"].width=15; ws.column_dimensions["F"].width=13; ws.column_dimensions["G"].width=60
ws.freeze_panes="A6"
# sources sheet
s2=wb.create_sheet("Источники")
src=[("КП ивент-агентства UGROUP.KZ (Рамис Халиуллин), прислано 21.10.2026","—"),
("Inform.kz — Новогодний корпоратив в цифрах: Актобе 10–35 тыс. ₸/чел., в основном ~20 тыс. (дек. 2025)","https://www.inform.kz/ru/novogodniy-korporativ-v-tsifrah-obzor-tsen-po-kazahstanu"),
("Kaspi Объявления — фотографы мероприятий Актобе: 15–30 тыс. ₸, видеограф от 25 тыс. ₸","https://obyavleniya.kaspi.kz/aktobe/uslugi/foto-video-semka/k--%D1%84%D0%BE%D1%82%D0%BE%D0%B3%D1%80%D0%B0%D1%84-%D0%BC%D0%B5%D1%80%D0%BE%D0%BF%D1%80%D0%B8%D1%8F%D1%82%D0%B8%D0%B9/"),
("Kaspi Объявления — широкоформатная печать, Актобе: 1 500–9 750 ₸","https://obyavleniya.kaspi.kz/a/shirokoformatnaya-pechat-113816543"),
("Satu.kz — буклеты A4: от 18 до 650 ₸/шт","https://satu.kz/Buklety-a4.html"),
("Satu.kz — тепловые пушки, Актобе: дизельная 30 кВт ~125 000 ₸","https://satu.kz/aktobe-gorod/Pushka.html")]
s2["A1"]="Источник"; s2["B1"]="Ссылка"
for c in ("A1","B1"): s2[c].font=hdr; s2[c].fill=PatternFill("solid",fgColor=teal)
for i,(a,b) in enumerate(src,2): s2.cell(i,1,a).font=norm; s2.cell(i,2,b).font=norm
s2.column_dimensions["A"].width=95; s2.column_dimensions["B"].width=70
wb.save("/home/claude/GREENTE_byudzhet_otkrytiya.xlsx"); print("saved", first,last,grand)
