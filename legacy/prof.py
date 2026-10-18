"""Профиль выгрузки legacy: файлы, строки, колонки. python prof.py <bp|unf> [подстрока-фильтр ...] [-c]"""
import sys, os, glob
base = sys.argv[1]; flt = [a for a in sys.argv[2:] if not a.startswith('-')]; cols = '-c' in sys.argv
d = rf'D:\anescom_edo\legacy\{base}'
for p in sorted(glob.glob(os.path.join(d, '*.tsv'))):
    n = os.path.basename(p)
    if flt and not any(f in n for f in flt):
        continue
    with open(p, encoding='utf-8-sig', errors='replace') as f:
        head = f.readline().rstrip('\n').split('\t')
        rows = sum(1 for _ in f)
    print(f'{n}\t{rows}' + ('\t' + ','.join(head) if cols else ''))
