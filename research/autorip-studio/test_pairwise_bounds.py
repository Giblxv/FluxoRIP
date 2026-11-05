import itertools
import unittest
from pairwise_bounds import equality_bounds


class BoundsTests(unittest.TestCase):
    def test_all_equal(self):
        r = equality_bounds(8, 0, 0, 0)
        self.assertEqual((r['all_distinct_min'], r['all_distinct_max']), (0, 0))

    def test_all_distinct_forced(self):
        r = equality_bounds(3, 3, 3, 3)
        self.assertEqual((r['all_distinct_min'], r['all_distinct_max']), (3, 3))

    def test_two_equal_forced(self):
        r = equality_bounds(3, 0, 3, 3)
        self.assertEqual((r['all_distinct_min'], r['all_distinct_max']), (0, 0))

    def test_ambiguous(self):
        r = equality_bounds(4, 2, 2, 2)
        self.assertEqual((r['all_distinct_min'], r['all_distinct_max']), (0, 2))

    def test_impossible_triangle(self):
        with self.assertRaisesRegex(ValueError, 'No feasible'):
            equality_bounds(10, 1, 1, 4)

    def test_negative(self):
        with self.assertRaises(ValueError):
            equality_bounds(5, -1, 0, 0)

    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            equality_bounds(5, 6, 0, 0)

    def test_bool_rejected(self):
        with self.assertRaises(TypeError):
            equality_bounds(True, 0, 0, 0)

    def test_exhaustive_small_triplets(self):
        # Exhaustively enumerate 3-byte alphabets for 2 positions.
        reachable = {}
        for values in itertools.product(range(3), repeat=6):
            triples = [values[:3], values[3:]]
            d = tuple(sum(t[i] != t[j] for t in triples)
                      for i, j in ((0, 1), (1, 2), (0, 2)))
            w = sum(len(set(t)) == 3 for t in triples)
            reachable.setdefault(d, set()).add(w)
        for d, expected in reachable.items():
            r = equality_bounds(2, *d)
            self.assertEqual(set(range(r['all_distinct_min'],
                                       r['all_distinct_max']+1, 2)), expected)

    def test_real_pairwise_counts_consistency(self):
        # Aggregate counts from the prior v0.71 evidence, not a new PRT scan.
        r = equality_bounds(265155120-48, 18519938, 18515358, 18520514)
        self.assertGreaterEqual(r['all_distinct_max'], r['all_distinct_min'])
        self.assertEqual(r['all_distinct_min'] % 2,
                         (18519938+18515358+18520514) % 2)


if __name__ == '__main__':
    unittest.main()
