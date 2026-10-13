"""PDF «Протокол подписания» — фирменный дизайн ЭДО АНЕСКОМ (собственный стиль, с QR)."""
import io
import os
from datetime import datetime, timedelta, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

from . import config

_FONT, _FONT_B, _registered = "Body", "Body-Bold", False
_STATIC = config.BASE_DIR / "app" / "static"

NAVY = colors.HexColor("#002a56")
NAVY2 = colors.HexColor("#013f78")
RED = colors.HexColor("#cc2b28")
GREEN = colors.HexColor("#188a54")
GREEN_BG = colors.HexColor("#e6f6ed")
INK = colors.HexColor("#22313f")
MUTE = colors.HexColor("#7a8795")
LINE = colors.HexColor("#e3e8ee")
CARD = colors.HexColor("#f8fafc")

_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    (str(_STATIC / "DejaVuSans.ttf"), str(_STATIC / "DejaVuSans-Bold.ttf")),
]


def _ensure_font():
    global _registered, _FONT, _FONT_B
    if _registered:
        return
    for reg, bold in _FONT_CANDIDATES:
        if os.path.exists(reg):
            pdfmetrics.registerFont(TTFont(_FONT, reg))
            pdfmetrics.registerFont(TTFont(_FONT_B, bold if os.path.exists(bold) else reg))
            _registered = True
            return
    _FONT, _FONT_B = "Helvetica", "Helvetica-Bold"
    _registered = True


def _fmt(iso):
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso).astimezone(timezone(timedelta(hours=config.TZ_OFFSET_HOURS)))
        return dt.strftime("%d.%m.%Y  %H:%M")
    except Exception:
        return str(iso)


def _watermark(c, W, H):
    wm = _STATIC / "logo_wm.png"
    if not wm.exists():
        return
    try:
        img = ImageReader(str(wm)); iw, ih = img.getSize()
        w = 140 * mm; h = w * ih / iw
        c.drawImage(img, (W - w) / 2, (H - h) / 2 - 20 * mm, w, h, mask="auto")
    except Exception:
        pass


def _qr(c, url, x, y, size):
    try:
        w = QrCodeWidget(url); b = w.getBounds()
        d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0, size / (b[3] - b[1]), 0, 0])
        d.add(w); renderPDF.draw(d, c, x, y)
    except Exception:
        pass


def _card(c, x, y, w, h, title=None):
    c.setFillColor(colors.white); c.setStrokeColor(LINE); c.setLineWidth(1)
    c.roundRect(x, y - h, w, h, 9, stroke=1, fill=1)
    if title:
        c.setFont(_FONT_B, 8.5); c.setFillColor(RED)
        c.drawString(x + 11, y - 15, title.upper())


def build_certificate(doc, events) -> bytes:
    _ensure_font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    M = 16 * mm
    doc_uid = doc["doc_uid"] or doc["id"]
    verify_url = f"{config.PUBLIC_BASE_URL}/s/{doc['sign_token']}"
    signed = doc["status"] == "signed"

    _watermark(c, W, H)

    # ---- верхняя тёмно-синяя полоса ----
    band = 30 * mm
    c.setFillColor(NAVY); c.rect(0, H - band, W, band, fill=1, stroke=0)
    c.setFillColor(RED); c.rect(0, H - band - 2.4 * mm, W, 2.4 * mm, fill=1, stroke=0)
    # логотип в белом чипе
    logo = _STATIC / "logo.png"
    if logo.exists():
        try:
            img = ImageReader(str(logo)); iw, ih = img.getSize()
            lw = 30 * mm; lh = lw * ih / iw
            c.setFillColor(colors.white)
            c.roundRect(M, H - band + (band - lh - 6 * mm) / 2, lw + 8 * mm, lh + 6 * mm, 6, fill=1, stroke=0)
            c.drawImage(img, M + 4 * mm, H - band + (band - lh) / 2, lw, lh, mask="auto")
        except Exception:
            pass
    c.setFillColor(colors.white)
    c.setFont(_FONT_B, 16); c.drawString(M + 46 * mm, H - 14 * mm, "Протокол подписания")
    c.setFont(_FONT, 9.5); c.setFillColor(colors.HexColor("#b9cde3"))
    c.drawString(M + 46 * mm, H - 19.5 * mm, "Электронный документооборот ЭДО АНЕСКОМ")
    c.setFont(_FONT, 8); c.drawRightString(W - M, H - 11 * mm, "DOC ID")
    c.setFont(_FONT_B, 9.5); c.setFillColor(colors.white)
    c.drawRightString(W - M, H - 15.5 * mm, doc_uid)

    y = H - band - 12 * mm

    # ---- полоса статуса ----
    sh = 15 * mm
    if signed:
        c.setFillColor(GREEN_BG); c.setStrokeColor(colors.HexColor("#bfe6cf"))
        c.roundRect(M, y - sh, W - 2 * M, sh, 9, stroke=1, fill=1)
        c.setFillColor(GREEN); c.circle(M + 11 * mm, y - sh / 2, 5 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont(_FONT_B, 13)
        c.drawCentredString(M + 11 * mm, y - sh / 2 - 2.0 * mm, "✓")
        c.setFillColor(GREEN); c.setFont(_FONT_B, 13)
        c.drawString(M + 22 * mm, y - sh / 2 + 1.2 * mm, "ДОКУМЕНТ ПОДПИСАН")
        c.setFillColor(colors.HexColor("#2f7f57")); c.setFont(_FONT, 8.5)
        c.drawString(M + 22 * mm, y - sh / 2 - 3.4 * mm, "Простая электронная подпись (ПЭП) · подтверждение кодом")
    else:
        c.setFillColor(colors.HexColor("#fff4d6")); c.setStrokeColor(colors.HexColor("#f0dca0"))
        c.roundRect(M, y - sh, W - 2 * M, sh, 9, stroke=1, fill=1)
        c.setFillColor(colors.HexColor("#8a6400")); c.setFont(_FONT_B, 12)
        c.drawString(M + 11 * mm, y - sh / 2 - 1 * mm, "Статус: " + (doc["status"] or ""))
    y -= sh + 8 * mm

    # ---- две колонки: документ (слева) + QR (справа) ----
    col_gap = 8 * mm
    qr_w = 52 * mm
    left_w = W - 2 * M - qr_w - col_gap
    doc_h = 52 * mm
    _card(c, M, y, left_w, doc_h, "Документ")

    def kv(x0, yy, k, v, w, vcolor=INK):
        c.setFont(_FONT, 8.5); c.setFillColor(MUTE); c.drawString(x0, yy, k)
        c.setFont(_FONT_B, 9.5); c.setFillColor(vcolor)
        s = str(v) if v not in (None, "") else "—"
        while c.stringWidth(s, _FONT_B, 9.5) > w and len(s) > 6:
            s = s[:-2]
        c.drawString(x0, yy - 4.6 * mm, s)

    ix = M + 11; iy = y - 24
    kv(ix, iy, "Тема документа", doc["title"], left_w - 22); iy -= 11.5 * mm
    kv(ix, iy, "Номер в 1С", doc["external_id"], left_w / 2 - 14)
    kv(ix + left_w / 2, iy, "Дата создания", _fmt(doc["created_at"]), left_w / 2 - 14); iy -= 11.5 * mm
    c.setFont(_FONT, 8.5); c.setFillColor(MUTE); c.drawString(ix, iy, "Хэш документа (SHA-256)")
    c.setFont(_FONT, 7.5); c.setFillColor(INK); c.drawString(ix, iy - 4.2 * mm, (doc["doc_hash"] or "")[:52])

    # QR-карточка
    qx = M + left_w + col_gap
    _card(c, qx, y, qr_w, doc_h)
    c.setFont(_FONT_B, 8.5); c.setFillColor(RED)
    c.drawCentredString(qx + qr_w / 2, y - 15, "ПРОВЕРКА ПОДЛИННОСТИ")
    _qr(c, verify_url, qx + (qr_w - 30 * mm) / 2, y - doc_h + 14 * mm, 30 * mm)
    c.setFont(_FONT, 7); c.setFillColor(MUTE)
    c.drawCentredString(qx + qr_w / 2, y - doc_h + 9 * mm, "Отсканируйте для проверки")
    c.drawCentredString(qx + qr_w / 2, y - doc_h + 5.5 * mm, "статуса документа")
    y -= doc_h + 8 * mm

    # ---- подписант + отправитель/получатель ----
    sp_h = 40 * mm
    _card(c, M, y, W - 2 * M, sp_h, "Подписант")
    c.setFillColor(RED); c.roundRect(M, y - sp_h, 3.5, sp_h, 2, fill=1, stroke=0)
    ix = M + 13; iy = y - 24
    kv(ix, iy, "ФИО подписанта", doc["signer_name"], (W - 2 * M) / 2 - 20)
    kv(ix + (W - 2 * M) / 2, iy, "Телефон", doc["client_phone"], (W - 2 * M) / 2 - 20); iy -= 12 * mm
    kv(ix, iy, "Дата и время подписи", _fmt(doc["signed_at"]), (W - 2 * M) / 2 - 20)
    kv(ix + (W - 2 * M) / 2, iy, "IP-адрес", doc["signer_ip"], (W - 2 * M) / 2 - 20); iy -= 12 * mm
    kv(ix, iy, "Отправитель", "ТОО «ANESCOM/АНЕСКОМ»", (W - 2 * M) / 2 - 20)
    kv(ix + (W - 2 * M) / 2, iy, "Тип подписи", "ПЭП, код из WhatsApp", (W - 2 * M) / 2 - 20)
    y -= sp_h + 8 * mm

    # ---- хронология (временная шкала) ----
    c.setFont(_FONT_B, 8.5); c.setFillColor(RED); c.drawString(M, y, "ХРОНОЛОГИЯ")
    y -= 8 * mm
    names = {"created": "Документ создан", "sent": "Отправлен клиенту",
             "viewed": "Просмотрен клиентом", "signed": "Документ подписан",
             "code_failed": "Введён неверный код", "sign_rejected": "Отклонён"}
    tx = M + 3 * mm
    evs = list(events)
    for i, e in enumerate(evs):
        if y < 28 * mm:
            c.showPage(); _ensure_font(); _watermark(c, W, H); y = H - 24 * mm; tx = M + 3 * mm
        if i < len(evs) - 1:
            c.setStrokeColor(LINE); c.setLineWidth(1.2); c.line(tx, y, tx, y - 12 * mm)
        c.setFillColor(RED); c.circle(tx, y, 1.8 * mm, fill=1, stroke=0)
        c.setFont(_FONT_B, 9.5); c.setFillColor(NAVY)
        c.drawString(tx + 6 * mm, y - 1 * mm, names.get(e["kind"], e["kind"]))
        c.setFont(_FONT, 8); c.setFillColor(MUTE)
        c.drawString(tx + 6 * mm, y - 4.8 * mm, f"{_fmt(e['ts'])}  ·  IP {e['ip'] or '—'}")
        if e["detail"]:
            det = e["detail"]
            if c.stringWidth(det, _FONT, 7.5) > (W - 2 * M - 10 * mm):
                det = det[:110]
            c.setFont(_FONT, 7.5); c.setFillColor(colors.HexColor("#95a2af"))
            c.drawString(tx + 6 * mm, y - 8.2 * mm, det)
        y -= 14 * mm

    # ---- нижняя тёмно-синяя полоса ----
    fb = 14 * mm
    c.setFillColor(NAVY); c.rect(0, 0, W, fb, fill=1, stroke=0)
    c.setFillColor(RED); c.rect(0, fb, W, 1.6 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont(_FONT_B, 8.5)
    c.drawString(M, fb / 2 + 0.6 * mm, "ЭДО АНЕСКОМ")
    c.setFont(_FONT, 7.5); c.setFillColor(colors.HexColor("#b9cde3"))
    c.drawString(M, fb / 2 - 3.2 * mm, "Подлинность проверяется по QR-коду · подпись простая электронная (ПЭП)")
    c.setFont(_FONT, 7.5); c.drawRightString(W - M, fb / 2 - 1.2 * mm, "DOC ID " + doc_uid)

    c.showPage()
    c.save()
    return buf.getvalue()
