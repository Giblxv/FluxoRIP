"""Synthetic-only controlled capture tests (no proprietary data or printing)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from controlled_capture import (
    ARTWORKS, EXPECTED, load_plan, template, validate_plan,
    verify_capture_set,
)

MODULE = Path(__file__).with_name("controlled_capture.py")


class ControlledCaptureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.samples_dir = self.root / "samples"
        self.samples_dir.mkdir()
        self.plan = template("study_001")
        self.plan["common_config_sha256"] = hashlib.sha256(b"controlled-config").hexdigest()
        self.plan["artworks"] = {
            art: hashlib.sha256(("artwork-source:" + art).encode()).hexdigest()
            for art in ARTWORKS
        }
        for sample in self.plan["samples"]:
            # Exact rerip at 50: same bytes in a separate independently created file.
            payload = (sample["artwork"] + "::" + sample["level"]).encode() * 16
            p = self.samples_dir / sample["filename"]
            p.write_bytes(payload)
            sample["size_bytes"] = len(payload)
            sample["sha256"] = hashlib.sha256(payload).hexdigest()

    def find(self, art, level, rep=1):
        return next(s for s in self.plan["samples"] if
                    (s["artwork"], s["level"], s["replicate"]) == (art, level, rep))

    def change_file_and_attest(self, sample, data):
        path = self.samples_dir / sample["filename"]
        path.write_bytes(data)
        sample["size_bytes"] = len(data)
        sample["sha256"] = hashlib.sha256(data).hexdigest()

    def test_template_has_twelve_unfilled_capture_slots(self):
        stub = template()
        self.assertEqual(len(stub["samples"]), 12)
        self.assertEqual(
            {(s["artwork"], s["level"], s["replicate"]) for s in stub["samples"]}, EXPECTED)
        with self.assertRaisesRegex(ValueError, "configuration"):
            validate_plan(stub)

    def test_all_twelve_cryptographically_verified(self):
        report = verify_capture_set(self.plan, self.samples_dir, chunk_bytes=11)
        self.assertEqual(report["verified_file_count"], 12)
        self.assertEqual(report["verified_total_bytes"], sum(s["size_bytes"] for s in self.plan["samples"]))
        self.assertTrue(report["sha256_agrees_with_operator_supplied_manifest"])
        for art in ARTWORKS:
            self.assertTrue(report["same_setting_reexport_and_level_checks"][art]["white_50_reexport_byte_identical"])
        self.assertEqual(report["warnings"], [])

    def test_source_bytes_are_never_modified(self):
        original = {p.name: p.read_bytes() for p in self.samples_dir.iterdir()}
        verify_capture_set(self.plan, self.samples_dir)
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.samples_dir.iterdir()})

    def test_repeatability_failure_is_reported_not_hidden(self):
        rec = self.find("art_b", "white_50", 2)
        self.change_file_and_attest(rec, b"independent-rerip-differs" * 5)
        report = verify_capture_set(self.plan, self.samples_dir)
        self.assertFalse(report["same_setting_reexport_and_level_checks"]["art_b"]["white_50_reexport_byte_identical"])
        self.assertTrue(any("art_b: identical operator settings" in w for w in report["warnings"]))

    def test_equal_white_levels_are_flagged_not_assumed_effective(self):
        source = self.find("art_b", "white_0")
        rec = self.find("art_b", "white_100")
        self.change_file_and_attest(rec, (self.samples_dir / source["filename"]).read_bytes())
        report = verify_capture_set(self.plan, self.samples_dir)
        self.assertTrue(report["same_setting_reexport_and_level_checks"]["art_b"]["level_pairwise_byte_identical"]["0_equals_100"])
        self.assertTrue(any("art_b: one or more" in w for w in report["warnings"]))

    def test_changed_payload_rejected(self):
        rec = self.find("art_c", "white_100")
        path = self.samples_dir / rec["filename"]
        payload = bytearray(path.read_bytes())
        payload[-1] ^= 1  # one-byte mutation, same size: specifically test SHA-256 gate
        path.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_capture_set(self.plan, self.samples_dir)

    def test_shortened_capture_rejected(self):
        rec = self.find("art_a", "white_0")
        (self.samples_dir / rec["filename"]).write_bytes(b"short")
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            verify_capture_set(self.plan, self.samples_dir)

    def test_swapped_condition_hashes_rejected(self):
        left = self.find("art_a", "white_0")
        right = self.find("art_a", "white_100")
        left["sha256"], right["sha256"] = right["sha256"], left["sha256"]
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_capture_set(self.plan, self.samples_dir)

    def test_duplicate_condition_rejected(self):
        self.plan["samples"][1]["artwork"] = self.plan["samples"][0]["artwork"]
        self.plan["samples"][1]["level"] = self.plan["samples"][0]["level"]
        self.plan["samples"][1]["replicate"] = self.plan["samples"][0]["replicate"]
        with self.assertRaisesRegex(ValueError, "repeated"):
            validate_plan(self.plan)

    def test_missing_capture_rejected(self):
        self.plan["samples"].pop()
        with self.assertRaisesRegex(ValueError, "twelve"):
            validate_plan(self.plan)

    def test_malformed_digest_rejected(self):
        self.find("art_a", "white_0")["sha256"] = "NOT_A_SHA256"
        with self.assertRaisesRegex(ValueError, "independent capture"):
            validate_plan(self.plan)

    def test_artworks_must_be_distinct(self):
        self.plan["artworks"]["art_b"] = self.plan["artworks"]["art_a"]
        with self.assertRaisesRegex(ValueError, "distinct"):
            validate_plan(self.plan)

    def test_path_traversal_rejected(self):
        self.find("art_a", "white_0")["filename"] = "../secrets.PRT"
        with self.assertRaisesRegex(ValueError, "Unsafe capture filename"):
            validate_plan(self.plan)

    def test_case_insensitive_duplicate_filenames_rejected(self):
        self.plan["samples"][1]["filename"] = self.plan["samples"][0]["filename"].lower()
        with self.assertRaisesRegex(ValueError, "Repeated PRT filename"):
            validate_plan(self.plan)

    def test_symlink_sample_rejected(self):
        rec = self.find("art_c", "white_100")
        path = self.samples_dir / rec["filename"]
        original = self.samples_dir / "original_data.tmp"
        path.rename(original)
        try:
            path.symlink_to(original)
        except (NotImplementedError, OSError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            verify_capture_set(self.plan, self.samples_dir)

    def test_hardlink_alias_rejected(self):
        a = self.find("art_a", "white_0")
        b = self.find("art_a", "white_50", 1)
        target = self.samples_dir / b["filename"]
        target.unlink()
        try:
            os.link(self.samples_dir / a["filename"], target)
        except (NotImplementedError, OSError):
            self.skipTest("Hardlinks unavailable")
        b["size_bytes"] = a["size_bytes"]
        b["sha256"] = a["sha256"]
        with self.assertRaisesRegex(ValueError, "hardlink alias"):
            verify_capture_set(self.plan, self.samples_dir)

    def test_manifest_duplicate_json_key_rejected(self):
        path = self.root / "plan.json"
        path.write_text('{"schema": 1, "schema": 2}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            load_plan(path)

    def test_manifest_symlink_rejected(self):
        original = self.root / "actual_plan.json"
        original.write_text(json.dumps(self.plan), encoding="utf-8")
        alias = self.root / "alias_plan.json"
        try:
            alias.symlink_to(original)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises((ValueError, OSError)):
            load_plan(alias)

    def test_manifest_size_limit(self):
        huge = self.root / "manifest.json"
        huge.write_bytes(b"x" * 65537)
        with self.assertRaisesRegex(ValueError, "65536"):
            load_plan(huge)

    def test_report_has_no_raw_bytes_or_artwork_fingerprints(self):
        report = verify_capture_set(self.plan, self.samples_dir)
        as_json = json.dumps(report)
        self.assertNotIn(self.plan["artworks"]["art_a"], as_json)
        self.assertNotIn("payload", as_json)
        self.assertNotIn("sample_directory", as_json)

    def test_chunk_sizes_invariant(self):
        a = verify_capture_set(self.plan, self.samples_dir, chunk_bytes=1)
        b = verify_capture_set(self.plan, self.samples_dir, chunk_bytes=4096)
        self.assertEqual(a, b)

    def test_invalid_chunk_size_rejected(self):
        for chunk in (0, -1, 8 * 1024 * 1024 + 1):
            with self.assertRaisesRegex(ValueError, "chunk size"):
                verify_capture_set(self.plan, self.samples_dir, chunk_bytes=chunk)

    def test_cli_verifies_and_writes_only_new_output(self):
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        report_path = self.root / "report.json"
        cmd = [sys.executable, str(MODULE), "verify", "--manifest", str(plan_path),
               "--directory", str(self.samples_dir), "--output", str(report_path)]
        first = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(report_path.read_text())["verified_file_count"], 12)
        second = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(json.loads(report_path.read_text())["verified_file_count"], 12)

    def test_cli_template_emits_unverified_skeleton(self):
        path = self.root / "new_plan.json"
        run = subprocess.run([sys.executable, str(MODULE), "template",
                              "--experiment-id", "Pilot_002", "--output", str(path)],
                             capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(path.read_text())["experiment_id"], "Pilot_002")
        with self.assertRaisesRegex(ValueError, "configuration"):
            validate_plan(json.loads(path.read_text()))



    def test_boolean_replicate_rejected_instead_of_equating_true_to_one(self):
        self.plan["samples"][0]["replicate"] = True
        with self.assertRaisesRegex(ValueError, "exact types"):
            validate_plan(self.plan)

    def test_string_replicate_rejected(self):
        self.plan["samples"][0]["replicate"] = "1"
        with self.assertRaisesRegex(ValueError, "exact types"):
            validate_plan(self.plan)

    def test_condition_names_cannot_be_swapped_with_hashes(self):
        first = self.plan["samples"][0]
        second = self.plan["samples"][1]
        first["filename"], second["filename"] = second["filename"], first["filename"]
        with self.assertRaisesRegex(ValueError, "does not match declared capture"):
            validate_plan(self.plan)

    def test_filename_casing_is_allowed_but_condition_binding_is_strict(self):
        self.plan["samples"][0]["filename"] = self.plan["samples"][0]["filename"].upper()
        self.assertIs(validate_plan(self.plan), self.plan)

if __name__ == "__main__":
    unittest.main()
