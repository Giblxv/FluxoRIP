"""Monitoramento PASSIVO de diretórios locais/compartilhados.

Detecta arquivos somente depois de 6 segundos sem alteração. Não abre,
não move, não modifica e não envia nada ao PrintExp. É intencionalmente
um polling leve, para tolerar caminhos de rede Windows/SMB e múltiplas máquinas.
"""
from pathlib import Path
from datetime import datetime, timezone
from threading import Event, Thread
import time
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db import SessionLocal
from app.models import Printer, Order, ProductionEvent, ObservedFile

POLL_SECONDS = 4
STABLE_SECONDS = 6
EXCLUDED_SUFFIXES = {'.tmp', '.part', '.partial', '.crdownload', '.lock'}


class FolderMonitor:
    def __init__(self):
        self.stop_event = Event()
        self.thread = None
        self.last_errors = {}

    def start(self):
        self.stop_event.clear()
        self.thread = Thread(target=self._loop, name='folder-monitor', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=7)

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                self.scan()
            except Exception as exc:
                self.last_errors['global'] = str(exc)
            self.stop_event.wait(POLL_SECONDS)

    def scan(self):
        with SessionLocal() as db:
            printers = db.scalars(select(Printer).where(Printer.enabled == 1)).all()
            for printer in printers:
                if not printer.watch_folder:
                    continue
                folder = Path(printer.watch_folder)
                if not folder.is_dir():
                    self.last_errors[printer.id] = 'Pasta não encontrada ou sem acesso.'
                    continue
                try:
                    # Sem recursão e sem modificar os diretórios do operador.
                    for file in folder.iterdir():
                        if not file.is_file() or file.suffix.lower() in EXCLUDED_SUFFIXES:
                            continue
                        try:
                            stat = file.stat()
                        except OSError:
                            continue
                        if stat.st_size <= 0 or time.time() - stat.st_mtime < STABLE_SECONDS:
                            continue
                        exists = db.scalar(select(ObservedFile.id).where(
                            ObservedFile.printer_id == printer.id,
                            ObservedFile.filepath == str(file),
                            ObservedFile.mtime_ns == stat.st_mtime_ns,
                            ObservedFile.size_bytes == stat.st_size,
                        ))
                        if exists:
                            continue
                        # Associação apenas se código estiver presente no nome de arquivo.
                        codes = db.scalars(select(Order.code)).all()
                        name = file.name.upper()
                        matches = [code for code in codes if code.upper() in name]
                        match = max(matches, key=len) if len(matches) == 1 else None
                        db.add(ObservedFile(printer_id=printer.id,
                            order_code=match, filename=file.name, filepath=str(file),
                            size_bytes=stat.st_size, mtime_ns=stat.st_mtime_ns))
                        db.add(ProductionEvent(printer_id=printer.id, order_code=match,
                            event_type='ARQUIVO_DETECTADO',
                            message=f'Arquivo estável observado: {file.name} ({stat.st_size} bytes). Não significa impressão.'))
                        try:
                            db.commit()
                        except IntegrityError:
                            db.rollback()
                    self.last_errors.pop(printer.id, None)
                except (OSError, PermissionError) as exc:
                    db.rollback()
                    self.last_errors[printer.id] = str(exc)
