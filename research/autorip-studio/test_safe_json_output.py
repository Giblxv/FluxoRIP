import json
import os
from pathlib import Path
import tempfile
import unittest
from safe_json_output import write_new_json


class OutputSafetyTests(unittest.TestCase):
    def test_new_file_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'nested' / 'result.json'
            write_new_json(p, {'safe': True})
            self.assertEqual(json.loads(p.read_text()), {'safe': True})
            with self.assertRaises(FileExistsError):
                write_new_json(p, {'safe': False})
            self.assertEqual(json.loads(p.read_text()), {'safe': True})

    def test_hardlink_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            original = Path(d) / 'input.prt'
            original.write_bytes(b'PRT original synthetic bytes')
            alias = Path(d) / 'result.json'
            os.link(original, alias)
            with self.assertRaises(FileExistsError):
                write_new_json(alias, {'danger': 1})
            self.assertEqual(original.read_bytes(), b'PRT original synthetic bytes')

    def test_symlink_never_followed(self):
        with tempfile.TemporaryDirectory() as d:
            original = Path(d) / 'input.prt'
            original.write_bytes(b'original')
            alias = Path(d) / 'result.json'
            alias.symlink_to(original)
            with self.assertRaises((FileExistsError, OSError)):
                write_new_json(alias, {'danger': 1})
            self.assertEqual(original.read_bytes(), b'original')

    def test_existing_directory_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((FileExistsError, IsADirectoryError)):
                write_new_json(d, {'a': 1})

    def test_permissions_private_on_posix(self):
        if os.name != 'posix':
            self.skipTest('POSIX permission test')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'evidence.json'
            write_new_json(p, {'a': 1})
            self.assertEqual(p.stat().st_mode & 0o077, 0)


if __name__ == '__main__':
    unittest.main()
