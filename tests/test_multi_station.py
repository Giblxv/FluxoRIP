import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db
from app.central_auth import create_credentials, get_credentials, verify_admin, verify_agent
from app.station_agent import read_config, build_heartbeat
from app.paths import DATA_ROOT


class MultiStationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_password_hash_and_rotation(self):
        with tempfile.TemporaryDirectory() as t, patch('app.central_auth.CREDENTIAL_FILE', Path(t)/'auth.json'):
            password = create_credentials()
            cfg = get_credentials()
            self.assertNotIn(password, json.dumps(cfg))
            basic='Basic '+base64.b64encode(f'forge:{password}'.encode()).decode()
            self.assertTrue(verify_admin(basic,cfg))
            self.assertFalse(verify_admin('Basic '+base64.b64encode(b'forge:wrong').decode(),cfg))
            self.assertTrue(verify_agent(cfg['agent_token'],cfg))
            with self.assertRaises(FileExistsError): create_credentials()
            second = create_credentials(force=True)
            changed = get_credentials()
            self.assertFalse(verify_agent(cfg['agent_token'],changed))
            self.assertNotEqual(password,second)

    def test_lan_denies_anonymous_and_agent_cannot_access_orders(self):
        with tempfile.TemporaryDirectory() as t, patch('app.central_auth.CREDENTIAL_FILE', Path(t)/'auth.json'):
            password=create_credentials()
            cfg=get_credentials()
            admin='Basic '+base64.b64encode(f'forge:{password}'.encode()).decode()
            with patch.dict(os.environ, {'FORGE_CENTRAL_MODE':'1'}):
                with TestClient(app) as c:
                    self.assertEqual(c.get('/').status_code,401)
                    self.assertEqual(c.get('/static/app.js').status_code,401)
                    self.assertIn('Basic',c.get('/').headers.get('www-authenticate',''))
                    self.assertEqual(c.get('/api/orders',headers={'X-FORGE-Agent-Key':cfg['agent_token']}).status_code,401)
                    self.assertEqual(c.get('/api/health',headers={'Authorization':admin}).status_code,200)
                    self.assertEqual(c.get('/',headers={'Authorization':admin}).status_code,200)
                    self.assertEqual(c.post('/api/stations/heartbeat',json={},headers={'X-FORGE-Agent-Key':'wrong'}).status_code,401)
                    report={'station_id':'st-12345678','station_name':'DTF 01','hostname':'pc-dtf01','os_name':'Windows 10',
                        'interfaces':[{'id':9,'name':'Ethernet Hoson','status':'Up','ips':['192.168.127.100'],'hoson_subnet':True}],
                        'observations':[{'ip':'192.168.127.10','mac':'00-11-22-33-44-55','interface_name':'Ethernet Hoson','evidence':['ARP']} ]}
                    ok=c.post('/api/stations/heartbeat',json=report,headers={'X-FORGE-Agent-Key':cfg['agent_token']})
                    self.assertEqual(ok.status_code,200,ok.text)
                    stations=c.get('/api/stations',headers={'Authorization':admin})
                    self.assertEqual(stations.status_code,200,stations.text)
                    self.assertEqual(stations.json()['stations'][0]['name'],'DTF 01')
                    self.assertEqual(stations.json()['stations'][0]['observations'][0]['ip'],'192.168.127.10')
                    self.assertEqual(c.post('/api/stations/heartbeat',json=report,headers={'X-FORGE-Agent-Key':cfg['agent_token'],'Origin':'http://evil.example'}).status_code,403)

    def test_agent_config_private_url_and_no_automatic_scans(self):
        with tempfile.TemporaryDirectory() as t, patch('app.station_agent.CONFIG_PATH',Path(t)/'estacao.json') as config_path:
            config_path.write_text(json.dumps({'central_url':'http://192.168.1.100:8765','agent_token':'x'*32,'station_name':'DTF 05'}))
            cfg=read_config()
            self.assertEqual(cfg['central_url'],'http://192.168.1.100:8765')
            self.assertFalse(cfg['scan_on_start'])
            with patch('app.station_agent.get_adapters',return_value=[{'id':2,'name':'Ethernet','status':'Up','ips':[{'ip':'192.168.127.100','prefix':24}],'is_hoson_subnet':True}]), \
                 patch('app.station_agent.scan_network') as scan, patch('app.station_agent.ID_PATH',Path(t)/'station_id.txt'):
                report=build_heartbeat('DTF 05')
                self.assertEqual(report['interfaces'][0]['ips'],['192.168.127.100'])
                scan.assert_not_called()
            config_path.write_text(json.dumps({'central_url':'https://8.8.8.8','agent_token':'x'*32}))
            with self.assertRaises(ValueError):read_config()

    def test_local_mode_backward_compat(self):
        with patch.dict(os.environ,{'FORGE_CENTRAL_MODE':'0'}):
            with TestClient(app) as c:
                self.assertEqual(c.get('/api/health').status_code,200)
                self.assertEqual(c.get('/api/stations').status_code,200)
                self.assertIn('Estações',c.get('/gestao').text)


if __name__=='__main__': unittest.main()
