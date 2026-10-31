"""Testes puros do mapeamento, sem scanner e sem conexão com impressoras."""
import json
import unittest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base
from app.models import Printer, ProductionEvent
from app.stations import Station
from app.printer_links import (PrinterStationLink, LinkRequest,
                               assign_link, remove_link, list_links)


class PrinterStationLinkTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://', poolclass=StaticPool,
                                  connect_args={'check_same_thread':False})
        Base.metadata.create_all(self.engine)
        self.db=Session(self.engine)
        self.db.add_all([
            Printer(id='DTF-1',name='DTF 1',technology='DTF',controller='Hoson',ip='192.168.127.10'),
            Printer(id='DTF-2',name='DTF 2',technology='DTF',controller='Hoson',ip='192.168.127.10'),
            Printer(id='DTF-3',name='DTF 3',technology='DTF',controller='Hoson',ip='192.168.127.20'),
            Station(id='st-testhost01',name='PC 1',hostname='PC-01',os_name='Windows 10',
                last_seen=datetime.now(timezone.utc),
                interfaces_json=json.dumps([
                    {'id':4,'name':'Ethernet A','status':'Up','ips':['192.168.127.100'],'hoson_subnet':True},
                    {'id':7,'name':'Ethernet B','status':'Up','ips':['192.168.127.101'],'hoson_subnet':True}]),
                observations_json=json.dumps([{'ip':'192.168.127.10','mac':'AA-BB-CC-DD-EE-FF',
                                               'interface_id':4,'interface_name':'Ethernet A','evidence':['ARP']}]))
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_duplicate_ips_allowed_on_distinct_ports(self):
        first=assign_link('DTF-1',LinkRequest(station_id='st-testhost01',interface_id=4),self.db)
        self.assertTrue(first['observed_ip_on_interface'])
        self.assertEqual(first['observed_mac'],'AA-BB-CC-DD-EE-FF')
        second=assign_link('DTF-2',LinkRequest(station_id='st-testhost01',interface_id=7),self.db)
        self.assertFalse(second['observed_ip_on_interface'])
        self.assertEqual(len(list_links(self.db)['links']),2)
        self.assertEqual(second['status'],'VINCULO_CADASTRADO')

    def test_same_ip_same_port_rejected(self):
        assign_link('DTF-1',LinkRequest(station_id='st-testhost01',interface_id=4),self.db)
        with self.assertRaises(HTTPException) as ctx:
            assign_link('DTF-2',LinkRequest(station_id='st-testhost01',interface_id=4),self.db)
        self.assertEqual(ctx.exception.status_code,409)
        self.assertEqual(len(list_links(self.db)['links']),1)

    def test_missing_interface_and_unknown_printer(self):
        with self.assertRaises(HTTPException) as ctx:
            assign_link('DTF-1',LinkRequest(station_id='st-testhost01',interface_id=99),self.db)
        self.assertEqual(ctx.exception.status_code,422)
        with self.assertRaises(HTTPException) as ctx:
            assign_link('NADA',LinkRequest(station_id='st-testhost01',interface_id=4),self.db)
        self.assertEqual(ctx.exception.status_code,404)

    def test_stale_agent_and_missing_interface_flagged(self):
        assign_link('DTF-1',LinkRequest(station_id='st-testhost01',interface_id=4),self.db)
        station=self.db.get(Station,'st-testhost01')
        station.last_seen=datetime.now(timezone.utc)-timedelta(hours=1)
        self.db.commit()
        self.assertEqual(list_links(self.db)['links'][0]['status'],'ESTACAO_SEM_SINAL')
        station.last_seen=datetime.now(timezone.utc)
        station.interfaces_json='[]'
        self.db.commit()
        self.assertEqual(list_links(self.db)['links'][0]['status'],'INTERFACE_NAO_ENCONTRADA')

    def test_delete_audited_and_no_machine_commands(self):
        assign_link('DTF-1',LinkRequest(station_id='st-testhost01',interface_id=4),self.db)
        response=remove_link('DTF-1',self.db)
        self.assertTrue(response['removed'])
        self.assertEqual(response['mode'],'observe_only')
        self.assertIsNone(self.db.get(PrinterStationLink,'DTF-1'))
        self.assertTrue(any(x.event_type=='VINCULO_REMOVIDO'
                            for x in self.db.scalars(select(ProductionEvent)).all()))

if __name__=='__main__':unittest.main()
