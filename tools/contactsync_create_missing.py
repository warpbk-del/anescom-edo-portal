import sys, json, collections, time
sys.path.insert(0, r"D:\anescom_edo")
from app.analytics import conn
from app.b24people import _b24
from app.contactsync import norm_phone, norm_email, split, _now
LIVE = len(sys.argv) > 1 and sys.argv[1] == "live"
with conn() as db:
    plan = [dict(r) for r in db.execute("""select p.deal, lower(o.partner_key) pk, lower(o.person_key) sk from contactsync_plan p
        join b24_snap_deal d on d.id=p.deal join an_order_clients o on lower(o.order_key)=d.origin
        where p.kind='нет записи в Б24' and p.status='план'""")]
    orig = collections.Counter(r[0] for r in db.execute("select originator from b24_snap_contact where originator<>''")).most_common(1)
    originator = orig[0][0] if orig else ""
    cts = {r[0] for r in db.execute("select id from b24_snap_contact")}
    P = {r["key"].lower(): dict(r) for r in db.execute("select * from an_partners")}
    reg = collections.defaultdict(list)
    for r in db.execute("select lower(partner) p, type_name, b24_id from an_b24ids where type_name='Контакт'"):
        reg[r["p"]].append(r["b24_id"])
print("originator", originator, "deals", len(plan), "LIVE" if LIVE else "DRY")
target, log = {}, []
for pk in sorted({x["pk"] for x in plan}):
    p = P.get(pk) or {}
    alive = [i for i in reg.get(pk, []) if i in cts]
    if alive:
        cid = alive[0]
        cur = _b24("crm.contact.get", {"id": cid}) or {}
        o = (cur.get("ORIGIN_ID") or "").lower()
        if o and o != pk:
            print("SKIP чужой ORIGIN", p.get("name"), cid, o); continue
        if not o and LIVE:
            _b24("crm.contact.update", {"id": cid, "fields": {"ORIGIN_ID": pk, "ORIGINATOR_ID": originator}, "params": {"REGISTER_SONET_EVENT": "N"}})
        target[pk] = cid; print("есть", p.get("name"), cid, "origin" if o else "origin+")
    else:
        w = (p.get("name") or "").split()
        f = {"LAST_NAME": w[0] if w else "", "NAME": w[1] if len(w) > 1 else "", "SECOND_NAME": " ".join(w[2:]),
             "TYPE_ID": "CLIENT", "ORIGIN_ID": pk, "ORIGINATOR_ID": originator, "OPENED": "Y",
             "PHONE": [{"VALUE": "+" + n, "VALUE_TYPE": "WORK"} for n in dict.fromkeys(norm_phone(v) for v in split(p.get("phones"))) if n],
             "EMAIL": [{"VALUE": e, "VALUE_TYPE": "WORK"} for e in dict.fromkeys(norm_email(v) for v in split(p.get("emails"))) if e]}
        cid = _b24("crm.contact.add", {"fields": f, "params": {"REGISTER_SONET_EVENT": "N"}}) if LIVE else "NEW"
        target[pk] = str(cid); print("создать", p.get("name"), cid, len(f["PHONE"]), "тел", len(f["EMAIL"]), "e-mail")
st = collections.Counter()
for x in plan:
    cid = target.get(x["pk"])
    if not cid: st["нет цели"] += 1; continue
    if not LIVE: st["к привязке"] += 1; continue
    try:
        d = _b24("crm.deal.get", {"id": x["deal"]}) or {}
        fields = {"CONTACT_IDS": [cid]}
        co = d.get("COMPANY_ID")
        if co and co != "0":
            try:
                _b24("crm.company.get", {"id": co})
            except Exception:
                fields["COMPANY_ID"] = 0
        _b24("crm.deal.update", {"id": x["deal"], "fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}})
        with conn() as db:
            db.execute("UPDATE contactsync_plan SET status='сделано', applied=?, new_contact=? WHERE deal=?", (_now(), cid, x["deal"]))
        st["привязано"] += 1; time.sleep(0.4)
    except Exception as e:
        st["ошибка"] += 1; print("ERR", x["deal"], e)
print(dict(st))
