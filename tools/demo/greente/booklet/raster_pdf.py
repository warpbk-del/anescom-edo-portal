import os, glob
from PIL import Image
from playwright.sync_api import sync_playwright
os.makedirs('png',exist_ok=True)
for f in glob.glob('png/*.png'): os.remove(f)
with sync_playwright() as p:
    br=p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    pg=br.new_page(viewport={'width':1920,'height':1080})
    pg.goto('file://'+os.path.abspath('deck_print.html')); pg.wait_for_timeout(1500)
    secs=pg.query_selector_all('section')
    for i,s in enumerate(secs): s.screenshot(path=f'png/d{i:02d}.png')
    # booklets: render each page at 250 dpi
    for key in ['zastroyshchiki','okonnye_kompanii','arhitektory_predprinimateli']:
        bp=br.new_page(viewport={'width':1123,'height':794},device_scale_factor=2.6)
        bp.goto('file:///home/claude/booklet/b_'+key+'.html'); bp.wait_for_timeout(800)
        for j,sh in enumerate(bp.query_selector_all('.sheet')): sh.screenshot(path=f'png/b_{key}_{j}.png')
        bp.close()
    br.close()
def topdf(files,out,dpi):
    ims=[Image.open(f).convert('RGB') for f in files]
    ims[0].save(out,save_all=True,append_images=ims[1:],resolution=dpi,quality=92)
deck=sorted(glob.glob('png/d*.png'))
books=[f'png/b_{k}_{j}.png' for k in ['zastroyshchiki','okonnye_kompanii','arhitektory_predprinimateli'] for j in (0,1)]
topdf(deck+books,'/home/claude/GREENTE_prezentaciya_otkrytiya_polnaya.pdf',96)
for k in ['zastroyshchiki','okonnye_kompanii','arhitektory_predprinimateli']:
    topdf([f'png/b_{k}_0.png',f'png/b_{k}_1.png'],f'/home/claude/GREENTE_buklet_{k}.pdf',250)
print(len(deck),len(books))
