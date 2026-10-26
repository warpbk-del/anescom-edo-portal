# Дубли контрагентов по БИН/ИИН (ANESCOM_FIX) — ТОЛЬКО ЧТЕНИЕ: классификация групп и план объединения.
import re, collections, csv
BINF = 'ИНН'
def nn(x):
    x = (x or '').lower().replace('ё', 'е')
    x = re.sub(r'\b(тоо|ип|ао|оао|зао|ооо|кх|филиал|компания|корпорация|рго|гу|ргу)\b', ' ', x)
    return re.sub(r'[^a-zа-я0-9әғқңөұүһі]', '', x)
R = q(f'ВЫБРАТЬ К.Ссылка КАК С, К.Наименование КАК Н, К.{BINF} КАК Б, К.Партнер КАК П, К.ЮрФизЛицо КАК ЮФ ИЗ Справочник.Контрагенты КАК К '
      f'ГДЕ НЕ К.ПометкаУдаления И К.{BINF} В (ВЫБРАТЬ К2.{BINF} ИЗ Справочник.Контрагенты КАК К2 ГДЕ НЕ К2.ПометкаУдаления И К2.{BINF} <> "" СГРУППИРОВАТЬ ПО К2.{BINF} ИМЕЮЩИЕ КОЛИЧЕСТВО(*) > 1)')
G = collections.defaultdict(list)
for r in R: G[r['Б'].strip()].append(r)
# использование: число ссылок на каждую карточку
a = ib.NewObject('Массив')
for r in R: a.Добавить(r['С'])
T = ib.НайтиПоСсылкам(a); use = collections.Counter(); X = ib.XMLСтрока
for i in range(T.Количество()):
    x = T.Получить(i)
    if x.Метаданные.ПолноеИмя() not in ('Справочник.Контрагенты', 'РегистрСведений.ВерсииОбъектов'): use[X(x.Ссылка)] += 1
auto, ask = [], []
for b, rs in G.items():
    names = {nn(r['Н']) for r in rs}; kinds = {s(r['ЮФ']) for r in rs}
    keep = max(rs, key=lambda r: use[X(r['С'])])
    row = dict(БИН=b, карточек=len(rs), оставить=s(keep['С']), ссылок_всего=sum(use[X(r['С'])] for r in rs),
               все=' | '.join(f"{r['Н']} [{use[X(r['С'])]}; партнёр: {s(r['П'])}]" for r in rs))
    (auto if len(names) == 1 and len(kinds) == 1 else ask).append(row)
print('ГРУПП', len(G), 'карточек', len(R), '| АВТО (одно название)', len(auto), '| РЕШИТЬ (разные названия/вид)', len(ask))
print('ссылок к переносу в АВТО:', sum(r['ссылок_всего'] for r in auto))
for r in ask[:25]: print(' ?', r['БИН'], '|', r['все'][:150])
with open(r'D:\anescom_edo\data\reports\Дубли_контрагентов_план.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['Решение', 'БИН', 'Карточек', 'Оставить', 'Ссылок', 'Карточки [ссылок; партнёр]'])
    for r in auto: w.writerow(['объединить', r['БИН'], r['карточек'], r['оставить'], r['ссылок_всего'], r['все']])
    for r in ask: w.writerow(['РЕШИТЬ', r['БИН'], r['карточек'], r['оставить'], r['ссылок_всего'], r['все']])
CDUP = dict(auto=auto, ask=ask, G=G, use=use)
