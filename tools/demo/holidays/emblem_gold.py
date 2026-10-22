import asyncio, base64
from playwright.async_api import async_playwright
D='/tmp/claude-0/kz/'
M=base64.b64encode(open(D+'emb_mask.png','rb').read()).decode()
W,H=1824,1950
html=f'''<!doctype html><html><head><style>*{{margin:0}}body{{background:transparent}}</style></head><body>
<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg"><defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#8a5f17"/><stop offset=".15" stop-color="#f6dc8a"/><stop offset=".3" stop-color="#c39233"/>
<stop offset=".47" stop-color="#fff0b8"/><stop offset=".63" stop-color="#b8862b"/><stop offset=".8" stop-color="#f1d27a"/><stop offset="1" stop-color="#7a5212"/></linearGradient>
<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><image href="data:image/png;base64,{M}" width="{W}" height="{H}"/></mask>
<filter id="bev" x="-5%" y="-5%" width="110%" height="110%">
<feGaussianBlur in="SourceAlpha" stdDeviation="6" result="b"/>
<feSpecularLighting in="b" surfaceScale="9" specularConstant="1.05" specularExponent="22" lighting-color="#fff4cc" result="s"><feDistantLight azimuth="235" elevation="40"/></feSpecularLighting>
<feComposite in="s" in2="SourceAlpha" operator="in" result="s2"/>
<feComposite in="SourceGraphic" in2="s2" operator="arithmetic" k2="1" k3=".7" result="lit"/>
<feDropShadow in="lit" dx="8" dy="12" stdDeviation="10" flood-color="#000" flood-opacity=".45"/></filter></defs>
<g filter="url(#bev)"><rect width="{W}" height="{H}" fill="url(#g)" mask="url(#m)"/></g></svg></body></html>'''
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':W,'height':H})
        await pg.set_content(html); await pg.wait_for_timeout(500)
        await pg.screenshot(path=D+'out/respublika_kuni_zoloto.png',omit_background=True); await b.close()
asyncio.run(main())
from PIL import Image
im=Image.open(D+'out/respublika_kuni_zoloto.png'); bb=im.getbbox(); im=im.crop(bb); im.save(D+'out/respublika_kuni_zoloto.png'); print(im.size)
for nm,c in (('t',(18,48,52,255)),('r',(180,30,38,255))):
    bg=Image.new('RGBA',im.size,c); bg.alpha_composite(im); bg.convert('RGB').resize((im.width*420//im.height,420)).save(D+f'prev_{nm}.png')
a=Image.open(D+'prev_t.png');c2=Image.open(D+'prev_r.png');c=Image.new('RGB',(a.width*2,420));c.paste(a,(0,0));c.paste(c2,(a.width,0));c.save(D+'prev2.png')
