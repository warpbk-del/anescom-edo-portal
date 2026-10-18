"""Общие функции чтения выгрузки ANESCOM_Reader (TSV, UTF-8 BOM, табуляция)."""
import csv, os, sys
csv.field_size_limit(10**8)
ROOT = os.environ.get("LEGACY_ROOT", r"D:\anescom_edo\legacy")


def path(base, name):
    return os.path.join(ROOT, base, name + ".tsv")


def exists(base, name):
    return os.path.exists(path(base, name))


def rows(base, name, cols=None):
    """Итератор строк-словарей; cols — оставить только эти колонки (экономия памяти)."""
    p = path(base, name)
    if not os.path.exists(p):
        return
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        head = next(r, None)
        if not head:
            return
        idx = [(i, h) for i, h in enumerate(head) if cols is None or h in cols]
        for line in r:
            yield {h: (line[i] if i < len(line) else "") for i, h in idx}


def header(base, name):
    p = path(base, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        return f.readline().rstrip("\r\n").split("\t")


def num(v):
    try:
        return float(v) if v not in ("", None) else 0.0
    except ValueError:
        try:
            return float(str(v).replace(" ", "").replace(",", "."))
        except ValueError:
            return 0.0


def out(*a):
    print(*a, flush=True)


sys.stdout.reconfigure(encoding="utf-8")
