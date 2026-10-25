# Служебное: отправить журнал исправлений копии (com_fix_log.txt) на портал (раздел аудита fixlog) — для манифеста повтора.
import json, urllib.request
rows = [{"n": i, "line": l.rstrip("\n")} for i, l in enumerate(open(LOG, encoding="utf-8"), 1)]
tok = ""
for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
body = json.dumps({"section": "fixlog", "source": "anescom", "replace": True, "rows": rows}, ensure_ascii=False).encode("utf-8")
rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
print("строк", len(rows), urllib.request.urlopen(rq, timeout=60).read().decode()[:80])
