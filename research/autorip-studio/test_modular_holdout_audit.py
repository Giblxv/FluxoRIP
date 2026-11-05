"""Synthetic-only regression checks for modular holdout measurements."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest

from modular_holdout_audit import analyze, _best_window, _at_phase, _optimal_phase_count
from verify_sample_hashes import LABELS


class ModularHoldoutTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.lines = 4
        self.stride = 24
        self.bands = 12
        self.period = self.lines * self.bands
        self.phase = 46  # deliberately wraps across the modular end
        self.paths = {}
        self.reference = {}
        self.contents = []
        for value in (0, 85, 255):
            header = bytearray(48)
            struct.pack_into('<H', header, 0, 0x5555)
            struct.pack_into('<I', header, 12, self.lines)
            struct.pack_into('<I', header, 16, self.stride)
            struct.pack_into('<I', header, 28, self.bands)
            body = bytearray(self.period * self.stride)
            if value:
                for cycle in range(self.stride):
                    for i in range(self.lines):
                        body[cycle * self.period + (self.phase + i) % self.period] = value
            self.contents.append(bytes(header + body))
        self.reset()

    def reset(self):
        self.paths = {}
        self.reference = {}
        for label, filename, data in zip(LABELS, ('TESTER1.PRT', 'TESTER1_1.PRT', 'TESTER1_0.PRT'), self.contents):
            path = self.root / filename
            path.write_bytes(data)
            self.paths[label] = path
            self.reference[label] = {'filename': filename,
                                     'size': len(data),
                                     'sha256': hashlib.sha256(data).hexdigest()}

    def run_analysis(self, chunk=73):
        return analyze(self.paths, reference=self.reference, chunk_bytes=chunk)

    def test_wraparound_and_holdout_concentration(self):
        result = self.run_analysis()
        self.assertEqual(result['candidate_period_bytes'], 48)
        self.assertEqual(result['candidate_window_bytes'], 4)
        self.assertEqual(result['training_window_phase'], self.phase)
        for pair in ('0_vs_50', '50_vs_100', '0_vs_100'):
            for half in result['pairwise'][pair]:
                self.assertEqual(half['changed_bytes'], 12 * 4)
                self.assertEqual(half['inside_fixed_training_window'], 48)
                self.assertEqual(half['outside_fixed_training_window'], 0)
                self.assertEqual(half['fixed_window_share'], 1)

    def test_chunk_size_invariance(self):
        baseline = self.run_analysis()
        for size in (1, 13, 48, 69, 1024*1024):
            self.assertEqual(baseline, self.run_analysis(chunk=size))

    def test_shorter_periods_do_not_fit_as_well(self):
        result = self.run_analysis()
        self.assertEqual({item['relative_period'] for item in result['candidate_shorter_periods']}, {'1/2', '1/4'})
        for candidate in result['candidate_shorter_periods']:
            self.assertLess(candidate['best_train_share'], 1)

    def test_no_changes_is_not_success(self):
        self.contents = [self.contents[0]] * 3
        self.reset()
        result = self.run_analysis()
        for pair in result['pairwise']:
            for half in result['pairwise'][pair]:
                self.assertEqual(half['changed_bytes'], 0)
                self.assertIsNone(half['fixed_window_share'])

    def test_holdout_drift_is_detected(self):
        modified = bytearray(self.contents[2])
        for cycle in range(self.stride // 2, self.stride):
            for i in range(self.lines):
                modified[48 + cycle * self.period + (self.phase + i) % self.period] = 0
                modified[48 + cycle * self.period + (self.phase + i + 12) % self.period] = 255
        self.contents[2] = bytes(modified)
        self.reset()
        result = self.run_analysis()
        train, holdout = result['pairwise']['0_vs_100']
        self.assertEqual(train['fixed_window_share'], 1)
        self.assertEqual(holdout['fixed_window_share'], 0)
        self.assertNotEqual(holdout['best_phase_descriptive_only'], result['training_window_phase'])

    def test_modified_payload_rejected_by_digest(self):
        p = self.paths['white_100']
        b = bytearray(p.read_bytes())
        b[-1] ^= 1
        p.write_bytes(b)
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
            self.run_analysis()

    def test_wrong_file_size_rejected(self):
        p = self.paths['white_50']
        p.write_bytes(p.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, 'size'):
            self.run_analysis()

    def test_swapped_labels_rejected(self):
        self.paths['white_50'], self.paths['white_100'] = self.paths['white_100'], self.paths['white_50']
        with self.assertRaisesRegex(ValueError, 'Unexpected filename'):
            self.run_analysis()

    def test_geometry_tampered_but_digest_updated_rejected(self):
        p = self.paths['white_0']
        b = bytearray(p.read_bytes())
        struct.pack_into('<I', b, 12, self.lines + 1)
        p.write_bytes(b)
        self.reference['white_0']['sha256'] = hashlib.sha256(b).hexdigest()
        with self.assertRaisesRegex(ValueError, 'headers are not identical'):
            self.run_analysis()

    def test_invalid_chunk_bounds(self):
        for bad in (0, -1, 16 * 1024 * 1024 + 1):
            with self.assertRaisesRegex(ValueError, 'chunk size'):
                self.run_analysis(chunk=bad)

    def test_missing_label_rejected(self):
        del self.paths['white_100']
        with self.assertRaisesRegex(ValueError, 'operator-labelled'):
            self.run_analysis()

    def test_symlink_source_rejected(self):
        p = self.paths['white_100']
        new = self.root / 'source_real.prt'
        p.rename(new)
        try:
            p.symlink_to(new)
        except (OSError, NotImplementedError):
            self.skipTest('Symlinks unavailable')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.run_analysis()

    def test_hardlink_source_rejected(self):
        target = self.paths['white_100']
        target.unlink()
        try:
            os.link(self.paths['white_0'], target)
        except (OSError, NotImplementedError):
            self.skipTest('Hardlinks unavailable')
        self.reference['white_100']['sha256'] = self.reference['white_0']['sha256']
        with self.assertRaisesRegex(ValueError, 'Hardlink'):
            self.run_analysis()

    def test_tied_optimal_phase_is_reported_not_hidden(self):
        import numpy as np
        counts = np.array([0, 0, 0, 5, 0, 0, 0, 0], dtype=np.int64)
        self.assertEqual(_best_window(counts, 3)[0], 1)
        self.assertEqual(_optimal_phase_count(counts, 3), 3)
        self.assertGreaterEqual(self.run_analysis()['training_equally_optimal_phase_count'], 1)

    def test_no_file_bytes_in_output(self):
        result = self.run_analysis()
        self.assertNotIn('payload', result)
        self.assertNotIn('full_histograms', result)
        self.assertNotIn('mask_bytes', result)
        self.assertEqual(result['source_sha256']['white_100'], self.reference['white_100']['sha256'])

    def test_window_helper_tie_break_and_wrap(self):
        import numpy as np
        counts = np.array([1, 0, 0, 1, 1, 0], dtype=np.int64)
        self.assertEqual(_best_window(counts, 2), (3, 2))
        self.assertEqual(_at_phase(counts, 3, 5), 1)


if __name__ == '__main__':
    unittest.main()
