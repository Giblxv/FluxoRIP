"""Synthetic-only preregistered PRT replication checks; no printer or vendor bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from controlled_capture import ARTWORKS, template
from prospective_periodicity import analyze, PERIOD, PHASE, WINDOW

MODULE = Path(__file__).with_name("prospective_periodicity.py")


class ProspectiveReplicationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.samples = self.root / "samples"
        self.samples.mkdir()
        self.plan = template("prospective_pilot_001")
        self.plan["common_config_sha256"] = hashlib.sha256(b"fixed synthetic config").hexdigest()
        self.plan["artworks"] = {
            art: hashlib.sha256(("independent art " + art).encode()).hexdigest()
            for art in ARTWORKS
        }
        self.phases = {art: PHASE for art in ARTWORKS}
        self._regenerate()

    def _record(self, art, level, replicate=1):
        return next(r for r in self.plan["samples"] if
                    (r["artwork"], r["level"], r["replicate"]) == (art, level, replicate))

    def _save(self, record, raw):
        file = self.samples / record["filename"]
        file.write_bytes(raw)
        record["size_bytes"] = len(raw)
        record["sha256"] = hashlib.sha256(raw).hexdigest()

    def _regenerate(self, *, stride=3):
        for idx, art in enumerate(ARTWORKS):
            header = bytearray(48)
            struct.pack_into("<H", header, 0, 0x5555)
            struct.pack_into("<I", header, 12, WINDOW)
            struct.pack_into("<I", header, 16, stride)
            struct.pack_into("<I", header, 28, 12)
            phase = self.phases[art]
            base = 5 + 6 * idx
            for level, replicate in (("white_0", 1), ("white_50", 1),
                                     ("white_100", 1), ("white_50", 2)):
                payload = bytearray([base] * (PERIOD * stride))
                if level != "white_0":
                    new_value = 75 + 6 * idx if level == "white_50" else 170 + 6 * idx
                    for cycle in range(stride):
                        start = cycle * PERIOD
                        for p in range(phase, phase + WINDOW):
                            payload[start + (p % PERIOD)] = new_value
                self._save(self._record(art, level, replicate), bytes(header + payload))

    def result(self, *, chunk=1024 * 1024):
        return analyze(self.plan, self.samples, chunk_bytes=chunk)

    def test_all_artworks_match_locked_phase_when_synthetic(self):
        report = self.result()
        self.assertEqual(report["verified_capture_count"], 12)
        self.assertEqual(report["locked_candidate"]["period_bytes"], 17472)
        self.assertEqual(report["locked_candidate"]["phase_bytes"], PHASE)
        self.assertEqual(report["locked_candidate"]["uniform_reference_share"], 1/12)
        for art in ARTWORKS:
            rec = report["artworks"][art]
            self.assertEqual(rec["status"], "descriptive_only_no_ink_inference")
            self.assertTrue(rec["white_50_reexport_byte_identical"])
            for pair in ("0_vs_50", "50_vs_100", "0_vs_100"):
                comparison = rec["comparisons"][pair]
                self.assertEqual(comparison["locked_window_share"], 1)
                self.assertEqual(comparison["outside_locked_window"], 0)
            self.assertEqual(rec["comparisons"]["50_reexport"]["changed_bytes"], 0)
            self.assertIsNone(rec["comparisons"]["50_reexport"]["locked_window_share"])

    def test_locked_phase_never_refitted_on_shifted_artwork(self):
        self.phases["art_c"] = (PHASE + 4000) % PERIOD
        self._regenerate()
        report = self.result()
        self.assertEqual(report["artworks"]["art_c"]["comparisons"]["0_vs_100"]["locked_window_share"], 0)
        self.assertEqual(report["artworks"]["art_a"]["comparisons"]["0_vs_100"]["locked_window_share"], 1)
        self.assertEqual(report["locked_candidate"]["phase_bytes"], PHASE)

    def test_repeatability_change_is_explicitly_confounded(self):
        rec = self._record("art_b", "white_50", 2)
        path = self.samples / rec["filename"]
        payload = bytearray(path.read_bytes())
        payload[-1] ^= 1
        self._save(rec, bytes(payload))
        report = self.result()
        self.assertEqual(report["artworks"]["art_b"]["status"], "repeatability_confounded")
        self.assertEqual(report["artworks"]["art_b"]["comparisons"]["50_reexport"]["changed_bytes"], 1)
        self.assertFalse(report["artworks"]["art_b"]["white_50_reexport_byte_identical"])
        self.assertTrue(report["reexport_warnings"])

    def test_no_white_level_difference_is_not_counted_as_support(self):
        white0 = (self.samples / self._record("art_b", "white_0")["filename"]).read_bytes()
        for level, replicate in (("white_50", 1), ("white_50", 2), ("white_100", 1)):
            self._save(self._record("art_b", level, replicate), white0)
        report = self.result()
        self.assertEqual(report["artworks"]["art_b"]["status"], "no_level_difference_observed")
        self.assertIsNone(report["artworks"]["art_b"]["comparisons"]["0_vs_100"]["locked_window_share"])

    def test_candidate_geometry_mismatch_is_not_evaluable(self):
        for level, replicate in (("white_0", 1), ("white_50", 1),
                                 ("white_100", 1), ("white_50", 2)):
            rec = self._record("art_c", level, replicate)
            raw = bytearray((self.samples / rec["filename"]).read_bytes())
            struct.pack_into("<I", raw, 12, WINDOW + 1)
            self._save(rec, bytes(raw))
        report = self.result()
        self.assertEqual(report["artworks"]["art_c"]["status"], "not_evaluable")
        self.assertEqual(report["artworks"]["art_c"]["reason"], "does_not_match_locked_candidate_geometry")
        self.assertEqual(report["artworks"]["art_a"]["status"], "descriptive_only_no_ink_inference")

    def test_header_mismatch_is_not_evaluable(self):
        rec = self._record("art_a", "white_50", 2)
        raw = bytearray((self.samples / rec["filename"]).read_bytes())
        raw[6] ^= 1
        self._save(rec, bytes(raw))
        report = self.result()
        self.assertEqual(report["artworks"]["art_a"]["status"], "not_evaluable")
        self.assertEqual(report["artworks"]["art_a"]["reason"], "headers_not_identical")

    def test_bad_signature_is_not_evaluable(self):
        for level, replicate in (("white_0", 1), ("white_50", 1),
                                 ("white_100", 1), ("white_50", 2)):
            rec = self._record("art_a", level, replicate)
            raw = bytearray((self.samples / rec["filename"]).read_bytes())
            raw[0:2] = b"\x00\x00"
            self._save(rec, bytes(raw))
        report = self.result()
        self.assertEqual(report["artworks"]["art_a"]["status"], "not_evaluable")
        self.assertEqual(report["artworks"]["art_a"]["reason"], "does_not_match_locked_candidate_geometry")

    def test_tampered_file_without_new_hash_rejected(self):
        rec = self._record("art_a", "white_100")
        path = self.samples / rec["filename"]
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 1
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.result()

    def test_truncated_file_rejected(self):
        rec = self._record("art_a", "white_0")
        path = self.samples / rec["filename"]
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            self.result()

    def test_distinct_chunk_sizes_produce_identical_results(self):
        base = self.result()
        for chunk in (137, 4096, 32768):
            self.assertEqual(base, self.result(chunk=chunk))

    def test_invalid_chunk_size_rejected(self):
        for chunk in (-1, 0, 8 * 1024 * 1024 + 1):
            with self.assertRaisesRegex(ValueError, "chunk size"):
                self.result(chunk=chunk)

    def test_samples_not_modified(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.samples.iterdir()}
        self.result()
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.samples.iterdir()}
        self.assertEqual(before, after)

    def test_aggregate_output_contains_no_source_data(self):
        report = self.result()
        output = json.dumps(report)
        self.assertNotIn("source_sha256", output)
        self.assertNotIn(self.plan["artworks"]["art_a"], output)
        self.assertNotIn("raw_payload", output)
        self.assertNotIn(str(self.samples), output)

    def test_output_rejects_existing_report_and_preserves_it(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(self.plan), encoding="utf-8")
        output = self.root / "report.json"
        output.write_text("SENTINEL", encoding="utf-8")
        cmd = [sys.executable, str(MODULE), "--manifest", str(manifest),
               "--directory", str(self.samples), "--output", str(output)]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(output.read_text(), "SENTINEL")

    def test_cli_output_cannot_replace_a_source(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(self.plan), encoding="utf-8")
        source = self.samples / self._record("art_b", "white_100")["filename"]
        before = source.read_bytes()
        cmd = [sys.executable, str(MODULE), "--manifest", str(manifest),
               "--directory", str(self.samples), "--output", str(source)]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(source.read_bytes(), before)

    def test_cli_output_cannot_replace_manifest(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(self.plan), encoding="utf-8")
        before = manifest.read_bytes()
        cmd = [sys.executable, str(MODULE), "--manifest", str(manifest),
               "--directory", str(self.samples), "--output", str(manifest)]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(manifest.read_bytes(), before)

    def test_cli_creates_new_json(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(self.plan), encoding="utf-8")
        output = self.root / "new_report.json"
        cmd = [sys.executable, str(MODULE), "--manifest", str(manifest),
               "--directory", str(self.samples), "--output", str(output)]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(output.read_text())["verified_capture_count"], 12)


if __name__ == "__main__":
    unittest.main()
