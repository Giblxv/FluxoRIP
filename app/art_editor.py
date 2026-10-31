"""FORGE Art Editor: local, non-destructive raster editing and optional OSS adapters."""
from __future__ import annotations

import io
import os
import subprocess
import tempfile
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base, SessionLocal
from app.models import Order, ProductionEvent

from app.paths import DATA_ROOT
ROOT = DATA_ROOT
ART_DIR = DATA_ROOT / 'art_storage'
ART_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD = 30 * 1024 * 1024
MAX_PIXELS = 70_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
warnings.simplefilter('error', Image.DecompressionBombWarning)
ALLOWED = {'PNG', 'JPEG', 'WEBP', 'BMP', 'TIFF'}
router = APIRouter(prefix='/api/art', tags=['Editor de arte'])


class ArtRevision(Base):
    __tablename__ = 'art_revisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    root_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey('art_revisions.id'), nullable=True)
    order_code: Mapped[str | None] = mapped_column(ForeignKey('orders.code'), nullable=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    file_format: Mapped[str] = mapped_column(String(12), nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    dpi_x: Mapped[int] = mapped_column(Integer, default=300)
    dpi_y: Mapped[int] = mapped_column(Integer, default=300)
    saved_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EditRequest(BaseModel):
    action: str
    x: int = 0
    y: int = 0
    width: int | None = Field(None, ge=1, le=15000)
    height: int | None = Field(None, ge=1, le=15000)
    keep_aspect: bool = True
    dpi: int | None = Field(None, ge=30, le=2400)
    tolerance: int = Field(28, ge=0, le=255)
    mode: str = 'color'
    scale: int = Field(2, ge=2, le=4)


def get_db():
    with SessionLocal() as db:
        yield db


def row_dict(row: ArtRevision) -> dict:
    return {key: getattr(row, key) for key in (
        'id', 'root_id', 'parent_id', 'order_code', 'original_name', 'operation',
        'file_format', 'width', 'height', 'dpi_x', 'dpi_y', 'created_at')}


def get_row(db: Session, asset_id: str) -> ArtRevision:
    row = db.get(ArtRevision, asset_id)
    if row is None:
        raise HTTPException(404, 'Arte não encontrada.')
    return row


def file_path(row: ArtRevision) -> Path:
    path = Path(row.saved_path)
    return path if path.is_absolute() else ROOT / path


def load_image(row: ArtRevision) -> Image.Image:
    try:
        with Image.open(file_path(row)) as im:
            im.load()
            return im.copy()
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise HTTPException(422, 'O arquivo desta revisão não pode ser aberto como imagem.') from exc


def validate_dimensions(w: int, h: int) -> None:
    if w < 1 or h < 1 or w > 15000 or h > 15000 or w * h > MAX_PIXELS:
        raise HTTPException(422, 'Dimensões fora do limite (15.000 px por lado e 70 MP).')


def safe_dpi(im: Image.Image) -> tuple[int, int]:
    raw = im.info.get('dpi') or (300, 300)
    try:
        return tuple(max(30, min(2400, round(float(x)))) for x in raw[:2])
    except (TypeError, ValueError, IndexError):
        return 300, 300


def encode_image(im: Image.Image, fmt: str, dpi: tuple[int, int]) -> bytes:
    out = io.BytesIO()
    params = {'dpi': dpi}
    if fmt == 'JPEG':
        im = im.convert('RGB')
        params.update(quality=95, subsampling=0)
    elif fmt == 'PNG':
        if im.mode not in ('RGB', 'RGBA', 'L', 'LA'):
            im = im.convert('RGBA')
        params.update(optimize=True)
    else:
        raise HTTPException(422, 'Formato de exportação não suportado.')
    if im.info.get('icc_profile'):
        params['icc_profile'] = im.info['icc_profile']
    im.save(out, format=fmt, **params)
    return out.getvalue()


def save_revision(db: Session, data: bytes, *, parent: ArtRevision | None,
                  order_code: str | None, operation: str, filename: str,
                  fmt: str, width: int, height: int, dpi: tuple[int, int]) -> dict:
    asset_id = str(uuid.uuid4())
    root_id = parent.root_id if parent else asset_id
    folder = ART_DIR / root_id
    folder.mkdir(parents=True, exist_ok=True)
    ext = {'PNG': '.png', 'JPEG': '.jpg', 'SVG': '.svg'}[fmt]
    dest = folder / f'{asset_id}{ext}'
    temp = folder / f'{asset_id}.tmp'
    try:
        temp.write_bytes(data)
        temp.replace(dest)
        row = ArtRevision(id=asset_id, root_id=root_id, parent_id=parent.id if parent else None,
                          order_code=order_code, original_name=filename[:255], operation=operation,
                          file_format=fmt, width=width, height=height, dpi_x=dpi[0], dpi_y=dpi[1],
                          saved_path=str(dest.relative_to(ROOT)))
        db.add(row)
        db.add(ProductionEvent(order_code=order_code, event_type='ARTE_' + operation.upper()[:40],
                               message=f'Editor: {operation} - revisão {asset_id[:8]} (original preservado).'))
        db.commit()
        db.refresh(row)
        return row_dict(row)
    except Exception:
        db.rollback()
        dest.unlink(missing_ok=True)
        temp.unlink(missing_ok=True)
        raise


@router.get('/capabilities')
def capabilities():
    import importlib.util
    exe = os.environ.get('FORGE_REALESRGAN_EXE', '')
    return {
        'basic': True,
        'simple_background': True,
        'vectorization': importlib.util.find_spec('vtracer') is not None,
        'ai_background': importlib.util.find_spec('rembg') is not None,
        'ai_upscale': bool(exe and Path(exe).is_file()),
        'ai_upscale_requires': 'FORGE_REALESRGAN_EXE (executável oficial NCNN Vulkan)',
        'max_upload_mb': 30,
        'max_megapixels': 70,
    }


@router.get('')
def list_art(order_code: str | None = None, db: Session = Depends(get_db)):
    q = select(ArtRevision).order_by(ArtRevision.created_at.desc()).limit(500)
    if order_code:
        q = q.where(ArtRevision.order_code == order_code)
    return [row_dict(r) for r in db.scalars(q).all()]


@router.post('/upload', status_code=201)
async def upload_art(file: UploadFile = File(...), order_code: str | None = Form(None),
                     db: Session = Depends(get_db)):
    if order_code and not db.scalar(select(Order.id).where(Order.code == order_code)):
        raise HTTPException(404, 'Pedido não encontrado. Selecione um projeto existente.')
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, 'Arquivo acima de 30 MB.')
    try:
        with Image.open(io.BytesIO(content)) as original:
            if original.format not in ALLOWED:
                raise HTTPException(415, 'Formato não suportado. Use PNG, JPG, WEBP, BMP ou TIFF.')
            original.load()
            image = ImageOps.exif_transpose(original)
            validate_dimensions(*image.size)
            if original.mode == 'CMYK':
                raise HTTPException(415, 'Arquivo CMYK: converta para RGB com perfil de cor apropriado antes de importar. Conversão automática poderia alterar cores DTF.')
            dpi = safe_dpi(original)
            # Preserve transparência do original, sem modificar a arte.
            bytes_out = encode_image(image, 'PNG', dpi)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(415, 'Não foi possível abrir esta imagem.') from exc
    result = save_revision(db, bytes_out, parent=None, order_code=order_code,
                           operation='importada', filename=Path(file.filename or 'arte.png').name,
                           fmt='PNG', width=image.width, height=image.height, dpi=dpi)
    # Cópia imutável dos bytes importados; alterações posteriores geram revisões PNG.
    original_ext = {'PNG':'.png','JPEG':'.jpg','WEBP':'.webp','BMP':'.bmp','TIFF':'.tif'}[original.format]
    (ART_DIR / result['root_id'] / ('original_recebido' + original_ext)).write_bytes(content)
    return result


@router.get('/{asset_id}/original')
def original_upload(asset_id: str, db: Session = Depends(get_db)):
    row = get_row(db, asset_id)
    candidates = list((ART_DIR / row.root_id).glob('original_recebido.*'))
    if not candidates:
        raise HTTPException(404, 'Original recebido não está disponível.')
    return FileResponse(candidates[0], filename=row.original_name, content_disposition_type='attachment',
                        media_type='application/octet-stream')


@router.get('/{asset_id}/download')
def download_art(asset_id: str, db: Session = Depends(get_db)):
    row = get_row(db, asset_id)
    ext = {'PNG': '.png', 'JPEG': '.jpg', 'SVG': '.svg'}[row.file_format]
    return FileResponse(file_path(row), media_type={'PNG':'image/png','JPEG':'image/jpeg','SVG':'image/svg+xml'}[row.file_format],
                        filename=f'FluxoRIP_{row.operation}_{row.id[:8]}{ext}', content_disposition_type='attachment')


@router.get('/{asset_id}/preview')
def preview_art(asset_id: str, db: Session = Depends(get_db)):
    row = get_row(db, asset_id)
    if row.file_format == 'SVG':
        raise HTTPException(415, 'Prévia SVG desativada por segurança. Faça download do SVG.')
    return FileResponse(file_path(row), media_type='image/png' if row.file_format == 'PNG' else 'image/jpeg')


def remove_simple_background(im: Image.Image, tol: int) -> Image.Image:
    """Apaga apenas regiões similares à cor dos cantos e conectadas aos cantos.
    Adequado a fundos chapados; preserva regiões internas isoladas.
    """
    work = im.convert('RGBA')
    w, h = work.size
    # Pillow floodfill uses the seed corner color and a tolerance, avoiding
    # deletion of non-connected interior regions.
    for pos in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if work.getpixel(pos)[3] == 0:
            continue
        ImageDraw.floodfill(work, pos, (0, 0, 0, 0), thresh=tol)
    return work


def run_vectorize(im: Image.Image, mode: str) -> bytes:
    try:
        import vtracer
    except ImportError as exc:
        raise HTTPException(409, 'VTracer não instalado. Execute INSTALAR_OPCIONAIS.bat.') from exc
    # Float / built-in alpha can affect tracing; convert transparent background
    # into white for compatibility with the Python adapter.
    background = Image.new('RGBA', im.size, '#ffffff')
    background.alpha_composite(im.convert('RGBA'))
    raster = io.BytesIO()
    background.convert('RGB').save(raster, format='PNG')
    try:
        if hasattr(vtracer, 'Config'):
            config = vtracer.Config(clustering='bw') if mode == 'bw' else vtracer.Config.poster()
            svg = config.convert_bytes(raster.getvalue())
        else:
            # API 0.6 fallback, if supported.
            with tempfile.TemporaryDirectory() as temp_dir:
                src, dst = Path(temp_dir) / 'source.png', Path(temp_dir) / 'result.svg'
                src.write_bytes(raster.getvalue())
                vtracer.convert_image_to_svg_py(str(src), str(dst), colormode='binary' if mode == 'bw' else 'color')
                svg = dst.read_text(encoding='utf-8')
        return svg.encode('utf-8') if isinstance(svg, str) else svg
    except Exception as exc:
        raise HTTPException(422, f'Não foi possível vetorizar: {str(exc)[:300]}') from exc


def run_ai_background(im: Image.Image) -> Image.Image:
    try:
        from rembg import remove, new_session
    except ImportError as exc:
        raise HTTPException(409, 'rembg não instalado. Execute INSTALAR_OPCIONAIS.bat.') from exc
    try:
        # Explicit u2net: do not use rembg defaults that may require commercial model licenses.
        session = new_session('u2net')
        result = remove(im.convert('RGBA'), session=session)
        return result.convert('RGBA')
    except Exception as exc:
        raise HTTPException(422, f'Falha na remoção com IA: {str(exc)[:280]}') from exc


def run_upscale(im: Image.Image, scale: int) -> Image.Image:
    exe = os.environ.get('FORGE_REALESRGAN_EXE', '')
    if not exe or not Path(exe).is_file():
        raise HTTPException(409, 'Real-ESRGAN não configurado. Consulte o README e defina FORGE_REALESRGAN_EXE.')
    with tempfile.TemporaryDirectory() as temp_dir:
        src, dst = Path(temp_dir) / 'original.png', Path(temp_dir) / 'ampliada.png'
        im.convert('RGBA').save(src, 'PNG')
        try:
            proc = subprocess.run([exe, '-i', str(src), '-o', str(dst), '-s', str(scale),
                                   '-n', 'realesrgan-x4plus-anime'], capture_output=True, text=True,
                                  timeout=240, check=False, cwd=str(Path(exe).resolve().parent))
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(422, f'Falha ao executar Real-ESRGAN: {str(exc)[:220]}') from exc
        if proc.returncode != 0 or not dst.is_file():
            raise HTTPException(422, 'Real-ESRGAN falhou: ' + (proc.stderr or proc.stdout)[-320:])
        with Image.open(dst) as image:
            image.load()
            validate_dimensions(*image.size)
            return image.copy()


@router.post('/{asset_id}/process', status_code=201)
def process_art(asset_id: str, payload: EditRequest, db: Session = Depends(get_db)):
    row = get_row(db, asset_id)
    if row.file_format == 'SVG':
        raise HTTPException(422, 'Selecione uma revisão PNG para continuar editando.')
    im = load_image(row)
    dpi = (row.dpi_x, row.dpi_y)
    action = payload.action
    if action == 'crop':
        if payload.width is None or payload.height is None:
            raise HTTPException(422, 'Informe a região de corte.')
        x, y, w, h = payload.x, payload.y, payload.width, payload.height
        if x < 0 or y < 0 or x + w > im.width or y + h > im.height:
            raise HTTPException(422, 'O corte ultrapassa os limites da imagem.')
        im = im.crop((x, y, x+w, y+h))
    elif action == 'resize':
        w = payload.width
        h = payload.height
        if not w and not h:
            raise HTTPException(422, 'Informe largura ou altura em pixels.')
        if payload.keep_aspect:
            if w:
                h = max(1, round(im.height * w / im.width))
            else:
                w = max(1, round(im.width * h / im.height))
        elif not (w and h):
            raise HTTPException(422, 'Informe largura e altura para redimensionar sem proporção.')
        validate_dimensions(w, h)
        im = im.resize((w, h), Image.Resampling.LANCZOS)
    elif action == 'dpi':
        if payload.dpi is None:
            raise HTTPException(422, 'Informe o DPI desejado.')
        dpi = (payload.dpi, payload.dpi)
    elif action == 'background_simple':
        if im.width * im.height > 20_000_000:
            raise HTTPException(422, 'Para remover fundo em imagens acima de 20 MP, reduza o tamanho ou recorte primeiro.')
        im = remove_simple_background(im, payload.tolerance)
    elif action == 'background_ai':
        if im.width * im.height > 20_000_000:
            raise HTTPException(422, 'Reduza ou recorte a arte antes de aplicar IA acima de 20 MP.')
        im = run_ai_background(im)
    elif action == 'vectorize':
        if im.width * im.height > 20_000_000:
            raise HTTPException(422, 'Reduza ou recorte a imagem antes de vetorizar arquivos acima de 20 MP.')
        result = run_vectorize(im, payload.mode)
        if len(result) > 20 * 1024 * 1024:
            raise HTTPException(422, 'SVG muito grande. Simplifique a imagem antes de vetorizar.')
        return save_revision(db, result, parent=row, order_code=row.order_code,
                             operation=action, filename=row.original_name, fmt='SVG',
                             width=im.width, height=im.height, dpi=dpi)
    elif action == 'upscale_ai':
        validate_dimensions(im.width * payload.scale, im.height * payload.scale)
        im = run_upscale(im, payload.scale)
    else:
        raise HTTPException(422, 'Operação não reconhecida.')
    validate_dimensions(*im.size)
    return save_revision(db, encode_image(im, 'PNG', dpi), parent=row, order_code=row.order_code,
                         operation=action, filename=row.original_name, fmt='PNG',
                         width=im.width, height=im.height, dpi=dpi)
