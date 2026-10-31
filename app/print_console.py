"""PrintExp-inspired operations console. Never sends commands to Hoson hardware.

All saved settings are FORGE administrative metadata, not printer firmware settings.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, Boolean, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from app.db import Base, SessionLocal
from app.models import Printer, PrintJob, ProductionEvent

router = APIRouter(prefix='/api/print-console', tags=['Impressões — integração passiva'])

def utcnow():
    return datetime.now(timezone.utc)

class PrinterSetup(Base):
    __tablename__ = 'forge_print_profiles'
    printer_id: Mapped[str] = mapped_column(ForeignKey('printers.id'), primary_key=True)
    print_mode: Mapped[str] = mapped_column(String(100), default='A definir no PrintExp')
    passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dpi_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dpi_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speed: Mapped[str] = mapped_column(String(12), default='MEDIUM')
    direction: Mapped[str] = mapped_column(String(16), default='BIDIRECTIONAL')
    margin_x_mm: Mapped[float] = mapped_column(Float, default=0)
    color_bar: Mapped[str] = mapped_column(String(12), default='OFF')
    color_bar_width_mm: Mapped[float] = mapped_column(Float, default=0)
    color_bar_distance_mm: Mapped[float] = mapped_column(Float, default=0)
    feather_mode: Mapped[str] = mapped_column(String(30), default='DESLIGADO')
    flash_before: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_clean: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_notes: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class JobLayout(Base):
    __tablename__ = 'forge_print_layouts'
    job_id: Mapped[int] = mapped_column(ForeignKey('print_jobs.id'), primary_key=True)
    columns: Mapped[int] = mapped_column(Integer, default=1)
    rows: Mapped[int] = mapped_column(Integer, default=1)
    spacing_x_mm: Mapped[float] = mapped_column(Float, default=0)
    spacing_y_mm: Mapped[float] = mapped_column(Float, default=0)
    origin_x_mm: Mapped[float] = mapped_column(Float, default=0)
    origin_y_mm: Mapped[float] = mapped_column(Float, default=0)
    region_width_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    region_height_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    art_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    operator_notes: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TechnicalRecord(Base):
    __tablename__ = 'forge_technical_records'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    printer_id: Mapped[str] = mapped_column(ForeignKey('printers.id'), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    procedure: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    operator: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ProfilePayload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    print_mode: str = Field('A definir no PrintExp', min_length=1, max_length=100)
    passes: int | None = Field(None, ge=1, le=32)
    dpi_x: int | None = Field(None, ge=72, le=2400)
    dpi_y: int | None = Field(None, ge=72, le=2400)
    speed: Literal['LOW','MEDIUM','HIGH'] = 'MEDIUM'
    direction: Literal['LEFT','RIGHT','BIDIRECTIONAL'] = 'BIDIRECTIONAL'
    margin_x_mm: float = Field(0, ge=0, le=1000)
    color_bar: Literal['OFF','LEFT','RIGHT','BOTH'] = 'OFF'
    color_bar_width_mm: float = Field(0, ge=0, le=200)
    color_bar_distance_mm: float = Field(0, ge=0, le=200)
    feather_mode: str = Field('DESLIGADO', min_length=1, max_length=30)
    flash_before: bool = False
    auto_clean: bool = False
    extra_notes: str = Field('', max_length=3000)

class LayoutPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    columns: int = Field(1, ge=1, le=100)
    rows: int = Field(1, ge=1, le=100)
    spacing_x_mm: float = Field(0, ge=0, le=10000)
    spacing_y_mm: float = Field(0, ge=0, le=10000)
    origin_x_mm: float = Field(0, ge=0, le=10000)
    origin_y_mm: float = Field(0, ge=0, le=10000)
    region_width_mm: float | None = Field(None, gt=0, le=10000)
    region_height_mm: float | None = Field(None, gt=0, le=10000)
    art_revision_id: str | None = Field(None, max_length=36)
    operator_notes: str = Field('', max_length=2000)

    @model_validator(mode='after')
    def validate_region(self):
        if (self.region_width_mm is None) != (self.region_height_mm is None):
            raise ValueError('Largura e altura da região devem ser informadas juntas.')
        return self

class RecordPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    printer_id: str = Field(min_length=2, max_length=64)
    category: Literal['CALIBRACAO','MANUTENCAO','CONFIGURACAO','DIAGNOSTICO']
    procedure: Literal[
        'TESTE_BICOS','NIVEL_CABECOTE','VERTICAL_CABECOTE','STEPPING',
        'ESPACAMENTO_HORIZONTAL','ESPACAMENTO_VERTICAL','BIDIRECIONAL','TRAPPING',
        'LIMPEZA','FLASH','HIDRATACAO','MOVIMENTACAO','ALIMENTACAO',
        'TINTA','TENSÃO_VERIFICADA','VERIFICACAO_REDE','BACKUP_PARAMETROS','OUTRO'
    ]
    outcome: Literal['PLANEJADO','REALIZADO','FALHA','PENDENTE']
    operator: str = Field(min_length=2, max_length=100)
    notes: str = Field('', max_length=2000)

CAPABILITIES = {
    'integration_mode': 'observe_only',
    'printexp_protocol_confirmed': False,
    'device_telemetry': False,
    'printer_commands_enabled': False,
    'authentication': 'credenciais do PrintExp não são usadas nem armazenadas',
    'available': ['perfis administrativos', 'propriedades de composição',
                  'prévia ilustrativa', 'histórico manual de manutenção e calibração',
                  'lista de impressoras', 'fila administrativa'],
    'documented_but_not_connected': ['iniciar/parar/pausar', 'limpeza/flash',
                 'movimentar motores', 'ajuste de voltagem', 'gravação de parâmetros',
                 'atualização de firmware', 'indicadores de temperatura/erro em tempo real'],
}

def db_session():
    with SessionLocal() as db:
        yield db

def require_printer(db, pid):
    obj = db.get(Printer, pid)
    if not obj:
        raise HTTPException(404, 'Impressora não encontrada.')
    return obj

def require_job(db, jid):
    obj = db.get(PrintJob, jid)
    if not obj:
        raise HTTPException(404, 'Trabalho não encontrado.')
    return obj

def to_data(obj, fields):
    return {f: getattr(obj, f) for f in fields}

PROFILE_FIELDS = tuple(ProfilePayload.model_fields)
LAYOUT_FIELDS = tuple(LayoutPayload.model_fields)

@router.get('/capabilities')
def capabilities():
    return CAPABILITIES

@router.get('/profiles/{printer_id}')
def get_profile(printer_id: str, db: Session = Depends(db_session)):
    require_printer(db, printer_id)
    obj = db.get(PrinterSetup, printer_id)
    return {'printer_id': printer_id, 'values': to_data(obj, PROFILE_FIELDS) if obj else ProfilePayload().model_dump(),
            'saved': bool(obj), 'applied_to_machine': False}

@router.put('/profiles/{printer_id}')
def save_profile(printer_id: str, payload: ProfilePayload, db: Session = Depends(db_session)):
    require_printer(db, printer_id)
    obj = db.get(PrinterSetup, printer_id)
    if obj is None:
        obj = PrinterSetup(printer_id=printer_id)
        db.add(obj)
    for field, value in payload.model_dump().items():
        setattr(obj, field, value)
    obj.updated_at = utcnow()
    db.add(ProductionEvent(printer_id=printer_id, event_type='PERFIL_FORGE',
        message='Perfil local alterado; nenhum parâmetro foi enviado ao PrintExp ou à Hoson.'))
    db.commit()
    return {'printer_id': printer_id, 'values': to_data(obj, PROFILE_FIELDS), 'saved': True, 'applied_to_machine': False}

@router.get('/jobs/{job_id}/layout')
def get_layout(job_id: int, db: Session = Depends(db_session)):
    job = require_job(db, job_id)
    obj = db.get(JobLayout, job_id)
    return {'job_id': job_id, 'printer_id': job.printer_id, 'copies': job.copies,
            'file_name': job.file_name, 'values': to_data(obj, LAYOUT_FIELDS) if obj else LayoutPayload().model_dump(),
            'saved': bool(obj), 'applied_to_machine': False}

@router.put('/jobs/{job_id}/layout')
def save_layout(job_id: int, payload: LayoutPayload, db: Session = Depends(db_session)):
    job = require_job(db, job_id)
    if job.status != 'AGUARDANDO':
        raise HTTPException(409, 'Altere a composição apenas quando o trabalho estiver AGUARDANDO.')
    if payload.art_revision_id:
        from app.art_editor import ArtRevision
        art = db.get(ArtRevision, payload.art_revision_id)
        if not art:
            raise HTTPException(404, 'Revisão de arte não encontrada.')
        if art.order_code and art.order_code != job.order_code:
            raise HTTPException(409, 'A arte pertence a outro projeto.')
    obj = db.get(JobLayout, job_id)
    if obj is None:
        obj = JobLayout(job_id=job_id)
        db.add(obj)
    for field, value in payload.model_dump().items():
        setattr(obj, field, value)
    obj.updated_at = utcnow()
    db.add(ProductionEvent(order_code=job.order_code, printer_id=job.printer_id,
        event_type='COMPOSICAO_FORGE',
        message=f'Composição administrativa editada para trabalho #{job_id}. Sem envio ao RIP.'))
    db.commit()
    return {'job_id': job_id, 'values': to_data(obj, LAYOUT_FIELDS), 'saved': True, 'applied_to_machine': False}

@router.get('/records')
def list_records(printer_id: str | None = None, limit: int = 100,
                 db: Session = Depends(db_session)):
    statement = select(TechnicalRecord)
    if printer_id:
        require_printer(db, printer_id)
        statement = statement.where(TechnicalRecord.printer_id == printer_id)
    statement = statement.order_by(TechnicalRecord.created_at.desc(), TechnicalRecord.id.desc()).limit(max(1, min(limit, 500)))
    return db.scalars(statement).all()

@router.post('/records', status_code=201)
def create_record(payload: RecordPayload, db: Session = Depends(db_session)):
    require_printer(db, payload.printer_id)
    obj = TechnicalRecord(**payload.model_dump())
    db.add(obj)
    db.add(ProductionEvent(printer_id=payload.printer_id, event_type='REGISTRO_TECNICO_MANUAL',
        message=f'{payload.category}: {payload.procedure} ({payload.outcome}) por {payload.operator}. Não executado pelo Fluxo RIP.'))
    db.commit()
    db.refresh(obj)
    return obj
