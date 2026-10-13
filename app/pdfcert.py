"""Генерация PDF «Квитанция о подписании» для ЭДО АНЕСКОМ.

Стиль повторяет квитанции Documentolog: логотип ANESCOM, DOC ID,
водяной знак, QR-код, блоки отправителя/получателя/подписанта и журнал.
"""
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

_FONT = "Body"
_FONT_B = "Body-Bold"
_registered = False
_STATIC = config.BASE_DIR / "app" / "static"

NAVY = colors.HexColor("#002a56")
BLUE = colors.HexColor("#cc2b28")  # фирменный красный ANESCOM (акцент)
GREY = colors.HexColor("#8a97a4")
DARK = colors.HexColor("#2a3744")

_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/DejaVuSans.ttf", "C:/Windows/Fonts/DejaVuSans-Bold.ttf"),
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
        dt = datetime.fromisoformat(iso).astimezone(
            timezone(timedelta(hours=config.TZ_OFFSET_HOURS)))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return str(iso)


def _stamp(c, W, H, doc_uid):
    """Фон/колонтитулы на каждой странице: водяной знак, DOC ID, логотип."""
    # водяной знак
    wm = _STATIC / "logo_wm.png"
    if wm.exists():
        try:
            img = ImageReader(str(wm))
            iw, ih = img.getSize()
            w = 150 * mm
            h = w * ih / iw
            c.drawImage(img, (W - w) / 2, (H - h) / 2, w, h, mask="auto")
        except Exception:
            pass
    # верхний колонтитул слева
    c.setFont(_FONT, 7); c.setFillColor(GREY)
    c.drawString(14 * mm, H - 10 * mm, f"DOC ID {doc_uid}")
    c.drawString(14 * mm, H - 13 * mm, f"Электронный документ подписан на портале {config.BRAND}")
    # DOC ID вертикально на правом поле
    c.saveState()
    c.translate(W - 6 * mm, H / 2)
    c.rotate(90)
    c.setFont(_FONT, 7); c.setFillColor(BLUE)
    c.drawCentredString(0, 0, f"DOC ID {doc_uid}")
    c.restoreState()


def _logo(c, W, H):
    logo = _STATIC / "logo.png"
    if not logo.exists():
        return
    try:
        img = ImageReader(str(logo))
        iw, ih = img.getSize()
        w = 42 * mm
        h = w * ih / iw
        x = W - 20 * mm - w
        y = H - 16 * mm - h
        c.drawImage(img, x, y, w, h, mask="auto")
        c.setFont(_FONT_B, 9); c.setFillColor(DARK)
        c.drawRightString(W - 20 * mm, y - 4 * mm, 'ТОО «ANESCOM/АНЕСКОМ»')
        c.setFont(_FONT, 8); c.setFillColor(BLUE)
        c.drawRightString(W - 20 * mm, y - 8 * mm, "www.anescom.kz")
    except Exception:
        pass


def _qr_footer(c, W, verify_url, doc_uid):
    try:
        qrw = QrCodeWidget(verify_url)
        b = qrw.getBounds()
        qw = b[2] - b[0]; qh = b[3] - b[1]
        size = 20 * mm
        d = Drawing(size, size, transform=[size / qw, 0, 0, size / qh, 0, 0])
        d.add(qrw)
        renderPDF.draw(d, c, 14 * mm, 8 * mm)
    except Exception:
        pass
    c.setFont(_FONT, 7); c.setFillColor(BLUE)
    c.drawString(37 * mm, 20 * mm, f"DOC ID {doc_uid}")
    c.setFillColor(GREY)
    c.drawString(37 * mm, 16 * mm, f"Электронный документ подписан на портале {config.BRAND}.")
    c.drawString(37 * mm, 12 * mm, "Подлинность проверяется по QR-коду. Подпись — простая электронная (ПЭП).")


def build_certificate(doc, events) -> bytes:
    _ensure_font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    doc_uid = doc["doc_uid"] or doc["id"]
    verify_url = f"{config.PUBLIC_BASE_URL}/s/{doc['sign_token']}"

    _stamp(c, W, H, doc_uid)
    _logo(c, W, H)

    x = 18 * mm
    y = H - 54 * mm

    c.setFont(_FONT_B, 17); c.setFillColor(NAVY)
    c.drawCentredString(W / 2, y, "Квитанция о подписании")
    y -= 12 * mm

    def section(title):
        nonlocal y
        c.setFillColor(colors.HexColor("#aab4bf"))
        c.setFont(_FONT_B, 9)
        c.drawString(x, y, title.upper())
        c.setStrokeColor(colors.HexColor("#e1e6ea")); c.setLineWidth(0.6)
        c.line(x, y - 2 * mm, W - 18 * mm, y - 2 * mm)
        y -= 8 * mm

    def kv(k, v, vcolor=colors.black):
        nonlocal y
        c.setFont(_FONT, 9.5); c.setFillColor(colors.HexColor("#5a6b7a"))
        c.drawString(x, y, k)
        c.setFont(_FONT, 9.5); c.setFillColor(vcolor)
        # перенос длинных значений
        s = str(v) if v not in (None, "") else "—"
        maxw = W - 18 * mm - (x + 52 * mm)
        while c.stringWidth(s, _FONT, 9.5) > maxw and len(s) > 10:
            s = s[:-2]
        c.drawString(x + 52 * mm, y, s)
        y -= 6 * mm

    section("Основная информация")
    kv("DOC ID:", doc_uid)
    kv("Тип документа:", "Документ")
    kv("Тема:", doc["title"])
    kv("Номер в 1С:", doc["external_id"])
    kv("Статус:", "ПОДПИСАН" if doc["status"] == "signed" else doc["status"],
       colors.HexColor("#15804a") if doc["status"] == "signed" else colors.black)
    kv("Дата создания:", _fmt(doc["created_at"]))
    kv("Хэш документа (SHA-256):", (doc["doc_hash"] or "")[:48] + "…")
    y -= 2 * mm

    section("Информация об отправителе")
    kv("Отправитель:", 'ТОО «ANESCOM/АНЕСКОМ»')
    y -= 2 * mm

    section("Информация о получателе")
    kv("Получатель:", doc["client_name"])
    kv("Телефон:", doc["client_phone"])
    y -= 2 * mm

    section("Информация о подписанте")
    kv("Подписал(а):", doc["signer_name"])
    kv("IP-адрес:", doc["signer_ip"])
    kv("Тип подписи:", "Простая электронная подпись (ПЭП), код-подтверждение")
    kv("Дата подписания:", _fmt(doc["signed_at"]))
    y -= 2 * mm

    section("Журнал событий (аудит)")
    c.setFont(_FONT, 8)
    names = {"created": "создан", "sent": "отправлен клиенту",
             "viewed": "просмотрен клиентом", "signed": "подписан",
             "code_failed": "неверный код", "sign_rejected": "отклонён"}
    for e in events:
        if y < 40 * mm:
            c.showPage()
            _ensure_font(); _stamp(c, W, H, doc_uid); _logo(c, W, H)
            y = H - 42 * mm
            c.setFont(_FONT, 8)
        c.setFillColor(DARK)
        c.drawString(x, y, f"{_fmt(e['ts'])}  ·  {names.get(e['kind'], e['kind'])}  ·  IP {e['ip'] or '—'}")
        y -= 4.5 * mm
        if e["detail"]:
            c.setFillColor(GREY)
            det = ("↳ " + e["detail"])
            if c.stringWidth(det, _FONT, 8) > (W - 36 * mm):
                det = det[:120]
            c.drawString(x + 5 * mm, y, det); y -= 4.5 * mm

    _qr_footer(c, W, verify_url, doc_uid)
    c.showPage()
    c.save()
    return buf.getvalue()
