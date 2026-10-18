"""Показать заголовок и несколько строк файла выгрузки: python peek.py bp accsub_Типовой [подстрока ...] [-n 5]"""
import sys
from lg import path
a = sys.argv[1:]
n = int(a[a.index("-n") + 1]) if "-n" in a else 5
base, name = a[0], a[1]
flt = [x for x in a[2:] if not x.startswith("-") and not x.isdigit()]
with open(path(base, name), encoding="utf-8-sig", errors="replace") as f:
    print(f.readline().rstrip())
    k = 0
    for line in f:
        if not flt or any(x in line for x in flt):
            print(line.rstrip()[:400])
            k += 1
            if k >= n:
                break
