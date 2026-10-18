"""Сборка зеркала архива для папки пользователя D:\\ANESCOM_Claude (правило 5 в CLAUDE.md).

python3 tools/mirror_pdf.py OUT_DIR
Кладёт в OUT_DIR ту же структуру: 00_ОГЛАВЛЕНИЕ.md/.pdf, Проекты\\NN_*.md/.pdf,
Журнал\\журнал.md/.pdf, Хронология_по_дням.md/.pdf, TASKS.md.
Статусы-эмодзи в PDF заменяются на [СДЕЛАНО]/[В РАБОТЕ]/…; PDF — через wkhtmltopdf.
"""
import re
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
ARC = ROOT / "archive"

STATUS = {"✅": "[СДЕЛАНО]", "🔄": "[В РАБОТЕ]", "⏳": "[ЖДЁТ]", "📋": "[В ОЧЕРЕДИ]", "💤": "[ОТЛОЖЕНО]",
          "⚠️": "[ВНИМАНИЕ]", "⚠": "[ВНИМАНИЕ]", "⏸": "[ПАУЗА]", "ℹ️": "[ИНФО]", "ℹ": "[ИНФО]", "⏰": "[НАПОМИНАНИЕ]"}

CSS = """body{font-family:'DejaVu Sans',Arial,sans-serif;font-size:10.5pt;color:#16222f;line-height:1.45;margin:0}
h1{color:#002a56;font-size:18pt;border-bottom:3px solid #cc2b28;padding-bottom:6px}
h2{color:#002a56;font-size:14pt;margin-top:18px}h3{color:#002a56;font-size:12pt}
blockquote{border-left:4px solid #cc2b28;background:#f5f7fa;margin:8px 0;padding:6px 12px}
code{font-family:'DejaVu Sans Mono',monospace;font-size:9pt;background:#f0f3f7;padding:0 3px}
.st{font-weight:bold;color:#002a56}"""


def clean(text: str) -> str:
    for k, v in STATUS.items():
        text = text.replace(k, v)
    # прочие эмодзи (вне BMP) — убрать, wkhtmltopdf их не рисует
    return re.sub("[\U00010000-\U0010ffff\u2600-\u27bf\ufe0f]", "", text)


def build(md_path: Path, out_md: Path, pdf=True):
    out_md.parent.mkdir(parents=True, exist_ok=True)
    text = md_path.read_text(encoding="utf-8")
    out_md.write_text(text, encoding="utf-8")
    if not pdf:
        return
    html = markdown.markdown(clean(text), extensions=["extra", "sane_lists"])
    html = re.sub(r"\[(СДЕЛАНО|В РАБОТЕ|ЖДЁТ|В ОЧЕРЕДИ|ОТЛОЖЕНО|ВНИМАНИЕ|ПАУЗА|ИНФО|НАПОМИНАНИЕ)\]",
                  r'<span class="st">[\1]</span>', html)
    tmp = out_md.with_suffix(".tmp.html")
    tmp.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
                   f"<body>{html}</body></html>", encoding="utf-8")
    subprocess.run(["wkhtmltopdf", "-q", "--encoding", "utf-8", "-s", "A4", "-T", "14mm", "-B", "14mm",
                    "-L", "14mm", "-R", "14mm",
                    str(tmp), str(out_md.with_suffix(".pdf"))], check=False)
    tmp.unlink()


def main(out: Path):
    for p in sorted(ARC.glob("*.md")):
        if p.name == "00_ОГЛАВЛЕНИЕ.md":
            build(p, out / p.name)
        elif re.match(r"\d\d_", p.name):
            build(p, out / "Проекты" / p.name)
    build(ARC / "ЖУРНАЛ.md", out / "Журнал" / "журнал.md")
    build(ARC / "ARCHIVE_ЗАДАЧ.md", out / "Хронология_по_дням.md")
    build(ROOT / "TASKS.md", out / "TASKS.md", pdf=False)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
