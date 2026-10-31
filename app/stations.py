"""Telemetria administrativa das estações; nenhuma ação na impressora."""
import json
from datetime import datetime, timezone, timedelta
from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import Base, SessionLocal
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

router=APIRouter(prefix='/api/stations',tags=['Estacoes'])

class Station(Base):
    __tablename__='stations'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    hostname: Mapped[str]=mapped_column(String(120),nullable=False)
    os_name: Mapped[str]=mapped_column(String(70),nullable=False)
    last_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    interfaces_json: Mapped[str]=mapped_column(Text,default='[]',nullable=False)
    observations_json: Mapped[str]=mapped_column(Text,default='[]',nullable=False)

class Interface(BaseModel):
    id: int = Field(ge=0)
    name: str = Field(min_length=1,max_length=120)
    status: str = Field(max_length=30)
    ips: list[str] = Field(default_factory=list,max_length=16)
    hoson_subnet: bool = False

class DeviceObservation(BaseModel):
    ip: str = Field(max_length=45)
    mac: str | None = Field(default=None,max_length=40)
    interface_name: str = Field(max_length=120)
    interface_id: int | None = Field(default=None, ge=0)
    evidence: list[str] = Field(default_factory=list,max_length=4)

class Heartbeat(BaseModel):
    station_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{8,64}$')
    station_name: str = Field(min_length=1,max_length=120)
    hostname: str = Field(min_length=1,max_length=120)
    os_name: str = Field(min_length=1,max_length=70)
    interfaces: list[Interface] = Field(default_factory=list,max_length=32)
    observations: list[DeviceObservation] = Field(default_factory=list,max_length=256)


def db_session():
    with SessionLocal() as db:yield db

@router.post('/heartbeat')
def heartbeat(report: Heartbeat, db:Session=Depends(db_session)):
    item=db.get(Station,report.station_id)
    if item is None:
        item=Station(id=report.station_id)
        db.add(item)
    item.name=report.station_name
    item.hostname=report.hostname
    item.os_name=report.os_name
    item.last_seen=datetime.now(timezone.utc)
    item.interfaces_json=json.dumps([entry.model_dump() for entry in report.interfaces],ensure_ascii=False)
    # Only overwrite the previous explicit scan when the station reports new observations.
    if report.observations:
        item.observations_json=json.dumps([d.model_dump() for d in report.observations],ensure_ascii=False)
    db.commit()
    return {'received':True,'mode':'observe_only','printer_commands':False}

@router.get('')
def list_stations(db:Session=Depends(db_session)):
    cutoff=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(minutes=5)
    items=db.scalars(select(Station).order_by(Station.last_seen.desc())).all()
    result=[]
    for item in items:
        result.append({'id':item.id,'name':item.name,'hostname':item.hostname,'os_name':item.os_name,
            'last_seen':item.last_seen.isoformat(), 'online':item.last_seen.replace(tzinfo=None)>=cutoff,
            'interfaces':json.loads(item.interfaces_json or '[]'),
            'observations':json.loads(item.observations_json or '[]')})
    return {'stations':result,'refresh_seconds':120,
            'note':'Conectividade do agente; nao significa que a impressora esta online. Scanner local executa apenas na estacao.'}
