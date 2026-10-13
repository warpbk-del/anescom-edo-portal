"""Хранилище портала ЭДО АНЕСКОМ (SQLite, stdlib).

Две таблицы:
  documents — документы на подпись и их статус/реквизиты подписанта;
  events    — журнал аудита (каждое значимое действие).
"""
import sqlite3
import secrets
import string
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id            TEXT PRIMARY KEY,
    doc_uid       TEXT,                 -- DOC ID для квитанции (видимый идентификатор)
    external_id   TEXT,                 -- ссылка/номер документа в 1С
    source        TEXT DEFAULT '1C',
    title         TEXT NOT NULL,
    client_name   TEXT,
    client_phone  TEXT,
    body_kind     TEXT NOT NULL,        -- 'pdf' | 'html'
    body_path     TEXT,                 -- путь к файлу (pdf) или html
    doc_hash      TEXT NOT NULL,        -- sha256 содержимого
    sign_token    TEXT UNIQUE NOT NULL, -- секрет в ссылке
    sign_code     TEXT NOT NULL,        -- код подтверждения (ПЭП)
    status        TEXT NOT NULL DEFAULT 'created',
    created_at    TEXT NOT NULL,
    sent_at       TEXT,
    viewed_at     TEXT,
    signed_at     TEXT,
    expires_at    TEXT,
    signer_name   TEXT,
    signer_ip     TEXT,
    signer_ua     TEXT,
    decline_reason TEXT,
    wa_status     TEXT,                 -- результат отправки в WhatsApp
    meta          TEXT                  -- произвольный JSON от 1С
);
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    ts          TEXT NOT NULL,
    kind        TEXT NOT NULL,
    ip          TEXT,
    ua          TEXT,
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_doc ON events(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_ext ON documents(external_id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def conn():
    c = sqlite3.connect(config.DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(_SCHEMA)


def gen_token(n: int = 24) -> str:
    return secrets.token_urlsafe(n)


def gen_code(n: int = None) -> str:
    n = n or config.SIGN_CODE_LEN
    return "".join(secrets.choice(string.digits) for _ in range(n))


def gen_doc_uid() -> str:
    """Видимый DOC ID квитанции, напр. AN-20261013-9F3A1C4D7B0E2655."""
    from datetime import datetime, timezone
    d = datetime.now(timezone.utc).strftime("%Y%m%d")
    tail = "".join(secrets.choice("0123456789ABCDEF") for _ in range(16))
    return f"AN-{d}-{tail}"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def add_event(c, document_id, kind, ip=None, ua=None, detail=None):
    c.execute(
        "INSERT INTO events(document_id, ts, kind, ip, ua, detail) VALUES(?,?,?,?,?,?)",
        (document_id, now_iso(), kind, ip, ua, detail),
    )


def get_doc(c, doc_id):
    return c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()


def get_doc_by_token(c, token):
    return c.execute("SELECT * FROM documents WHERE sign_token=?", (token,)).fetchone()


def get_events(c, doc_id):
    return c.execute(
        "SELECT * FROM events WHERE document_id=? ORDER BY id", (doc_id,)
    ).fetchall()
