# 21-25 (шаг 23) помощник: план zp3350 (без помесячной простыни) + автоматический ZP_SUB по виду субконто 1240/3340.
import urllib.request
_z = urllib.request.urlopen('https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/47c1ff3/tools/com_jobs/zp3350.py', timeout=30).read().decode('utf-8-sig')
DRY = True
exec(_z.split('D2 = ')[0], globals())
orgs = {s(r['О']): r['О'] for r in q('ВЫБРАТЬ О.Ссылка КАК О ИЗ Справочник.Организации КАК О')}
SUBM = {}
for c in ('1240', '3340'):
    t = acc(c).ВидыСубконто.Получить(0).ВидСубконто.ТипЗначения.Типы(); nm = ib.Метаданные.НайтиПоТипу(t.Получить(0)).ПолноеИмя()
    print('субконто', c, nm)
    if nm == 'Справочник.Организации': SUBM[c] = dict(orgs)
    else:
        SUBM[c] = {}
        for on, o in orgs.items():
            r = q(f'ВЫБРАТЬ ПЕРВЫЕ 1 К.Ссылка КАК К ИЗ {nm} КАК К ГДЕ К.Наименование = &Н ИЛИ К.НаименованиеПолное = &Н', Н=o.Наименование)
            if r: SUBM[c][on] = r[0]['К']
            print('   ', on[:40], '→', s(r[0]['К'])[:40] if r else 'НЕ НАЙДЕН')
need = {s(x[1]['Орг']) for x in pl} | {s(x[0]['Орг']) for x in pl}
miss = [(c, o) for c in ('1240', '3340') for o in need if o not in SUBM[c]]
print('не хватает субконто:', miss)
if not miss: ZP_SUB = SUBM; print('ZP_SUB готов')
