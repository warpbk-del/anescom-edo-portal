# GREENTE promo voice: edge-tts ru-RU-DmitryNeural. Run on server: python tts_greente.py D:\anescom_tts\gt
import asyncio, os, re, sys, zipfile, shutil
import edge_tts
V = "ru-RU-DmitryNeural"
T = ["Гринте. Новый завод алюминиевых конструкций в Актобе.",
"Три тысячи двести квадратных метров собственного производства.",
"Обрабатывающий центр режет профиль с точностью до десятой доли миллиметра.",
"Пять этапов на одной площадке: расчёт, обработка, покраска, сборка и упаковка. Ни один этап не отдаём на сторону.",
"Своя покрасочная линия. Любой цвет под ваш проект, без ожидания поставки.",
"Окна, двери и витражи для застройщиков, оконных компаний, архитекторов и предпринимателей.",
"Гринте. Долговечность в каждом миллиметре.",
"Открытие завода. Двенадцатого ноября. Ждём вас!"]
def parts(t): return [p.strip() for p in re.split(r"(?<=[.!?])\s+", t) if p.strip()]
async def main(out):
    os.makedirs(out, exist_ok=True); names=[]; bad=[]
    for i, t in enumerate(T):
        for j, p in enumerate(parts(t)):
            n = "seg%02d_%d.mp3" % (i, j); f = os.path.join(out, n); names.append(n)
            if os.path.exists(f) and os.path.getsize(f) > 1000: continue
            for k in range(20):
                try:
                    await asyncio.wait_for(edge_tts.Communicate(p, V, rate="+6%").save(f), 25)
                    if os.path.getsize(f) > 1000: break
                except Exception: await asyncio.sleep(1.5)
            ok = os.path.exists(f) and os.path.getsize(f) > 1000
            print(n, "OK" if ok else "FAIL")
            if not ok: bad.append(n)
    z = os.path.join(out, "gt.zip")
    with zipfile.ZipFile(z, "w") as zf:
        for n in names:
            if os.path.exists(os.path.join(out, n)): zf.write(os.path.join(out, n), n)
    shutil.copy(z, r"D:\anescom_edo\app\static\vo_tmp.zip")
    print("ZIP", os.path.getsize(z), "FAIL:", bad)
asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "gt"))
