import asyncio, math
from playwright.async_api import async_playwright
D='/tmp/claude-0/kz/'
DEFS='''<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#8a5f17"/><stop offset=".18" stop-color="#f6dc8a"/><stop offset=".32" stop-color="#c39233"/>
<stop offset=".5" stop-color="#fff0b8"/><stop offset=".66" stop-color="#b8862b"/><stop offset=".82" stop-color="#f1d27a"/><stop offset="1" stop-color="#7a5212"/></linearGradient>
<filter id="bev" x="-10%" y="-10%" width="120%" height="120%">
<feGaussianBlur in="SourceAlpha" stdDeviation="3" result="b"/>
<feSpecularLighting in="b" surfaceScale="6" specularConstant="1" specularExponent="22" lighting-color="#fff4cc" result="s"><feDistantLight azimuth="235" elevation="42"/></feSpecularLighting>
<feComposite in="s" in2="SourceAlpha" operator="in" result="s2"/>
<feComposite in="SourceGraphic" in2="s2" operator="arithmetic" k1="0" k2="1" k3=".75" k4="0" result="lit"/>
<feDropShadow in="lit" dx="4" dy="6" stdDeviation="5" flood-color="#000" flood-opacity=".45"/>
</filter></defs>'''
def feather(x,y,ang,L,Wd):
    return f'<path transform="translate({x} {y}) rotate({ang})" d="M0 0 C{-Wd} {-L*.15} {-Wd*.9} {-L*.8} 0 {-L} C{Wd*.9} {-L*.8} {Wd} {-L*.15} 0 0Z"/>'
def spiral(cx,cy,r0,turns,w,dirn=1,start=0):
    pts=[]; n=60
    for i in range(n+1):
        t=i/n; a=start+dirn*t*turns*2*math.pi; r=r0*(1-t*0.85)
        pts.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    d='M'+' L'.join('%.1f %.1f'%p for p in pts)
    return f'<path d="{d}" fill="none" stroke="url(#g)" stroke-width="{w}" stroke-linecap="round"/>'
def blade(x0,y0,x1,y1,bend,w):
    mx,my=(x0+x1)/2,(y0+y1)/2; dx,dy=x1-x0,y1-y0; L=math.hypot(dx,dy); nx,ny=-dy/L,dx/L
    c1=(mx+nx*(bend+w),my+ny*(bend+w)); c2=(mx+nx*(bend-w),my+ny*(bend-w))
    return f'<path d="M{x0} {y0} Q{c1[0]:.0f} {c1[1]:.0f} {x1} {y1} Q{c2[0]:.0f} {c2[1]:.0f} {x0} {y0}Z"/>'
up=''.join(blade(380,500,x,y,b,w) for x,y,b,w in [(470,60,40,34),(420,90,25,30),(370,140,15,26),(325,200,8,22),(290,270,4,18)])
rt=''.join(blade(400,560,x,y,b,w) for x,y,b,w in [(700,470,-30,26),(690,530,-22,24),(660,590,-14,22),(620,630,-8,18)])
eagle=f'''<g fill="url(#g)" filter="url(#bev)">
{up}{rt}
<path d="M300 520 C340 470 420 470 450 520 C480 570 450 640 390 660 C330 680 280 640 270 600 C262 570 275 545 300 520Z"/>
<path d="M300 520 C280 480 240 470 205 478 C185 482 165 498 150 520 C175 508 198 506 214 512 C196 522 186 540 188 560 C200 540 222 530 246 532 C262 534 280 540 292 552Z"/>
<path d="M210 478 C190 470 160 474 140 492 C150 500 160 512 166 528 C172 508 186 494 210 478Z"/>
{''.join(feather(330,650,a,L,20) for a,L in [(195,120),(215,135),(235,140),(255,130)])}
</g>
<g filter="url(#bev)">{spiral(560,700,55,1.1,16,-1,math.pi)}<path d="M440 640 C480 690 520 720 560 700" fill="none" stroke="url(#g)" stroke-width="18" stroke-linecap="round"/></g>
<circle cx="232" cy="500" r="7" fill="#3a2608"/>'''
txt='''<g fill="url(#g)" filter="url(#bev)" font-family="DejaVu Sans Condensed" font-weight="bold">
<text x="0" y="95" font-size="98">Республика</text>
<text x="0" y="205" font-size="98">күні</text>
<text x="215" y="400" font-size="270" letter-spacing="-6">25</text>
<text x="215" y="500" font-size="98">қазан</text>
</g>'''
sub='''<g fill="url(#g)" filter="url(#bev)" font-family="Inter" font-weight="500" text-anchor="middle">
<text x="450" y="80" font-size="78" letter-spacing="2">С ДНЁМ</text><text x="450" y="175" font-size="78" letter-spacing="2">РЕСПУБЛИКИ!</text></g>'''
def page(w,h,body): return f'<!doctype html><html><head><meta charset="utf-8"><style>*{{margin:0}}body{{background:transparent}}</style></head><body><svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">{DEFS}{body}</svg></body></html>'
jobs={
 'gold_eagle':(760,800,f'<g transform="translate(0 0)">{eagle}</g>'),
 'gold_text':(760,540,f'<g transform="translate(20 10)">{txt}</g>'),
 'gold_sub':(900,220,sub),
 'gold_all':(900,850,f'<g transform="translate(80 20)">{txt}</g><g transform="translate(0 610)">{sub}</g>'),
}
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for n,(w,h,body) in jobs.items():
            pg=await b.new_page(viewport={'width':w,'height':h},device_scale_factor=2)
            await pg.set_content(page(w,h,body)); await pg.wait_for_timeout(200)
            await pg.screenshot(path=D+f'out/{n}.png',omit_background=True); await pg.close()
        await b.close()
asyncio.run(main())
from PIL import Image
im=Image.open(D+'out/gold_all.png'); bg=Image.new('RGBA',im.size,(20,45,50,255)); bg.alpha_composite(im); bg.convert('RGB').resize((450,400)).save(D+'gold_prev.png')
