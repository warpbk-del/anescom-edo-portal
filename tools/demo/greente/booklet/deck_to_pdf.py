import re, os, json, subprocess
from playwright.sync_api import sync_playwright
D='/tmp/claude-0/-home-claude/bfd04471-82c1-5fea-8458-404f5d66c5f6/scratchpad/deck/project'
order=json.load(open(D+'/deck.json',encoding='utf-8'))['order']
blob={'6c5778388332cc3613a7e2c185fdae90':'/home/claude/deckimg/greente-hero-cinematic-v2.webp','78b5ae7895f311a84eab9b8737b92719':'/home/claude/deckimg/factory-aluminium-cnc.jpg','e26bf6b5418fd77bb86ac6f0d33d562b':'/home/claude/deckimg/hero-glass-towers.webp','7df6a9fc10f38e1574de7751b12c02ab':'/home/claude/deckimg/entrance-group-photoreal-v2.webp','cd92fe3dfe2ad7488445a8d20955354a':'/home/claude/deckimg/tws65-assembly-turn.webp','c3d8e900167bf118e6f128eaa75ad0cc':'/home/claude/deckimg/tfs50-facade-panorama.webp','f3b72a23203e1937999c893d7bcb9125':'/home/claude/deckimg/v_30.jpg','6629a0658a32cc66a520944ef2838cc0':'/home/claude/deckimg/v_56.jpg','053810425131d4620911bfbc8ab4ff87':'/home/claude/deckimg/v_72.jpg','b69db8ed799649edab954661f5f343d9':'/home/claude/deckimg/v_84.jpg','4a1fc5994f5cb8e3f2fa0441b7185804':'/home/claude/deckimg/v_99.jpg','341ef78b7af3b36a90316b5071dd0319':'/home/claude/deckimg/v_108.jpg','8b4504e5a5674560e902103036a8bafc':'/home/claude/deckimg/gt_mark.png','f1de3481c267b9888cefb164fe27efd1':'/home/claude/deckimg/logo_light.png'}
ICON={'Verified':'✔','Clock':'◷','Link':'⛓','Trust':'★','Warning':'!','CheckCircle':'✔'}
head='''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:'Montserrat';src:url(file:///usr/share/fonts/opentype/inter/Inter-Regular.otf);font-weight:400}
@font-face{font-family:'Montserrat';src:url(file:///usr/share/fonts/opentype/inter/Inter-Medium.otf);font-weight:500}
@font-face{font-family:'Montserrat';src:url(file:///usr/share/fonts/opentype/inter/Inter-SemiBold.otf);font-weight:600}
@font-face{font-family:'Montserrat';src:url(file:///usr/share/fonts/opentype/inter/Inter-Bold.otf);font-weight:700}
@font-face{font-family:'Montserrat';src:url(file:///usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf);font-weight:800}
@page{size:1920px 1080px;margin:0}
*{margin:0;box-sizing:border-box}body{margin:0}
section{position:relative;width:1920px;height:1080px;overflow:hidden;page-break-after:always}
h1,h2,h3{margin:0}aside{display:none}p{margin:0}
section > *:not([style*="position:absolute"]){position:relative}
.ic{display:flex;align-items:center;justify-content:center;font-weight:800;border-radius:50%;border:4px solid currentColor}
</style></head><body>'''
parts=[]
for sid in order:
    s=open(f'{D}/slides/{sid}.html',encoding='utf-8').read()
    for k,v in blob.items(): s=s.replace('/_blob/'+k,'file://'+v)
    s=re.sub(r'<x-icon name="(\w+)" style="([^"]*)"></x-icon>',lambda m:f'<div class="ic" style="{m.group(2)};font-size:36px">{ICON.get(m.group(1),"•")}</div>',s)
    parts.append(s)
open('deck_print.html','w',encoding='utf-8').write(head+'\n'.join(parts)+'</body></html>')
with sync_playwright() as p:
    br=p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    pg=br.new_page(viewport={'width':1920,'height':1080}); pg.goto('file://'+os.path.abspath('deck_print.html')); pg.wait_for_timeout(1500)
    pg.pdf(path='deck.pdf',width='1920px',height='1080px',print_background=True); br.close()
print('ok')
