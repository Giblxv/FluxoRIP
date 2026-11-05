"""Synthetic CLI safety tests; no proprietary sample inputs."""
import hashlib
import json
import subprocess
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = ("white_0", "white_50", "white_100")

class VerifiedCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = {}
        self.expected = {}
        for i, label in enumerate(LABELS):
            p = self.root / (label + ".fixture")
            head = bytearray(48)
            struct.pack_into("<H", head, 0, 0x5555)
            struct.pack_into("<I", head, 12, 1)
            struct.pack_into("<I", head, 16, 4)
            struct.pack_into("<I", head, 28, 12)
            p.write_bytes(head + bytes([i, 0, 0, 0] * 12))
            self.paths[label] = p
            self.expected[label] = hashlib.sha256(p.read_bytes()).hexdigest()
        self.manifest = self.root / "manifest.json"
        self.output = self.root / "output.json"

    def run_cli(self):
        cmd = [sys.executable, str(ROOT / "verified_ternary.py")]
        for label in LABELS:
            cmd += ["--" + label.replace("_", "-"), str(self.paths[label])]
        cmd += ["--sha256-manifest", str(self.manifest), "--output", str(self.output)]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20)

    def test_good_manifest_writes_output(self):
        self.manifest.write_text(json.dumps(self.expected))
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(self.output.read_text())["provenance_status"], "matched_external_sha256_manifest")

    def test_bad_manifest_does_not_create_output(self):
        bad = dict(self.expected)
        bad["white_50"] = "0" * 64
        self.manifest.write_text(json.dumps(bad))
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_existing_output_not_overwritten(self):
        self.manifest.write_text(json.dumps(self.expected))
        self.output.write_text("sentinel")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.output.read_text(), "sentinel")

    def test_output_same_as_source_rejected(self):
        self.manifest.write_text(json.dumps(self.expected))
        self.output = self.paths["white_0"]
        before = self.output.read_bytes()
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.output.read_bytes(), before)

    def test_oversized_manifest_rejected(self):
        self.manifest.write_text(" " * 4097)
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_manifest_symlink_rejected(self):
        original = self.root / "actual_manifest.json"
        original.write_text(json.dumps(self.expected))
        try:
            self.manifest.symlink_to(original)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_output_same_as_manifest_rejected(self):
        self.manifest.write_text(json.dumps(self.expected))
        before = self.manifest.read_bytes()
        self.output = self.manifest
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.manifest.read_bytes(), before)


    def test_empty_manifest_rejected_without_output(self):
        self.manifest.write_bytes(b"")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_invalid_json_rejected_without_output(self):
        self.manifest.write_text("{not-valid-json", encoding="utf-8")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_extra_label_rejected_without_output(self):
        extra = dict(self.expected)
        extra["white_25"] = "0" * 64
        self.manifest.write_text(json.dumps(extra), encoding="utf-8")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_uppercase_digest_rejected_without_output(self):
        upper = dict(self.expected)
        upper["white_0"] = upper["white_0"].upper()
        self.manifest.write_text(json.dumps(upper), encoding="utf-8")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_existing_symlink_output_rejected_without_replacing_target(self):
        self.manifest.write_text(json.dumps(self.expected), encoding="utf-8")
        original = self.root / "original.json"
        original.write_text("sentinel", encoding="utf-8")
        try:
            self.output.symlink_to(original)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(original.read_text(encoding="utf-8"), "sentinel")

if __name__ == "__main__":
    unittest.main()
