import os
import tempfile
import unittest
from unittest.mock import patch

TEST_HOME = tempfile.TemporaryDirectory(prefix='forge-scanner-')
os.environ.setdefault('FORGE_DATA_DIR', TEST_HOME.name)
from fastapi.testclient import TestClient
from app.main import app
from app.network_scanner import ScanRequest, scan_network

ADAPTERS = [
    {'id': 12, 'name': 'Ethernet Hoson', 'description': 'Realtek PCIe GBE',
     'status': 'Up', 'mac': '00-11-22-33-44-55', 'link_speed': '1 Gbps',
     'is_hoson_subnet': True, 'ips': [{'ip':'192.168.127.100','prefix':24}]},
    {'id': 13, 'name': 'Ethernet desconectada', 'status': 'Disconnected',
     'mac': '44-55-66-77-88-99', 'link_speed': '0 bps',
     'is_hoson_subnet': False, 'ips': []},
]

class ScannerTests(unittest.TestCase):
    def test_rejects_absent_adapter_and_wrong_subnet(self):
        with self.assertRaisesRegex(ValueError, 'não encontrado'):
            scan_network(ScanRequest(interface_index=777), ADAPTERS)
        with self.assertRaisesRegex(ValueError, 'desconectada'):
            scan_network(ScanRequest(interface_index=13), ADAPTERS)
        with self.assertRaisesRegex(ValueError, 'não possui um IP'):
            scan_network(ScanRequest(interface_index=12,network='192.168.126.0/24'), ADAPTERS)
        with self.assertRaisesRegex(ValueError, 'IPv4 /24'):
            scan_network(ScanRequest(interface_index=12,network='192.168.0.0/16'), ADAPTERS)

    def test_discovers_devices_but_not_as_verified_hoson(self):
        def fake_ping(ip, source):
            self.assertEqual(source, '192.168.127.100')
            return ip == '192.168.127.10'
        neighbors = {
            '192.168.127.10': {'mac':'A0-B1-C2-33-44-55','state':'Reachable'},
            '192.168.127.44': {'mac':'AA-BB-CC-00-11-22','state':'Reachable'},
            '192.168.127.60': {'mac':'00-00-00-00-00-00','state':'Stale'},
        }
        with patch('app.network_scanner.ping_target',side_effect=fake_ping),patch('app.network_scanner.get_neighbors',return_value=neighbors):
            result = scan_network(ScanRequest(interface_index=12), ADAPTERS)
        self.assertEqual(result['scanned'], 253)
        self.assertEqual(result['found'], 2)
        self.assertEqual([d['ip'] for d in result['devices']], ['192.168.127.10','192.168.127.44'])
        self.assertEqual(result['devices'][0]['device_type'],'não identificado')
        self.assertFalse(result['commands_sent_to_printer'])
        self.assertFalse(result['network_configuration_changed'])

    def test_scan_all_connected_hoson_ports(self):
        with TestClient(app) as c:
            with patch('app.network_scanner.get_adapters',return_value=ADAPTERS),patch('app.network_scanner.sys.platform','win32'),patch('app.network_scanner.ping_target',side_effect=lambda ip,source: ip=='192.168.127.10'),patch('app.network_scanner.get_neighbors',return_value={}):
                response=c.post('/api/network/scan-all')
                self.assertEqual(response.status_code,200,response.text)
                result=response.json()
                self.assertEqual(result['interfaces_scanned'],1)
                self.assertEqual(result['found'],1)
                self.assertEqual(result['devices'][0]['interface_id'],12)
                self.assertEqual(result['devices'][0]['interface_name'],'Ethernet Hoson')

    def test_api_and_static(self):
        with TestClient(app) as c:
            self.assertEqual(c.get('/static/network_scanner.js').status_code,200)
            self.assertEqual(c.get('/static/network_scanner.css').status_code,200)
            self.assertIn('Scanner de rede',c.get('/gestao').text)
            with patch('app.network_scanner.get_adapters',return_value=ADAPTERS),patch('app.network_scanner.sys.platform','win32'):
                r=c.get('/api/network/interfaces')
                self.assertEqual(r.status_code,200)
                self.assertEqual(len(r.json()['adapters']),2)
                bad=c.post('/api/network/scan',json={'interface_index':12,'network':'10.0.0.0/24'})
                self.assertEqual(bad.status_code,422)
                with patch('app.network_scanner.ping_target',return_value=False),patch('app.network_scanner.get_neighbors',return_value={}):
                    valid=c.post('/api/network/scan',json={'interface_index':12,'network':'192.168.127.0/24'})
                    self.assertEqual(valid.status_code,200,valid.text)
                    self.assertEqual(valid.json()['found'],0)

if __name__ == '__main__':
    unittest.main()
