"""Small synthetic test fixtures; no printer-ready PRTs are generated."""
from pathlib import Path
from hashlib import sha256
import struct
import tempfile
import unittest

from mask_periodicity import inspect_periodicity


def fixture(path, *, lines=2, stride=4, bands=12, changed=(), value=1,
            header_change=False):
    head = bytearray(48)
    struct.pack_into('<H', head, 0, 0x5555)
    struct.pack_into('<I', head, 12, lines)
    struct.pack_into('<I', head, 16, stride)
    struct.pack_into('<I', head, 28, bands)
    if header_change:
        head[33] = 1
    body = bytearray(lines * stride * bands)
    for slot, i in changed:
        body[slot * lines * stride + i] = value
    path.write_bytes(head + body)


class MaskPeriodicityTests(unittest.TestCase):
    def case(self, directory, *, repeated=False):
        paths = {label: str(Path(directory) / (label + '.bin'))
                 for label in ('white_0', 'white_50', 'white_100')}
        entries = []
        for i in range(1, 11):
            index = (i-1) % 3
            entries.append((i, index))
        # Same byte-mask positions, different changed values for 50 and 100.
        fixture(Path(paths['white_0']))
        fixture(Path(paths['white_50']), changed=entries, value=1)
        fixture(Path(paths['white_100']), changed=entries, value=3)
        return paths

    def test_repeats_every_three_in_interior(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            result = inspect_periodicity(paths, chunk_bytes=3)
            for pair in ('0_vs_50', '50_vs_100', '0_vs_100'):
                self.assertTrue(result['pair_results'][pair][
                    'interior_planes_1_to_10_repeat_with_period_3'])
            self.assertEqual(result['pair_results']['0_vs_100'][
                'different_bytes_by_candidate_plane'], [0] + [1]*10 + [0])
            self.assertEqual(result['pair_results']['0_vs_100'][
                'total_different_bytes'], 10)

    def test_hash_and_immutability(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            originals = {name: Path(p).read_bytes() for name,p in paths.items()}
            result = inspect_periodicity(paths, chunk_bytes=13)
            self.assertEqual(result['source_sha256'],
                             {name: sha256(raw).hexdigest() for name,raw in originals.items()})
            self.assertEqual({name: Path(p).read_bytes() for name,p in paths.items()}, originals)

    def test_nonrepeat_interior_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            # Make a distinct changed-position mask in plane 4, unrelated to the period-3 slot 1.
            fixture(Path(paths['white_100']), changed=[(4,7)], value=3)
            result = inspect_periodicity(paths, chunk_bytes=3)
            self.assertFalse(result['pair_results']['0_vs_100'][
                'interior_planes_1_to_10_repeat_with_period_3'])

    def test_byte_chunk_independence(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            low = inspect_periodicity(paths, chunk_bytes=1)
            high = inspect_periodicity(paths, chunk_bytes=64)
            self.assertEqual(low, high)

    def test_middle_setting_can_break_only_50_vs_100_periodicity(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            f = Path(paths['white_50'])
            raw = bytearray(f.read_bytes())
            # Plane 5 has exactly the same changed position in 50 and 100,
            # so its 50-vs-100 mask loses one changed byte.
            raw[48 + 5 * 2 * 4 + (5 - 1) % 3] = 3
            f.write_bytes(raw)
            r = inspect_periodicity(paths, chunk_bytes=5)
            self.assertTrue(r['pair_results']['0_vs_50'][
                'interior_planes_1_to_10_repeat_with_period_3'])
            self.assertTrue(r['pair_results']['0_vs_100'][
                'interior_planes_1_to_10_repeat_with_period_3'])
            self.assertFalse(r['pair_results']['50_vs_100'][
                'interior_planes_1_to_10_repeat_with_period_3'])

    def test_mismatched_headers_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            fixture(Path(paths['white_100']), header_change=True)
            with self.assertRaisesRegex(ValueError,'headers'):
                inspect_periodicity(paths)

    def test_invalid_geometry_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            fixture(Path(paths['white_100']), bands=13)
            with self.assertRaises(ValueError):
                inspect_periodicity(paths)

    def test_alias_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            paths['white_50'] = paths['white_0']
            with self.assertRaisesRegex(ValueError,'different file paths'):
                inspect_periodicity(paths)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            link = Path(directory)/'link.bin'
            try:
                link.symlink_to(Path(paths['white_0']))
            except (OSError, NotImplementedError):
                self.skipTest('Symlink unavailable on current filesystem')
            paths['white_0'] = str(link)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                inspect_periodicity(paths)

    def test_bound_chunk_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            with self.assertRaisesRegex(ValueError,'chunk_bytes'):
                inspect_periodicity(paths, chunk_bytes=0)

    def test_no_false_period_from_one_plane_only(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.case(directory)
            fixture(Path(paths['white_100']), changed=[(1,1)], value=7)
            result = inspect_periodicity(paths, chunk_bytes=2)
            self.assertFalse(result['pair_results']['0_vs_100'][
                'interior_planes_1_to_10_repeat_with_period_3'])


if __name__ == '__main__':
    unittest.main()
