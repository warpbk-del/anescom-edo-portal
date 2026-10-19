"""Демо-сервер портала для скриншотов: вымышленные данные, Bitrix24/WhatsApp подменены."""
import base64, io, json, os, random, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, ".")
from starlette import templating as _t
_orig = _t.Jinja2Templates.TemplateResponse
def _compat(self, *a, **k):
    if a and isinstance(a[0], str):          # старый вызов (name, context, ...)
        name, ctx = a[0], (a[1] if len(a) > 1 else k.pop("context", {}))
        return _orig(self, ctx["request"], name, ctx, *a[2:], **k)
    return _orig(self, *a, **k)
_t.Jinja2Templates.TemplateResponse = _compat
from app import main, b24people, workflow, db, config, kadr, driver, b24auth, chatapp
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from app import pdfcert
random.seed(3)

PEOPLE = {
    "Ахметов Ерлан": 11, "Сергеева Анна": 12, "Каримов Данияр": 13, "Бимагамбетова Гульфара": 21, "Караменова Лаура": 31,
    "Болатұлы Бауыржан": 41, "Кулданов Бекбол": 51, "Имангалиева Алия": 52, "Нурланов Асет": 61, "Шинбаев Азамат": 71,
    "Жумабаев Нурлан": 14, "Тасымбетов Полат": 81, "Нариманов Алан": 82,
}
def U(name, uid):
    ln, fn = name.split()[:2]
    return {"ID": str(uid), "LAST_NAME": ln, "NAME": fn, "PERSONAL_MOBILE": f"+7701{uid:07d}", "WORK_POSITION": "", "UF_DEPARTMENT": [5]}
def ubn(n):
    for k, v in PEOPLE.items():
        if n and n.lower().startswith(k.lower()):
            return U(k, v)
    return {}
b24people.user_by_name = ubn
b24people.dept_head = lambda u: (U("Болатұлы Бауыржан", 41), "начальник")
b24people.manager = lambda order_no="", deal_id=None, manager_name="": (b24people.person(U(manager_name or "Ахметов Ерлан", PEOPLE.get(manager_name, 11)), "manager"), "демо")
b24people.storekeepers = lambda wh: ([b24people.person(U("Бимагамбетова Гульфара", 21), "storekeeper")], "Актобе")
b24people.order_contact_phone = lambda o: ("+77019990001", "демо")
workflow.notify = lambda ids, ip=None: ids
workflow.notify_done = lambda *a, **k: None

now = datetime.now(timezone(timedelta(hours=5)))
DELIV = [("ТОО «СтройМастер», ул. Есет батыра 102", "Центр", "09:00", "11:00", "00НФ-7952", "ON_WAY", 1840000),
         ("ИП Бекова А., мкр. 12, д. 4", "Батыс-2", "11:30", "13:00", "00НФ-7955", "CLIENT", 356000),
         ("ТОО «Евроокна Актобе», пр. Абилкайыр хана 67", "Центр", "14:00", "16:00", "00НФ-7961", "PREPARATION", 2210000),
         ("ТОО «Темир Курылыс», ул. Бокенбай батыра 155", "Промзона", "16:30", "18:00", "00НФ-7964", "PREPARATION", 980000),
         ("ИП Мусин Р., с. Каргалы", "Пригород", "08:00", "09:00", "00НФ-7940", "DELIVERED", 412000)]
def fake_b24(method, params):
    if method == "crm.item.list":
        items = []
        for i, (a, z, f, t, o, st, s) in enumerate(DELIV):
            d = now.strftime("%Y-%m-%d")
            items.append({"id": 900 + i, "title": f"Доставка {o}", "stageId": f"DT1036_17:{st}", driver.F_ADDR: a, driver.F_ZONE: z,
                          driver.F_FROM: f"{d}T{f}:00+05:00", driver.F_TO: f"{d}T{t}:00+05:00", driver.F_ORDER: o,
                          driver.F_WH: "Склад Актобе", driver.F_INFO: "Позвонить за 30 минут, разгрузка с торца", driver.F_PHONE: "+7 701 000 00 00",
                          "begindate": f"{d}T00:00:00+03:00", "opportunity": s, driver.F_DRIVER: 61})
        return {"items": items}
    return {}
b24people._b24 = fake_b24

def pdf(title, lines, kind="z2", org="ТОО «ANESCOM/АНЕСКОМ»"):
    pdfcert._ensure_font(); F, FB = pdfcert._FONT, pdfcert._FONT_B
    b = io.BytesIO(); c = canvas.Canvas(b, pagesize=A4); w, h = A4
    c.setFillColor(colors.HexColor("#cc2b28")); c.setFont(FB, 20); c.drawRightString(w - 18 * mm, h - 22 * mm, "AVTOCOMP" if "АВТО" in org else "ANESCOM")
    c.setFillColor(colors.black); c.setFont(F, 9); c.drawRightString(w - 18 * mm, h - 28 * mm, org)
    c.setFont(FB, 14); c.drawCentredString(w / 2, h - 45 * mm, title)
    y = h - 60 * mm; c.setFont(F, 10)
    if kind == "z2":
        c.drawString(20 * mm, y, "Организация (отправитель): " + org); y -= 6 * mm
        c.drawString(20 * mm, y, "Получатель: " + lines[0]); y -= 10 * mm
        cols = [20, 30, 110, 130, 150, 175]
        c.setFillColor(colors.HexColor("#e8eef5")); c.rect(20 * mm, y - 2 * mm, 170 * mm, 7 * mm, fill=1, stroke=0); c.setFillColor(colors.black)
        for x, t in zip(cols, ["№", "Наименование", "Ед.", "Кол-во", "Цена", "Сумма"]): c.setFont(FB, 9); c.drawString(x * mm, y, t)
        y -= 7 * mm; tot = 0
        for i, (n, q, p) in enumerate(lines[1], 1):
            c.setFont(F, 9)
            for x, t in zip(cols, [str(i), n, "шт", str(q), f"{p:,}".replace(",", " "), f"{q * p:,}".replace(",", " ")]): c.drawString(x * mm, y, t)
            tot += q * p; y -= 6 * mm
        c.setFont(FB, 10); c.drawRightString(190 * mm, y - 4 * mm, f"Итого: {tot:,} ₸".replace(",", " "))
        y -= 25 * mm; c.setFont(F, 9)
        c.drawString(20 * mm, y, "Отпуск разрешил ____________        Отпустил ____________        Получил ____________")
    else:
        for t in lines:
            c.drawString(20 * mm, y, t); y -= 6 * mm
        y -= 20 * mm; c.drawString(20 * mm, y, "Директор ______________"); c.drawString(110 * mm, y, "С приказом ознакомлен(а): ______________")
    c.showPage(); c.save(); return base64.b64encode(b.getvalue()).decode()

def seed():
    from fastapi.testclient import TestClient
    tc = TestClient(main.app); tc.__enter__()
    with db.conn() as c:
        c.executescript(b24auth._SCHEMA)
        for name, uid, role, pos, dept in [("Болатұлы Бауыржан", 41, "admin", "Директор по развитию", "Администрация"),
                                           ("Кулданов Бекбол", 51, "director", "Генеральный директор", "Администрация"),
                                           ("Ахметов Ерлан", 11, "manager", "Менеджер по продажам", "Отдел продаж Актобе"),
                                           ("Сергеева Анна", 12, "rop", "Руководитель отдела продаж", "Отдел продаж Актобе"),
                                           ("Бимагамбетова Гульфара", 21, "storekeeper", "Кладовщик", "Склад Актобе"),
                                           ("Караменова Лаура", 31, "hr", "Кадровик", "Администрация"),
                                           ("Нурланов Асет", 61, "driver", "Водитель-экспедитор", "Логистика Актобе"),
                                           ("Жумабекова Динара", 91, "accountant", "Главный бухгалтер", "Бухгалтерия"),
                                           ("Тасымбетов Полат", 81, "purchaser", "Закупщик", "Закупки")]:
            c.execute("INSERT OR REPLACE INTO users (b24_id,name,position,dept_names,role,role_suggest,role_confirmed,active,created_at,last_login) VALUES (?,?,?,?,?,?,1,1,?,?)",
                      (uid, name, pos, dept, role, role, now.isoformat(), now.isoformat()))
    H = {"Authorization": "Bearer " + config.API_TOKEN}
    Z = [("ТОО «СтройМастер»", "00НФ-7952", [("Профиль алюминиевый ALT 50", 120, 5200), ("Стеклопакет 4-16-4", 40, 9800)], 3),
         ("ИП Бекова А.", "00НФ-7955", [("Профиль ПВХ 70 мм белый", 80, 2400), ("Фурнитура поворотно-откидная", 20, 7800)], 1),
         ("ТОО «Евроокна Актобе»", "00НФ-7961", [("Стеклопакет энергосберегающий", 60, 14500), ("Уплотнитель EPDM", 300, 350)], 2),
         ("ТОО «Темир Курылыс»", "00НФ-7964", [("Сэндвич-панель 24 мм", 90, 6400)], 0),
         ("ТОО «Окна Каспия»", "00НФ-7930", [("Подоконник ПВХ 300 мм", 50, 3100), ("Ручка оконная", 100, 1200)], 3),
         ("ТОО «Алюкон»", "00НФ-7944", [("Профиль алюминиевый ALT F50", 200, 6100)], 1)]
    for i, (cl, o, items, sign_n) in enumerate(Z):
        r = tc.post("/api/z2", headers=H, json={"external_id": f"z2-{i}", "title": f"Накладная З-2 № {o} от {(now - timedelta(days=i)).strftime('%d.%m.%Y')}",
                    "body_base64": pdf(f"НАКЛАДНАЯ НА ОТПУСК ЗАПАСОВ НА СТОРОНУ № {o}", [cl, items]), "number": o, "order_no": o,
                    "warehouse": "Склад Актобе", "manager_name": "Ахметов Ерлан", "client_name": cl, "client_phone": f"+7701999000{i}"}).json()
        _sign_n(r["id"], sign_n)
    K = [("Приказ о приеме № 0000-000041 от 19.10.2026 — Нариманов Алан", "Приказ о приеме на работу", 4, "ТОО «AVTOCOMP/АВТОКОМП»"),
         ("Трудовой договор № 0000-000041 от 19.10.2026 — Нариманов Алан", "Трудовой договор", 2, "ТОО «AVTOCOMP/АВТОКОМП»"),
         ("Приказ о предоставлении отпуска № 00НФ-000019 — Тасымбетов Полат", "Приказ о предоставлении отпуска", 1, "ТОО «ANESCOM/АНЕСКОМ»")]
    for i, (t, h, sn, org) in enumerate(K):
        emp = t.split("— ")[1]
        r = tc.post("/api/kadr", headers=H, json={"external_id": f"k-{i}", "title": t, "org": org, "base": "avtocomp" if "АВТО" in org else "",
                    "body_base64": pdf(h.upper(), [f"Работник: {emp}", "Должность: Оператор автоматических линий", "Основание: личное заявление"], "kadr", org),
                    "employee": {"name": emp}, "acquaint": [{"name": "Шинбаев Азамат"}], "director_name": "Кулданов Бекбол"}).json()
        _sign_n(r["id"], sn)
    # договор и акт сверки (простые, без маршрута)
    return tc

def _sign_n(doc_id, n):
    with db.conn() as c:
        for _ in range(n):
            act = [s for s in workflow.signers(c, doc_id) if s["status"] in ("active", "viewed")]
            if not act: break
            for s in act:
                s2 = workflow.signer(c, s["id"])
                if s2["status"] in ("active", "viewed"):
                    workflow.sign(c, s2, s2["name"] or "Подписант", "10.0.0.1", "demo")
                    if not s2["all_of"]: break

if __name__ == "__main__":
    tc = seed()
    print("seeded")
    import uvicorn
    uvicorn.run(main.app, host="127.0.0.1", port=8099, log_level="warning")
