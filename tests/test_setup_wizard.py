"""First-run setup configuration, no Windows UI required in tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.startup_profile import validate_profile, load_profile

class SetupWizardTests(unittest.TestCase):
    def test_valid_profiles(self):
        self.assertEqual(validate_profile({'modo':'local'}), {'modo':'local'})
        self.assertEqual(validate_profile({'modo':'estacao'}), {'modo':'estacao'})
        self.assertEqual(validate_profile({'modo':'central','ip':'192.168.1.100','porta':8765}),
                         {'modo':'central','ip':'192.168.1.100','porta':8765})

    def test_cannot_select_printer_network_as_central(self):
        for ip in ['192.168.127.100','192.168.127.10','127.0.0.1','8.8.8.8','169.254.1.10']:
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                validate_profile({'modo':'central','ip':ip,'porta':8765})

    def test_broken_and_untrusted_settings(self):
        for profile in [{}, {'modo':'outro'}, {'modo':'central','ip':'192.168.1.1','porta':12},
                        {'modo':'central','ip':'not-ip','porta':8765}, None]:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                validate_profile(profile)

    def test_load_profile_does_not_store_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'modo_inicial.json'
            self.assertIsNone(load_profile(path))
            path.write_text(json.dumps({'modo':'estacao','agent_token':'SHOULD_NOT_LEAK'}))
            self.assertEqual(load_profile(path), {'modo':'estacao'})

    def test_wizard_bundled_in_spec(self):
        root=Path(__file__).resolve().parents[1]
        spec=(root/'FORGE.spec').read_text(encoding='utf-8')
        self.assertIn("'ASSISTENTE_FORGE.ps1'",spec)
        self.assertTrue((root/'setup'/'ASSISTENTE_FORGE.ps1').exists())
        self.assertIn('open_first_run_wizard', (root/'forge_launcher.py').read_text(encoding='utf-8'))

if __name__=='__main__': unittest.main()
