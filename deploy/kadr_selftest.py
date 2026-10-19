"""6п: самопроверка /api/kadr на временной базе (EDO_DATA_DIR задаёт деплой), Bitrix24 и WhatsApp подменены.
Запуск из D:\\anescom_edo: set EDO_DATA_DIR=<temp> & .venv\\Scripts\\python.exe kadr_selftest.py"""
import base64, os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
os.environ.setdefault("EDO_API_TOKEN", "t")
from fastapi.testclient import TestClient
from app import main, b24people, workflow, db, kadr
U = {"Караменова Лаура": {"ID": "1", "LAST_NAME": "Караменова", "NAME": "Лаура", "PERSONAL_MOBILE": "+77010000001"},
     "Диярова Динара": {"ID": "2", "LAST_NAME": "Диярова", "NAME": "Динара", "PERSONAL_MOBILE": "+77010000002", "UF_DEPARTMENT": [10]},
     "Болатұлы Бауыржан": {"ID": "3", "LAST_NAME": "Болатұлы", "NAME": "Бауыржан", "PERSONAL_MOBILE": "+77010000003"},
     "Кулданов Бекбол": {"ID": "4", "LAST_NAME": "Кулданов", "NAME": "Бекбол", "PERSONAL_MOBILE": "+77010000004"}}
def ubn(n):
    for k, v in U.items():
        if n and n.startswith(k): return v
    return {}
b24people.user_by_name = ubn
b24people.dept_head = lambda u: (U["Болатұлы Бауыржан"], "начальник «Уральск»")
workflow.notify = lambda ids, ip=None: ids
pdf = base64.b64encode(b"%PDF-1.4 test").decode()
c = TestClient(main.app); c.__enter__()   # startup: схема БД
H = {"Authorization": "Bearer " + os.environ["EDO_API_TOKEN"]}
r = c.post("/api/kadr", headers=H, json={"external_id": "g1|NEW", "title": "Приказ о приеме № УРНФ-000004 от 01.10.2026",
    "body_base64": pdf, "org": "Филиал ТОО \"ANESCOM/АНЕСКОМ\" г. Уральск", "department": "Филиал г. Уральск",
    "employee": {"name": "Диярова Динара Кайрулловна"}, "acquaint": [{"name": "Новикова Анна", "phone": "+7 702 000 0009"}, {"name": "Болатұлы Бауыржан"}],
    "director_name": "Кулданов Бекбол Сисенбиевич",
    "phonebook": {"Караменова Лаура Алтынбековна": "+7 (705) 000-00-11", "Новикова Анна Петровна": "8 702 000 0009"}})
j = r.json(); print(r.status_code, j["status"], j["problems"]); print(j["steps"])
print("в шаге 2:", [x["name"] for x in j["steps"][1]["candidates"]])
did = j["id"]
with db.conn() as cc:
    S = workflow.signers(cc, did)
    def sg(role):
        s = [x for x in workflow.signers(cc, did) if x["role"] == role][0]
        return workflow.sign(cc, s, s["name"] or "X")
    print("hr", sg("hr"))
    acq = [x for x in workflow.signers(cc, did) if x["role"] == "acquaint"][0]
    print("удаление ознакомляемого:", workflow.remove_signer(cc, acq["id"], "тест", "selftest"))
    print("emp (ожидаем переход к руководителю)", sg("employee")); print("head", sg("head")); print("dir", sg("director"))
    print(cc.execute("select status from documents where id=?", (did,)).fetchone()[0])
r = c.post("/api/kadr", headers=H, json={"external_id": "g2", "title": "Договор ГПХ № 1", "body_base64": pdf, "base": "АВТОКОМП", "org": "ТОО АВТОКОМП", "employee": {"name": "Иванов Иван", "phone": "8 701 111 2233"}})
print(r.json()["problems"], r.json()["steps"])
print("справочник:", kadr.book_phone("Караменова Лаура"))
