import sys, json, time
sys.path.insert(0, r"D:\anescom_edo")
from app.b24people import _b24
R = r"D:\anescom_edo\data\reports"
plan = json.load(open(R + r"\pair_names_plan.json", encoding="utf-8"))
done = set()
try:
    for l in open(R + r"\pair_names_backup.jsonl", encoding="utf-8"):
        done.add(json.loads(l)["id"])
except FileNotFoundError:
    pass
bk = open(R + r"\pair_names_backup.jsonl", "a", encoding="utf-8")
def call(m, p):
    for a in range(6):
        try:
            return _b24(m, p)
        except Exception as e:
            if a == 5: raise
            time.sleep(3 + a * 3)
st = {"done": 0, "skip_changed": 0, "skip_done": 0, "errors": 0}
n = lambda v: (v or "").strip()
for i, x in enumerate(plan):
    if x["id"] in done:
        st["skip_done"] += 1; continue
    try:
        cur = call("crm.contact.get", {"id": x["id"]}) or {}
        if (n(cur.get("LAST_NAME")), n(cur.get("NAME")), n(cur.get("SECOND_NAME"))) != (n(x["last"]), n(x["name"]), n(x["second"])):
            st["skip_changed"] += 1; continue
        call("crm.contact.update", {"id": x["id"], "fields": {"NAME": x["title"].strip(), "LAST_NAME": "", "SECOND_NAME": ""},
                                    "params": {"REGISTER_SONET_EVENT": "N"}})
        bk.write(json.dumps({"id": x["id"], "LAST_NAME": cur.get("LAST_NAME"), "NAME": cur.get("NAME"),
                             "SECOND_NAME": cur.get("SECOND_NAME"), "new": x["title"]}, ensure_ascii=False) + "\n"); bk.flush()
        st["done"] += 1
    except Exception as e:
        st["errors"] += 1; print("ERR", x["id"], e, flush=True)
    time.sleep(0.5)
    if i % 100 == 0: print(i, st, flush=True)
print("END", st, flush=True)
