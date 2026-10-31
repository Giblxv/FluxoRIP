"""Vínculos administrativos impressora ↔ estação ↔ interface Ethernet.

Nenhuma conexão com a controladora ou PrintExp. IP/MAC observados são
indícios de rede, nunca confirmação de identidade ou status da impressora.
"""
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from app.db import Base, SessionLocal
from app.models import Printer, ProductionEvent
from app.stations import Station

router = APIRouter(prefix='/api/printer-links', tags=['Mapa das impressoras'])


class PrinterStationLink(Base):
    __tablename__ = 'printer_station_links'
    printer_id: Mapped[str] = mapped_column(String(64), ForeignKey('printers.id'), primary_key=True)
    station_id: Mapped[str] = mapped_column(String(64), ForeignKey('stations.id'), nullable=False)
    interface_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class LinkRequest(BaseModel):
    station_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{8,64}$')
    interface_id: int = Field(ge=0)


def session():
    with SessionLocal() as db:
        yield db


def station_interfaces(station):
    try:
        return json.loads(station.interfaces_json or '[]')
    except (ValueError, TypeError):
        return []


def format_link(link, station, printer):
    interfaces = station_interfaces(station)
    interface = next((x for x in interfaces if x.get('id') == link.interface_id), None)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    station_online = station.last_seen.replace(tzinfo=None) >= cutoff
    observations = json.loads(station.observations_json or '[]')
    observed = [o for o in observations if interface and o.get('ip') == printer.ip and
                (o.get('interface_id') == link.interface_id or
                 (o.get('interface_id') is None and o.get('interface_name') == interface.get('name')))]
    state = ('ESTACAO_SEM_SINAL' if not station_online else
             'INTERFACE_NAO_ENCONTRADA' if not interface else 'VINCULO_CADASTRADO')
    return {
        'printer_id': printer.id, 'printer_name': printer.name,
        'printer_ip': printer.ip, 'technology': printer.technology,
        'station_id': station.id, 'station_name': station.name,
        'station_online': station_online, 'interface_id': link.interface_id,
        'interface_name': interface.get('name') if interface else None,
        'interface_status': interface.get('status') if interface else None,
        'interface_ips': interface.get('ips', []) if interface else [],
        'observed_ip_on_interface': bool(observed),
        'observed_mac': observed[0].get('mac') if observed else None,
        'status': state, 'linked_at': link.created_at.isoformat(),
        'note': 'Vínculo manual; não confirma que a placa Hoson está online.'
    }


@router.get('')
def list_links(db: Session = Depends(session)):
    links = db.scalars(select(PrinterStationLink).order_by(PrinterStationLink.printer_id)).all()
    result = []
    for link in links:
        printer = db.get(Printer, link.printer_id)
        station = db.get(Station, link.station_id)
        if printer and station:
            result.append(format_link(link, station, printer))
    used = {l['printer_id'] for l in result}
    unassigned = [{'id':p.id,'name':p.name,'ip':p.ip,'technology':p.technology}
                  for p in db.scalars(select(Printer).order_by(Printer.name)) if p.id not in used]
    return {'links': result, 'unassigned':unassigned, 'mode':'observe_only',
            'note':'A identificação é administrativa. Dispositivo detectado por IP não é automaticamente uma impressora.'}


@router.put('/{printer_id}')
def assign_link(printer_id: str, body: LinkRequest, db: Session = Depends(session)):
    printer = db.get(Printer, printer_id)
    station = db.get(Station, body.station_id)
    if printer is None:
        raise HTTPException(404, 'Impressora não cadastrada.')
    if station is None:
        raise HTTPException(404, 'Estação não encontrada. Inicie o agente primeiro.')
    interface = next((i for i in station_interfaces(station) if i.get('id') == body.interface_id), None)
    if interface is None:
        raise HTTPException(422, 'Porta Ethernet não identificada no relatório mais recente da estação.')
    # Duplicar o mesmo IP na MESMA interface é ambíguo e arriscado.
    # O mesmo IP em portas distintas pode ser normal em placas Hoson dedicadas.
    if printer.ip:
        try:
            ipaddress.IPv4Address(printer.ip)
        except ValueError as exc:
            raise HTTPException(422, 'IP cadastrado inválido. Corrija o cadastro antes do vínculo.') from exc
        for link in db.scalars(select(PrinterStationLink).where(
                PrinterStationLink.station_id == station.id,
                PrinterStationLink.interface_id == body.interface_id,
                PrinterStationLink.printer_id != printer.id)):
            other = db.get(Printer, link.printer_id)
            if other and other.ip == printer.ip:
                raise HTTPException(409,
                    f'IP {printer.ip} já atribuído a {other.name} nesta mesma porta. '
                    'Use a porta correta ou verifique o conflito na rede.')
    linked = db.get(PrinterStationLink, printer_id)
    if linked is None:
        linked = PrinterStationLink(printer_id=printer_id)
        db.add(linked)
    linked.station_id = station.id
    linked.interface_id = body.interface_id
    db.add(ProductionEvent(printer_id=printer.id, event_type='VINCULO_ESTACAO',
        message=f'Associação manual com estação {station.name}, Ethernet {interface.get("name")} (índice {body.interface_id}).'))
    db.commit()
    db.refresh(linked)
    return format_link(linked, station, printer)


@router.delete('/{printer_id}')
def remove_link(printer_id: str, db: Session = Depends(session)):
    linked = db.get(PrinterStationLink, printer_id)
    if linked is None:
        raise HTTPException(404, 'Impressora não está associada a uma estação.')
    db.delete(linked)
    db.add(ProductionEvent(printer_id=printer_id, event_type='VINCULO_REMOVIDO',
                           message='Associação de estação/porta removida manualmente.'))
    db.commit()
    return {'removed':True, 'printer_id':printer_id, 'mode':'observe_only'}
