# Документальный ролик GREENTE «Как это сделано»: голос Дмитрия (edge-tts), спокойный темп.
# Запуск на сервере: D:\anescom_tts\Scripts\python.exe tts_doc.py D:\anescom_tts\doc
import asyncio, os, re, sys, zipfile
import edge_tts
V = "ru-RU-DmitryNeural"
T = [
 "Алюминиевое окно начинается с профиля. Это история о том, как он становится готовым изделием.",
 "Профиль приходит на завод неокрашенным — длинными хлыстами по шесть метров.",
 "Прежде чем красить, металл нужно подготовить. Профиль проходит химическую обработку: обезжиривание, промывку и нанесение защитного слоя.",
 "Этот этап не видно в готовом окне, но именно он определяет, как долго краска будет держаться на металле.",
 "Чистый профиль развешивают на конвейере и отправляют в покрасочную камеру.",
 "Порошковая краска получает электрический заряд и притягивается к металлу, ложась ровным слоем даже в углах и пазах.",
 "Затем профиль уходит в печь. При температуре около двухсот градусов порошок плавится и превращается в прочное покрытие.",
 "Окрашенный профиль режут на автоматических пилах. Программа раскладывает размеры так, чтобы отходов было как можно меньше.",
 "Обрабатывающий центр фрезерует отверстия под замки, ручки и петли, а также пазы для отвода воды.",
 "Дальше начинается сборка. Углы рамы соединяют на уголках с клеем и опрессовывают, чтобы соединение не расходилось годами.",
 "Устанавливают уплотнители, фурнитуру и стеклопакет. Каждую створку проверяют: как она открывается и как прилегает к раме.",
 "Готовое изделие оборачивают защитной плёнкой. Так покрытие доедет до объекта без единой царапины.",
 "От неокрашенного профиля до готового окна — весь путь проходит на одном заводе. Гринтэ.",
]
def parts(t): return [p.strip() for p in re.split(r"(?<=[.!?])\s+", t) if p.strip()]
async def main(out):
    os.makedirs(out, exist_ok=True); names=[]; bad=[]
    for i, t in enumerate(T):
        for j, p in enumerate(parts(t)):
            n = "d%02d_%d.mp3" % (i, j); f = os.path.join(out, n); names.append(n)
            if os.path.exists(f) and os.path.getsize(f) > 1000: continue
            for k in range(20):
                try:
                    await asyncio.wait_for(edge_tts.Communicate(p, V, rate="-4%").save(f), 25)
                    if os.path.getsize(f) > 1000: break
                except Exception: await asyncio.sleep(1.5)
            ok = os.path.exists(f) and os.path.getsize(f) > 1000
            print(n, "OK" if ok else "FAIL")
            if not ok: bad.append(n)
    z = os.path.join(out, "doc.zip")
    with zipfile.ZipFile(z, "w") as zf:
        for n in names:
            if os.path.exists(os.path.join(out, n)): zf.write(os.path.join(out, n), n)
    print("ZIP", os.path.getsize(z), "FAIL:", bad)
asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "doc"))
