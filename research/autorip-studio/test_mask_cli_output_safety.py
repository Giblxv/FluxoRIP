"""CLI-level protection tests using synthetic PRT-shaped fixtures only."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def synthetic_prt(path, changed=False):
    header = bytearray(48)
    struct.pack_into('<H', header, 0, 0x5555)
    struct.pack_into('<I', header, 12, 2)
    struct.pack_into('<I', header, 16, 4)
    struct.pack_into('<I', header, 28, 12)
    payload = bytearray(96)
    if changed:
        payload[4] = 3
    path.write_bytes(header + payload)


class MaskCLIOutputSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = [root / ('input%d.prt' % i) for i in range(3)]
        for i, path in enumerate(self.paths):
            synthetic_prt(path, i == 2)
        self.original = [p.read_bytes() for p in self.paths]

    def run_cli(self, output):
        args = [sys.executable, str(HERE / 'mask_periodicity.py'),
                '--white-0', str(self.paths[0]), '--white-50', str(self.paths[1]),
                '--white-100', str(self.paths[2]), '--output', str(output)]
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        self.assertEqual([p.read_bytes() for p in self.paths], self.original)
        return result

    def test_new_output_created_and_rejected_on_second_run(self):
        output = Path(self.temp.name) / 'result.json'
        self.assertEqual(self.run_cli(output).returncode, 0)
        before = output.read_bytes()
        self.assertEqual(json.loads(before)['pair_results']['0_vs_100']['total_different_bytes'], 1)
        self.assertNotEqual(self.run_cli(output).returncode, 0)
        self.assertEqual(output.read_bytes(), before)

    def test_hardlink_output_rejected(self):
        output = Path(self.temp.name) / 'alias.json'
        os.link(self.paths[0], output)
        self.assertNotEqual(self.run_cli(output).returncode, 0)

    def test_symlink_output_rejected(self):
        output = Path(self.temp.name) / 'alias.json'
        try:
            output.symlink_to(self.paths[0])
        except (OSError, NotImplementedError):
            self.skipTest('Symlink not available')
        self.assertNotEqual(self.run_cli(output).returncode, 0)

    def test_existing_unrelated_file_preserved(self):
        output = Path(self.temp.name) / 'report.json'
        output.write_text('existing result')
        self.assertNotEqual(self.run_cli(output).returncode, 0)
        self.assertEqual(output.read_text(), 'existing result')


if __name__ == '__main__':
    unittest.main()
