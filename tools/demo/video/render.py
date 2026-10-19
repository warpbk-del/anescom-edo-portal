import sys, os, asyncio
from playwright.async_api import async_playwright
here=os.path.dirname(os.path.abspath(__file__))
async def main(mode, a, b, fps, out):
    async with async_playwright() as p:
        br=await p.chromium.launch(args=["--allow-file-access-from-files","--disable-web-security"])
        pg=await br.new_page(viewport={"width":1920,"height":1080})
        msgs=[]; pg.on("console", lambda m: msgs.append(m.text)); pg.on("pageerror", lambda e: msgs.append("ERR "+str(e)))
        await pg.goto("file://"+here+"/film.html"); await pg.evaluate("window.ready"); await pg.wait_for_timeout(300)
        os.makedirs(out, exist_ok=True)
        if mode=="stills":
            for t in [float(x) for x in a.split(",")]:
                await pg.evaluate(f"seek({t})"); await pg.screenshot(path=f"{out}/s_{t:06.2f}.jpg", type="jpeg", quality=80)
        else:
            a=int(a); b=int(b)
            for i in range(a,b):
                await pg.evaluate(f"seek({i/fps})")
                await pg.screenshot(path=f"{out}/f_{i:05d}.jpg", type="jpeg", quality=90)
        print("\n".join(msgs[:20]))
        await br.close()
mode=sys.argv[1]
if mode=="stills": asyncio.run(main(mode, sys.argv[2], None, 30, sys.argv[3]))
else: asyncio.run(main(mode, sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]))
