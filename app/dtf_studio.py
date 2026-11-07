"""Local DTF prepress: deterministic nesting, real raster work and durable exports.

No controller protocol, device halftoning or production PRT is implemented here.
RGB+alpha and white are portable; CMYK requires an operator supplied output ICC.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageChops, ImageCms, ImageFilter, ImageOps
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, Text, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.art_editor import ArtRevision, file_path, get_row, load_image, row_dict
from app.db import Base, SessionLocal
from app.paths import DATA_ROOT

router = APIRouter(prefix="/api/studio", tags=["Studio DTF"])
EXPORT_DIR = DATA_ROOT / "dtf_exports"
PROFILE_DIR = DATA_ROOT / "dtf_profiles"
MAX_SHEET_PIXELS = 40_000_000
MAX_THUMBNAIL = 900
ACTIVE = ("AGUARDANDO", "PROCESSANDO")


def now():
    return datetime.now(timezone.utc)


class DtfRun(Base):
    __tablename__ = "dtf_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="AGUARDANDO")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str] = mapped_column(String(160), default="Na fila de rasterização")
    request_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DtfProfile(Base):
    __tablename__ = "dtf_color_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class PlacementRequest(StrictModel):
    asset_id: str = Field(min_length=1, max_length=36)
    width_mm: float = Field(100, ge=1, le=2000)
    copies: int = Field(1, ge=1, le=200)


class SheetRequest(StrictModel):
    name: str = Field("Composição DTF", min_length=1, max_length=120)
    items: list[PlacementRequest] = Field(min_length=1, max_length=50)
    film_width_mm: float = Field(600, ge=50, le=2000)
    margin_mm: float = Field(10, ge=0, le=100)
    gap_mm: float = Field(5, ge=0, le=100)
    dpi: Literal[150, 300, 600] = 300
    mirror: bool = True
    trim: bool = True
    white_percent: int = Field(100, ge=0, le=100)
    choke_mm: float = Field(0.15, ge=0, le=1)
    profile_id: str | None = Field(None, max_length=36)


def get_db():
    with SessionLocal() as db:
        yield db


def profile_info(row):
    return {"id": row.id, "name": row.name, "sha256": row.sha256}


def source_rgb(image):
    """Normalize embedded RGB profiles; fail closed if a supplied ICC is invalid."""
    rgb = image.convert("RGB")
    embedded = image.info.get("icc_profile")
    if not embedded:
        return rgb
    try:
        return ImageCms.profileToProfile(
            rgb,
            ImageCms.ImageCmsProfile(io.BytesIO(embedded)),
            ImageCms.createProfile("sRGB"),
            outputMode="RGB",
        )
    except (ImageCms.PyCMSError, OSError, ValueError) as exc:
        raise HTTPException(
            422,
            "Perfil ICC da arte inválido ou incompatível com RGB. Converta a arte para sRGB.",
        ) from exc


_inspection_lock = threading.Lock()


def inspection_key(row):
    if row.file_format == "SVG":
        raise HTTPException(422, "Rasterize o SVG antes de preparar a composição DTF.")
    path = file_path(row)
    try:
        stat = path.stat()
    except OSError as exc:
        raise HTTPException(
            422, "O arquivo desta revisão não está disponível."
        ) from exc
    return str(path), stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=256)
def _metadata(path, mtime_ns, size_bytes):
    # Only small metadata survives this call; never retain full-resolution rasters.
    image = load_image(ArtRevision(saved_path=path))
    alpha = image.convert("RGBA").getchannel("A")
    # Validate an embedded profile without duplicating a potentially 70 MP image.
    probe = Image.new("RGB", (1, 1))
    if image.info.get("icc_profile"):
        probe.info["icc_profile"] = image.info["icc_profile"]
        source_rgb(probe)
    return (
        image.size,
        alpha.getbbox(),
        alpha.getextrema(),
        bool(image.info.get("icc_profile")),
    )


def asset_metadata(row):
    # Coalesce simultaneous layout/preflight calls during rapid input changes.
    with _inspection_lock:
        return _metadata(*inspection_key(row))


@lru_cache(maxsize=16)
def _thumbnail(path, mtime_ns, size_bytes):
    image = load_image(ArtRevision(saved_path=path))
    image.thumbnail((MAX_THUMBNAIL, MAX_THUMBNAIL))
    out = io.BytesIO()
    image.convert("RGBA").save(out, "PNG")
    return out.getvalue()


@router.get("/assets")
def assets(db: Session = Depends(get_db)):
    # Imported artwork, including old editor revisions, remains available.
    rows = db.scalars(
        select(ArtRevision)
        .where(ArtRevision.file_format != "SVG")
        .order_by(ArtRevision.created_at.desc())
        .limit(500)
    ).all()
    return [row_dict(row) for row in rows]


@router.get("/assets/{asset_id}/preflight")
def preflight(asset_id: str, db: Session = Depends(get_db)):
    row = get_row(db, asset_id)
    dimensions, bbox, extrema, embedded = asset_metadata(row)
    return {
        "id": row.id,
        "pixels": list(dimensions),
        "content_box": bbox,
        "has_transparency": extrema[0] < 255,
        "empty": bbox is None,
        "embedded_icc": embedded,
        "source_dpi": [row.dpi_x, row.dpi_y],
        "warnings": (
            []
            if extrema[0] < 255
            else ["Arte sem transparência: o fundo também receberá tinta branca."]
        )
        + (
            [] if embedded else ["Sem ICC incorporado: entrada interpretada como sRGB."]
        ),
    }


@router.get("/assets/{asset_id}/thumbnail")
def thumbnail(asset_id: str, db: Session = Depends(get_db)):
    from fastapi.responses import Response

    with _inspection_lock:
        data = _thumbnail(*inspection_key(get_row(db, asset_id)))
    return Response(
        data, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"}
    )


@router.get("/profiles")
def profiles(db: Session = Depends(get_db)):
    return [profile_info(r) for r in db.scalars(select(DtfProfile)).all()]


@router.post("/profiles", status_code=201)
async def upload_profile(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(413, "ICC acima de 4 MB.")
    try:
        profile = ImageCms.ImageCmsProfile(io.BytesIO(data))
        if profile.profile.xcolor_space.strip() != "CMYK":
            raise ValueError("not CMYK")
        ImageCms.buildTransform(ImageCms.createProfile("sRGB"), profile, "RGB", "CMYK")
    except (ImageCms.PyCMSError, OSError, ValueError, TypeError) as exc:
        raise HTTPException(
            422,
            "Use um perfil ICC de saída CMYK válido para sua tinta, filme e impressora.",
        ) from exc
    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(DtfProfile).where(DtfProfile.sha256 == digest))
    if existing:
        return profile_info(existing)
    row = DtfProfile(
        id=str(uuid.uuid4()),
        name=Path(file.filename or "Perfil CMYK").name[:160],
        sha256=digest,
    )
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    path = PROFILE_DIR / f"{row.id}.icc"
    path.write_bytes(data)
    try:
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return profile_info(row)


def compute_layout(payload: SheetRequest, db: Session):
    if sum(i.copies for i in payload.items) > 200:
        raise HTTPException(422, "Máximo de 200 cópias por composição.")
    available = payload.film_width_mm - 2 * payload.margin_mm
    if available <= 0:
        raise HTTPException(422, "As margens ocupam toda a largura do filme.")
    placements, warnings, definitions = [], [], []
    for item in payload.items:
        row = get_row(db, item.asset_id)
        dimensions, bbox, extrema, embedded = asset_metadata(row)
        if bbox is None:
            raise HTTPException(
                422, f"{row.original_name}: arte totalmente transparente."
            )
        bounds = bbox if payload.trim else (0, 0, *dimensions)
        w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]
        height_mm = item.width_mm * h / w
        if item.width_mm > available + 1e-6:
            raise HTTPException(
                422,
                f"{row.original_name}: largura de {item.width_mm:g} mm excede a área útil de {available:g} mm.",
            )
        effective_dpi = w * 25.4 / item.width_mm
        if effective_dpi < payload.dpi:
            warnings.append(
                f"{row.original_name}: resolução efetiva {effective_dpi:.0f} DPI; haverá interpolação para {payload.dpi} DPI."
            )
        if extrema[0] == 255:
            warnings.append(
                f"{row.original_name}: sem transparência; o fundo fará parte da impressão."
            )
        if not embedded:
            warnings.append(
                f"{row.original_name}: entrada sem ICC interpretada como sRGB."
            )
        definitions.extend(
            [
                {
                    "asset_id": row.id,
                    "name": row.original_name,
                    "width_mm": item.width_mm,
                    "height_mm": height_mm,
                    "content_box": list(bounds),
                    "effective_dpi": round(effective_dpi, 1),
                }
                for _ in range(item.copies)
            ]
        )
    # First-fit decreasing shelf packing, deterministic for a given request.
    shelves = []
    for spec in sorted(definitions, key=lambda r: (-r["height_mm"], -r["width_mm"])):
        shelf = next(
            (
                s
                for s in shelves
                if s["x"] + spec["width_mm"]
                <= payload.film_width_mm - payload.margin_mm + 1e-6
            ),
            None,
        )
        if shelf is None:
            y = (
                (shelves[-1]["y"] + shelves[-1]["height"] + payload.gap_mm)
                if shelves
                else payload.margin_mm
            )
            shelf = {"x": payload.margin_mm, "y": y, "height": spec["height_mm"]}
            shelves.append(shelf)
        placements.append({**spec, "x_mm": shelf["x"], "y_mm": shelf["y"]})
        shelf["x"] += spec["width_mm"] + payload.gap_mm
    height = shelves[-1]["y"] + shelves[-1]["height"] + payload.margin_mm
    width_px = max(1, round(payload.film_width_mm * payload.dpi / 25.4))
    height_px = max(1, math.ceil(height * payload.dpi / 25.4))
    if width_px * height_px > MAX_SHEET_PIXELS or max(width_px, height_px) > 30000:
        raise HTTPException(
            422,
            "Composição excede 40 MP ou 30.000 px por lado. Reduza cópias, tamanho ou DPI, ou divida em mais composições.",
        )
    profile = db.get(DtfProfile, payload.profile_id) if payload.profile_id else None
    if payload.profile_id and not profile:
        raise HTTPException(404, "Perfil ICC não encontrado.")
    if not profile:
        warnings.append(
            "Saída RGB + branco. Para gerar CMYK calibrado, selecione um ICC de saída CMYK."
        )
    area = sum(p["width_mm"] * p["height_mm"] for p in placements)
    return {
        "film_width_mm": payload.film_width_mm,
        "film_height_mm": round(height, 4),
        "width_px": width_px,
        "height_px": height_px,
        "placements": placements,
        "copies": len(placements),
        "utilization_percent": round(100 * area / (payload.film_width_mm * height), 1),
        "warnings": list(dict.fromkeys(warnings)),
        "profile": profile_info(profile) if profile else None,
    }


@router.post("/layout")
def layout(payload: SheetRequest, db: Session = Depends(get_db)):
    return compute_layout(payload, db)


def run_info(row):
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "progress": row.progress,
        "phase": row.phase,
        "error": row.error,
        "created_at": row.created_at,
        "finished_at": row.finished_at,
        "request": json.loads(row.request_json),
        "result": json.loads(row.result_json) if row.result_json else None,
        "download_url": f"/api/studio/runs/{row.id}/download"
        if row.status == "CONCLUIDO"
        else None,
    }


@router.get("/runs")
def runs(db: Session = Depends(get_db)):
    return [
        run_info(r)
        for r in db.scalars(
            select(DtfRun).order_by(DtfRun.created_at.desc()).limit(100)
        ).all()
    ]


@router.post("/runs", status_code=201)
def enqueue(payload: SheetRequest, db: Session = Depends(get_db)):
    compute_layout(payload, db)
    if len(db.scalars(select(DtfRun.id).where(DtfRun.status.in_(ACTIVE))).all()) >= 20:
        raise HTTPException(
            409, "Fila cheia. Aguarde a rasterização dos trabalhos atuais."
        )
    row = DtfRun(
        id=str(uuid.uuid4()),
        name=payload.name.strip() or "Composição DTF",
        request_json=payload.model_dump_json(),
    )
    db.add(row)
    db.commit()
    worker.wake.set()
    return run_info(row)


@router.post("/runs/{run_id}/cancel")
def cancel(run_id: str, db: Session = Depends(get_db)):
    row = db.get(DtfRun, run_id)
    if not row:
        raise HTTPException(404, "Trabalho não encontrado.")
    changed = db.execute(
        update(DtfRun)
        .where(DtfRun.id == run_id, DtfRun.status.in_(ACTIVE))
        .values(status="CANCELADO", phase="Cancelado pelo operador", finished_at=now())
    )
    if not changed.rowcount:
        raise HTTPException(409, "Este trabalho já foi finalizado.")
    db.commit()
    db.refresh(row)
    return run_info(row)


@router.get("/runs/{run_id}/download")
def download(run_id: str, db: Session = Depends(get_db)):
    row = db.get(DtfRun, run_id)
    if not row:
        raise HTTPException(404, "Trabalho não encontrado.")
    path = EXPORT_DIR / f"{row.id}.zip"
    if row.status != "CONCLUIDO" or not path.is_file():
        raise HTTPException(
            409,
            "Pacote ainda não está disponível. Gere novamente se o arquivo foi removido.",
        )
    return FileResponse(
        path, media_type="application/zip", filename=f"FluxoRIP_DTF_{row.id[:8]}.zip"
    )


class Cancelled(Exception):
    pass


def checkpoint(run_id, progress, phase):
    with SessionLocal() as db:
        changed = db.execute(
            update(DtfRun)
            .where(DtfRun.id == run_id, DtfRun.status.in_(ACTIVE))
            .values(progress=progress, phase=phase)
        )
        if not changed.rowcount:
            raise Cancelled()
        db.commit()


def white_mask(alpha, dpi, choke_mm, percent):
    radius = round(choke_mm * dpi / 25.4)
    if radius:
        # Explicit zero border makes erosion of opaque sheet edges correct too.
        expanded = ImageOps.expand(alpha, border=radius, fill=0)
        alpha = expanded.filter(ImageFilter.MinFilter(radius * 2 + 1)).crop(
            (radius, radius, radius + alpha.width, radius + alpha.height)
        )
    return alpha.point([round(v * percent / 100) for v in range(256)])


def encode(image, fmt, dpi, **params):
    buffer = io.BytesIO()
    image.save(buffer, fmt, dpi=(dpi, dpi), **params)
    return buffer.getvalue()


def archive_digest(archive, filename):
    with archive.open(filename) as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def render_run(run_id):
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = EXPORT_DIR / f"{run_id}.partial"
    final = EXPORT_DIR / f"{run_id}.zip"
    try:
        with SessionLocal() as db:
            row = db.get(DtfRun, run_id)
            payload = SheetRequest.model_validate_json(row.request_json)
            plan = compute_layout(payload, db)
            checkpoint(run_id, 5, "Conferência concluída")
            sheet = Image.new(
                "RGBA", (plan["width_px"], plan["height_px"]), (0, 0, 0, 0)
            )
            for i, p in enumerate(plan["placements"]):
                image = load_image(get_row(db, p["asset_id"])).crop(p["content_box"])
                alpha = image.convert("RGBA").getchannel("A")
                normalized = source_rgb(image).convert("RGBA")
                normalized.putalpha(alpha)
                image = normalized.resize(
                    (
                        max(1, round(p["width_mm"] * payload.dpi / 25.4)),
                        max(1, round(p["height_mm"] * payload.dpi / 25.4)),
                    ),
                    Image.Resampling.LANCZOS,
                )
                sheet.alpha_composite(
                    image,
                    (
                        round(p["x_mm"] * payload.dpi / 25.4),
                        round(p["y_mm"] * payload.dpi / 25.4),
                    ),
                )
                checkpoint(
                    run_id,
                    5 + round(50 * (i + 1) / plan["copies"]),
                    f"Compondo arte {i + 1} de {plan['copies']}",
                )
            if payload.mirror:
                sheet = ImageOps.mirror(sheet)
            alpha = sheet.getchannel("A")
            white = white_mask(
                alpha, payload.dpi, payload.choke_mm, payload.white_percent
            )
            checkpoint(run_id, 65, "Base branca calculada")
            manifest = {
                "schema": "fluxorip.dtf-prepress.v1",
                "created_at": now().isoformat(),
                "request": payload.model_dump(),
                "layout": plan,
                "white_semantics": "0 = sem tinta; 255 = cobertura máxima; não é canal spot de impressora.",
                "orientation": "espelhada" if payload.mirror else "normal",
                "printer_ready": False,
                "halftoned": False,
                "note": "Pré-impressão raster. Importar no RIP de destino, conferir dimensões, evitar novo espelhamento e configurar o branco. Sem PRT/controle Hoson.",
            }
            with zipfile.ZipFile(
                temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1
            ) as archive:
                archive.writestr(
                    "cor_sRGB.png",
                    encode(
                        sheet,
                        "PNG",
                        payload.dpi,
                        icc_profile=ImageCms.ImageCmsProfile(
                            ImageCms.createProfile("sRGB")
                        ).tobytes(),
                    ),
                )
                checkpoint(run_id, 75, "Cor RGB exportada")
                archive.writestr(
                    "branco_W.tif",
                    encode(white, "TIFF", payload.dpi, compression="tiff_lzw"),
                )
                if payload.profile_id:
                    profile_data = (
                        PROFILE_DIR / f"{payload.profile_id}.icc"
                    ).read_bytes()
                    cmyk = ImageCms.profileToProfile(
                        sheet.convert("RGB"),
                        ImageCms.createProfile("sRGB"),
                        ImageCms.ImageCmsProfile(io.BytesIO(profile_data)),
                        outputMode="CMYK",
                    )
                    cmyk = Image.merge(
                        "CMYK",
                        tuple(
                            ImageChops.multiply(band, alpha) for band in cmyk.split()
                        ),
                    )
                    archive.writestr(
                        "cor_CMYK.tif",
                        encode(
                            cmyk,
                            "TIFF",
                            payload.dpi,
                            compression="tiff_lzw",
                            icc_profile=profile_data,
                        ),
                    )
                checkpoint(run_id, 90, "Separações exportadas")
                manifest["files"] = [
                    {
                        "name": info.filename,
                        "size_bytes": info.file_size,
                        "sha256": archive_digest(archive, info.filename),
                    }
                    for info in archive.infolist()
                ]
                archive.writestr(
                    "manifesto.json", json.dumps(manifest, indent=2, ensure_ascii=False)
                )
                archive.writestr(
                    "LEIA_ANTES_DE_IMPRIMIR.txt",
                    "Fluxo RIP — pré-impressão DTF\n\n"
                    "cor_sRGB.png: cor com transparência, perfil sRGB e DPI.\n"
                    "branco_W.tif: máscara em cinza (0=sem tinta, 255=cobertura máxima).\n"
                    "cor_CMYK.tif, quando presente: conversão com o ICC selecionado; cobertura modulada pelo alfa.\n"
                    "O branco é uma separação independente, não um canal spot reconhecido automaticamente.\n"
                    "Importe as separações em um RIP compatível e confira tamanho, orientação e associação do branco.\n"
                    "Se já espelhado, desative o espelhamento no RIP de destino.\n"
                    "Não há retícula de dispositivo, PRT homologado ou envio à controladora.\n",
                )
            with SessionLocal() as finish_db:
                changed = finish_db.execute(
                    update(DtfRun)
                    .where(DtfRun.id == run_id, DtfRun.status.in_(ACTIVE))
                    .values(
                        status="CONCLUIDO",
                        progress=100,
                        phase="Pacote de pré-impressão pronto",
                        result_json=json.dumps(plan),
                        finished_at=now(),
                    )
                )
                if not changed.rowcount:
                    raise Cancelled()
                temp.replace(final)
                finish_db.commit()
    except Cancelled:
        temp.unlink(missing_ok=True)
    except Exception as exc:
        temp.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        logging.exception("Falha na rasterização DTF %s", run_id)
        with SessionLocal() as db:
            row = db.get(DtfRun, run_id)
            if row and row.status != "CANCELADO":
                row.status, row.phase, row.finished_at = (
                    "ERRO",
                    "Não foi possível concluir",
                    now(),
                )
                row.error = (
                    exc.detail
                    if isinstance(exc, HTTPException)
                    else "Falha ao processar ou gravar os arquivos. Confira espaço em disco e integridade das artes."
                )
                db.commit()


class RasterWorker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        # Never present a partially written raster as a completed package.
        with SessionLocal() as db:
            for row in db.scalars(
                select(DtfRun).where(DtfRun.status == "PROCESSANDO")
            ).all():
                row.status, row.phase, row.error = (
                    "ERRO",
                    "Processamento interrompido",
                    "O aplicativo foi fechado durante a rasterização. Gere novamente.",
                )
                row.finished_at = now()
            db.commit()
        self.thread = threading.Thread(
            target=self.loop, name="dtf-raster-worker", daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=7)

    def loop(self):
        while not self.stop_event.is_set():
            try:
                from app.dtf_hotfolder import monitor

                monitor.scan()
                with SessionLocal() as db:
                    row = db.scalar(
                        select(DtfRun)
                        .where(DtfRun.status == "AGUARDANDO")
                        .order_by(DtfRun.created_at)
                        .limit(1)
                    )
                    run_id = row.id if row else None
                    if row:
                        row.status, row.phase = (
                            "PROCESSANDO",
                            "Conferindo artes e dimensões",
                        )
                        db.commit()
                if run_id:
                    render_run(run_id)
                    continue
            except Exception:
                logging.exception("Falha no worker DTF")
            self.wake.wait(1)
            self.wake.clear()


worker = RasterWorker()
