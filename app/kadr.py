"""6п (19.10.2026): кадровые документы 1С (ANESCOM и АВТОКОМП) на подпись через портал.

1С (расширение «ANESCOM: Кадровые на подпись») при проведении приказа о приёме, переводе, увольнении,
отпуске, трудового договора или договора ГПХ шлёт POST /api/kadr (Bearer EDO_API_TOKEN) с PDF печатной
формы «(NEW)». Маршрут по решению пользователя 19.10.2026:
  1) кадровик (KADR_HR, Караменова Лаура);
  2) сотрудник + все из «Листа ознакомления» — подписывают ВСЕ (шаг all_of);
  3) начальник подразделения сотрудника в Bitrix24 (UF_HEAD);
  4) директор: «Руководитель» из документа, иначе ANESCOM — KADR_DIRECTOR_ANESCOM,
     АВТОКОМП — KADR_DIRECTOR_AVTOKOMP (Имангалиева Алия).
Сотрудник и ознакомляемые ищутся в Bitrix24 по ФИО; телефон — из карточки физлица 1С (решение 19.10 14:17), если там пусто — из Bitrix24.
Повторное проведение — как у З-2: тот же PDF → duplicate, изменённый → старая версия отменяется.
"""
import base64
import binascii
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import config, db, workflow, b24people, chatapp
from .z2 import require_api

router = APIRouter()


class PersonIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None       # телефоны из 1С через «;»
    position: Optional[str] = None


class KadrIn(BaseModel):
    external_id: str = Field(..., description="GUID документа 1С + вид печатной формы")
    title: str
    body_base64: str
    doc_type: Optional[str] = None    # ПриемНаРаботу, Увольнение, Отпуск, …
    form: Optional[str] = None        # представление печатной формы
    number: Optional[str] = None
    org: Optional[str] = None         # организация 1С
    base: Optional[str] = None        # ANESCOM | АВТОКОМП (какая база прислала)
    department: Optional[str] = None
    employee: Optional[PersonIn] = None
    acquaint: Optional[List[PersonIn]] = None
    director_name: Optional[str] = None   # реквизит «Руководитель» документа
    phonebook: Optional[dict] = None      # ФИО физлица 1С → телефоны (19.10 14:20: телефоны всех — из карточек физлиц 1С)
    start: bool = True


def is_avtokomp(p: KadrIn) -> bool:
    t = f"{p.base or ''} {p.org or ''}".lower()
    return "автокомп" in t or "avtokomp" in t or "avtocomp" in t


_BOOK = {}


def _key(name) -> str:
    """«Фамилия Имя [Отчество]» → «фамилия имя» (ё=е): так совпадают ФИО из 1С и из Bitrix24."""
    w = (name or "").lower().replace("ё", "е").split()
    return " ".join(w[:2])


def book_phone(name) -> str:
    return _BOOK.get(_key(name), "")


def _who(name, role, phone_1c="", title=None, all_of=False):
    """Человек по ФИО из Bitrix24, иначе с телефоном из 1С. → (signer, проблема | '')."""
    u = {}
    try:
        u = b24people.user_by_name(name or "")
    except Exception as e:  # noqa
        b24err = str(e)[:120]
    else:
        b24err = ""
    p1c = chatapp.first_phone(phone_1c or "") or chatapp.first_phone(book_phone(name))
    if u:
        s = b24people.person(u, role)
        if p1c:                  # 19.10 14:17: телефоны сотрудников ведут в карточке физлица 1С — он главнее Bitrix24
            s["phone"] = p1c
    else:
        s = {"role": role, "name": name or None, "phone": p1c}
    if title:
        s["role_title"] = title
    if all_of:
        s["all_of"] = True
    prob = ""
    if not s.get("phone"):
        prob = f"{title or workflow.ROLE_TITLES.get(role, role)} {name or ''}: нет мобильного телефона" + (
            f" (Bitrix24: {b24err})" if b24err else (" (в Bitrix24 не найден)" if not u else ""))
    return s, prob, u


def resolve_steps(p: KadrIn):
    problems = []
    _BOOK.clear()
    for k, v in (p.phonebook or {}).items():
        if v and _key(k):
            _BOOK.setdefault(_key(k), str(v))
    hr, pr, _ = _who(config.KADR_HR, "hr")
    problems += [pr] if pr else []

    emp_name = (p.employee.name if p.employee else "") or ""
    emp, pr, emp_u = _who(emp_name, "employee", p.employee.phone if p.employee else "", all_of=True)
    problems += [pr] if pr else []
    step2 = [emp]
    seen = {emp_name.strip().lower()}
    for a in p.acquaint or []:
        if not a.name or a.name.strip().lower() in seen:
            continue
        seen.add(a.name.strip().lower())
        s, pr, _ = _who(a.name, "acquaint", a.phone or "", all_of=True)
        problems += [pr] if pr else []
        step2.append(s)

    head = {}
    how = "сотрудник не найден в Bitrix24"
    if emp_u:
        try:
            hu, how = b24people.dept_head(emp_u)
            head = b24people.person(hu, "head") if hu else {}
            if head and book_phone(head.get("name")):
                head["phone"] = chatapp.first_phone(book_phone(head.get("name"))) or head.get("phone")
        except Exception as e:  # noqa
            how = f"Bitrix24: {str(e)[:120]}"
    if not head:
        head = {"role": "head", "name": None, "phone": ""}
        problems.append(f"Руководитель подразделения: {how} — указать в кабинете")
    elif not head.get("phone"):
        problems.append(f"Руководитель подразделения {head.get('name')}: нет мобильного телефона")

    dname = (config.KADR_DIRECTOR_AVTOKOMP if is_avtokomp(p)
             else (p.director_name or config.KADR_DIRECTOR_ANESCOM))
    dtitle = "Директор АВТОКОМП" if is_avtokomp(p) else "Генеральный директор"
    director, pr, _ = _who(dname, "director", title=dtitle)
    problems += [pr] if pr else []

    # 19.10 15:22: человек из листа ознакомления, который и так подписывает документ как кадровик,
    # руководитель подразделения или директор, второй раз не подписывает — убираем его из ознакомления.
    def _same(a, b):
        if a.get("b24_user_id") and b.get("b24_user_id"):
            return str(a["b24_user_id"]) == str(b["b24_user_id"])
        return bool(_key(a.get("name"))) and _key(a.get("name")) == _key(b.get("name"))
    others = [hr, head, director]
    step2 = [step2[0]] + [a for a in step2[1:] if not any(_same(a, o) for o in others)]
    steps = [[hr], step2, [head], [director]]
    # руководитель подразделения = директор → шаг не дублируем
    if head.get("b24_user_id") and head.get("b24_user_id") == director.get("b24_user_id"):
        steps.pop(2)
    return steps, problems


@router.post("/api/kadr")
def api_kadr(p: KadrIn, request: Request, _=Depends(require_api)):
    try:
        raw = base64.b64decode("".join((p.body_base64 or "").split()), validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "body_base64 не является корректным base64")
    if raw[:4] != b"%PDF":
        raise HTTPException(400, "Содержимое не похоже на PDF (нет сигнатуры %PDF)")
    doc_hash = db.sha256_bytes(raw)
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "?")

    with db.conn() as c:
        workflow.init(c)
        prev = c.execute("SELECT * FROM documents WHERE external_id=? AND workflow=1 "
                         "AND status<>'cancelled' ORDER BY created_at DESC", (p.external_id,)).fetchall()
        for old in prev:
            if old["status"] == "signed":
                return {"status": "already_signed", "id": old["id"], "doc_uid": old["doc_uid"]}
            if old["doc_hash"] == doc_hash:
                return {"status": "duplicate", "id": old["id"], "doc_uid": old["doc_uid"],
                        "steps": workflow.summary(workflow.signers(c, old["id"]))}
        for old in prev:
            workflow.cancel(c, old["id"], "документ в 1С изменён — отправлена новая версия", ip)

    steps, problems = resolve_steps(p)

    doc_id = db.gen_token(8)
    doc_uid = db.gen_doc_uid()
    expires = (datetime.now(timezone.utc) + timedelta(days=config.LINK_TTL_DAYS)).isoformat()
    body_path = str(config.DOCS_DIR / f"{doc_id}.pdf")
    with open(body_path, "wb") as f:
        f.write(raw)
    org = "АВТОКОМП" if is_avtokomp(p) else "ANESCOM"
    meta = {"kind": "kadr", "category": "kadr", "doc_type": p.doc_type, "form": p.form, "number": p.number,
            "org": p.org, "company": org, "branch": f"{p.department or ''} {p.org or ''}",
            "employee": p.employee.name if p.employee else None, "problems": problems}
    emp = steps[1][0]

    with db.conn() as c:
        c.execute(
            """INSERT INTO documents(id, doc_uid, external_id, source, title, client_name,
               client_phone, body_kind, body_path, doc_hash, sign_token, sign_code, status,
               created_at, expires_at, meta)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, doc_uid, p.external_id, "1C", p.title, emp.get("name"),
             emp.get("phone") or None, "pdf", body_path, doc_hash,
             db.gen_token(24), db.gen_code(), "in_progress", db.now_iso(), expires,
             json.dumps(meta, ensure_ascii=False)),
        )
        db.add_event(c, doc_id, "created", ip=ip, detail=f"1С ({org}): {p.title}; hash={doc_hash}")
        workflow.add_signers(c, doc_id, steps)
        for pr in problems:
            db.add_event(c, doc_id, "problem", ip=ip, detail=pr)
        first = workflow.start(c, doc_id, ip) if p.start else []

    sent = workflow.notify(first, ip) if first else []
    with db.conn() as c:
        summary = workflow.summary(workflow.signers(c, doc_id))
    return {"status": "created", "id": doc_id, "doc_uid": doc_uid, "problems": problems,
            "steps": summary, "sent": sent,
            "cabinet_url": f"{config.PUBLIC_BASE_URL}/cabinet/doc/{doc_id}"}
