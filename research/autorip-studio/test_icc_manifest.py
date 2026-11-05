from pathlib import Path
import tempfile
import unittest
from icc_manifest import inventory
from test_icc_inspect import sample


class ManifestTests(unittest.TestCase):
    def test_duplicate_profiles_and_sorted_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sample(root/'z.icc'); (root/'a.icm').write_bytes((root/'z.icc').read_bytes())
            result=inventory(root)
            self.assertEqual([e['path'] for e in result['entries']], ['a.icm','z.icc'])
            self.assertEqual(result['valid_headers'],2)
            self.assertEqual(len(result['duplicate_sha256']),1)
    def test_invalid_profile_is_reported_without_abort(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'bad.icc').write_bytes(b'broken'); sample(root/'ok.icm')
            result=inventory(root)
            self.assertEqual(result['valid_headers'],1)
            self.assertEqual(result['entries'][0]['status'],'invalid')
    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sample(root/'a.icc')
            try: (root/'link.icc').symlink_to(root/'a.icc')
            except (OSError, NotImplementedError): self.skipTest('symlinks unavailable')
            result=inventory(root)
            self.assertEqual(result['entries'][1]['status'],'skipped_symlink')
    def test_count_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sample(root/'a.icc'); sample(root/'b.icc')
            with self.assertRaises(ValueError): inventory(root,max_files=1)
    def test_missing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): inventory(Path(d)/'missing')

if __name__=='__main__': unittest.main()
