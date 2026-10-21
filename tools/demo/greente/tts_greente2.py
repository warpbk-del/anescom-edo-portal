# GREENTE promo voice: edge-tts ru-RU-DmitryNeural. Run on server: python tts_greente.py D:\anescom_tts\gt
import asyncio, os, re, sys, zipfile, shutil
import edge_tts
V = "ru-RU-DmitryNeural"
T = ["Гринтэ. Завод алюминиевых конструкций полного цикла.",
"Профиль режется на автоматических станках с точностью до десятой доли миллиметра.",
"Программа оптимизирует раскрой: минимум отходов и никакого человеческого фактора.",
"Отверстия под замки и фурнитуру фрезеруются за один зажим профиля.",
"Перед покраской профиль проходит химподготовку. Порошковое покрытие держится годами.",
"Окрашенный профиль с завода ждут до шестидесяти дней. Мы красим сами, и это в разы быстрее.",
"Сборка по ГОСТу, расчёт статики и узлов. Риски исключены.",
"Упаковка в защитную плёнку и доставка по всему Казахстану.",
"Мы не самые дешёвые и не самые дорогие. Наша задача — качество.",
"Пришлите проект до тридцать первого декабря и получите скидку пятьдесят процентов.",
"Гринтэ. Долговечность в каждом миллиметре."]
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
    z = os.path.join(out, "gt2.zip")
    with zipfile.ZipFile(z, "w") as zf:
        for n in names:
            if os.path.exists(os.path.join(out, n)): zf.write(os.path.join(out, n), n)
        print("ZIP", os.path.getsize(z), "FAIL:", bad)
asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "gt"))
