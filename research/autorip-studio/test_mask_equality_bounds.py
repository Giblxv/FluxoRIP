import copy
import json
import tempfile
import unittest
from pathlib import Path

from mask_equality_bounds import tighten


class MaskEqualityBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads((Path(__file__).parent / 'real_mask_periodicity.json').read_text())

    def test_real_derived_interior_exact(self):
        result = tighten(self.evidence)
        expected = self.evidence['pair_results']['50_vs_100']['different_bytes_by_candidate_plane']
        for i in range(1, 11):
            self.assertEqual(result['segments'][i]['all_distinct_min'], expected[i])
            self.assertEqual(result['segments'][i]['all_distinct_max'], expected[i])

    def test_real_derived_global_bounds(self):
        result = tighten(self.evidence)
        self.assertEqual(result['all_distinct_min'], 18369528)
        self.assertEqual(result['all_distinct_max'], 18514782)

    def test_edges_remain_uncertain(self):
        result = tighten(self.evidence)
        self.assertEqual(result['segments'][0]['inference'], 'aggregate_counts_only')
        self.assertEqual(result['segments'][11]['inference'], 'aggregate_counts_only')

    def test_reject_forged_equal_digest_with_different_counts(self):
        data = copy.deepcopy(self.evidence)
        data['pair_results']['0_vs_100']['difference_mask_sha256_by_candidate_plane'][0] = data['pair_results']['0_vs_50']['difference_mask_sha256_by_candidate_plane'][0]
        with self.assertRaisesRegex(ValueError, 'unequal counts'):
            tighten(data)

    def test_reject_invalid_digest(self):
        data = copy.deepcopy(self.evidence)
        data['pair_results']['0_vs_100']['difference_mask_sha256_by_candidate_plane'][0] = 'bad'
        with self.assertRaisesRegex(ValueError, 'Invalid SHA'):
            tighten(data)


if __name__ == '__main__':
    unittest.main()