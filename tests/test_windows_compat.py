"""Mocks verify OS branching without requiring live Windows 10/11 VMs."""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch, MagicMock

os.environ.setdefault('FORGE_DATA_DIR', tempfile.mkdtemp(prefix='forge-wincompat-'))

from app import windows_compat
import forge_launcher


class WindowsCompatibilityTests(TestCase):
    def test_recognizes_windows_10_client(self):
        ver = SimpleNamespace(major=10, minor=0, build=19045, product_type=1)
        with patch.object(windows_compat.sys, 'platform', 'win32'), \
             patch.object(windows_compat.sys, 'getwindowsversion', return_value=ver, create=True):
            d = windows_compat.windows_details()
        self.assertEqual(d['name'], 'Windows 10')
        self.assertTrue(d['supported'])
        self.assertEqual(d['build'], 19045)

    def test_recognizes_windows_11_client_and_server(self):
        for build, typ, expected in ((22631, 1, 'Windows 11'),
                                     (26100, 1, 'Windows 11'),
                                     (20348, 3, 'Windows Server')):
            ver = SimpleNamespace(major=10, minor=0, build=build, product_type=typ)
            with patch.object(windows_compat.sys, 'platform', 'win32'):
                with patch.object(windows_compat.sys, 'getwindowsversion', return_value=ver, create=True):
                    self.assertEqual(windows_compat.windows_details()['name'], expected)

    def test_webview2_missing_falls_back_to_browser(self):
        with patch('forge_launcher.webview2_runtime', return_value={'detected': False}), \
             patch('forge_launcher.show_in_browser') as browser:
            forge_launcher.open_desktop('http://127.0.0.1:8123/')
            browser.assert_called_once()

    def test_webview2_failure_falls_back_to_browser(self):
        webview = MagicMock()
        webview.start.side_effect = RuntimeError('Edge Runtime não inicializou')
        with patch('forge_launcher.webview2_runtime', return_value={'detected': True}), \
             patch.dict(sys.modules, {'webview': webview}), \
             patch('forge_launcher.show_in_browser') as browser:
            forge_launcher.open_desktop('http://127.0.0.1:8123/')
            webview.start.assert_called_once_with(gui='edgechromium')
            browser.assert_called_once()

    def test_scan_error_includes_both_windows_versions(self):
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            response = c.post('/api/network/scan', json={'interface_index': 1, 'network': '192.168.127.0/24'})
            if sys.platform != 'win32':
                self.assertEqual(response.status_code, 501)
                self.assertIn('Windows 10 ou 11', response.json()['detail'])
            response = c.get('/api/system')
            self.assertEqual(response.status_code, 200)
            self.assertIn('os', response.json())
            self.assertIn('webview2', response.json())
