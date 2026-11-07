import io
import os
from pathlib import Path
import tempfile
import unittest
from PIL import Image

TEST_DIR = tempfile.TemporaryDirectory(prefix='forge-tests-')
os.environ['FORGE_DATA_DIR'] = TEST_DIR.name
os.environ['FORGE_NO_DIALOG'] = '1'

from fastapi.testclient import TestClient
from app.main import app
from app.paths import DATA_ROOT
from forge_launcher import migrate_if_needed


class ForgeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_01_health_and_static(self):
        health = self.client.get('/api/health')
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()['status'], 'ok')
        self.assertEqual(self.client.get('/api/system').json()['data_dir'], str(DATA_ROOT))
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Studio DTF', page.text)
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)

    def test_02_queues_and_order(self):
        printer = {'id': 'DTF-01', 'name': 'DTF de Teste', 'technology': 'DTF',
                   'controller': 'Hoson', 'enabled': True}
        self.assertEqual(self.client.post('/api/printers', json=printer).status_code, 201)
        order = {'code': 'PED-TEST-07', 'customer': 'Cliente Teste',
                 'process': 'DTF', 'printer_id': 'DTF-01'}
        self.assertEqual(self.client.post('/api/orders', json=order).status_code, 201)
        self.assertEqual(self.client.get('/api/orders').json()[0]['code'], 'PED-TEST-07')
        self.assertEqual(self.client.get('/api/printers/DTF-01/integration').json()['mode'], 'observe_only')
        self.assertEqual(self.client.get('/api/jobs').status_code, 200)

    def test_03_editor_upload_and_resize(self):
        picture = Image.new('RGBA', (32, 32), (255, 0, 0, 255))
        buffer = io.BytesIO()
        picture.save(buffer, format='PNG', dpi=(300, 300))
        response = self.client.post('/api/art/upload', files={'file': ('teste.png', buffer.getvalue(), 'image/png')})
        self.assertEqual(response.status_code, 201, response.text)
        original = response.json()
        self.assertEqual((original['width'], original['height']), (32, 32))
        edited = self.client.post(f"/api/art/{original['id']}/process", json={
            'action': 'resize', 'width': 64, 'keep_aspect': True})
        self.assertEqual(edited.status_code, 201, edited.text)
        self.assertEqual((edited.json()['width'], edited.json()['height']), (64, 64))
        self.assertEqual(self.client.get(f"/api/art/{original['id']}/original").status_code, 200)
        self.assertTrue((DATA_ROOT / 'art_storage' / original['root_id']).is_dir())

    def test_04_migration_copies_without_overwriting(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='forge-migrate-') as source_dir, \
             tempfile.TemporaryDirectory(prefix='forge-dest-') as target_dir:
            source = Path(source_dir)
            target = Path(target_dir)
            (source / 'production.db').write_bytes(b'database-example')
            (source / 'art_storage' / 'test').mkdir(parents=True)
            (source / 'art_storage' / 'test' / 'print.png').write_bytes(b'image-example')
            for folder in ('dtf_profiles', 'dtf_exports'):
                (source / folder).mkdir()
                (source / folder / 'exemplo').write_bytes(b'dtf-fixture')
            with patch('forge_launcher.DATA_ROOT', target):
                self.assertTrue(migrate_if_needed(source))
                self.assertFalse(migrate_if_needed(source))
            self.assertEqual((target / 'production.db').read_bytes(), b'database-example')
            self.assertEqual((target / 'art_storage/test/print.png').read_bytes(), b'image-example')
            self.assertTrue((source / 'production.db').exists())
            for folder in ('dtf_profiles', 'dtf_exports'):
                self.assertEqual((target / folder / 'exemplo').read_bytes(), b'dtf-fixture')
                self.assertEqual((source / folder / 'exemplo').read_bytes(), b'dtf-fixture')


    def test_05_print_console_profiles(self):
        capabilities = self.client.get('/api/print-console/capabilities')
        self.assertEqual(capabilities.status_code, 200)
        self.assertFalse(capabilities.json()['printer_commands_enabled'])
        self.assertEqual(capabilities.json()['integration_mode'], 'observe_only')
        defaults = self.client.get('/api/print-console/profiles/DTF-01').json()
        self.assertFalse(defaults['saved'])
        saved = self.client.put('/api/print-console/profiles/DTF-01', json={
            'print_mode': '4PASS_TESTE', 'passes': 4, 'dpi_x': 360, 'dpi_y': 720,
            'speed': 'MEDIUM', 'color_bar': 'LEFT', 'direction': 'BIDIRECTIONAL',
            'feather_mode': 'SUAVE', 'extra_notes': 'Referência local'} )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertFalse(saved.json()['applied_to_machine'])
        self.assertEqual(saved.json()['values']['passes'], 4)
        bad = self.client.put('/api/print-console/profiles/DTF-01', json={'passes': -2})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(self.client.get('/api/print-console/profiles/NAO_EXISTE').status_code, 404)

    def test_06_print_console_layout_and_records(self):
        job = self.client.post('/api/jobs', json={'order_code': 'PED-TEST-07', 'printer_id': 'DTF-01',
             'file_name': 'teste.prn', 'copies': 2})
        self.assertEqual(job.status_code, 201, job.text)
        job_id = job.json()['id']
        layout = self.client.put(f'/api/print-console/jobs/{job_id}/layout', json={
            'columns': 2, 'rows': 3, 'spacing_x_mm': 5.5, 'spacing_y_mm': 6,
            'origin_x_mm': 15, 'origin_y_mm': 4, 'region_width_mm': 100, 'region_height_mm': 60})
        self.assertEqual(layout.status_code, 200, layout.text)
        self.assertFalse(layout.json()['applied_to_machine'])
        self.assertEqual(self.client.get(f'/api/print-console/jobs/{job_id}/layout').json()['values']['columns'], 2)
        self.assertEqual(self.client.put(f'/api/print-console/jobs/{job_id}/layout', json={'region_width_mm': 20}).status_code, 422)
        record = self.client.post('/api/print-console/records', json={
            'printer_id':'DTF-01','category':'CALIBRACAO','procedure':'TESTE_BICOS',
            'outcome':'REALIZADO','operator':'Operador Teste','notes':'Sem falhas'})
        self.assertEqual(record.status_code, 201, record.text)
        self.assertEqual(self.client.get('/api/print-console/records?printer_id=DTF-01').json()[0]['procedure'], 'TESTE_BICOS')
        self.assertEqual(self.client.post('/api/print-console/records', json={
            'printer_id':'DTF-01','category':'CALIBRACAO','procedure':'FACTORY_RESET',
            'outcome':'REALIZADO','operator':'Operador Teste'}).status_code, 422)
        self.assertEqual(self.client.patch(f'/api/jobs/{job_id}/status', json={'status':'IMPRIMINDO'}).status_code, 200)
        self.assertEqual(self.client.put(f'/api/print-console/jobs/{job_id}/layout', json={'columns': 4}).status_code, 409)

    def test_08_motion_bundle_and_user_preference(self):
        page = self.client.get('/').text
        self.assertIn('motion.css?v=10', page)
        self.assertIn('motion.js?v=10', page)
        self.assertIn('id="motion-toggle"', page)
        css = self.client.get('/static/motion.css')
        js = self.client.get('/static/motion.js')
        self.assertEqual(css.status_code, 200)
        self.assertEqual(js.status_code, 200)
        self.assertIn('prefers-reduced-motion', css.text)
        self.assertIn('motion-off', css.text)
        self.assertIn('forgeMotionOnRender', js.text)

    def test_07_console_assets_and_compatibility(self):
        page = self.client.get('/gestao').text
        self.assertIn('data-page="prints"', page)
        self.assertIn('prints.js', page)
        self.assertEqual(self.client.get('/static/prints.js').status_code, 200)
        self.assertEqual(self.client.get('/api/health').json()['version'], '2.0.0')
        self.assertEqual(self.client.get('/api/printers/DTF-01/integration').json()['mode'], 'observe_only')


if __name__ == '__main__':
    unittest.main()
