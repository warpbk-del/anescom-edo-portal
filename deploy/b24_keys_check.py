# Проект 19 (23.10.2026): снимок контактов и компаний Bitrix24 (только чтение) и проверка, чей GUID лежит в ORIGIN_ID:
# партнёра (ключи продаж/закупок/оплат) или контрагента (ключи долгов). Снимок → D:\anescom_edo\data\analytics.sqlite3,
# таблицы b24_snap_contact / b24_snap_company. Итог печатается и пишется в D:\anescom_edo\b24_keys_check.txt.
import json, sqlite3, sys, time
import httpx
sys.stdout.reconfigure(encoding="utf-8")
env = {}
for line in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.strip().split("=", 1)
        env[k.strip()] = v.strip()
HOOK = env["EDO_B24_WEBHOOK"].rstrip("/")


def call(method, params):
    for attempt in range(5):
        r = httpx.post(f"{HOOK}/{method}.json", json=params, timeout=60)
        if r.status_code == 503:  # лимит запросов
            time.sleep(2 + attempt * 2)
            continue
        r.raise_for_status()
        js = r.json()
        if "error" in js:
            raise RuntimeError(f"{method}: {js.get('error_description') or js['error']}")
        return js
    raise RuntimeError(f"{method}: 503 подряд")


def dump(entity, select):
    """Все записи страницами по 50 (фильтр >ID, start=-1 — без медленного подсчёта)."""
    rows, last = [], 0
    while True:
        js = call(f"crm.{entity}.list", {"order": {"ID": "ASC"}, "filter": {">ID": last}, "select": select, "start": -1})
        part = js.get("result") or []
        if not part:
            break
        rows += part
        last = int(part[-1]["ID"])
        if len(part) < 50:
            break
    return rows


def first(lst):
    return ";".join(x.get("VALUE", "") for x in (lst or []))


c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3", timeout=30)
c.executescript("""
DROP TABLE IF EXISTS b24_snap_contact; DROP TABLE IF EXISTS b24_snap_company;
CREATE TABLE b24_snap_contact (id TEXT PRIMARY KEY, name TEXT, origin TEXT, originator TEXT, company_id TEXT,
  phones TEXT, emails TEXT, created TEXT, modified TEXT);
CREATE TABLE b24_snap_company (id TEXT PRIMARY KEY, name TEXT, origin TEXT, originator TEXT, ctype TEXT,
  phones TEXT, emails TEXT, created TEXT, modified TEXT);
""")
t0 = time.time()
ct = dump("contact", ["ID", "NAME", "LAST_NAME", "SECOND_NAME", "ORIGIN_ID", "ORIGINATOR_ID", "COMPANY_ID", "PHONE",
                      "EMAIL", "DATE_CREATE", "DATE_MODIFY"])
c.executemany("INSERT INTO b24_snap_contact VALUES(?,?,?,?,?,?,?,?,?)", [
    (x["ID"], " ".join(filter(None, [x.get("LAST_NAME"), x.get("NAME"), x.get("SECOND_NAME")])),
     (x.get("ORIGIN_ID") or "").lower(), x.get("ORIGINATOR_ID") or "", x.get("COMPANY_ID") or "",
     first(x.get("PHONE")), first(x.get("EMAIL")), x.get("DATE_CREATE"), x.get("DATE_MODIFY")) for x in ct])
co = dump("company", ["ID", "TITLE", "ORIGIN_ID", "ORIGINATOR_ID", "COMPANY_TYPE", "PHONE", "EMAIL", "DATE_CREATE",
                      "DATE_MODIFY"])
c.executemany("INSERT INTO b24_snap_company VALUES(?,?,?,?,?,?,?,?,?)", [
    (x["ID"], x.get("TITLE") or "", (x.get("ORIGIN_ID") or "").lower(), x.get("ORIGINATOR_ID") or "",
     x.get("COMPANY_TYPE") or "", first(x.get("PHONE")), first(x.get("EMAIL")), x.get("DATE_CREATE"),
     x.get("DATE_MODIFY")) for x in co])
c.commit()
out = [f"снимок: контактов {len(ct)}, компаний {len(co)} за {time.time() - t0:.0f} с"]
keys = {
    "партнёр (продажи)": "SELECT DISTINCT lower(client_key) FROM an_sales",
    "партнёр (оплаты)": "SELECT DISTINCT lower(client_key) FROM an_payments",
    "партнёр (закупки)": "SELECT DISTINCT lower(supplier_key) FROM an_purchases",
    "контрагент (долги)": "SELECT DISTINCT lower(client_key) FROM an_debts",
}
for tab in ("b24_snap_contact", "b24_snap_company"):
    origins = {r[0] for r in c.execute(f"SELECT origin FROM {tab} WHERE originator='ONE_C' AND origin<>''")}
    dup = c.execute(f"SELECT COUNT(*) FROM (SELECT origin FROM {tab} WHERE origin<>'' GROUP BY origin HAVING COUNT(*)>1)").fetchone()[0]
    out.append(f"{tab}: из 1С {len(origins)}, один GUID у нескольких записей: {dup}")
    for k, q in keys.items():
        s = {r[0] for r in c.execute(q)}
        out.append(f"   совпало с ключами «{k}»: {len(origins & s)} из {len(s)}")
both = c.execute("SELECT COUNT(*) FROM b24_snap_contact a JOIN b24_snap_company b ON a.origin=b.origin AND a.origin<>''").fetchone()[0]
out.append(f"один GUID и в контактах, и в компаниях: {both}")
open(r"D:\anescom_edo\b24_keys_check.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
