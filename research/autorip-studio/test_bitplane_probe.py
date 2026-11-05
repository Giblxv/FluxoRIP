"""Only small, synthetic binary fixtures. No production files created."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from bitplane_probe import analyze_symbol_transitions


def sample(path, payload, *, lines=1, stride=4, bands=12, signature=0x5555):
    header = bytearray(48)
    struct.pack_into('<H', header, 0, signature)
    for off, value in ((12, lines), (16, stride), (28, bands)):
        struct.pack_into('<I', header, off, value)
    path.write_bytes(header + payload)


class TwoBitResearchTests(unittest.TestCase):
    def make(self, directory, x, y, z, **kwargs):
        paths = [directory / name for name in ('zero.dat', 'half.dat', 'full.dat')]
        for p, v in zip(paths, (x, y, z)):
            sample(p, v + bytes(47), **kwargs)
        return dict(zip(('white_0', 'white_50', 'white_100'), paths))

    def test_four_lanes_0_1_3(self):
        with tempfile.TemporaryDirectory() as folder:
            d = self.make(Path(folder), bytes([0]), bytes([0x55]), bytes([0xff]))
            before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in d.values()]
            result = analyze_symbol_transitions(d, chunk_bytes=7)
            self.assertEqual(result['changed_bytes_0_vs_100'], 1)
            self.assertEqual(result['changed_2bit_symbols_0_vs_100'], 4)
            self.assertEqual(result['strict_ascending_changed_2bit_symbols'], 4)
            self.assertEqual(result['most_common_symbol_patterns'][0]['symbols_0_50_100'], [0, 1, 3])
            self.assertEqual(result['most_common_symbol_patterns'][0]['count'], 4)
            self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in d.values()], before)

    def test_byte_monotonic_but_symbol_nonmonotonic(self):
        with tempfile.TemporaryDirectory() as folder:
            d = self.make(Path(folder), bytes([3]), bytes([4]), bytes([7]))
            result = analyze_symbol_transitions(d, chunk_bytes=10)
            self.assertEqual(result['strictly_ascending_full_byte_triplets_among_changed_bytes'], 1)
            self.assertEqual(result['strict_ascending_changed_2bit_symbols'], 0)
            self.assertEqual(result['changed_2bit_symbols_0_vs_100'], 1)

    def test_stable_samples_are_not_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            d = self.make(Path(folder), bytes([3]), bytes([3]), bytes([3]))
            result = analyze_symbol_transitions(d)
            self.assertEqual(result['changed_bytes_0_vs_100'], 0)
            self.assertEqual(result['most_common_symbol_patterns'], [])

    def test_reject_bad_signature(self):
        with tempfile.TemporaryDirectory() as folder:
            d = self.make(Path(folder), b'\x00', b'\x55', b'\xff')
            sample(d['white_50'], bytes([0x55]) + bytes(47), signature=0xaaaa)
            with self.assertRaisesRegex(ValueError, 'signature'):
                analyze_symbol_transitions(d)

    def test_reject_repeated_source(self):
        with tempfile.TemporaryDirectory() as folder:
            d = self.make(Path(folder), b'\x00', b'\x55', b'\xff')
            d['white_100'] = d['white_50']
            with self.assertRaisesRegex(ValueError, 'Distinct'):
                analyze_symbol_transitions(d)

    def test_reject_truncation(self):
        with tempfile.TemporaryDirectory() as folder:
            d = self.make(Path(folder), b'\x00', b'\x55', b'\xff')
            p = d['white_0']
            p.write_bytes(p.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, 'geometry'):
                analyze_symbol_transitions(d)

    def test_reject_invalid_chunk(self):
        with tempfile.TemporaryDirectory() as folder:
            d = self.make(Path(folder), b'\x00', b'\x55', b'\xff')
            with self.assertRaisesRegex(ValueError, 'Chunk'):
                analyze_symbol_transitions(d, chunk_bytes=0)


if __name__ == '__main__':
    unittest.main()
