import os, sqlite3, sys, json, hmac, hashlib, time
sys.path.insert(0, ".")
from app import b24auth, clientcab, access
from playwright.sync_api import sync_playwright
SP = sys.argv[1]; OUT = os.path.join(SP, "shots"); BASE = "http://127.0.0.1:8099"
D = sqlite3.connect(os.path.join(SP, "demo/data/edo.sqlite3")); D.row_factory = sqlite3.Row
docs = D.execute("SELECT id, title, sign_token, status FROM documents ORDER BY created_at").fetchall()
z2 = [d for d in docs if d["title"].startswith("Накладная")]; kd = [d for d in docs if not d["title"].startswith("Накладная")]
cl_sig = D.execute("SELECT s.token, s.code FROM signers s JOIN documents d ON d.id=s.document_id WHERE s.role='client' AND s.status IN ('active','viewed') LIMIT 1").fetchone()
emp_sig = D.execute("SELECT s.token, s.code FROM signers s WHERE s.role='employee' AND s.status IN ('active','viewed') LIMIT 1").fetchone()
def ck(uid): return [{"name": b24auth.COOKIE, "value": b24auth.make_session(uid), "url": BASE}]
PH = "77019990000"
client_ck = [{"name": clientcab.COOKIE, "value": f"{PH}.{clientcab._sig(PH)}", "url": BASE}]
JOBS = [  # имя, путь, cookies, (w,h), полная страница
    ("01_cabinet_tasks", "/cabinet", ck(41), (1440, 900), False),
    ("02_cabinet_registry", "/cabinet?view=all", ck(41), (1440, 900), False),
    ("03_cabinet_kadr", "/cabinet?view=all&cat=kadr", ck(41), (1440, 900), False),
    ("04_doc_z2_route", f"/cabinet/doc/{z2[0]['id']}", ck(41), (1440, 900), False),
    ("05_doc_kadr_route", f"/cabinet/doc/{kd[1]['id']}", ck(41), (1440, 900), False),
    ("06_sign_client_mobile", f"/s/{cl_sig['token']}?k={cl_sig['code']}", [], (390, 844), True),
    ("07_sign_employee_mobile", f"/s/{emp_sig['token']}?k={emp_sig['code']}", [], (390, 844), True),
    ("10_dash_company", "/dash", ck(41), (1440, 900), False),
    ("11_dash_branches", "/dash/branches", ck(41), (1440, 900), False),
    ("12_dash_stock", "/dash/stock", ck(41), (1440, 900), False),
    ("13_dash_purchase", "/dash/purchase", ck(41), (1440, 900), False),
    ("14_dash_money", "/dash/money", ck(41), (1440, 900), False),
    ("15_dash_finplan", "/dash/finplan", ck(41), (1440, 900), False),
    ("16_dash_acc", "/dash/acc", ck(41), (1440, 900), False),
    ("17_dash_prod", "/dash/prod", ck(41), (1440, 900), False),
    ("18_dash_mgr", "/dash/mgr", ck(41), (1440, 900), False),
    ("18b_manager_dash", "/dash", ck(11), (1440, 900), False),
    ("19_dash_history", "/dash/history", ck(41), (1440, 900), False),
    ("20_roles", "/cabinet/roles", ck(41), (1440, 900), False),
    ("21_driver_mobile", "/driver", ck(61), (390, 844), True),
    ("22_client_cabinet_mobile", "/my", client_ck, (390, 844), True),
    ("23_client_cabinet_desktop", "/my", client_ck, (1440, 900), False),
    ("24_finplan_print", "/dash/finplan/print?y=2027&scope=company", ck(41), (1300, 900), False),
    ("25_cabinet_new", "/cabinet/new", ck(41), (1440, 900), False),
    ("26_cabinet_clients", "/cabinet/clients", ck(41), (1440, 900), False),
    ("28_report_company", "/dash/report?tab=company", ck(41), (1300, 900), False),
    ("29_report_acc", "/dash/acc/report", ck(41), (1300, 900), False),
    ("27_storekeeper_cabinet", "/cabinet", ck(21), (1440, 900), False),
]
only = set(sys.argv[2:])
signed = D.execute("SELECT sign_token FROM documents WHERE status='signed' LIMIT 1").fetchone()
if signed and (not only or "30_certificate" in only):
    import urllib.request
    for nm, url in (("30_certificate", f"/s/{signed['sign_token']}/certificate"), ("31_stamped_pdf", f"/s/{signed['sign_token']}/view")):
        data = urllib.request.urlopen(BASE + url).read(); tmp = os.path.join(SP, nm + ".pdf"); open(tmp, "wb").write(data)
        os.system(f"pdftoppm -png -r 130 {tmp} {os.path.join(OUT, nm)}"); print(nm, len(data))
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, path, cookies, (w, h), full in JOBS:
        if only and name not in only: continue
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, locale="ru-RU")
        if cookies: ctx.add_cookies(cookies)
        pg = ctx.new_page()
        try:
            r = pg.goto(BASE + path, wait_until="networkidle", timeout=30000)
            pg.wait_for_timeout(1200)
            fr = pg.query_selector("iframe[src*='/view']")
            if fr:
                src = fr.get_attribute("src"); data = pg.request.get(BASE + src if src.startswith("/") else src).body()
                tmp = os.path.join(SP, "tmp_doc.pdf"); open(tmp, "wb").write(data)
                os.system(f"pdftoppm -png -r 110 -f 1 -l 1 {tmp} {os.path.join(SP, 'tmp_doc')}")
                import base64, glob
                png = sorted(glob.glob(os.path.join(SP, "tmp_doc*.png")))[0]
                b64 = base64.b64encode(open(png, "rb").read()).decode()
                pg.evaluate("""(b64) => { const f = document.querySelector("iframe[src*='/view']");
                    const im = document.createElement('img'); im.src = 'data:image/png;base64,' + b64;
                    im.style.cssText = 'width:100%;height:100%;object-fit:contain;object-position:top;background:#525659;display:block';
                    f.replaceWith(im); }""", b64)
                for g in glob.glob(os.path.join(SP, "tmp_doc*")): os.remove(g)
                pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(OUT, name + ".png"), full_page=full)
            print(name, r.status if r else "?", pg.url[-40:])
        except Exception as e:
            print(name, "ERR", str(e)[:120])
        ctx.close()
    b.close()
