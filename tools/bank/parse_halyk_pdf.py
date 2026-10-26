import pdfplumber, re, json, sys
def parse(path):
    rows = []; cur = None
    with pdfplumber.open(path) as p:
        for pg in p.pages:
            lines = {}
            for w in pg.extract_words(keep_blank_chars=False):
                lines.setdefault(round(w["top"]), []).append(w)
            for top in sorted(lines):
                ws = sorted(lines[top], key=lambda w: w["x0"])
                first = ws[0]["text"]
                if re.fullmatch(r"\d\d\.\d\d\.\d{4}", first) and ws[0]["x0"] < 60:
                    deb = "".join(w["text"] for w in ws if 120 < w["x0"] and w["x1"] < 240 and re.fullmatch(r"[\d,]+", w["text"]))
                    kre = "".join(w["text"] for w in ws if w["x0"] >= 225 and w["x1"] < 300 and re.fullmatch(r"[\d,]+", w["text"]))
                    num = ws[1]["text"] if len(ws) > 1 else ""
                    rest = " ".join(w["text"] for w in ws if w["x0"] >= 300)
                    f = lambda t: float(t.replace(",", ".")) if t else 0.0
                    cur = {"d": first, "n": num, "deb": f(deb), "kre": f(kre), "txt": rest}; rows.append(cur)
                elif cur is not None and ws[0]["x0"] >= 300:
                    cur["txt"] += " " + " ".join(w["text"] for w in ws)
                elif cur is not None and any(w["text"] in ("Обороты:", "Исходящий") for w in ws):
                    cur = None
    return rows
for path in sys.argv[1:]:
    R = parse(path); n = path.split("/")[-1][9:17]
    print(n, len(R), f"{sum(r['deb'] for r in R):,.2f}", f"{sum(r['kre'] for r in R):,.2f}", "пустых", sum(1 for r in R if not r['deb'] and not r['kre']), "обе", sum(1 for r in R if r['deb'] and r['kre']))
    json.dump(R, open(f"/tmp/vyp/{n}.json", "w"), ensure_ascii=False)
