import base64, math, asyncio
from playwright.async_api import async_playwright
D='/tmp/claude-0/kz/'
LW=base64.b64encode(open(D+'logo_white.png','rb').read()).decode()
W,H=1080,1920
UNIT='<path d="M30 58 L30 36 C30 18 46 10 53 19 C59 27 51 36 44 30 M30 36 C30 18 14 10 7 19 C1 27 9 36 16 30" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
def strip(y,flip=False):
    g=''
    for x in range(-20,W+60,62):
        t=f'translate({x} {y})'+(' scale(1 -1) translate(0 -60)' if flip else '')
        g+=f'<g transform="{t}">{UNIT}</g>'
    return g
cx,cy=540,790
rays=''
for i in range(32):
    a=2*math.pi*i/32; w=math.pi/32*0.5; ri,ro=262,400
    p=[(cx+ri*math.cos(a-w),cy+ri*math.sin(a-w)),(cx+ro*math.cos(a),cy+ro*math.sin(a)),(cx+ri*math.cos(a+w),cy+ri*math.sin(a+w))]
    rays+='<polygon points="%s"/>'%' '.join('%.1f,%.1f'%q for q in p)
html=f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{width:{W}px;height:{H}px;overflow:hidden;font-family:Inter,sans-serif}}
.c{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:radial-gradient(ellipse at 50% 42%,#d63039 0%,#b81f28 40%,#7c1016 100%)}}
.logo{{position:absolute;left:50%;transform:translateX(-50%);top:190px;width:430px}}
.n{{position:absolute;left:0;right:0;top:640px;text-align:center;font-size:330px;font-weight:900;line-height:.8;letter-spacing:-10px;color:#fff;text-shadow:0 10px 40px rgba(80,0,0,.45)}}
.m{{position:absolute;left:0;right:0;top:1225px;text-align:center}}
.m .q{{display:inline-block;font-size:44px;font-weight:800;letter-spacing:10px;color:#FEC50C}}
.m .d{{font-size:96px;font-weight:900;line-height:1.02;color:#fff;margin-top:26px;letter-spacing:1px}}
.m .line{{width:120px;height:4px;background:#FEC50C;margin:40px auto 34px}}
.m .kz{{font-size:50px;font-weight:600;color:#fff;opacity:.95}}
.url{{position:absolute;left:0;right:0;bottom:160px;text-align:center;color:#fff;font-size:38px;font-weight:700;letter-spacing:2px;opacity:.9}}
</style></head><body><div class="c">
<svg width="{W}" height="{H}" style="position:absolute;inset:0">
<defs><radialGradient id="rg" cx="50%" cy="50%" r="50%"><stop offset=".45" stop-color="#FEC50C" stop-opacity=".55"/><stop offset="1" stop-color="#FEC50C" stop-opacity="0"/></radialGradient></defs>
<g fill="#FEC50C">{rays}</g>
<circle cx="{cx}" cy="{cy}" r="245" fill="#00AFCA"/><circle cx="{cx}" cy="{cy}" r="245" fill="none" stroke="#FEC50C" stroke-width="8"/>
<g stroke="#FEC50C" stroke-width="5" opacity=".9">{strip(40)}{strip(H-100,True)}</g>
<rect x="0" y="118" width="{W}" height="3" fill="#FEC50C" opacity=".9"/><rect x="0" y="{H-121}" width="{W}" height="3" fill="#FEC50C" opacity=".9"/>
</svg>
<img class="logo" src="data:image/png;base64,{LW}">
<div class="n">25</div>
<div class="m"><div class="q">ҚАЗАН · ОКТЯБРЯ</div><div class="d">ДЕНЬ<br>РЕСПУБЛИКИ</div><div class="line"></div><div class="kz">Республика күні құтты болсын!</div></div>
<div class="url">anescom.kz</div>
</div></body></html>"""
open(D+'story2.html','w').write(html)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':W,'height':H})
        await pg.goto('file://'+D+'story2.html'); await pg.wait_for_timeout(300)
        await pg.screenshot(path=D+'out/story2.png'); await b.close()
asyncio.run(main())
from PIL import Image
Image.open(D+'out/story2.png').resize((450,800)).save(D+'story_prev.png')
