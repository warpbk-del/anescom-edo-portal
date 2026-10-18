from PIL import Image, ImageDraw, ImageFont
import numpy as np, sys
S=sys.argv[1]; R='/home/claude/anescom-edo-portal/app/static/'
src=Image.open(R+'logo.png').convert('RGBA')
import numpy as np
a=np.array(src.crop((0,0,src.width,114))).astype(float)
# «краснота»: насколько пиксель отличается от белого по зелёному каналу, с учётом прозрачности
r=np.clip((255-a[:,:,1])/(255-43),0,1)*(a[:,:,3]/255)
al=Image.fromarray((r*255).astype('uint8'))
box=al.point(lambda x:255 if x>20 else 0).getbbox(); alpha=al.crop(box)
mark=Image.new('RGBA',alpha.size)
def tint(col):
    m=Image.new('RGBA',mark.size,col); m.putalpha(alpha); return m
NAVY=(0,29,61); RED=(204,43,40); WHITE=(255,255,255)
B=S+'/fonts/Roboto-Black.ttf'; M=S+'/fonts/Roboto-Medium.ttf'
def icon(bg, mk, txt, txtc, sub=None, subc=None, ring=None):
    N=1024; im=Image.new('RGBA',(N,N),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((0,0,N-1,N-1),radius=220,fill=bg)
    if ring: d.rounded_rectangle((40,40,N-41,N-41),radius=185,outline=ring,width=10)
    w=600; h=int(mark.height*w/mark.width); mm=tint(mk).resize((w,h),Image.LANCZOS)
    y0=(N-(h+40+150))//2 if txt else (N-h)//2
    im.alpha_composite(mm,((N-w)//2,y0))
    if txt:
        f=ImageFont.truetype(B,190); tw=d.textlength(txt,font=f)
        d.text(((N-tw)/2,y0+h+10),txt,font=f,fill=txtc)
    return im.resize((512,512),Image.LANCZOS)
v={
 'A':icon(NAVY,RED,'EDO',WHITE,ring=(255,255,255,40)),
 'B':icon(RED,WHITE,'EDO',WHITE),
 'C':icon(WHITE,RED,'EDO',NAVY),
}
for k,im in v.items(): im.save(f'{S}/icon_{k}.png')
# горизонтальный логотип для шапки (на тёмном фоне)
def wide(dark):
    W,H=1400,300; im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    ic=v['A' if not dark else 'B'].resize((260,260),Image.LANCZOS); im.alpha_composite(ic,(20,20))
    f=ImageFont.truetype(B,120); f2=ImageFont.truetype(M,52)
    c1=WHITE if dark else NAVY
    d.text((320,40),'EDO.',font=f,fill=RED if not dark else WHITE)
    x=320+d.textlength('EDO.',font=f); d.text((x,40),'ANESCOM',font=f,fill=c1)
    d.text((324,185),'документы и аналитика',font=f2,fill=(143,166,191) if dark else (107,124,144))
    return im
wide(True).save(S+'/wide_dark.png'); wide(False).save(S+'/wide_light.png')
# лист предпросмотра
sheet=Image.new('RGB',(1800,1000),(238,241,245)); d=ImageDraw.Draw(sheet)
f=ImageFont.truetype(M,40)
for i,k in enumerate('ABC'):
    sheet.paste(v[k].resize((400,400)),(100+i*560,60),v[k].resize((400,400)))
    d.text((280+i*560,480),k,font=f,fill=NAVY)
nav=Image.new('RGB',(860,360),NAVY); w=wide(True).resize((800,171),Image.LANCZOS); nav.paste(w,(30,95),w)
sheet.paste(nav,(40,580)); 
wl=wide(False).resize((800,171),Image.LANCZOS); sheet.paste(wl,(950,675),wl)
sheet.save(S+'/logo_options.png')
