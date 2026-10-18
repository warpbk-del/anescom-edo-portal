"""Штамп электронной подписи EDO.ANESCOM внизу каждой страницы документа (18.10.2026).

Оригинал файла не меняется (его SHA-256 хранится в базе) — штамп накладывается при выдаче
документа на просмотр. В штампе: статус, кто и когда подписал, DOC ID, начало хэша оригинала,
QR на страницу проверки и защитная сетка с микротекстом.
"""
import io
import math

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from . import config, pdfcert
from .pdfcert import NAVY, RED, GREEN, INK

MUTE = colors.HexColor("#46525f")  # темнее, чем в протоколе: штамп печатают и на ч/б принтере

AMBER = colors.HexColor("#a86b05")
GUILL_OK = colors.HexColor("#d9efe2")
GUILL_WAIT = colors.HexColor("#f3e9d2")


def _short_name(n: str) -> str:
    """«Кулданов Бекбол Сисенбиевич» → «Кулданов Б. С.»."""
    p = [x for x in (n or "").split() if x]
    if len(p) <= 1:
        return n or ""
    return p[0] + " " + " ".join(x[0] + "." for x in p[1:3])


def _who(doc, chain):
    """[(ФИО, когда)] подписавших по порядку."""
    out = []
    if chain:
        for s in chain:
            if s["status"] == "signed":
                out.append((s["signer_name"] or s["name"] or s["role_title"] or "", s["signed_at"]))
    elif doc["status"] == "signed":
        out.append((doc["signer_name"] or doc["client_name"] or "", doc["signed_at"]))
    return out


def _fit(c, text, font, size, width):
    while c.stringWidth(text, font, size) > width and len(text) > 4:
        text = text[:-2].rstrip(" ,·") + "…"
    return text


def _guilloche(c, x, y, w, h, col):
    """Защитная сетка: пересекающиеся тонкие волны (как на бланках)."""
    c.saveState()
    p = c.beginPath(); p.roundRect(x, y, w, h, 5); c.clipPath(p, stroke=0, fill=0)
    c.setStrokeColor(col); c.setLineWidth(0.35)
    for k in range(9):
        for sgn in (1, -1):
            path = c.beginPath()
            ph = k * 0.7
            for i in range(0, 121):
                t = i / 120
                xx = x + t * w
                yy = y + h / 2 + sgn * (h * 0.42) * math.sin(t * 7 * math.pi + ph) * math.cos(t * 2 * math.pi + k)
                (path.moveTo if i == 0 else path.lineTo)(xx, yy)
            c.drawPath(path, stroke=1, fill=0)
    c.restoreState()


def _shield(c, cx, cy, r, col, ok):
    c.saveState()
    c.setFillColor(col)
    p = c.beginPath()
    p.moveTo(cx, cy + r)
    p.curveTo(cx + r * 0.55, cy + r * 0.82, cx + r * 0.85, cy + r * 0.82, cx + r * 0.85, cy + r * 0.55)
    p.curveTo(cx + r * 0.85, cy - r * 0.25, cx + r * 0.45, cy - r * 0.75, cx, cy - r)
    p.curveTo(cx - r * 0.45, cy - r * 0.75, cx - r * 0.85, cy - r * 0.25, cx - r * 0.85, cy + r * 0.55)
    p.curveTo(cx - r * 0.85, cy + r * 0.82, cx - r * 0.55, cy + r * 0.82, cx, cy + r)
    c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(colors.white); c.setLineWidth(r * 0.2); c.setLineCap(1); c.setLineJoin(1)
    if ok:  # галочка
        q = c.beginPath(); q.moveTo(cx - r * 0.38, cy + r * 0.02); q.lineTo(cx - r * 0.08, cy - r * 0.3)
        q.lineTo(cx + r * 0.42, cy + r * 0.32); c.drawPath(q, stroke=1, fill=0)
    else:   # часы
        c.setLineWidth(r * 0.13); c.circle(cx, cy, r * 0.42, stroke=1, fill=0)
        q = c.beginPath(); q.moveTo(cx, cy + r * 0.26); q.lineTo(cx, cy); q.lineTo(cx + r * 0.2, cy - r * 0.12)
        c.drawPath(q, stroke=1, fill=0)
    c.restoreState()


def _stamp_page(pw, ph, doc, chain, n, total) -> bytes:
    pdfcert._ensure_font()
    F, FB = pdfcert._FONT, pdfcert._FONT_B
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))

    signed = doc["status"] == "signed"
    who = _who(doc, chain)
    col = GREEN if signed else (NAVY if who else AMBER)
    rows = who[:3]
    w = min(122 * mm, pw - 20 * mm)
    h = (21.5 + 3.3 * max(len(rows), 1)) * mm
    # 10 мм от краёв: в эту зону печатает любой принтер, штамп не обрежется
    x = pw - w - 10 * mm
    y = 10 * mm
    qs = min(h - 5 * mm, 24 * mm)         # размер QR
    tx = x + 14 * mm                      # начало текста
    tw = w - (tx - x) - qs - 6 * mm       # ширина текстовой колонки

    # подложка: белая, рамка цвета статуса, защитная сетка
    c.setFillColor(colors.white); c.setStrokeColor(col); c.setLineWidth(1)
    c.roundRect(x, y, w, h, 5, stroke=1, fill=1)
    _guilloche(c, x, y, w, h, GUILL_OK if (signed or who) else GUILL_WAIT)
    c.setFillColor(colors.white)  # без прозрачности — одинаково на экране и при печати
    c.roundRect(tx - 1.5 * mm, y + 3 * mm, tw + 3 * mm, h - 5 * mm, 3, stroke=0, fill=1)
    # красная полоса ANESCOM слева
    c.setFillColor(RED); c.roundRect(x, y, 2.2 * mm, h, 1.5, stroke=0, fill=1)
    _shield(c, x + 8.2 * mm, y + h / 2 + 1 * mm, 4.6 * mm, col, signed)

    # текст
    yy = y + h - 6 * mm
    title = ("ДОКУМЕНТ ПОДПИСАН ЭЛЕКТРОННО" if signed else
             "ИДЁТ ПОДПИСАНИЕ" if who else "ОЖИДАЕТ ПОДПИСИ")
    c.setFillColor(col); c.setFont(FB, 8.4); c.drawString(tx, yy, _fit(c, title, FB, 8.4, tw))
    yy -= 4.4 * mm
    if rows:
        for n_, t in rows:
            c.setFillColor(col); c.setFont(FB, 7); c.drawString(tx, yy, "✓")
            c.setFillColor(INK); c.setFont(F, 7)
            c.drawString(tx + 3.2 * mm, yy, _fit(c, _short_name(n_), F, 7, tw * 0.55))
            c.setFillColor(MUTE); c.setFont(F, 6.6)
            c.drawRightString(tx + tw, yy, " ".join(pdfcert._fmt(t).split()))
            yy -= 3.3 * mm
        if len(who) > 3:
            yy += 3.3 * mm
            c.setFillColor(MUTE); c.drawRightString(tx + tw * 0.6, yy, f"и ещё {len(who) - 3}")
            yy -= 3.3 * mm
    else:
        c.setFillColor(INK); c.setFont(F, 6.8)
        c.drawString(tx, yy, _fit(c, "Подписей пока нет", F, 6.8, tw))
        yy -= 3.3 * mm
    yy -= 0.6 * mm
    c.setFillColor(MUTE); c.setFont(F, 6.1)
    uid = doc["doc_uid"] or doc["id"]
    c.drawString(tx, yy, _fit(c, f"DOC ID {uid} · SHA-256 {(doc['doc_hash'] or '')[:16]}…", F, 6.1, tw))
    yy -= 3.3 * mm
    c.drawString(tx, yy, _fit(c, f"Электронная подпись с кодом подтверждения · лист {n} из {total}", F, 6.1, tw))
    yy -= 3.4 * mm
    c.setFillColor(NAVY); c.setFont(FB, 6.3)
    c.drawString(tx, yy, _fit(c, "Проверить подлинность: наведите камеру на QR →", FB, 6.3, tw))

    # QR в белой рамке
    qx = x + w - qs - 2.5 * mm
    qy = y + (h - qs) / 2
    c.setFillColor(colors.white); c.setStrokeColor(col); c.setLineWidth(0.6)
    c.roundRect(qx - 0.8 * mm, qy - 0.8 * mm, qs + 1.6 * mm, qs + 1.6 * mm, 2, stroke=1, fill=1)
    pdfcert._qr(c, f"{config.PUBLIC_BASE_URL}/s/{doc['sign_token']}", qx, qy, qs)

    # микротекст по нижнему краю
    c.setFillColor(col); c.setFont(F, 3.2)
    micro = ("EDO.ANESCOM ✓ " + ("ПОДПИСАНО " if signed else "НА ПОДПИСАНИИ ") + uid + " ") * 12
    c.drawString(x + 3.5 * mm, y + 0.9 * mm, _fit(c, micro, F, 3.2, w - qs - 8 * mm))

    c.showPage(); c.save()
    return buf.getvalue()


def stamp(pdf: bytes, doc, chain=None) -> bytes:
    """Возвращает PDF со штампом внизу каждой страницы. При любой ошибке — исходный PDF."""
    try:
        reader = PdfReader(io.BytesIO(pdf))
        if reader.is_encrypted:
            return pdf
        writer = PdfWriter()
        total = len(reader.pages)
        for i, page in enumerate(reader.pages, start=1):
            page.transfer_rotation_to_content()
            box = page.mediabox
            pw, ph = float(box.width), float(box.height)
            ov = PdfReader(io.BytesIO(_stamp_page(pw, ph, doc, chain, i, total))).pages[0]
            if float(box.left) or float(box.bottom):
                from pypdf import Transformation
                ov.add_transformation(Transformation().translate(float(box.left), float(box.bottom)))
            page.merge_page(ov)
            writer.add_page(page)
        writer.add_metadata({"/Producer": "EDO.ANESCOM", "/Subject": f"DOC ID {doc['doc_uid'] or doc['id']}"})
        out = io.BytesIO(); writer.write(out)
        return out.getvalue()
    except Exception:
        return pdf
