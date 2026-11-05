"""Controlled comparison tests, tiny synthetic files; no production formats generated."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from prt_white_experiment import analyze_white_levels
from test_prt_diff import fixture


class ExperimentTests(unittest.TestCase):
    def three(self, folder, *, slots=12, rows=3, stride=4):
        paths = {k: Path(folder)/(k+'.bin') for k in ('white_0','white_50','white_100')}
        fixture(paths['white_0'],rows=rows,slots=slots,stride=stride)
        fixture(paths['white_50'],rows=rows,slots=slots,stride=stride,edits=[(48+8,1)])
        fixture(paths['white_100'],rows=rows,slots=slots,stride=stride,edits=[(48+8,2),(48+16,3)])
        return paths

    def test_pairwise_differences_and_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.three(folder)
            original={key:p.read_bytes() for key,p in paths.items()}
            result=analyze_white_levels(paths,block_size=3)
            self.assertEqual(result['candidate_geometry']['slots'],12)
            self.assertEqual(result['candidate_geometry']['expected_bytes'],48+3*12*4)
            for label,p in paths.items():
                self.assertEqual(result['sources'][label]['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
            for pair_name, expected in [('white_0_vs_white_50',1),
                                        ('white_50_vs_white_100',2),
                                        ('white_0_vs_white_100',2)]:
                pair=result['pairwise'][pair_name]
                for layout in pair['candidate_layouts'].values():
                    self.assertEqual(layout['total_changed_bytes'],expected)
            self.assertEqual(original,{key:p.read_bytes() for key,p in paths.items()})
            self.assertEqual(result['color_channel_mapping'],'unverified')

    def test_reject_non_twelve_slots(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'exactly 12'):
                analyze_white_levels(self.three(folder,slots=11))

    def test_reject_different_geometry(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.three(folder)
            fixture(paths['white_100'],rows=4,slots=12,stride=4)
            with self.assertRaisesRegex(ValueError,'identical candidate geometry'):
                analyze_white_levels(paths)

    def test_reject_duplicate_source_path(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.three(folder)
            paths['white_50']=paths['white_0']
            with self.assertRaisesRegex(ValueError,'different original file'):
                analyze_white_levels(paths)

    def test_reject_missing_label(self):
        with self.assertRaisesRegex(ValueError,'Required labels'):
            analyze_white_levels({'white_0':'a','white_50':'b'})


if __name__=='__main__':
    unittest.main()
