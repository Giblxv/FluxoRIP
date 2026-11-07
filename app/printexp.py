"""Read-only PrintExp file integration. No DLL loading, process launch or sockets.

The TSKF v24 envelope and first four length-prefixed fields were checked against
four operator-supplied files. The remaining record bytes are deliberately opaque.
They do not establish printer status or a supported command protocol.
"""

from __future__ import annotations

import configparser
import hashlib
import os
import stat
import struct
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base, SessionLocal
from app.dtf_studio import StrictModel, get_db

router = APIRouter(prefix="/api/studio/printexp", tags=["PrintExp em leitura"])
MAX_TASK_BYTES = 16 * 1024 * 1024
MAX_RECORDS = 10000
DISPLAY_LIMIT = 30
TASK_FILES = ("fileTask.tf", "printTask.tf", "HistoryTask.tf", "recordTask.tf")


class PrintExpConfig(Base):
    __tablename__ = "printexp_read_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)


class PrintExpRequest(StrictModel):
    enabled: bool = False
    folder: str = Field("", max_length=2048)


class FileEvidenceError(ValueError):
    pass


def read_source(root: Path, relative: str, limit: int) -> tuple[bytes, str]:
    """Read only fixed files inside the selected root; reject links and races."""
    path = root / relative
    for part in (path, *path.parents):
        if part == root.parent:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise FileEvidenceError("Link de arquivo ou pasta não permitido.")
    if not path.resolve().is_relative_to(root.resolve()):
        raise FileEvidenceError("Arquivo fora da pasta selecionada.")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise FileEvidenceError("Arquivo inválido ou acima do limite de leitura.")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        content = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    final = path.stat()
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if len(content) > limit or any(
        signature(s) != signature(before) for s in (opened, after, final)
    ):
        raise FileEvidenceError(
            "Arquivo em atualização. Atualize a leitura em instantes."
        )
    return content, datetime.fromtimestamp(after.st_mtime, UTC).isoformat()


def decode_text(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    for encoding in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    raise FileEvidenceError("Codificação de texto não reconhecida.")


def parse_ini(data: bytes) -> configparser.ConfigParser:
    # Project.ini uses // separators in addition to ordinary INI comments.
    parser = configparser.ConfigParser(
        interpolation=None, strict=True, comment_prefixes=(";", "#", "//")
    )
    parser.read_string(decode_text(data))
    return parser


def parse_tasks(data: bytes) -> dict:
    if len(data) < 12 or data[:4] != b"TSKF":
        raise FileEvidenceError("Assinatura TSKF não reconhecida.")
    version, count = struct.unpack_from("<II", data, 4)
    if version != 24:
        raise FileEvidenceError("Versão TSKF não validada. Suporte disponível: 24.")
    if count > MAX_RECORDS:
        raise FileEvidenceError("Quantidade de tarefas acima do limite de leitura.")
    cursor, items = 12, []
    for _ in range(count):
        if cursor + 4 > len(data):
            raise FileEvidenceError("Lista de tarefas incompleta.")
        size = struct.unpack_from("<I", data, cursor)[0]
        start, end = cursor + 4, cursor + 4 + size
        if size < 20 or end > len(data):
            raise FileEvidenceError("Registro de tarefa incompleto.")
        field_cursor, fields = start + 4, []  # First uint32 is opaque.
        for _ in range(4):
            if field_cursor + 4 > end:
                raise FileEvidenceError("Campo de tarefa incompleto.")
            length = struct.unpack_from("<I", data, field_cursor)[0]
            field_cursor += 4
            if length > 4096 or field_cursor + length > end:
                raise FileEvidenceError("Tamanho de campo de tarefa inválido.")
            fields.append(data[field_cursor : field_cursor + length])
            field_cursor += length
        # Never follow task paths or open previews. Only return a basename.
        try:
            task_path = fields[2].decode("utf-8-sig")
        except UnicodeError:
            # This installation contains legacy Windows-1252 Portuguese names.
            # Keep INI's Chinese encoding fallback separate from task filenames.
            task_path = fields[2].decode("cp1252")
        filename = PureWindowsPath(task_path.rstrip("\0")).name
        if not filename or any(ord(c) < 32 for c in filename):
            raise FileEvidenceError("Nome de arquivo de tarefa inválido.")
        if len(items) < DISPLAY_LIMIT:
            items.append(
                {
                    "filename": filename,
                    "extension": PureWindowsPath(filename).suffix.lower(),
                }
            )
        cursor = end
    if cursor != len(data):
        raise FileEvidenceError(
            "Bytes extras na lista de tarefas; formato não validado."
        )
    return {
        "format_version": version,
        "count": count,
        "items": items,
        "shown": len(items),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def settings() -> PrintExpRequest:
    with SessionLocal() as db:
        row = db.get(PrintExpConfig, 1)
        return (
            PrintExpRequest.model_validate_json(row.value_json)
            if row
            else PrintExpRequest()
        )


def snapshot(config: PrintExpRequest) -> dict:
    result = {
        "settings": config.model_dump(),
        "mode": "observe_only",
        "machine_status": "NAO_VERIFICADO",
        "can_submit": False,
        "read_at": datetime.now(UTC).isoformat(),
        "sources": [],
        "configuration": {},
        "issues": [],
    }
    if not config.enabled:
        return result
    root = Path(config.folder)
    try:
        raw, _ = read_source(root, "Project.ini", 128 * 1024)
        project = parse_ini(raw)
        # Allowlisted non-secret options only; never return a whole INI file.
        result["configuration"] = {
            "comm_module": project.getint("COMM_CONFIG", "COMM_MODULE", fallback=None),
            "platform_enabled": project.getboolean(
                "PLATFORM_CONFIG", "ENABLE", fallback=None
            ),
            "project_sha256": hashlib.sha256(raw).hexdigest(),
        }
    except (OSError, ValueError, configparser.Error):
        result["issues"].append(
            "Project.ini indisponível ou com formato não reconhecido."
        )
    for name in TASK_FILES:
        source = {"file": name, "state": "INDISPONIVEL"}
        try:
            raw, modified = read_source(root, f"Data/{name}", MAX_TASK_BYTES)
            source.update(parse_tasks(raw), state="LIDO", modified_at=modified)
        except FileNotFoundError:
            source["error"] = "Arquivo não encontrado nesta instalação."
        except (OSError, ValueError) as exc:
            source["error"] = (
                str(exc)
                if isinstance(exc, FileEvidenceError)
                else "Arquivo indisponível para leitura."
            )
        result["sources"].append(source)
    return result


@router.get("")
def inspect(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return snapshot(settings())


@router.put("")
def configure(
    payload: PrintExpRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    if payload.enabled:
        root = Path(payload.folder).expanduser()
        if (
            not root.is_absolute()
            or not root.is_dir()
            or root.is_symlink()
            or (hasattr(root, "is_junction") and root.is_junction())
        ):
            raise HTTPException(
                422, "Informe a pasta absoluta do PrintExp neste computador servidor."
            )
        root = root.resolve()
        try:
            parse_ini(read_source(root, "Project.ini", 128 * 1024)[0])
            if not (root / "Data").is_dir():
                raise FileEvidenceError("Pasta Data ausente.")
        except (OSError, ValueError, configparser.Error):
            raise HTTPException(
                422,
                "Selecione a pasta que contém Project.ini e a subpasta Data do PrintExp.",
            ) from None
        payload.folder = str(root)
    else:
        payload.folder = ""
    row = db.get(PrintExpConfig, 1)
    if row:
        row.value_json = payload.model_dump_json()
    else:
        db.add(PrintExpConfig(id=1, value_json=payload.model_dump_json()))
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return snapshot(payload)
