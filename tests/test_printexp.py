"""Synthetic TSKF records only. Proprietary samples stay outside version control."""

import hashlib
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TEST_DATA = tempfile.TemporaryDirectory(prefix="fluxo-printexp-tests-")
os.environ.setdefault("FORGE_DATA_DIR", _TEST_DATA.name)
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.printexp import (
    FileEvidenceError,
    PrintExpRequest,
    parse_tasks,
    read_source,
    snapshot,
)


def task_file(count=1, version=24, filename="teste-ação.PRT", encoding="utf-8"):
    def field(value):
        raw = value.encode(encoding) + b"\0"
        return struct.pack("<I", len(raw)) + raw

    record = (
        struct.pack("<I", 123)
        + b"".join(
            field(s)
            for s in (filename, "(null)", "C:\\privado\\" + filename, filename + ".bmp")
        )
        + b"opaque-synthetic-tail"
    )
    return (
        b"TSKF"
        + struct.pack("<II", version, count)
        + (struct.pack("<I", len(record)) + record) * count
    )


class PrintExpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="printexp-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "Data").mkdir()
        (self.root / "Project.ini").write_text(
            "// separator\n[COMM_CONFIG]\nCOMM_MODULE=1\nServerIP=secret-IP\n"
            "[PLATFORM_CONFIG]\nENABLE=0\nSECRET=do-not-return\n",
            encoding="utf-8",
        )
        for name in ("fileTask.tf", "printTask.tf", "HistoryTask.tf", "recordTask.tf"):
            (self.root / "Data" / name).write_bytes(task_file(2))
        self.client.put("/api/studio/printexp", json={"enabled": False})
        self.addCleanup(
            lambda: self.client.put("/api/studio/printexp", json={"enabled": False})
        )

    def link(self):
        return self.client.put(
            "/api/studio/printexp", json={"enabled": True, "folder": str(self.root)}
        )

    def test_reads_counts_names_and_config_without_mutating_source(self):
        before = {
            p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in self.root.rglob("*")
            if p.is_file()
        }
        # No device code may run during this integration.
        with (
            patch("socket.socket", side_effect=AssertionError("No sockets")),
            patch("subprocess.Popen", side_effect=AssertionError("No process")),
        ):
            snapshot(PrintExpRequest(enabled=True, folder=str(self.root)))
        response = self.link()
        self.assertEqual(response.status_code, 200, response.text)
        result = self.client.get("/api/studio/printexp")
        data = result.json()
        self.assertEqual(result.headers["cache-control"], "no-store")
        self.assertEqual(data["mode"], "observe_only")
        self.assertEqual(data["machine_status"], "NAO_VERIFICADO")
        self.assertFalse(data["can_submit"])
        self.assertFalse(data["configuration"]["platform_enabled"])
        self.assertTrue(all(s["count"] == 2 for s in data["sources"]))
        self.assertTrue(
            all(s["items"][0]["filename"] == "teste-ação.PRT" for s in data["sources"])
        )
        self.assertNotIn("privado", result.text)
        self.assertNotIn("secret-IP", result.text)
        self.assertNotIn("do-not-return", result.text)
        after = {
            p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in self.root.rglob("*")
            if p.is_file()
        }
        self.assertEqual(before, after)

    def test_disabled_never_reads_or_retains_path(self):
        self.link()
        self.client.put(
            "/api/studio/printexp", json={"enabled": False, "folder": "ignored"}
        )
        with patch("app.printexp.read_source", side_effect=AssertionError("No reads")):
            data = self.client.get("/api/studio/printexp").json()
        self.assertEqual(data["settings"], {"enabled": False, "folder": ""})
        self.assertEqual(data["sources"], [])

    def test_bad_input_and_unsupported_format_are_not_accepted_as_tasks(self):
        good = task_file()
        for raw in (
            b"",
            b"wrong",
            good[:-1],
            good + b"extra",
            task_file(version=25),
            b"TSKF" + struct.pack("<II", 24, 10001),
            good[:12] + struct.pack("<I", 0),
            good[:20] + struct.pack("<I", 9000) + good[24:],
        ):
            with self.subTest(raw=raw[:24]), self.assertRaises(FileEvidenceError):
                parse_tasks(raw)
        self.assertEqual(parse_tasks(task_file(0))["count"], 0)
        data = parse_tasks(task_file(100))
        self.assertEqual(data["count"], 100)
        self.assertEqual(data["shown"], 30)
        self.assertEqual(
            parse_tasks(task_file(encoding="cp1252"))["items"][0]["filename"],
            "teste-ação.PRT",
        )

    def test_independent_failures_and_live_refresh(self):
        self.link()
        (self.root / "Data/printTask.tf").write_bytes(task_file(version=25))
        (self.root / "Data/recordTask.tf").unlink()
        data = self.client.get("/api/studio/printexp").json()
        self.assertEqual(
            [s["state"] for s in data["sources"]],
            ["LIDO", "INDISPONIVEL", "LIDO", "INDISPONIVEL"],
        )
        (self.root / "Data/printTask.tf").write_bytes(task_file(3))
        self.assertEqual(
            self.client.get("/api/studio/printexp").json()["sources"][1]["count"], 3
        )
        (self.root / "Project.ini").write_bytes(b"invalid")
        self.assertTrue(self.client.get("/api/studio/printexp").json()["issues"])

    def test_path_and_origin_validation(self):
        for path in ("relative", str(self.root / "missing"), str(self.root / "Data")):
            response = self.client.put(
                "/api/studio/printexp", json={"enabled": True, "folder": path}
            )
            self.assertEqual(response.status_code, 422, response.text)
        response = self.client.put(
            "/api/studio/printexp",
            json={"enabled": True, "folder": str(self.root)},
            headers={"Origin": "https://outside.example"},
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.put(
            "/api/studio/printexp",
            json={"enabled": True, "folder": str(self.root), "submit": True},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.post("/api/studio/printexp/print", json={}).status_code, 404
        )

    def test_read_limits_links_and_changed_files(self):
        with self.assertRaises(FileEvidenceError):
            read_source(self.root, "Project.ini", 4)
        with self.assertRaises(FileEvidenceError):
            read_source(self.root, "../outside", 4)
        source = self.root / "Data/printTask.tf"
        source.unlink()
        try:
            source.symlink_to(self.root / "Data/fileTask.tf")
        except (OSError, NotImplementedError):
            pass  # Windows without symlink privilege still runs remaining guards.
        else:
            with self.assertRaises(FileEvidenceError):
                read_source(self.root, "Data/printTask.tf", 10000)
        actual = os.fstat

        def changed(fd):
            value = actual(fd)
            fake = type("Changed", (), {})()
            for k in ("st_dev", "st_ino", "st_size", "st_mtime_ns"):
                setattr(fake, k, getattr(value, k))
            fake.st_size += 1
            return fake

        with (
            patch("app.printexp.os.fstat", side_effect=changed),
            self.assertRaises(FileEvidenceError),
        ):
            read_source(self.root, "Project.ini", 10000)
