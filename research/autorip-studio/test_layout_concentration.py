"""Small synthetic fixtures only. Never produces printer-ready PRT files."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from layout_concentration import analyze_concentration


def fixture(path, change=(), *, lines=3, stride=4, bands=12, header_change=False):
    header = bytearray(48)
    struct.pack_into('<H', header, 0, 0x5555)
    for k, value in ((12, lines), (16, stride), (28, bands)):
        struct.pack_into('<I', header, k, value)
    if header_change:
        header[35] = 2
    payload = bytearray(lines * stride * bands)
    for k in change:
        payload[k] = 3
    path.write_bytes(header + payload)


class ConcentrationTests(unittest.TestCase):
    def setup_triplet(self, folder, *, changes=()):
        paths = {key: str(Path(folder) / (key + '.fixture'))
                 for key in ('white_0', 'white_50', 'white_100')}
        fixture(Path(paths['white_0']))
        fixture(Path(paths['white_50']))
        fixture(Path(paths['white_100']), changes)
        return paths

    def test_hypotheses_locate_expected_slots(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.setup_triplet(d, changes=[2*4+1, 12*4+2])
            result = analyze_concentration(p, chunk_bytes=7)
            data = result['candidate_layout_counts']['0_vs_100']
            self.assertEqual(data['row_major']['count_by_candidate_band'][2], 1)
            self.assertEqual(data['row_major']['count_by_candidate_band'][0], 1)
            self.assertEqual(data['plane_major']['count_by_candidate_band'][0], 1)
            self.assertEqual(data['plane_major']['count_by_candidate_band'][4], 1)
            self.assertEqual(sum(data['byte_interleaved']['count_by_candidate_band']), 2)
            self.assertEqual(data['byte_interleaved']['count_by_candidate_band'][9], 1)
            self.assertEqual(data['byte_interleaved']['count_by_candidate_band'][2], 1)

    def test_hash_integrity_without_modification(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.setup_triplet(d, changes=[0, 2, 4])
            content = [Path(x).read_bytes() for x in p.values()]
            r = analyze_concentration(p, chunk_bytes=5)
            for name, raw in zip(p, content):
                self.assertEqual(r['source_sha256'][name], hashlib.sha256(raw).hexdigest())
            self.assertEqual([Path(x).read_bytes() for x in p.values()], content)

    def test_pairwise_totals(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.setup_triplet(d, changes=[0, 1, 2, 3])
            r = analyze_concentration(p, chunk_bytes=13)
            counts = r['candidate_layout_counts']
            self.assertEqual(counts['0_vs_50']['row_major']['total'], 0)
            self.assertEqual(counts['50_vs_100']['row_major']['total'], 4)
            self.assertEqual(counts['0_vs_100']['plane_major']['total'], 4)

    def test_nonmatching_geometry_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.setup_triplet(d)
            fixture(Path(p['white_100']), lines=4)
            with self.assertRaisesRegex(ValueError, 'Incompatible candidate geometries'):
                analyze_concentration(p)

    def test_changed_header_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.setup_triplet(d)
            fixture(Path(p['white_100']), header_change=True)
            with self.assertRaisesRegex(ValueError, 'Headers are not identical'):
                analyze_concentration(p)

    def test_too_many_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.setup_triplet(d)
            with self.assertRaisesRegex(ValueError, 'Chunk size'):
                analyze_concentration(p, chunk_bytes=17*1024*1024)

    def test_source_alias_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.setup_triplet(d)
            p['white_50'] = p['white_0']
            with self.assertRaisesRegex(ValueError, 'distinct'):
                analyze_concentration(p)


if __name__ == '__main__':
    unittest.main()
