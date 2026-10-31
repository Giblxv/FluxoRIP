from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Printer(Base):
    __tablename__ = 'printers'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    technology: Mapped[str] = mapped_column(String(20), nullable=False)
    controller: Mapped[str] = mapped_column(String(40), default='Hoson', nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    watch_folder: Mapped[str | None] = mapped_column(Text, nullable=True)
    workstation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    firmware: Mapped[str | None] = mapped_column(String(120), nullable=True)
    printexp_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(160), nullable=False)
    process: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default='RECEBIDO', nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default='NORMAL', nullable=False)
    printer_id: Mapped[str | None] = mapped_column(ForeignKey('printers.id'), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProductionEvent(Base):
    __tablename__ = 'production_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_code: Mapped[str | None] = mapped_column(ForeignKey('orders.code'), nullable=True)
    printer_id: Mapped[str | None] = mapped_column(ForeignKey('printers.id'), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ObservedFile(Base):
    __tablename__ = 'observed_files'
    __table_args__ = (UniqueConstraint('printer_id', 'filepath', 'mtime_ns', 'size_bytes'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    printer_id: Mapped[str] = mapped_column(ForeignKey('printers.id'), nullable=False)
    order_code: Mapped[str | None] = mapped_column(ForeignKey('orders.code'), nullable=True)
    filepath: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mtime_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PrintJob(Base):
    """Fila de planejamento MANUAL; não é a fila interna do PrintExp."""
    __tablename__ = 'print_jobs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_code: Mapped[str] = mapped_column(ForeignKey('orders.code'), nullable=False)
    printer_id: Mapped[str] = mapped_column(ForeignKey('printers.id'), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), default='AGUARDANDO', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
