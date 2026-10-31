import ipaddress
import re
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal

Technology = Literal['DTF', 'DTF_UV']
Priority = Literal['BAIXA', 'NORMAL', 'ALTA', 'URGENTE']
Status = Literal['RECEBIDO', 'ARTE', 'APROVADO', 'AGUARDANDO_RIP',
                 'PROCESSADO_RIP', 'AGUARDANDO_IMPRESSAO', 'IMPRIMINDO',
                 'IMPRESSAO_CONCLUIDA', 'ACABAMENTO', 'CONCLUIDO', 'BLOQUEADO']


class PrinterCreate(BaseModel):
    id: str = Field(min_length=2, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=2, max_length=120)
    technology: Technology
    controller: Literal['Hoson'] = 'Hoson'
    ip: str | None = None
    watch_folder: str | None = Field(default=None, max_length=800)
    workstation: str | None = Field(default=None, max_length=120)
    firmware: str | None = Field(default=None, max_length=120)
    printexp_version: str | None = Field(default=None, max_length=120)
    enabled: bool = False

    @field_validator('ip')
    @classmethod
    def validate_ip(cls, value):
        if not value or not value.strip():
            return None
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ValueError('Endereço IP inválido.') from exc


class PrinterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    ip: str | None = None
    watch_folder: str | None = Field(default=None, max_length=800)
    workstation: str | None = Field(default=None, max_length=120)
    firmware: str | None = Field(default=None, max_length=120)
    printexp_version: str | None = Field(default=None, max_length=120)
    enabled: bool | None = None

    @field_validator('ip')
    @classmethod
    def validate_ip(cls, value):
        if not value or not value.strip():
            return None
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ValueError('Endereço IP inválido.') from exc


class OrderCreate(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    customer: str = Field(min_length=2, max_length=160)
    process: Technology
    priority: Priority = 'NORMAL'
    printer_id: str | None = None
    due_date: str | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator('due_date')
    @classmethod
    def validate_date(cls, value):
        if value and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('Use AAAA-MM-DD.')
        return value


class StatusUpdate(BaseModel):
    status: Status


class AssignmentUpdate(BaseModel):
    printer_id: str | None = None


class PrintJobCreate(BaseModel):
    order_code: str = Field(min_length=3, max_length=40)
    printer_id: str = Field(min_length=2, max_length=64)
    file_name: str | None = Field(default=None, max_length=255)
    copies: int = Field(default=1, ge=1, le=9999)
    notes: str | None = Field(default=None, max_length=2000)


class PrintJobStatus(BaseModel):
    status: Literal['AGUARDANDO','IMPRIMINDO','CONCLUIDO','ERRO','CANCELADO']


class PrintJobMove(BaseModel):
    direction: Literal['up', 'down', 'top', 'bottom']
