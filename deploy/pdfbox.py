"""Размеры страниц (MediaBox/CropBox) PDF последних кадровых документов. Запуск из D:\\anescom_edo."""
import io, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
from pypdf import PdfReader
c = sqlite3.connect(r"D:\anescom_edo\data\edo.sqlite3")
for title, path in c.execute("SELECT title, body_path FROM documents WHERE meta LIKE '%\"kind\": \"kadr\"%' ORDER BY created_at DESC LIMIT 2"):
    r = PdfReader(path)
    p = r.pages[0]
    print(title[:60], "| страниц", len(r.pages), "| media", [round(float(x)) for x in p.mediabox], "| crop", [round(float(x)) for x in p.cropbox], "| rotate", p.get("/Rotate"))
