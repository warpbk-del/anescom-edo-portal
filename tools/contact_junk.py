import re
R1,R2='qwertyuiop','asdfghjkl'
def junk_email(e):
    e=e.strip(); 
    if '@' not in e: return 'не e-mail'
    loc,dom=e.rsplit('@',1); l=loc.lower()
    if dom.lower() in ('g.us','s.whatsapp.net'): return 'id WhatsApp'
    if re.search(r'[^\x00-\x7f]',e): return 'кириллица'
    if re.fullmatch(r'\d+',l): return 'только цифры'
    if l.isalpha() and len(l)>=4 and len(set(l))<=2: return 'повтор букв'
    if l.isalpha() and len(l)>=5 and not set(l)&set('zxcvbnma'): return 'набор клавиш'
    return ''
def junk_phone(p):
    d=re.sub(r'\D','',p)
    if len(d)<10: return 'короткий'
    t=d[-7:]
    if len(set(t))<=1 or t in ('1234567','7654321','0123456'): return 'повтор цифр'
    return ''
