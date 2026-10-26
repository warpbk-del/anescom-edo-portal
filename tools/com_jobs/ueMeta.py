# Пользовательские ошибки (только чтение): реквизиты нужных объектов → файл на сервере + краткая печать.
MD = ib.Метаданные
OBJ = ['Документы.РеализацияТоваровУслуг', 'Документы.ПриобретениеТоваровУслуг', 'Документы.СчетФактураВыданный', 'Документы.СчетФактураПолученный',
       'Документы.ЗаказКлиента', 'Документы.ПоступлениеБезналичныхДенежныхСредств', 'Документы.СписаниеБезналичныхДенежныхСредств',
       'Документы.ПриходныйКассовыйОрдер', 'Документы.РасходныйКассовыйОрдер', 'Документы.ПеремещениеТоваров', 'Документы.СписаниеНедостачТоваров',
       'Документы.ОприходованиеИзлишковТоваров', 'Документы.АвансовыйОтчет', 'Документы.ЭСФ', 'Документы.ЭлектронныйСчетФактура',
       'Справочники.Контрагенты', 'Справочники.Номенклатура', 'Справочники.Партнеры', 'Справочники.ФизическиеЛица']
out = []
for o in OBJ:
    kind, nm = o.split('.')
    m = getattr(MD, kind).Найти(nm)
    if m is None: out.append(f'{o}: НЕТ'); continue
    at = [m.Реквизиты.Получить(i).Имя for i in range(m.Реквизиты.Количество())]
    tc = []
    for j in range(m.ТабличныеЧасти.Количество()):
        t = m.ТабличныеЧасти.Получить(j)
        if t.Имя in ('Товары', 'Услуги', 'РасшифровкаПлатежа'):
            tc.append(t.Имя + '(' + ','.join(t.Реквизиты.Получить(k).Имя for k in range(t.Реквизиты.Количество())) + ')')
    out.append(f'{o}: ' + ','.join(at) + ' || ' + ' '.join(tc))
# все документы с "ЭСФ"/"СчетФактура" в имени
out.append('DOCS_ESF: ' + ','.join(MD.Документы.Получить(i).Имя for i in range(MD.Документы.Количество()) if 'ЭСФ' in MD.Документы.Получить(i).Имя or 'СчетФакт' in MD.Документы.Получить(i).Имя))
p = r'D:\anescom_edo\data\reports\ue_meta.txt'
open(p, 'w', encoding='utf-8').write('\n'.join(out))
# отправить на портал как раздел ue_meta (для чтения через браузер)
import json, urllib.request
tok = ''
for l in open(r'D:\anescom_edo\config.env', encoding='utf-8-sig'):
    if l.strip().startswith('EDO_API_TOKEN='): tok = l.split('=', 1)[1].strip().strip('"')
body = json.dumps({'section': 'ue_meta', 'source': 'anescom', 'replace': True, 'rows': [{'t': x} for x in out]}, ensure_ascii=False).encode('utf-8')
rq = urllib.request.Request('https://edo.anescom.kz/api/analytics/audit', data=body, method='POST', headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok})
print('PUSH', urllib.request.urlopen(rq, timeout=120).read().decode()[:80])
print('OK', len(out), p)
