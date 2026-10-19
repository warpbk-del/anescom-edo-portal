import asyncio, edge_tts, os
T = ["Портал ЭДО Анеском.", "Он соединяет.", "Данные идут сами, без ручного ввода.", "Первое — кабинеты отделов.", "Привет, это проверка голоса."]
async def one(t, v, r):
    f = "D:\\anescom_tts\\t.mp3"
    try:
        await edge_tts.Communicate(t, v, rate=r).save(f); return "OK %d" % os.path.getsize(f)
    except Exception as e:
        return type(e).__name__
async def main():
    for v in ["ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"]:
        for r in ["+0%", "+4%"]:
            for t in T:
                print(v[6:12], r, (await one(t, v, r)), t[:25])
asyncio.run(main())
