import base64, math, asyncio
from playwright.async_api import async_playwright
D='/tmp/claude-0/kz/'
b64=lambda p: base64.b64encode(open(D+p,'rb').read()).decode()
LW=b64('logo_white.png')
BLUE='#00AFCA'; GOLD='#FEC50C'; RED='#C4232B'

UNIT='<path d="M30 58 L30 36 C30 18 46 10 53 19 C59 27 51 36 44 30 M30 36 C30 18 14 10 7 19 C1 27 9 36 16 30" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'

def sun(cx,cy,r,ri,ro,col=GOLD):
    s=f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}"/>'
    for i in range(32):
        a=2*math.pi*i/32; w=math.pi/32*0.55
        p=[(cx+ri*math.cos(a-w),cy+ri*math.sin(a-w)),(cx+ro*math.cos(a),cy+ro*math.sin(a)),(cx+ri*math.cos(a+w),cy+ri*math.sin(a+w))]
        s+='<polygon points="%s" fill="%s"/>'%(' '.join('%.1f,%.1f'%q for q in p),col)
    return s

def rosette(cx,cy,R,n,scale,op):
    g=f'<g opacity="{op}" stroke="#fff" stroke-width="{4/scale:.1f}">'
    for i in range(n):
        ang=360*i/n
        g+=f'<g transform="translate({cx} {cy}) rotate({ang}) translate(0 {-R}) scale({scale}) translate(-30 -30)">{UNIT}</g>'
    return g+'</g>'

CSS="""*{margin:0;padding:0;box-sizing:border-box}body{width:1080px;height:1080px;overflow:hidden;font-family:Inter,sans-serif;color:#fff}
.card{position:relative;width:1080px;height:1080px;overflow:hidden}"""

card1=f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}
.bg{{position:absolute;inset:0;background:radial-gradient(circle at 50% 40%,#d0303a 0%,{RED} 45%,#9e1a21 100%)}}
.logo{{position:absolute;left:60px;top:58px;width:250px}}
.quote{{position:absolute;left:62px;top:200px;font-style:italic;font-weight:600;font-size:34px;line-height:1.25}}
.date{{position:absolute;right:60px;top:62px;display:flex;align-items:center;gap:14px}}
.date b{{font-size:104px;font-weight:800;color:{BLUE};line-height:1;text-shadow:0 2px 0 rgba(0,0,0,.08)}}
.date span{{font-size:32px;font-weight:800;line-height:1.1}}
.t{{position:absolute;left:62px;right:62px;bottom:64px}}
.kz{{font-size:84px;font-weight:800;line-height:1.05;letter-spacing:-1px}}
.line{{width:180px;height:3px;background:#fff;margin:30px 0 26px}}
.ru{{font-size:58px;font-weight:700;line-height:1.1}}
</style></head><body><div class="card"><div class="bg"></div>
<svg width="1080" height="1080" style="position:absolute;inset:0">
{rosette(720,430,300,24,1.6,.10)}{rosette(720,430,215,16,1.3,.10)}
<circle cx="720" cy="430" r="190" fill="{BLUE}"/>
<circle cx="720" cy="430" r="190" fill="url(#sh)"/>
<defs><radialGradient id="sh" cx="35%" cy="30%"><stop offset="0" stop-color="#fff" stop-opacity=".25"/><stop offset="1" stop-color="#000" stop-opacity=".12"/></radialGradient></defs>
{sun(720,430,62,74,150)}
<circle cx="720" cy="430" r="190" fill="none" stroke="{GOLD}" stroke-width="6"/>
</svg>
<img class="logo" src="data:image/png;base64,{LW}">
<div class="date"><b>25</b><span>ҚАЗАН<br>ОКТЯБРЯ</span></div>
<div class="quote">“Елің аман,<br>жұртың тыныш<br>болсын!”</div>
<div class="t"><div class="kz">Республика күні<br>құтты болсын!</div><div class="line"></div><div class="ru">С Днём Республики!</div></div>
</div></body></html>"""

# card 2: blue panel left with wave edge
strip=''.join(f'<g transform="translate(28 {y}) scale(1.05)">{UNIT}</g>' for y in range(10,1080,64))
card2=f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}
.bg{{position:absolute;inset:0;background:linear-gradient(135deg,#cf2c34,{RED} 50%,#a51c23)}}
.logo{{position:absolute;right:64px;top:62px;width:240px}}
.txt{{position:absolute;right:64px;top:250px;width:520px;text-align:right}}
.h{{font-size:46px;font-weight:800;line-height:1.2;margin-bottom:46px}}
.p{{font-size:38px;font-weight:400;line-height:1.42}}
.p b{{font-weight:700}}
.url{{position:absolute;right:64px;bottom:72px;font-size:36px;font-weight:800}}
</style></head><body><div class="card"><div class="bg"></div>
<svg width="1080" height="1080" style="position:absolute;inset:0">
<defs>
<linearGradient id="fold" x1="0" y1="0" x2="1" y2=".25">
<stop offset="0" stop-color="#000" stop-opacity=".10"/><stop offset=".22" stop-color="#fff" stop-opacity=".22"/>
<stop offset=".42" stop-color="#000" stop-opacity=".12"/><stop offset=".62" stop-color="#fff" stop-opacity=".18"/>
<stop offset=".85" stop-color="#000" stop-opacity=".16"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></linearGradient>
<clipPath id="flag"><path d="M0 0 H470 C430 180 520 330 470 520 C420 700 520 860 455 1080 H0 Z"/></clipPath>
<filter id="ds" x="-10%" y="-10%" width="130%" height="130%"><feDropShadow dx="10" dy="0" stdDeviation="14" flood-opacity=".35"/></filter>
</defs>
<g filter="url(#ds)"><path d="M0 0 H470 C430 180 520 330 470 520 C420 700 520 860 455 1080 H0 Z" fill="{BLUE}"/></g>
<g clip-path="url(#flag)">
<g stroke="{GOLD}" stroke-width="5">{strip}</g>
{sun(285,400,78,92,185)}
<rect width="560" height="1080" fill="url(#fold)"/>
</g>
</svg>
<img class="logo" src="data:image/png;base64,{LW}">
<div class="txt"><div class="h">Уважаемые<br>партнёры!</div>
<div class="p">Поздравляем<br>с Днём Республики!<br>Хотим сообщить, что<br><b>26 октября —<br>выходной день.</b><br>Ждём вас 27 октября<br>с 09.00 до 18.00.</div></div>
<div class="url">anescom.kz</div>
</div></body></html>"""

open(D+'card1.html','w').write(card1); open(D+'card2.html','w').write(card2)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1080,'height':1080})
        for n in ('card1','card2'):
            await pg.goto('file://'+D+n+'.html'); await pg.wait_for_timeout(300)
            await pg.screenshot(path=D+'out/'+n+'.png')
        await b.close()
asyncio.run(main())
