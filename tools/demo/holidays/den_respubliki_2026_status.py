import base64, math, asyncio
from playwright.async_api import async_playwright
D='/tmp/claude-0/kz/'
LW=base64.b64encode(open(D+'logo_white.png','rb').read()).decode()
W,H=1080,1920
UNIT='<path d="M30 58 L30 36 C30 18 46 10 53 19 C59 27 51 36 44 30 M30 36 C30 18 14 10 7 19 C1 27 9 36 16 30" fill="none" stroke-linecap="round"/>'
def rosette(cx,cy,R,n,sc,op):
    g=f'<g opacity="{op}" stroke="#fff" stroke-width="{4/sc:.1f}">'
    for i in range(n): g+=f'<g transform="translate({cx} {cy}) rotate({360*i/n}) translate(0 {-R}) scale({sc}) translate(-30 -30)">{UNIT}</g>'
    return g+'</g>'

def bez(p0,p1,p2,p3,t):
    u=1-t; return tuple(u**3*a+3*u*u*t*b+3*u*t*t*c+t**3*d for a,b,c,d in zip(p0,p1,p2,p3))
def feathers(p0,p1,p2,p3,n,l0,l1,side,w0=10,w1=22,curl=0.35):
    out=''
    for i in range(n):
        t=i/(n-1)
        x,y=bez(p0,p1,p2,p3,t); xa,ya=bez(p0,p1,p2,p3,max(0,t-0.01)); x2,y2=bez(p0,p1,p2,p3,min(1,t+0.01))
        tx,ty=x2-xa,y2-ya; L=math.hypot(tx,ty) or 1; tx,ty=tx/L,ty/L
        nx,ny=-ty*side,tx*side
        ln=l0+(l1-l0)*t**1.3; wd=w0+(w1-w0)*t
        # feather direction: normal tilted back along tangent
        dx,dy=nx*(1-curl)-tx*curl, ny*(1-curl)-ty*curl
        m=math.hypot(dx,dy); dx,dy=dx/m,dy/m
        ex,ey=x+dx*ln,y+dy*ln
        px,py=-dy,dx
        c1=(x+dx*ln*.45+px*wd, y+dy*ln*.45+py*wd); c2=(x+dx*ln*.55-px*wd*.6, y+dy*ln*.55-py*wd*.6)
        out+=f'<path d="M{x:.1f} {y:.1f} Q{c1[0]:.1f} {c1[1]:.1f} {ex:.1f} {ey:.1f} Q{c2[0]:.1f} {c2[1]:.1f} {x:.1f} {y:.1f}Z"/>'
    return out
# wing 1: from body up-left
w1=feathers((330,1270),(150,1150),(110,850),(230,560),26,60,230,1,8,20,0.45)
# wing 2: from body along bottom to right
w2=feathers((330,1290),(520,1400),(760,1360),(990,1300),24,50,190,1,8,18,0.5)
body='<path d="M250 1300 C300 1255 380 1250 440 1290 C400 1330 330 1345 270 1330 L180 1345 C200 1325 225 1310 250 1300Z"/><path d="M180 1345 L130 1360 L170 1330Z"/>'
tail='<path d="M430 1290 L520 1255 L500 1300 L540 1300 L455 1320Z"/>'
# skyline
sky='<g fill="#5e0d12" opacity=".85">'
import random; random.seed(4)
x=0
while x<W:
    w=random.randint(50,120); h=random.randint(40,200)
    if 440<x<640: h=random.randint(20,60)
    sky+=f'<rect x="{x}" y="{H-200-h}" width="{w-6}" height="{h+200}"/>'; x+=w
# Baiterek
bx=540
sky+=f'<path d="M{bx-9} {H-200} L{bx-6} {H-330} L{bx+6} {H-330} L{bx+9} {H-200}Z" fill="#5e0d12"/>'
for k in range(-3,4):
    ex=bx+k*22; ey=H-430-abs(k)*6
    sky+=f'<path d="M{bx} {H-330} C{bx+k*4} {H-370} {ex+k*6} {H-395} {ex} {ey}" stroke="#5e0d12" stroke-width="7" fill="none" stroke-linecap="round"/>'
sky+='</g>'
sky+=f'<circle cx="{bx}" cy="{H-418}" r="44" fill="url(#gold)" filter="url(#glow)"/>'
sky+=f'<rect x="0" y="{H-210}" width="{W}" height="210" fill="#4a0a0e"/>'
html=f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{width:{W}px;height:{H}px;overflow:hidden;font-family:Inter,sans-serif}}
.c{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:radial-gradient(ellipse at 50% 35%,#d4313a 0%,#b31f27 45%,#7a1117 100%)}}
.logo{{position:absolute;left:50%;transform:translateX(-50%);top:110px;width:440px}}
.txt{{position:absolute;left:330px;top:560px}}
.n{{font-size:330px;font-weight:900;line-height:.9;letter-spacing:-8px;background:linear-gradient(180deg,#FFE680,#FEC50C 55%,#E0A100);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 0 30px rgba(254,197,12,.45))}}
.m{{font-size:96px;font-weight:900;line-height:1;margin-top:10px;background:linear-gradient(180deg,#FFE680,#FEC50C 60%,#E0A100);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 0 18px rgba(254,197,12,.4))}}
.d{{font-size:76px;font-weight:800;line-height:1.05;color:#fff;margin-top:22px}}
.kz{{position:absolute;left:334px;top:1150px;color:#FFE680;font-size:44px;font-weight:700}}
.url{{position:absolute;left:0;right:0;bottom:90px;text-align:center;color:#fff;font-size:40px;font-weight:800;letter-spacing:1px}}
</style></head><body><div class="c">
<svg width="{W}" height="{H}" style="position:absolute;inset:0">
<defs>
<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFE680"/><stop offset=".5" stop-color="#FEC50C"/><stop offset="1" stop-color="#D99A00"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="10" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<radialGradient id="rays" cx="50%" cy="30%"><stop offset="0" stop-color="#fff" stop-opacity=".18"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#rays)"/>
{rosette(560,840,420,28,1.9,.07)}{rosette(560,840,300,20,1.5,.07)}
{sky}
<g fill="url(#gold)" filter="url(#glow)">{w1}{w2}{body}{tail}</g>
</svg>
<img class="logo" src="data:image/png;base64,{LW}">
<div class="txt"><div class="n">25</div><div class="m">ОКТЯБРЯ</div><div class="d">ДЕНЬ<br>РЕСПУБЛИКИ</div></div>
<div class="kz">Республика күні<br>құтты болсын!</div>
<div class="url">anescom.kz</div>
</div></body></html>"""
open(D+'story.html','w').write(html)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':W,'height':H})
        await pg.goto('file://'+D+'story.html'); await pg.wait_for_timeout(300)
        await pg.screenshot(path=D+'out/story.png'); await b.close()
asyncio.run(main())
from PIL import Image
Image.open(D+'out/story.png').resize((450,800)).save(D+'story_prev.png')
