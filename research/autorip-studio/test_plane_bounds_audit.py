"""Synthetic and prior-aggregate regression checks (no proprietary PRT)."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from plane_bounds_audit import audit, main, EXPECTED_HASHES

EVIDENCE = Path(__file__).resolve().parent / 'real_mask_periodicity.json'


class PlaneBoundsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))

    def test_prior_aggregate_yields_stricter_lower_bound(self):
        result = audit(self.evidence)
        self.assertEqual(result['global_min_without_segment_counts'], 0)
        self.assertEqual(result['segment_informed_all_distinct_min'], 4)
        self.assertEqual(result['segment_informed_all_distinct_max'], 18514782)

    def test_four_odd_parity_segments(self):
        r = audit(self.evidence)
        self.assertEqual([s['candidate_segment'] for s in r['segments'] if s['parity'] == 'odd'], [2, 8, 10, 11])

    def test_hashes_are_provenance_only(self):
        r = audit(self.evidence)
        self.assertEqual(r['source_sha256'], EXPECTED_HASHES)
        self.assertIn('not freshly verified', r['limitations'][0])

    def test_wrong_source_hash_rejected(self):
        d = copy.deepcopy(self.evidence)
        d['source_sha256']['white_0'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Unexpected PRT source hashes'):
            audit(d)

    def test_wrong_schema_rejected(self):
        d = copy.deepcopy(self.evidence)
        d['schema'] = 'untrusted'
        with self.assertRaisesRegex(ValueError, 'Unsupported evidence schema'):
            audit(d)

    def test_inconsistent_total_rejected(self):
        d = copy.deepcopy(self.evidence)
        d['pair_results']['0_vs_50']['total_different_bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'Inconsistent aggregate totals'):
            audit(d)

    def test_negative_count_rejected(self):
        d = copy.deepcopy(self.evidence)
        d['pair_results']['0_vs_50']['different_bytes_by_candidate_plane'][0] = -1
        with self.assertRaisesRegex(ValueError, 'Invalid per-segment counts'):
            audit(d)

    def test_boolean_count_rejected(self):
        d = copy.deepcopy(self.evidence)
        d['pair_results']['0_vs_50']['different_bytes_by_candidate_plane'][0] = True
        with self.assertRaisesRegex(ValueError, 'Invalid per-segment counts'):
            audit(d)

    def test_missing_segment_rejected(self):
        d = copy.deepcopy(self.evidence)
        d['pair_results']['0_vs_50']['different_bytes_by_candidate_plane'].pop()
        with self.assertRaisesRegex(ValueError, 'Invalid per-segment counts'):
            audit(d)

    def test_output_helper_does_not_overwrite_existing(self):
        from safe_json_output import write_new_json
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'evidence.json'
            p.write_text('untouched', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                write_new_json(p, {'x': 1})
            self.assertEqual(p.read_text(), 'untouched')


if __name__ == '__main__':
    unittest.main()
