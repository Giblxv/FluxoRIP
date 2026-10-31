from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db import SessionLocal, init_db
from app.models import Printer, Order, ProductionEvent, ObservedFile, PrintJob
from app.schemas import PrinterCreate, PrinterUpdate, OrderCreate, StatusUpdate, AssignmentUpdate, PrintJobCreate, PrintJobStatus, PrintJobMove
from app.hoson import HosonAdapter
from app.watcher import FolderMonitor
from app.art_editor import router as art_router
from app.print_console import router as print_console_router
from app.network_scanner import router as network_scanner_router
from app.stations import router as station_router
from app.printer_links import router as printer_links_router
from app.central_auth import auth_middleware

from app.paths import BUNDLE_ROOT, DATA_ROOT
from app.windows_compat import windows_details, webview2_runtime
STATIC = BUNDLE_ROOT / 'web'
monitor = FolderMonitor()


def get_db():
    with SessionLocal() as db:
        yield db


def require_printer(db: Session, printer_id: str):
    item = db.get(Printer, printer_id)
    if not item:
        raise HTTPException(404, 'Impressora não encontrada.')
    return item


def require_order(db: Session, code: str):
    item = db.scalar(select(Order).where(Order.code == code))
    if not item:
        raise HTTPException(404, 'Pedido não encontrado.')
    return item


def validate_assignment(db, printer_id, process):
    if printer_id:
        printer = require_printer(db, printer_id)
        if printer.technology != process:
            raise HTTPException(400, 'Tipo de impressão do pedido é incompatível com a impressora.')


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    monitor.start()
    yield
    monitor.stop()


app = FastAPI(title='Fluxo RIP — Central de Produção', version='1.5.0', lifespan=lifespan)
app.middleware('http')(auth_middleware)
app.include_router(station_router)
app.include_router(printer_links_router)
app.include_router(art_router)
app.include_router(print_console_router)
app.include_router(network_scanner_router)
app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(STATIC / 'index.html')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '1.5.0', 'integration_mode': 'observe_only',
            'machine_telemetry': False, 'monitor_errors': monitor.last_errors,
            'multi_station':True, 'central_mode': __import__('os').environ.get('FORGE_CENTRAL_MODE') == '1'}


@app.get('/api/system')
def system_info():
    return {'version': '1.5.0', 'data_dir': str(DATA_ROOT),
            'interface': 'aplicativo local ou central LAN', 'print_control': False,
            'os': windows_details(), 'webview2': webview2_runtime()}


@app.get('/api/stats')
def stats(db: Session = Depends(get_db)):
    orders = db.scalars(select(Order)).all()
    return {
        'orders_total': len(orders),
        'active': sum(o.status not in ('CONCLUIDO', 'BLOQUEADO') for o in orders),
        'pending_rip': sum(o.status in ('APROVADO', 'AGUARDANDO_RIP') for o in orders),
        'in_print': sum(o.status == 'IMPRIMINDO' for o in orders),
        'completed': sum(o.status == 'CONCLUIDO' for o in orders),
        'printers_total': db.scalar(select(func.count()).select_from(Printer)),
        'files_detected': db.scalar(select(func.count()).select_from(ObservedFile)),
    }


@app.get('/api/printers')
def list_printers(db: Session = Depends(get_db)):
    return db.scalars(select(Printer).order_by(Printer.id)).all()


@app.post('/api/printers', status_code=201)
def create_printer(payload: PrinterCreate, db: Session = Depends(get_db)):
    if db.get(Printer, payload.id):
        raise HTTPException(409, 'Já existe uma impressora com esse ID.')
    item = Printer(**payload.model_dump(exclude={'enabled'}), enabled=int(payload.enabled))
    db.add(item)
    db.add(ProductionEvent(printer_id=item.id, event_type='IMPRESSORA_CADASTRADA',
                           message=f'Impressora {item.name} cadastrada (observação passiva).'))
    db.commit(); db.refresh(item)
    return item


@app.patch('/api/printers/{printer_id}')
def edit_printer(printer_id: str, payload: PrinterUpdate, db: Session = Depends(get_db)):
    item = require_printer(db, printer_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, int(value) if field == 'enabled' else value)
    db.add(ProductionEvent(printer_id=printer_id, event_type='IMPRESSORA_CONFIGURADA',
                           message='Cadastro da impressora atualizado.'))
    db.commit(); db.refresh(item)
    return item


@app.get('/api/printers/{printer_id}/integration')
def printer_integration_status(printer_id: str, db: Session = Depends(get_db)):
    printer = require_printer(db, printer_id)
    return HosonAdapter(printer_id=printer.id, ip=printer.ip,
                        firmware=printer.firmware,
                        printexp_version=printer.printexp_version).health()


@app.post('/api/orders', status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Order.id).where(Order.code == payload.code)):
        raise HTTPException(409, 'Código de pedido já cadastrado.')
    validate_assignment(db, payload.printer_id, payload.process)
    item = Order(**payload.model_dump())
    db.add(item)
    db.add(ProductionEvent(order_code=item.code, printer_id=item.printer_id,
                           event_type='PEDIDO_CRIADO', message='Pedido cadastrado.'))
    db.commit(); db.refresh(item)
    return item


@app.get('/api/orders')
def list_orders(db: Session = Depends(get_db)):
    return db.scalars(select(Order).order_by(Order.created_at.desc())).all()


@app.patch('/api/orders/{code}/status')
def update_order_status(code: str, payload: StatusUpdate, db: Session = Depends(get_db)):
    item = require_order(db, code)
    old = item.status
    if old == payload.status:
        return item
    item.status = payload.status
    db.add(ProductionEvent(order_code=code, printer_id=item.printer_id,
                           event_type='STATUS_MANUAL',
                           message=f'Operador alterou status: {old} → {payload.status}. Não é telemetria da máquina.'))
    db.commit(); db.refresh(item)
    return item


@app.patch('/api/orders/{code}/printer')
def assign_printer(code: str, payload: AssignmentUpdate, db: Session = Depends(get_db)):
    item = require_order(db, code)
    validate_assignment(db, payload.printer_id, item.process)
    item.printer_id = payload.printer_id
    db.add(ProductionEvent(order_code=code, printer_id=item.printer_id,
                           event_type='IMPRESSORA_ATRIBUIDA',
                           message=f'Impressora atribuída: {payload.printer_id or "sem atribuição"}.'))
    db.commit(); db.refresh(item)
    return item


@app.get('/api/files')
def files(limit: int = 150, db: Session = Depends(get_db)):
    return db.scalars(select(ObservedFile).order_by(ObservedFile.detected_at.desc()).limit(max(1, min(limit, 500)))).all()


@app.get('/api/events')
def events(limit: int = 150, db: Session = Depends(get_db)):
    return db.scalars(select(ProductionEvent).order_by(ProductionEvent.created_at.desc()).limit(max(1, min(limit, 500)))).all()


# --- Fila operacional declarada por operadores; SEM controle da controladora ---
@app.get('/api/jobs')
def list_print_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(PrintJob).order_by(PrintJob.position.asc(), PrintJob.id.asc())).all()


@app.post('/api/jobs', status_code=201)
def add_print_job(payload: PrintJobCreate, db: Session = Depends(get_db)):
    order = require_order(db, payload.order_code)
    validate_assignment(db, payload.printer_id, order.process)
    # Garante trabalho único em execução por equipamento no sistema de gestão.
    position = (db.scalar(select(func.max(PrintJob.position))) or 0) + 1
    job = PrintJob(**payload.model_dump(), position=position)
    db.add(job)
    db.flush()
    db.add(ProductionEvent(order_code=order.code, printer_id=payload.printer_id,
                           event_type='FILA_ADICIONADO_MANUAL',
                           message=f'Trabalho #{job.id} adicionado à fila de planejamento (sem enviar à máquina).'))
    db.commit()
    db.refresh(job)
    return job


@app.patch('/api/jobs/{job_id}/status')
def set_print_job_status(job_id: int, payload: PrintJobStatus, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job:
        raise HTTPException(404, 'Trabalho não encontrado.')
    transitions = {
        'AGUARDANDO': {'IMPRIMINDO', 'CANCELADO'},
        'IMPRIMINDO': {'AGUARDANDO', 'CONCLUIDO', 'ERRO'},
        'ERRO': {'AGUARDANDO', 'CANCELADO'},
        'CANCELADO': {'AGUARDANDO'},
        'CONCLUIDO': set(),
    }
    target = payload.status
    if target == job.status:
        return job
    if target not in transitions.get(job.status, set()):
        raise HTTPException(409, f'Transição não permitida: {job.status} → {target}.')
    if target == 'IMPRIMINDO':
        competing = db.scalar(select(PrintJob.id).where(PrintJob.printer_id == job.printer_id,
                                                        PrintJob.status == 'IMPRIMINDO',
                                                        PrintJob.id != job.id))
        if competing:
            raise HTTPException(409, f'Já existe trabalho #{competing} marcado como imprimindo nesta máquina.')
    old = job.status
    job.status = target
    now = datetime.now(timezone.utc)
    if target == 'IMPRIMINDO':
        job.started_at = now
        job.finished_at = None
    if target in ('CONCLUIDO', 'ERRO', 'CANCELADO'):
        job.finished_at = now
    if target == 'AGUARDANDO':
        job.finished_at = None
        job.started_at = None
    db.add(ProductionEvent(order_code=job.order_code, printer_id=job.printer_id,
                           event_type='FILA_STATUS_MANUAL',
                           message=f'Trabalho #{job.id}: {old} → {target}. Informado pelo operador; sem confirmação Hoson.'))
    db.commit()
    db.refresh(job)
    return job


@app.patch('/api/jobs/{job_id}/move')
def move_print_job(job_id: int, payload: PrintJobMove, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job:
        raise HTTPException(404, 'Trabalho não encontrado.')
    if job.status != 'AGUARDANDO':
        raise HTTPException(409, 'Só é permitido reordenar trabalhos aguardando.')
    items = db.scalars(select(PrintJob).where(PrintJob.printer_id == job.printer_id,
                                              PrintJob.status == 'AGUARDANDO')
                       .order_by(PrintJob.position, PrintJob.id)).all()
    idx = next((i for i, item in enumerate(items) if item.id == job.id), None)
    if idx is None:
        raise HTTPException(404, 'Trabalho não encontrado na fila.')
    ordered = [item for item in items if item.id != job.id]
    if payload.direction == 'top':
        pos = 0
    elif payload.direction == 'bottom':
        pos = len(ordered)
    elif payload.direction == 'up':
        pos = max(0, idx - 1)
    else:
        pos = min(len(ordered), idx + 1)
    ordered.insert(pos, job)
    # Reserva posições menores para trabalhos aguardando dentro da mesma impressora.
    for i, item in enumerate(ordered):
        item.position = i + 1
    db.add(ProductionEvent(order_code=job.order_code, printer_id=job.printer_id,
                           event_type='FILA_REORDENADA_MANUAL',
                           message=f'Trabalho #{job.id} movido ({payload.direction}) na fila administrativa.'))
    db.commit()
    db.refresh(job)
    return job
