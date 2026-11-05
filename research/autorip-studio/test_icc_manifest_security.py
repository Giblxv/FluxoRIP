"""Symlink security regression tests; tiny synthetic ICCs only."""
from pathlib import Path
import tempfile
import unittest

from icc_manifest import inventory
from test_icc_inspect import sample


class ManifestSecurityTests(unittest.TestCase):
    def _link(self, path, target, *, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'Symbolic links not supported: {exc}')

    def test_skips_outside_directory_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root, outside = base/'root', base/'outside'
            root.mkdir(); outside.mkdir()
            sample(root/'inside.icc'); sample(outside/'external.icm')
            self._link(root/'outside-link', outside, directory=True)
            result = inventory(root)
            self.assertEqual([x['path'] for x in result['entries']], ['inside.icc'])
            self.assertEqual(result['skipped_symlink_directories'], ['outside-link'])
            self.assertEqual(result['total'], 1)

    def test_skips_directory_link_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'child').mkdir()
            sample(root/'child'/'profile.icc')
            self._link(root/'child'/'loop', root, directory=True)
            result = inventory(root)
            self.assertEqual(result['total'], 1)
            self.assertIn('child/loop', result['skipped_symlink_directories'])

    def test_rejects_symlink_root(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); (base/'true').mkdir()
            self._link(base/'alias', base/'true', directory=True)
            with self.assertRaisesRegex(ValueError, 'symbolic-link root'):
                inventory(base/'alias')

    def test_file_symlink_to_external_is_not_read(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); root = base/'root'; root.mkdir()
            sample(base/'elsewhere.icc')
            self._link(root/'linked.icc', base/'elsewhere.icc')
            result = inventory(root)
            self.assertEqual(result['entries'][0]['status'], 'skipped_symlink')
            self.assertEqual(result['valid_headers'], 0)

    def test_validates_count_limit_before_processing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'a.icc').write_bytes(b'x'); (root/'b.icm').write_bytes(b'y')
            with self.assertRaisesRegex(ValueError, 'Profile count exceeds limit'):
                inventory(root, max_files=1)

    def test_rejects_bad_limit_values(self):
        with tempfile.TemporaryDirectory() as d:
            for invalid in (0, -1, 10_001, True, 2.5):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    inventory(d, max_files=invalid)

    def test_nested_deterministic_sort(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'z').mkdir(); (root/'a').mkdir()
            sample(root/'z'/'b.icc'); sample(root/'a'/'c.ICM'); sample(root/'a'/'B.icc')
            entries = inventory(root)['entries']
            self.assertEqual([e['path'] for e in entries], ['a/B.icc','a/c.ICM','z/b.icc'])


if __name__ == '__main__':
    unittest.main()
