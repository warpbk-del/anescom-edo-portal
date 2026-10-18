# Какие регистры расчётов есть в базе (из диагностики, сохранённой в резервной копии аналитики).
import glob, json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
f = sorted(glob.glob(r"D:\anescom_edo\data\analytics.sqlite3.bak_*"))[-1]
c = sqlite3.connect(f)
b = None
for (body,) in c.execute("SELECT body FROM an_meta ORDER BY id DESC"):
    j = json.loads(body)
    if j.get("kind") == "diagnostics":
        b = j; break
for r in b["registers"]:
    if "Расчет" in r["name"] or "Сверк" in r["name"]:
        print("==", r["name"])
        print("  изм:", ", ".join(x.split(" ")[0] for x in r.get("Измерения", [])))
        print("  рес:", ", ".join(x.split(" ")[0] for x in r.get("Ресурсы", [])))
        print("  рекв:", ", ".join(x.split(" ")[0] for x in r.get("Реквизиты", [])))
