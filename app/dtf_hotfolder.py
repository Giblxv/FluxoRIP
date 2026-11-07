"""Opt-in local hot folder. Sources are read only; packages stay in dtf_exports."""

from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import Integer, String, Text, literal_column, select
from sqlalchemy.orm import Mapped, mapped_column

from app.art_editor import ART_DIR, MAX_UPLOAD, import_art_bytes
from app.db import Base, SessionLocal
from app.dtf_studio import (
    ACTIVE,
    EXPORT_DIR,
    PROFILE_DIR,
    DtfRun,
    SheetRequest,
    StrictModel,
    compute_layout,
    get_db,
)

router = APIRouter(prefix="/api/studio/hotfolder", tags=["Automação DTF"])
STABLE_SECONDS = 6
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


class HotFolderConfig(Base):
    __tablename__ = "dtf_hotfolder_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)


class HotFolderReceipt(Base):
    __tablename__ = "dtf_hotfolder_receipts"
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class HotFolderRequest(StrictModel):
    enabled: bool = False
    folder: str = Field("", max_length=2048)
    art_width_mm: float = Field(100, ge=1, le=2000)
    film_width_mm: float = Field(600, ge=50, le=2000)
    margin_mm: float = Field(10, ge=0, le=100)
    max_page_length_mm: float = Field(1000, ge=50, le=3000)
    gap_mm: float = Field(5, ge=0, le=100)
    dpi: int = Field(300)
    mirror: bool = True
    trim: bool = True
    white_percent: int = Field(100, ge=0, le=100)
    choke_mm: float = Field(0.15, ge=0, le=1)
    profile_id: str | None = None


def settings():
    with SessionLocal() as db:
        row = db.get(HotFolderConfig, 1)
        return (
            HotFolderRequest.model_validate_json(row.value_json)
            if row
            else HotFolderRequest()
        )


def sheet_for(config, asset_id, filename):
    values = config.model_dump(exclude={"enabled", "folder", "art_width_mm"})
    return SheetRequest(
        **values,
        name=f"Auto · {filename}"[:120],
        items=[{"asset_id": asset_id, "width_mm": config.art_width_mm, "copies": 1}],
    )


@router.get("")
def get_config():
    with SessionLocal() as db:
        rows = db.execute(
            select(HotFolderReceipt, DtfRun)
            .outerjoin(DtfRun, DtfRun.id == HotFolderReceipt.run_id)
            .order_by(literal_column("dtf_hotfolder_receipts.rowid").desc())
            .limit(30)
        ).all()
        return {
            "settings": settings().model_dump(),
            "last_error": monitor.last_error,
            "receipts": [
                {
                    "filename": receipt.filename,
                    "status": run.status if run else receipt.status,
                    "phase": run.phase if run else None,
                    "run_id": receipt.run_id,
                    "error": receipt.error or (run.error if run else None),
                }
                for receipt, run in rows
            ],
        }


@router.put("")
def configure(payload: HotFolderRequest, db=Depends(get_db)):
    if payload.dpi not in (150, 300, 600):
        raise HTTPException(422, "Selecione 150, 300 ou 600 DPI.")
    if payload.art_width_mm > payload.film_width_mm - 2 * payload.margin_mm:
        raise HTTPException(
            422, "A largura da arte deve caber entre as margens do filme."
        )
    if payload.profile_id:
        from app.dtf_studio import DtfProfile

        if not db.get(DtfProfile, payload.profile_id):
            raise HTTPException(404, "Perfil ICC não encontrado.")
    if payload.enabled:
        folder = Path(payload.folder).expanduser()
        if not folder.is_absolute() or not folder.is_dir():
            raise HTTPException(
                422,
                "Escolha o caminho absoluto de uma pasta existente neste computador servidor.",
            )
        folder = folder.resolve()
        for storage in (ART_DIR, EXPORT_DIR, PROFILE_DIR):
            storage = storage.resolve()
            if (
                folder == storage
                or folder in storage.parents
                or storage in folder.parents
            ):
                raise HTTPException(
                    422,
                    "Use uma pasta de entrada separada das pastas de artes, perfis e exportações do Fluxo RIP.",
                )
        payload.folder = str(folder)
    row = db.get(HotFolderConfig, 1)
    if row:
        row.value_json = payload.model_dump_json()
    else:
        db.add(HotFolderConfig(id=1, value_json=payload.model_dump_json()))
    db.commit()
    monitor.last_error = None
    return {"settings": payload.model_dump()}


class HotFolderMonitor:
    def __init__(self):
        self.last_error = None
        self.observed = {}

    def scan(self):
        config = settings()
        if not config.enabled:
            self.observed.clear()
            return
        folder = Path(config.folder)
        try:
            files = sorted(folder.iterdir())
        except OSError:
            self.last_error = "Pasta automática indisponível. Confira o caminho e a permissão de leitura."
            return
        self.last_error = None
        # Bound per-poll work; don't scan recursively or follow symbolic links.
        candidates = []
        for path in files:
            if (
                path.suffix.lower() not in EXTENSIONS
                or path.is_symlink()
                or not path.is_file()
            ):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size <= 0:
                continue
            signature = (stat.st_size, stat.st_mtime_ns)
            key = str(path)
            previous = self.observed.get(key)
            if previous is None or previous[0] != signature:
                self.observed[key] = (signature, time.monotonic())
                continue
            if time.monotonic() - previous[1] < STABLE_SECONDS:
                continue
            fingerprint = hashlib.sha256(
                (key + "\0" + repr(signature)).encode()
            ).hexdigest()
            candidates.append((path, stat, fingerprint))
        present = {str(p) for p in files}
        self.observed = {k: v for k, v in self.observed.items() if k in present}
        for path, stat, fingerprint in candidates:
            with SessionLocal() as db:
                if db.get(HotFolderReceipt, fingerprint):
                    continue
                if (
                    len(
                        db.scalars(
                            select(DtfRun.id).where(DtfRun.status.in_(ACTIVE))
                        ).all()
                    )
                    >= 20
                ):
                    return
                if stat.st_size > MAX_UPLOAD:
                    db.add(
                        HotFolderReceipt(
                            fingerprint=fingerprint,
                            filename=path.name[:255],
                            status="ERRO",
                            error="Arquivo acima de 30 MB.",
                        )
                    )
                    db.commit()
                    continue
                try:
                    # Re-check after the bounded read: partially copied sources wait.
                    with path.open("rb") as source:
                        data = source.read(MAX_UPLOAD + 1)
                    after = path.stat()
                    if (after.st_size, after.st_mtime_ns) != (
                        stat.st_size,
                        stat.st_mtime_ns,
                    ):
                        self.observed.pop(str(path), None)
                        continue
                    imported = import_art_bytes(data, path.name, db)
                    sheet = sheet_for(config, imported["id"], path.name)
                    compute_layout(sheet, db)
                    run_id = str(uuid.uuid4())
                    db.add(
                        DtfRun(
                            id=run_id,
                            name=sheet.name,
                            request_json=sheet.model_dump_json(),
                        )
                    )
                    db.add(
                        HotFolderReceipt(
                            fingerprint=fingerprint,
                            filename=path.name[:255],
                            status="ENFILEIRADO",
                            run_id=run_id,
                        )
                    )
                    db.commit()
                except OSError:
                    db.rollback()
                    self.last_error = f"Não foi possível ler {path.name}. Nova tentativa no próximo ciclo."
                except HTTPException as exc:
                    db.rollback()
                    db.add(
                        HotFolderReceipt(
                            fingerprint=fingerprint,
                            filename=path.name[:255],
                            status="ERRO",
                            error=str(exc.detail),
                        )
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    self.last_error = "Não foi possível importar uma arte. Confira a pasta e o espaço em disco."
                # One new file per tick keeps the raster queue responsive.
                return


monitor = HotFolderMonitor()
